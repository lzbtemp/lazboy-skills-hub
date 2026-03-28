#!/usr/bin/env python3
"""Validate a GitHub Actions workflow YAML for common issues.

Checks for: missing permissions, no timeout, missing cache, hardcoded secrets,
deprecated actions, missing concurrency groups, and other best-practice violations.

Usage:
    python check_pipeline.py .github/workflows/ci.yml
    python check_pipeline.py --strict .github/workflows/*.yml
    python check_pipeline.py --format json .github/workflows/ci.yml

Requires: PyYAML (pip install pyyaml)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    severity: Severity
    rule: str
    message: str
    location: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity.value,
            "rule": self.rule,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class ValidationResult:
    file: str
    issues: list[Issue] = field(default_factory=list)
    valid: bool = True

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)
        if issue.severity == Severity.ERROR:
            self.valid = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "summary": {
                "errors": sum(1 for i in self.issues if i.severity == Severity.ERROR),
                "warnings": sum(1 for i in self.issues if i.severity == Severity.WARNING),
                "info": sum(1 for i in self.issues if i.severity == Severity.INFO),
            },
        }


# Known deprecated actions and their replacements
DEPRECATED_ACTIONS = {
    "actions/checkout@v1": "actions/checkout@v4",
    "actions/checkout@v2": "actions/checkout@v4",
    "actions/checkout@v3": "actions/checkout@v4",
    "actions/setup-node@v1": "actions/setup-node@v4",
    "actions/setup-node@v2": "actions/setup-node@v4",
    "actions/setup-node@v3": "actions/setup-node@v4",
    "actions/setup-python@v1": "actions/setup-python@v5",
    "actions/setup-python@v2": "actions/setup-python@v5",
    "actions/setup-python@v3": "actions/setup-python@v5",
    "actions/setup-python@v4": "actions/setup-python@v5",
    "actions/upload-artifact@v1": "actions/upload-artifact@v4",
    "actions/upload-artifact@v2": "actions/upload-artifact@v4",
    "actions/upload-artifact@v3": "actions/upload-artifact@v4",
    "actions/download-artifact@v1": "actions/download-artifact@v4",
    "actions/download-artifact@v2": "actions/download-artifact@v4",
    "actions/download-artifact@v3": "actions/download-artifact@v4",
}

# Patterns that indicate hardcoded secrets
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^${}][^'\"]{4,}", "Hardcoded password"),
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][^${}][^'\"]{8,}", "Hardcoded API key"),
    (r"(?i)(secret|token)\s*[:=]\s*['\"][^${}][^'\"]{8,}", "Hardcoded secret/token"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"xox[bpoa]-[a-zA-Z0-9-]+", "Slack Token"),
]


def check_permissions(workflow: dict[str, Any], result: ValidationResult) -> None:
    """Check for missing or overly broad permissions."""
    if "permissions" not in workflow:
        result.add(Issue(
            severity=Severity.WARNING,
            rule="permissions-missing",
            message="No top-level 'permissions' defined. Workflow runs with default (broad) permissions. "
                    "Add explicit permissions to follow least-privilege principle.",
            location="(top-level)",
        ))
        return

    perms = workflow["permissions"]
    if perms == "write-all" or (isinstance(perms, dict) and perms.get("contents") == "write"):
        result.add(Issue(
            severity=Severity.WARNING,
            rule="permissions-broad",
            message="Workflow has broad write permissions. Restrict to only what is needed.",
            location="permissions",
        ))


def check_timeouts(workflow: dict[str, Any], result: ValidationResult) -> None:
    """Check for missing timeout-minutes on jobs."""
    jobs = workflow.get("jobs", {})
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if "timeout-minutes" not in job:
            result.add(Issue(
                severity=Severity.WARNING,
                rule="timeout-missing",
                message=f"Job '{job_name}' has no timeout-minutes. Stuck jobs will consume runner "
                        f"minutes (default: 6 hours). Add timeout-minutes.",
                location=f"jobs.{job_name}",
            ))


def check_caching(workflow: dict[str, Any], result: ValidationResult) -> None:
    """Check for missing dependency caching."""
    jobs = workflow.get("jobs", {})
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])

        has_setup_node = False
        has_node_cache = False
        has_setup_python = False
        has_python_cache = False

        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")

            if "actions/setup-node" in uses:
                has_setup_node = True
                with_config = step.get("with", {})
                if isinstance(with_config, dict) and "cache" in with_config:
                    has_node_cache = True

            if "actions/setup-python" in uses:
                has_setup_python = True
                with_config = step.get("with", {})
                if isinstance(with_config, dict) and "cache" in with_config:
                    has_python_cache = True

        if has_setup_node and not has_node_cache:
            result.add(Issue(
                severity=Severity.WARNING,
                rule="cache-missing",
                message=f"Job '{job_name}' uses setup-node without cache. "
                        f"Add 'cache: npm' (or yarn/pnpm) to speed up builds.",
                location=f"jobs.{job_name}",
            ))

        if has_setup_python and not has_python_cache:
            result.add(Issue(
                severity=Severity.WARNING,
                rule="cache-missing",
                message=f"Job '{job_name}' uses setup-python without cache. "
                        f"Add 'cache: pip' to speed up builds.",
                location=f"jobs.{job_name}",
            ))


def check_hardcoded_secrets(workflow_text: str, result: ValidationResult) -> None:
    """Scan raw YAML text for hardcoded secrets."""
    for line_num, line in enumerate(workflow_text.splitlines(), 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        for pattern, description in SECRET_PATTERNS:
            if re.search(pattern, line):
                result.add(Issue(
                    severity=Severity.ERROR,
                    rule="hardcoded-secret",
                    message=f"Possible {description} found. Use GitHub Secrets instead.",
                    location=f"line {line_num}",
                ))


def check_deprecated_actions(workflow: dict[str, Any], result: ValidationResult) -> None:
    """Check for deprecated GitHub Actions versions."""
    jobs = workflow.get("jobs", {})
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            if uses in DEPRECATED_ACTIONS:
                result.add(Issue(
                    severity=Severity.WARNING,
                    rule="deprecated-action",
                    message=f"Action '{uses}' is outdated. Update to '{DEPRECATED_ACTIONS[uses]}'.",
                    location=f"jobs.{job_name}",
                ))


def check_concurrency(workflow: dict[str, Any], result: ValidationResult) -> None:
    """Check for missing concurrency group."""
    if "concurrency" not in workflow:
        result.add(Issue(
            severity=Severity.INFO,
            rule="concurrency-missing",
            message="No concurrency group defined. Concurrent pushes may waste runner minutes. "
                    "Consider adding: concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, "
                    "cancel-in-progress: true }",
            location="(top-level)",
        ))


def check_trigger_config(workflow: dict[str, Any], result: ValidationResult) -> None:
    """Check trigger configuration for common issues."""
    on = workflow.get("on", workflow.get(True, {}))  # YAML parses 'on' as True sometimes

    if isinstance(on, dict):
        push = on.get("push", {})
        if isinstance(push, dict):
            branches = push.get("branches", [])
            if not branches and not push.get("tags", []) and not push.get("paths", []):
                result.add(Issue(
                    severity=Severity.WARNING,
                    rule="trigger-unfiltered",
                    message="Push trigger has no branch/path filter. Workflow runs on every push to any branch.",
                    location="on.push",
                ))


def check_shell_injection(workflow: dict[str, Any], result: ValidationResult) -> None:
    """Check for potential shell injection via untrusted inputs."""
    dangerous_contexts = [
        "github.event.pull_request.title",
        "github.event.pull_request.body",
        "github.event.issue.title",
        "github.event.issue.body",
        "github.event.comment.body",
        "github.event.review.body",
        "github.head_ref",
    ]

    jobs = workflow.get("jobs", {})
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if not isinstance(step, dict):
                continue
            run_cmd = step.get("run", "")
            if not isinstance(run_cmd, str):
                continue
            for ctx in dangerous_contexts:
                if ctx in run_cmd:
                    result.add(Issue(
                        severity=Severity.ERROR,
                        rule="shell-injection",
                        message=f"Potentially unsafe use of '${{{{ {ctx} }}}}' in a run step. "
                                f"This can be exploited for command injection. "
                                f"Use an environment variable or action input instead.",
                        location=f"jobs.{job_name}",
                    ))


def check_pinned_actions(workflow: dict[str, Any], result: ValidationResult) -> None:
    """Check if third-party actions use SHA pinning."""
    trusted_owners = {"actions", "github", "docker"}

    jobs = workflow.get("jobs", {})
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            if not uses or "/" not in uses:
                continue
            owner = uses.split("/")[0]
            if owner in trusted_owners:
                continue
            # Check if it's pinned to a SHA (40 hex chars after @)
            if "@" in uses:
                ref = uses.split("@")[1]
                if not re.match(r"^[a-f0-9]{40}$", ref):
                    result.add(Issue(
                        severity=Severity.INFO,
                        rule="action-not-pinned",
                        message=f"Third-party action '{uses}' is not pinned to a commit SHA. "
                                f"Pin to a full SHA for supply chain security.",
                        location=f"jobs.{job_name}",
                    ))


def validate_workflow(filepath: Path, strict: bool = False) -> ValidationResult:
    """Run all checks against a workflow file."""
    result = ValidationResult(file=str(filepath))

    if not filepath.exists():
        result.add(Issue(
            severity=Severity.ERROR,
            rule="file-not-found",
            message=f"File not found: {filepath}",
        ))
        return result

    try:
        text = filepath.read_text()
    except OSError as e:
        result.add(Issue(
            severity=Severity.ERROR,
            rule="file-read-error",
            message=f"Cannot read file: {e}",
        ))
        return result

    try:
        workflow = yaml.safe_load(text)
    except yaml.YAMLError as e:
        result.add(Issue(
            severity=Severity.ERROR,
            rule="yaml-parse-error",
            message=f"Invalid YAML: {e}",
        ))
        return result

    if not isinstance(workflow, dict):
        result.add(Issue(
            severity=Severity.ERROR,
            rule="invalid-workflow",
            message="Workflow file does not contain a valid mapping/object at the top level.",
        ))
        return result

    # Required fields
    if "name" not in workflow:
        result.add(Issue(
            severity=Severity.INFO,
            rule="name-missing",
            message="Workflow has no 'name' field. Adding a name improves readability in the Actions UI.",
            location="(top-level)",
        ))

    on_key = "on" if "on" in workflow else True if True in workflow else None
    if on_key is None:
        result.add(Issue(
            severity=Severity.ERROR,
            rule="trigger-missing",
            message="Workflow has no 'on' trigger defined.",
            location="(top-level)",
        ))

    if "jobs" not in workflow:
        result.add(Issue(
            severity=Severity.ERROR,
            rule="jobs-missing",
            message="Workflow has no 'jobs' defined.",
            location="(top-level)",
        ))
        return result

    # Run all checks
    check_permissions(workflow, result)
    check_timeouts(workflow, result)
    check_caching(workflow, result)
    check_hardcoded_secrets(text, result)
    check_deprecated_actions(workflow, result)
    check_concurrency(workflow, result)
    check_trigger_config(workflow, result)
    check_shell_injection(workflow, result)
    check_pinned_actions(workflow, result)

    # In strict mode, warnings become errors
    if strict:
        for issue in result.issues:
            if issue.severity == Severity.WARNING:
                issue.severity = Severity.ERROR
                result.valid = False

    return result


def format_text(results: list[ValidationResult]) -> str:
    """Format results as human-readable text."""
    lines: list[str] = []
    total_errors = 0
    total_warnings = 0

    for res in results:
        lines.append(f"\n{'=' * 60}")
        lines.append(f"File: {res.file}")
        lines.append(f"{'=' * 60}")

        if not res.issues:
            lines.append("  No issues found.")
            continue

        for issue in res.issues:
            icon = {"error": "[ERROR]", "warning": "[WARN] ", "info": "[INFO] "}[issue.severity.value]
            loc = f" ({issue.location})" if issue.location else ""
            lines.append(f"  {icon} [{issue.rule}]{loc}")
            lines.append(f"         {issue.message}")

            if issue.severity == Severity.ERROR:
                total_errors += 1
            elif issue.severity == Severity.WARNING:
                total_warnings += 1

    lines.append(f"\n{'=' * 60}")
    lines.append(f"Summary: {total_errors} error(s), {total_warnings} warning(s) "
                 f"across {len(results)} file(s)")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate GitHub Actions workflow YAML files for common issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rules checked:
  permissions-missing    No explicit permissions block
  permissions-broad      Overly permissive permissions
  timeout-missing        Job without timeout-minutes
  cache-missing          Setup action without cache
  hardcoded-secret       Possible secret in plain text
  deprecated-action      Outdated action version
  concurrency-missing    No concurrency group
  trigger-unfiltered     Push trigger without branch filter
  shell-injection        Unsafe context in run step
  action-not-pinned      Third-party action not SHA-pinned
        """,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="Workflow YAML file(s) to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (non-zero exit code)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    results = []
    for filepath in args.files:
        result = validate_workflow(filepath.resolve(), strict=args.strict)
        results.append(result)

    if args.format == "json":
        output = [r.to_dict() for r in results]
        print(json.dumps(output, indent=2))
    else:
        print(format_text(results))

    # Exit with non-zero if any file had errors
    has_errors = any(not r.valid for r in results)
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
