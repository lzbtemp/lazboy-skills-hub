#!/usr/bin/env python3
"""Scan Claude Code / AI agent configurations for security issues.

Checks .claude/ directory, CLAUDE.md, settings.json, mcp.json, hooks,
and agent definitions for hardcoded secrets, misconfigurations,
prompt injection patterns, and permission issues.

Usage:
    python scan_agent_config.py .
    python scan_agent_config.py /path/to/project --format json
    python scan_agent_config.py . --min-severity high
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path


class Severity(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


SEVERITY_LABELS = {
    Severity.INFO: "info",
    Severity.LOW: "low",
    Severity.MEDIUM: "medium",
    Severity.HIGH: "high",
    Severity.CRITICAL: "critical",
}


@dataclass
class Finding:
    severity: Severity
    category: str
    file: str
    message: str
    line: int = 0
    suggestion: str = ""


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    grade: str = "A"
    score: int = 100

    def add(self, finding: Finding):
        self.findings.append(finding)

    def calculate_score(self):
        deductions = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0,
        }
        total = sum(deductions[f.severity] for f in self.findings)
        self.score = max(0, 100 - total)
        if self.score >= 90:
            self.grade = "A"
        elif self.score >= 75:
            self.grade = "B"
        elif self.score >= 60:
            self.grade = "C"
        elif self.score >= 40:
            self.grade = "D"
        else:
            self.grade = "F"


# --- Secret patterns ---
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI / API Secret Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    (r"github_pat_[a-zA-Z0-9_]{80,}", "GitHub Fine-Grained PAT"),
    (r"xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{24}", "Slack Bot Token"),
    (r"sk_live_[a-zA-Z0-9]{24,}", "Stripe Live Key"),
    (r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY-----", "Private Key"),
    (r"(postgres|mysql|mongodb)://[^\s\"']+:[^\s\"']+@", "Database Connection String"),
    (r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "Bearer Token"),
]

# --- Prompt injection patterns ---
INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?previous\s+instructions", "Prompt injection — ignore instructions"),
    (r"forget\s+(all\s+)?(your\s+)?rules", "Prompt injection — forget rules"),
    (r"you\s+are\s+now\s+(?:a\s+)?(?:different|new)", "Prompt injection — identity override"),
    (r"run\s+(?:this|the\s+following)\s+(?:command|immediately)", "Auto-execution instruction"),
    (r"execute\s+(?:this|immediately|without)", "Auto-execution instruction"),
    (r"curl\s+https?://", "External URL fetch in instructions"),
    (r"wget\s+https?://", "External URL fetch in instructions"),
]

# --- Dangerous Bash patterns ---
DANGEROUS_BASH = [
    "Bash(*)",
    "Bash(npm *)",
    "Bash(sh *)",
    "Bash(bash *)",
    "Bash(python *)",
    "Bash(node *)",
]


def scan_file_for_secrets(filepath: Path, result: ScanResult):
    """Scan a file for hardcoded secrets."""
    try:
        content = filepath.read_text(errors="replace")
    except (OSError, UnicodeDecodeError):
        return

    for line_num, line in enumerate(content.splitlines(), 1):
        # Skip comments that are examples
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            # Check if it looks like documentation vs actual secret
            if any(word in stripped.lower() for word in ["example", "pattern", "detect", "regex"]):
                continue

        for pattern, name in SECRET_PATTERNS:
            if re.search(pattern, line):
                result.add(Finding(
                    severity=Severity.CRITICAL,
                    category="secrets",
                    file=str(filepath),
                    line=line_num,
                    message=f"Possible {name} found",
                    suggestion="Remove and use environment variable reference ($ENV_VAR)",
                ))


def scan_file_for_injection(filepath: Path, result: ScanResult):
    """Scan a file for prompt injection patterns."""
    try:
        content = filepath.read_text(errors="replace")
    except (OSError, UnicodeDecodeError):
        return

    for line_num, line in enumerate(content.splitlines(), 1):
        for pattern, name in INJECTION_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                result.add(Finding(
                    severity=Severity.HIGH,
                    category="injection",
                    file=str(filepath),
                    line=line_num,
                    message=name,
                    suggestion="Remove or rewrite to require explicit user approval",
                ))


def scan_settings(filepath: Path, result: ScanResult):
    """Scan settings.json for permission issues."""
    try:
        data = json.loads(filepath.read_text())
    except (OSError, json.JSONDecodeError):
        return

    result.files_scanned += 1
    permissions = data.get("permissions", {})
    allow_list = permissions.get("allow", [])
    deny_list = permissions.get("deny", [])

    # Check for wildcard Bash access
    for item in allow_list:
        if item in DANGEROUS_BASH:
            result.add(Finding(
                severity=Severity.CRITICAL,
                category="permissions",
                file=str(filepath),
                message=f"Wildcard Bash access: '{item}' grants unrestricted shell access",
                suggestion="Replace with scoped commands: Bash(npm test), Bash(npm run lint)",
            ))

    # Check for missing deny list
    if allow_list and not deny_list:
        result.add(Finding(
            severity=Severity.MEDIUM,
            category="permissions",
            file=str(filepath),
            message="No deny list configured — destructive commands are not blocked",
            suggestion="Add deny list blocking: rm -rf, curl, wget, git push --force, sudo",
        ))

    # Check for sandbox bypass
    if data.get("dangerouslyDisableSandbox"):
        result.add(Finding(
            severity=Severity.CRITICAL,
            category="permissions",
            file=str(filepath),
            message="Sandbox is disabled — file system restrictions bypassed",
            suggestion="Remove dangerouslyDisableSandbox or set to false",
        ))

    # Check for no-verify bypass
    if data.get("skipHooks") or data.get("noVerify"):
        result.add(Finding(
            severity=Severity.HIGH,
            category="permissions",
            file=str(filepath),
            message="Git hooks / verification bypass is enabled",
            suggestion="Remove skipHooks/noVerify — hooks are a security control",
        ))


def scan_mcp_config(filepath: Path, result: ScanResult):
    """Scan MCP server configuration."""
    try:
        data = json.loads(filepath.read_text())
    except (OSError, json.JSONDecodeError):
        return

    result.files_scanned += 1
    servers = data.get("mcpServers", data) if "mcpServers" in data else data

    for name, config in servers.items():
        if not isinstance(config, dict):
            continue

        # Check for missing description
        if not config.get("description"):
            result.add(Finding(
                severity=Severity.INFO,
                category="mcp",
                file=str(filepath),
                message=f"MCP server '{name}' has no description",
                suggestion="Add a description so agents understand the server's purpose",
            ))

        # Check command
        cmd = config.get("command", "")
        if cmd in ("bash", "sh", "/bin/bash", "/bin/sh"):
            result.add(Finding(
                severity=Severity.CRITICAL,
                category="mcp",
                file=str(filepath),
                message=f"MCP server '{name}' uses shell command: '{cmd}'",
                suggestion="Use a specific program instead of a shell interpreter",
            ))

        # Check for npx auto-install
        args = config.get("args", [])
        if cmd == "npx" and "-y" in args:
            pkg = next((a for a in args if not a.startswith("-")), "unknown")
            result.add(Finding(
                severity=Severity.MEDIUM,
                category="mcp",
                file=str(filepath),
                message=f"MCP server '{name}' uses npx -y (auto-install): {pkg}",
                suggestion="Verify package name and pin version to prevent supply chain attacks",
            ))

        # Check for hardcoded secrets in env
        env = config.get("env", {})
        for env_key, env_val in env.items():
            if isinstance(env_val, str) and not env_val.startswith("$"):
                for pattern, secret_name in SECRET_PATTERNS:
                    if re.search(pattern, env_val):
                        result.add(Finding(
                            severity=Severity.CRITICAL,
                            category="secrets",
                            file=str(filepath),
                            message=f"Hardcoded {secret_name} in MCP server '{name}' env.{env_key}",
                            suggestion="Use environment variable: $" + env_key,
                        ))


def scan_hooks(claude_dir: Path, result: ScanResult):
    """Scan hook configurations for command injection and exfiltration."""
    # Check settings.json for hooks
    settings = claude_dir / "settings.json"
    if not settings.exists():
        return

    try:
        data = json.loads(settings.read_text())
    except (OSError, json.JSONDecodeError):
        return

    hooks = data.get("hooks", {})
    for hook_type, hook_list in hooks.items():
        if not isinstance(hook_list, list):
            continue

        for hook in hook_list:
            cmd = hook.get("command", "")

            # Check for variable interpolation
            if re.search(r'\$\{[^}]+\}', cmd) or re.search(r'\$[a-zA-Z_]', cmd):
                result.add(Finding(
                    severity=Severity.HIGH,
                    category="hooks",
                    file=str(settings),
                    message=f"Variable interpolation in {hook_type} hook: potential command injection",
                    suggestion="Avoid interpolating variables into shell commands",
                ))

            # Check for external network calls
            if re.search(r'curl|wget|nc\s|netcat', cmd):
                result.add(Finding(
                    severity=Severity.CRITICAL,
                    category="hooks",
                    file=str(settings),
                    message=f"Network call in {hook_type} hook: potential data exfiltration",
                    suggestion="Hooks should not make external network requests",
                ))

            # Check for silent error suppression
            if re.search(r'2>/dev/null|\|\|\s*true|\|\|\s*:', cmd):
                result.add(Finding(
                    severity=Severity.MEDIUM,
                    category="hooks",
                    file=str(settings),
                    message=f"Silent error suppression in {hook_type} hook",
                    suggestion="Don't suppress errors — they may indicate security failures",
                ))


def scan_agents(claude_dir: Path, result: ScanResult):
    """Scan agent definition files."""
    agents_dir = claude_dir / "agents"
    if not agents_dir.exists():
        return

    for agent_file in agents_dir.glob("*.md"):
        result.files_scanned += 1
        content = agent_file.read_text(errors="replace")

        # Check for unrestricted tool access
        if re.search(r"use\s+any\s+tools?", content, re.IGNORECASE):
            result.add(Finding(
                severity=Severity.HIGH,
                category="agents",
                file=str(agent_file),
                message="Agent has unrestricted tool access",
                suggestion="Specify explicit tool list with minimum required permissions",
            ))

        # Check for Bash access
        if re.search(r"\bbash\b", content, re.IGNORECASE) and not re.search(r"no\s+bash", content, re.IGNORECASE):
            result.add(Finding(
                severity=Severity.MEDIUM,
                category="agents",
                file=str(agent_file),
                message="Agent may have Bash access — verify this is necessary",
                suggestion="Remove Bash access if agent only needs read/analysis capabilities",
            ))

        # Check for prompt injection surface
        scan_file_for_injection(agent_file, result)
        scan_file_for_secrets(agent_file, result)


def scan_project(project_path: Path) -> ScanResult:
    """Run all scans on a project directory."""
    result = ScanResult()

    # Scan CLAUDE.md
    claude_md = project_path / "CLAUDE.md"
    if claude_md.exists():
        result.files_scanned += 1
        scan_file_for_secrets(claude_md, result)
        scan_file_for_injection(claude_md, result)

    # Scan .claude/ directory
    claude_dir = project_path / ".claude"
    if claude_dir.exists():
        # settings.json
        settings = claude_dir / "settings.json"
        if settings.exists():
            scan_settings(settings, result)
            scan_file_for_secrets(settings, result)
            scan_hooks(claude_dir, result)

        # mcp.json
        for mcp_file in ["mcp.json", "mcp_servers.json"]:
            mcp_path = claude_dir / mcp_file
            if mcp_path.exists():
                scan_mcp_config(mcp_path, result)

        # Agent definitions
        scan_agents(claude_dir, result)

        # Scan all files for secrets
        for f in claude_dir.rglob("*"):
            if f.is_file() and f.suffix in (".json", ".md", ".yml", ".yaml", ".toml"):
                result.files_scanned += 1
                scan_file_for_secrets(f, result)

    result.calculate_score()
    return result


def format_text(result: ScanResult, min_severity: Severity) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append(f"\n{'=' * 60}")
    lines.append(f"  Agent Configuration Security Scan")
    lines.append(f"  Grade: {result.grade} ({result.score}/100)")
    lines.append(f"  Files scanned: {result.files_scanned}")
    lines.append(f"{'=' * 60}\n")

    filtered = [f for f in result.findings if f.severity >= min_severity]

    if not filtered:
        lines.append("  No findings. Configuration looks secure.\n")
        return "\n".join(lines)

    # Group by severity
    for sev in sorted(set(f.severity for f in filtered), reverse=True):
        sev_findings = [f for f in filtered if f.severity == sev]
        label = SEVERITY_LABELS[sev].upper()
        lines.append(f"  [{label}] ({len(sev_findings)} findings)")
        lines.append(f"  {'-' * 40}")
        for f in sev_findings:
            loc = f"{f.file}"
            if f.line:
                loc += f":{f.line}"
            lines.append(f"    {f.message}")
            lines.append(f"    File: {loc}")
            if f.suggestion:
                lines.append(f"    Fix:  {f.suggestion}")
            lines.append("")

    # Summary
    counts = {}
    for f in filtered:
        label = SEVERITY_LABELS[f.severity]
        counts[label] = counts.get(label, 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda x: -Severity[x[0].upper()]))
    lines.append(f"  Summary: {summary}")
    lines.append("")

    return "\n".join(lines)


def format_json(result: ScanResult, min_severity: Severity) -> str:
    """Format results as JSON."""
    filtered = [f for f in result.findings if f.severity >= min_severity]
    output = {
        "grade": result.grade,
        "score": result.score,
        "files_scanned": result.files_scanned,
        "summary": {
            "critical": sum(1 for f in filtered if f.severity == Severity.CRITICAL),
            "high": sum(1 for f in filtered if f.severity == Severity.HIGH),
            "medium": sum(1 for f in filtered if f.severity == Severity.MEDIUM),
            "low": sum(1 for f in filtered if f.severity == Severity.LOW),
            "info": sum(1 for f in filtered if f.severity == Severity.INFO),
        },
        "findings": [
            {
                "severity": SEVERITY_LABELS[f.severity],
                "category": f.category,
                "file": f.file,
                "line": f.line,
                "message": f.message,
                "suggestion": f.suggestion,
            }
            for f in filtered
        ],
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Scan AI agent configurations for security issues")
    parser.add_argument("path", nargs="?", default=".", help="Project directory to scan")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument(
        "--min-severity",
        choices=["info", "low", "medium", "high", "critical"],
        default="info",
        help="Minimum severity to report",
    )
    args = parser.parse_args()

    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"Error: {project_path} does not exist", file=sys.stderr)
        sys.exit(1)

    min_sev = Severity[args.min_severity.upper()]
    result = scan_project(project_path)

    if args.format == "json":
        print(format_json(result, min_sev))
    else:
        print(format_text(result, min_sev))

    # Exit code based on findings
    critical_high = sum(1 for f in result.findings if f.severity >= Severity.HIGH)
    sys.exit(2 if critical_high > 0 else 0)


if __name__ == "__main__":
    main()
