#!/usr/bin/env python3
"""
health_check.py — Docker Container / Service Health Checker

Checks the health of a running Docker container or HTTP service and
produces a structured health report.

Checks performed:
  - HTTP health endpoint (status code, response time)
  - Docker container status (running, healthy, restart count)
  - Resource usage (CPU %, memory usage/limit)
  - Container uptime and image info

Usage:
    # Check by HTTP URL
    python health_check.py --url http://localhost:3000/health

    # Check by Docker container name or ID
    python health_check.py --container myapp-api

    # Check both (URL for HTTP health, container for Docker stats)
    python health_check.py --url http://localhost:3000/health --container myapp-api

    # Output as JSON
    python health_check.py --container myapp-api --format json

    # Set custom thresholds
    python health_check.py --container myapp-api --cpu-warn 70 --mem-warn 80
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HttpCheck:
    url: str = ""
    status_code: int = 0
    response_time_ms: float = 0.0
    healthy: bool = False
    error: str = ""
    body_preview: str = ""


@dataclass
class ContainerCheck:
    container_id: str = ""
    name: str = ""
    image: str = ""
    status: str = ""
    health_status: str = ""
    running: bool = False
    restart_count: int = 0
    uptime: str = ""
    started_at: str = ""
    ports: str = ""
    error: str = ""


@dataclass
class ResourceCheck:
    cpu_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_limit_mb: float = 0.0
    memory_percent: float = 0.0
    network_rx_mb: float = 0.0
    network_tx_mb: float = 0.0
    pids: int = 0
    error: str = ""


@dataclass
class HealthReport:
    timestamp: str = ""
    overall_status: str = HealthStatus.UNKNOWN.value
    http: HttpCheck | None = None
    container: ContainerCheck | None = None
    resources: ResourceCheck | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Thresholds:
    http_timeout_s: float = 5.0
    http_slow_ms: float = 1000.0
    cpu_warn_percent: float = 80.0
    cpu_critical_percent: float = 95.0
    mem_warn_percent: float = 80.0
    mem_critical_percent: float = 95.0
    restart_warn: int = 3
    restart_critical: int = 10


# ---------------------------------------------------------------------------
# HTTP Health Check
# ---------------------------------------------------------------------------


def check_http(url: str, timeout: float = 5.0) -> HttpCheck:
    """Perform an HTTP health check against the given URL."""
    result = HttpCheck(url=url)

    try:
        start = time.monotonic()
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "health-check/1.0")
        req.add_header("Accept", "application/json, text/plain")

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = (time.monotonic() - start) * 1000
            result.status_code = resp.status
            result.response_time_ms = round(elapsed, 2)
            body = resp.read(1024).decode("utf-8", errors="replace")
            result.body_preview = body[:200]
            result.healthy = 200 <= resp.status < 300

    except urllib.error.HTTPError as e:
        elapsed = (time.monotonic() - start) * 1000
        result.status_code = e.code
        result.response_time_ms = round(elapsed, 2)
        result.healthy = False
        result.error = f"HTTP {e.code}: {e.reason}"

    except urllib.error.URLError as e:
        result.healthy = False
        result.error = f"Connection failed: {e.reason}"

    except Exception as e:
        result.healthy = False
        result.error = str(e)

    return result


# ---------------------------------------------------------------------------
# Docker Container Check
# ---------------------------------------------------------------------------


def _run_docker(args: list[str]) -> tuple[str, str, int]:
    """Run a docker command and return (stdout, stderr, returncode)."""
    try:
        proc = subprocess.run(
            ["docker"] + args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except FileNotFoundError:
        return "", "Docker CLI not found. Is Docker installed?", 1
    except subprocess.TimeoutExpired:
        return "", "Docker command timed out", 1


def check_container(name_or_id: str) -> ContainerCheck:
    """Check Docker container status and metadata."""
    result = ContainerCheck()

    # Use docker inspect to get detailed container info
    inspect_format = (
        '{"id":"{{.Id}}",'
        '"name":"{{.Name}}",'
        '"image":"{{.Config.Image}}",'
        '"status":"{{.State.Status}}",'
        '"health":"{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",'
        '"running":{{.State.Running}},'
        '"restarts":{{.RestartCount}},'
        '"started":"{{.State.StartedAt}}",'
        '"ports":"{{range $p, $conf := .NetworkSettings.Ports}}{{$p}}->{{range $conf}}{{.HostIp}}:{{.HostPort}}{{end}} {{end}}"}'
    )

    stdout, stderr, rc = _run_docker(["inspect", "--format", inspect_format, name_or_id])

    if rc != 0:
        result.error = stderr or f"Container '{name_or_id}' not found"
        return result

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        result.error = f"Failed to parse container info: {stdout}"
        return result

    result.container_id = data.get("id", "")[:12]
    result.name = data.get("name", "").lstrip("/")
    result.image = data.get("image", "")
    result.status = data.get("status", "")
    result.health_status = data.get("health", "none")
    result.running = data.get("running", False)
    result.restart_count = data.get("restarts", 0)
    result.started_at = data.get("started", "")
    result.ports = data.get("ports", "").strip()

    # Calculate uptime
    if result.started_at and result.running:
        try:
            # Docker uses RFC3339 format
            started = result.started_at.split(".")[0]
            if started.endswith("Z"):
                started = started[:-1]
            start_dt = datetime.fromisoformat(started).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - start_dt
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours >= 24:
                days = hours // 24
                hours = hours % 24
                result.uptime = f"{days}d {hours}h {minutes}m"
            else:
                result.uptime = f"{hours}h {minutes}m {seconds}s"
        except (ValueError, TypeError):
            result.uptime = "unknown"

    return result


# ---------------------------------------------------------------------------
# Resource Usage Check
# ---------------------------------------------------------------------------


def check_resources(name_or_id: str) -> ResourceCheck:
    """Check container resource usage (CPU, memory, network, PIDs)."""
    result = ResourceCheck()

    # docker stats --no-stream gives a single snapshot
    stdout, stderr, rc = _run_docker([
        "stats", "--no-stream", "--format",
        '{"cpu":"{{.CPUPerc}}","mem_usage":"{{.MemUsage}}","mem_perc":"{{.MemPerc}}","net":"{{.NetIO}}","pids":"{{.PIDs}}"}',
        name_or_id,
    ])

    if rc != 0:
        result.error = stderr or "Failed to get container stats"
        return result

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        result.error = f"Failed to parse stats: {stdout}"
        return result

    # Parse CPU percentage (e.g., "0.50%")
    try:
        result.cpu_percent = float(data.get("cpu", "0").rstrip("%"))
    except ValueError:
        pass

    # Parse memory usage (e.g., "45.3MiB / 512MiB")
    mem_str = data.get("mem_usage", "")
    if " / " in mem_str:
        usage_str, limit_str = mem_str.split(" / ")
        result.memory_usage_mb = _parse_mem(usage_str)
        result.memory_limit_mb = _parse_mem(limit_str)

    # Parse memory percentage
    try:
        result.memory_percent = float(data.get("mem_perc", "0").rstrip("%"))
    except ValueError:
        pass

    # Parse network I/O (e.g., "1.5MB / 2.3MB")
    net_str = data.get("net", "")
    if " / " in net_str:
        rx_str, tx_str = net_str.split(" / ")
        result.network_rx_mb = _parse_mem(rx_str)
        result.network_tx_mb = _parse_mem(tx_str)

    # Parse PIDs
    try:
        result.pids = int(data.get("pids", "0"))
    except ValueError:
        pass

    return result


def _parse_mem(s: str) -> float:
    """Parse a memory string like '45.3MiB' or '1.5GB' into MB."""
    s = s.strip()
    multipliers = {
        "B": 1 / (1024 * 1024),
        "KiB": 1 / 1024,
        "KB": 1 / 1024,
        "kB": 1 / 1024,
        "MiB": 1.0,
        "MB": 1.0,
        "GiB": 1024.0,
        "GB": 1024.0,
    }
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if s.endswith(suffix):
            try:
                return round(float(s[: -len(suffix)].strip()) * mult, 2)
            except ValueError:
                return 0.0
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Report Assembly
# ---------------------------------------------------------------------------


def build_report(
    url: str | None,
    container: str | None,
    thresholds: Thresholds,
) -> HealthReport:
    """Run all applicable checks and assemble a health report."""
    report = HealthReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    statuses: list[HealthStatus] = []

    # HTTP check
    if url:
        http_result = check_http(url, timeout=thresholds.http_timeout_s)
        report.http = http_result

        if http_result.healthy:
            statuses.append(HealthStatus.HEALTHY)
            if http_result.response_time_ms > thresholds.http_slow_ms:
                report.warnings.append(
                    f"HTTP response time is slow: {http_result.response_time_ms}ms "
                    f"(threshold: {thresholds.http_slow_ms}ms)"
                )
                statuses.append(HealthStatus.DEGRADED)
        else:
            statuses.append(HealthStatus.UNHEALTHY)
            report.errors.append(
                f"HTTP health check failed: {http_result.error or f'status {http_result.status_code}'}"
            )

    # Container check
    if container:
        container_result = check_container(container)
        report.container = container_result

        if container_result.error:
            statuses.append(HealthStatus.UNHEALTHY)
            report.errors.append(f"Container check failed: {container_result.error}")
        elif not container_result.running:
            statuses.append(HealthStatus.UNHEALTHY)
            report.errors.append(f"Container is not running (status: {container_result.status})")
        else:
            statuses.append(HealthStatus.HEALTHY)

            # Check health status from Docker
            if container_result.health_status == "unhealthy":
                statuses.append(HealthStatus.UNHEALTHY)
                report.errors.append("Docker HEALTHCHECK reports unhealthy")
            elif container_result.health_status == "starting":
                statuses.append(HealthStatus.DEGRADED)
                report.warnings.append("Container is still starting up")

            # Check restart count
            if container_result.restart_count >= thresholds.restart_critical:
                statuses.append(HealthStatus.UNHEALTHY)
                report.errors.append(
                    f"Container has restarted {container_result.restart_count} times "
                    f"(critical threshold: {thresholds.restart_critical})"
                )
            elif container_result.restart_count >= thresholds.restart_warn:
                statuses.append(HealthStatus.DEGRADED)
                report.warnings.append(
                    f"Container has restarted {container_result.restart_count} times "
                    f"(warning threshold: {thresholds.restart_warn})"
                )

        # Resource check (only if container is accessible)
        if not container_result.error and container_result.running:
            resource_result = check_resources(container)
            report.resources = resource_result

            if not resource_result.error:
                # CPU thresholds
                if resource_result.cpu_percent >= thresholds.cpu_critical_percent:
                    statuses.append(HealthStatus.UNHEALTHY)
                    report.errors.append(
                        f"CPU usage critical: {resource_result.cpu_percent}% "
                        f"(threshold: {thresholds.cpu_critical_percent}%)"
                    )
                elif resource_result.cpu_percent >= thresholds.cpu_warn_percent:
                    statuses.append(HealthStatus.DEGRADED)
                    report.warnings.append(
                        f"CPU usage high: {resource_result.cpu_percent}% "
                        f"(threshold: {thresholds.cpu_warn_percent}%)"
                    )

                # Memory thresholds
                if resource_result.memory_percent >= thresholds.mem_critical_percent:
                    statuses.append(HealthStatus.UNHEALTHY)
                    report.errors.append(
                        f"Memory usage critical: {resource_result.memory_percent}% "
                        f"({resource_result.memory_usage_mb}MB / {resource_result.memory_limit_mb}MB)"
                    )
                elif resource_result.memory_percent >= thresholds.mem_warn_percent:
                    statuses.append(HealthStatus.DEGRADED)
                    report.warnings.append(
                        f"Memory usage high: {resource_result.memory_percent}% "
                        f"({resource_result.memory_usage_mb}MB / {resource_result.memory_limit_mb}MB)"
                    )

    # Determine overall status (worst wins)
    if HealthStatus.UNHEALTHY in statuses:
        report.overall_status = HealthStatus.UNHEALTHY.value
    elif HealthStatus.DEGRADED in statuses:
        report.overall_status = HealthStatus.DEGRADED.value
    elif HealthStatus.HEALTHY in statuses:
        report.overall_status = HealthStatus.HEALTHY.value
    else:
        report.overall_status = HealthStatus.UNKNOWN.value

    return report


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

STATUS_ICONS = {
    "healthy": "[OK]",
    "degraded": "[WARN]",
    "unhealthy": "[FAIL]",
    "unknown": "[?]",
}


def format_text(report: HealthReport) -> str:
    """Format the health report as human-readable text."""
    lines: list[str] = []
    icon = STATUS_ICONS.get(report.overall_status, "[?]")

    lines.append("=" * 60)
    lines.append(f"  Health Report  {icon}  {report.overall_status.upper()}")
    lines.append(f"  Timestamp: {report.timestamp}")
    lines.append("=" * 60)

    # HTTP section
    if report.http:
        h = report.http
        lines.append("")
        lines.append("  HTTP Health Check")
        lines.append("  " + "-" * 40)
        lines.append(f"  URL:           {h.url}")
        lines.append(f"  Status Code:   {h.status_code}")
        lines.append(f"  Response Time: {h.response_time_ms} ms")
        lines.append(f"  Healthy:       {'Yes' if h.healthy else 'No'}")
        if h.error:
            lines.append(f"  Error:         {h.error}")
        if h.body_preview:
            lines.append(f"  Body Preview:  {h.body_preview[:100]}")

    # Container section
    if report.container:
        c = report.container
        lines.append("")
        lines.append("  Container Status")
        lines.append("  " + "-" * 40)
        lines.append(f"  ID:            {c.container_id}")
        lines.append(f"  Name:          {c.name}")
        lines.append(f"  Image:         {c.image}")
        lines.append(f"  Status:        {c.status}")
        lines.append(f"  Health:        {c.health_status}")
        lines.append(f"  Running:       {'Yes' if c.running else 'No'}")
        lines.append(f"  Restarts:      {c.restart_count}")
        lines.append(f"  Uptime:        {c.uptime}")
        if c.ports:
            lines.append(f"  Ports:         {c.ports}")
        if c.error:
            lines.append(f"  Error:         {c.error}")

    # Resources section
    if report.resources:
        r = report.resources
        lines.append("")
        lines.append("  Resource Usage")
        lines.append("  " + "-" * 40)
        lines.append(f"  CPU:           {r.cpu_percent}%")
        lines.append(f"  Memory:        {r.memory_usage_mb} MB / {r.memory_limit_mb} MB ({r.memory_percent}%)")
        lines.append(f"  Network RX:    {r.network_rx_mb} MB")
        lines.append(f"  Network TX:    {r.network_tx_mb} MB")
        lines.append(f"  PIDs:          {r.pids}")
        if r.error:
            lines.append(f"  Error:         {r.error}")

    # Warnings and errors
    if report.warnings:
        lines.append("")
        lines.append("  Warnings")
        lines.append("  " + "-" * 40)
        for w in report.warnings:
            lines.append(f"  [WARN] {w}")

    if report.errors:
        lines.append("")
        lines.append("  Errors")
        lines.append("  " + "-" * 40)
        for e in report.errors:
            lines.append(f"  [FAIL] {e}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json(report: HealthReport) -> str:
    """Format the health report as JSON."""
    data = asdict(report)
    # Remove None values
    for key in list(data.keys()):
        if data[key] is None:
            del data[key]
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check health of a Docker container or HTTP service."
    )
    parser.add_argument(
        "--url",
        "-u",
        type=str,
        default=None,
        help="HTTP health endpoint URL (e.g., http://localhost:3000/health).",
    )
    parser.add_argument(
        "--container",
        "-c",
        type=str,
        default=None,
        help="Docker container name or ID.",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=5.0,
        help="HTTP request timeout in seconds (default: 5).",
    )
    parser.add_argument(
        "--cpu-warn",
        type=float,
        default=80.0,
        help="CPU usage warning threshold %% (default: 80).",
    )
    parser.add_argument(
        "--cpu-critical",
        type=float,
        default=95.0,
        help="CPU usage critical threshold %% (default: 95).",
    )
    parser.add_argument(
        "--mem-warn",
        type=float,
        default=80.0,
        help="Memory usage warning threshold %% (default: 80).",
    )
    parser.add_argument(
        "--mem-critical",
        type=float,
        default=95.0,
        help="Memory usage critical threshold %% (default: 95).",
    )
    args = parser.parse_args()

    if not args.url and not args.container:
        parser.error("At least one of --url or --container is required.")

    thresholds = Thresholds(
        http_timeout_s=args.http_timeout,
        cpu_warn_percent=args.cpu_warn,
        cpu_critical_percent=args.cpu_critical,
        mem_warn_percent=args.mem_warn,
        mem_critical_percent=args.mem_critical,
    )

    report = build_report(
        url=args.url,
        container=args.container,
        thresholds=thresholds,
    )

    if args.format == "json":
        print(format_json(report))
    else:
        print(format_text(report))

    # Exit code based on overall status
    if report.overall_status == HealthStatus.UNHEALTHY.value:
        sys.exit(2)
    elif report.overall_status == HealthStatus.DEGRADED.value:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
