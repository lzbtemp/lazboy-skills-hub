#!/usr/bin/env python3
"""
Automated pre-review checks for code review.

Scans a directory for common issues before a human review begins:
  - Hardcoded secrets patterns (API keys, tokens, passwords)
  - TODO/FIXME counts and locations
  - Large files that may need splitting
  - Import organization issues (Python files)
  - Common anti-patterns

Usage:
    python review_pr.py /path/to/directory
    python review_pr.py /path/to/directory --max-file-lines 400 --json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MAX_FILE_LINES = 300

# File extensions to scan
SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".java", ".go", ".rs", ".rb", ".php",
    ".yaml", ".yml", ".toml", ".json", ".env",
    ".sh", ".bash", ".zsh",
    ".sql", ".graphql",
    ".css", ".scss", ".less",
    ".html", ".xml", ".svg",
    ".md", ".txt", ".rst",
    ".dockerfile",
}

# Directories to always skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "coverage", ".terraform", ".eggs",
    "vendor", "target",
}

# ---------------------------------------------------------------------------
# Secret detection patterns
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    # AWS
    (r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}", "AWS Access Key ID"),
    # Generic high-entropy tokens assigned to variables
    (r"""(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|pwd)\s*[:=]\s*['"][A-Za-z0-9/+=]{20,}['"]""", "Possible hardcoded secret"),
    # Private keys
    (r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----", "Private key"),
    # Connection strings with credentials
    (r"(?:mongodb|postgres|mysql|redis|amqp)://[^:]+:[^@]+@", "Connection string with credentials"),
    # Generic Bearer tokens in code
    (r"""['"]Bearer\s+[A-Za-z0-9\-._~+/]+=*['"]""", "Hardcoded Bearer token"),
    # GitHub tokens
    (r"gh[pousr]_[A-Za-z0-9_]{36,}", "GitHub token"),
    # Slack tokens
    (r"xox[baprs]-[0-9]{10,}-[A-Za-z0-9-]+", "Slack token"),
    # Generic hex secrets (32+ chars assigned to a variable)
    (r"""(?:secret|token|key|password)\s*[:=]\s*['"][0-9a-fA-F]{32,}['"]""", "Possible hex secret"),
]

# Compile once
_SECRET_REGEXES = [(re.compile(pat, re.IGNORECASE), desc) for pat, desc in SECRET_PATTERNS]

# ---------------------------------------------------------------------------
# Anti-pattern detection
# ---------------------------------------------------------------------------

ANTI_PATTERNS = [
    # eval / exec with variables
    (r"\beval\s*\(", "eval() usage — potential code injection risk", {".py", ".js", ".ts", ".tsx", ".jsx"}),
    (r"\bexec\s*\(", "exec() usage — potential code injection risk", {".py"}),
    # dangerouslySetInnerHTML
    (r"dangerouslySetInnerHTML", "dangerouslySetInnerHTML — XSS risk", {".js", ".ts", ".tsx", ".jsx"}),
    # console.log left in code
    (r"\bconsole\.log\s*\(", "console.log() — remove before merge", {".js", ".ts", ".tsx", ".jsx"}),
    # Python print statements (likely debug)
    (r"^\s*print\s*\(", "print() statement — likely debug output", {".py"}),
    # Catch-all exception handlers
    (r"except\s*:", "Bare except — catches all exceptions including KeyboardInterrupt", {".py"}),
    # TODO/FIXME without ticket
    (r"\b(?:TODO|FIXME|HACK|XXX)\b(?!.*(?:[A-Z]+-\d+|#\d+))", "TODO/FIXME without ticket reference", None),
]

_ANTI_PATTERN_REGEXES = [(re.compile(pat, re.MULTILINE), desc, exts) for pat, desc, exts in ANTI_PATTERNS]

# ---------------------------------------------------------------------------
# Python import ordering check
# ---------------------------------------------------------------------------

_STDLIB_MODULES = {
    "abc", "argparse", "ast", "asyncio", "base64", "bisect", "collections",
    "configparser", "contextlib", "copy", "csv", "dataclasses", "datetime",
    "decimal", "difflib", "enum", "errno", "functools", "glob", "hashlib",
    "heapq", "hmac", "html", "http", "importlib", "inspect", "io",
    "itertools", "json", "logging", "math", "multiprocessing", "operator",
    "os", "pathlib", "pickle", "platform", "pprint", "queue", "random",
    "re", "secrets", "shutil", "signal", "socket", "sqlite3", "ssl",
    "string", "struct", "subprocess", "sys", "tempfile", "textwrap",
    "threading", "time", "timeit", "traceback", "typing", "unittest",
    "urllib", "uuid", "warnings", "weakref", "xml", "zipfile",
}


# ---------------------------------------------------------------------------
# Data classes for findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    category: str
    severity: str  # critical, high, medium, low, info
    message: str


@dataclass
class FileStats:
    path: str
    lines: int
    extension: str


@dataclass
class Report:
    directory: str
    files_scanned: int = 0
    findings: list = field(default_factory=list)
    large_files: list = field(default_factory=list)
    todo_count: int = 0
    fixme_count: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "medium")


# ---------------------------------------------------------------------------
# Scanning functions
# ---------------------------------------------------------------------------

def should_scan(path: Path) -> bool:
    """Determine whether a file should be scanned."""
    if path.name.startswith("."):
        return False
    # Check for Dockerfile (no extension)
    if path.name.lower() in ("dockerfile", "makefile", "vagrantfile"):
        return True
    return path.suffix.lower() in SCANNABLE_EXTENSIONS


def iter_files(directory: Path):
    """Yield all scannable files in the directory tree."""
    for root, dirs, files in os.walk(directory):
        # Prune skipped directories in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            fpath = Path(root) / fname
            if should_scan(fpath):
                yield fpath


def read_file_safe(path: Path) -> Optional[str]:
    """Read a file, returning None if it cannot be decoded."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None


def check_secrets(filepath: Path, content: str, report: Report):
    """Scan for hardcoded secret patterns."""
    for line_no, line in enumerate(content.splitlines(), start=1):
        # Skip comments that look like documentation examples
        stripped = line.strip()
        if stripped.startswith("#") and "example" in stripped.lower():
            continue
        if stripped.startswith("//") and "example" in stripped.lower():
            continue

        for regex, description in _SECRET_REGEXES:
            if regex.search(line):
                report.findings.append(Finding(
                    file=str(filepath),
                    line=line_no,
                    category="secret",
                    severity="critical",
                    message=description,
                ))


def check_anti_patterns(filepath: Path, content: str, report: Report):
    """Scan for common anti-patterns."""
    ext = filepath.suffix.lower()
    for regex, description, allowed_exts in _ANTI_PATTERN_REGEXES:
        if allowed_exts is not None and ext not in allowed_exts:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                # Determine severity
                if "injection" in description.lower() or "xss" in description.lower():
                    severity = "high"
                elif "console.log" in description or "print()" in description:
                    severity = "low"
                elif "TODO" in description:
                    severity = "info"
                elif "Bare except" in description:
                    severity = "medium"
                else:
                    severity = "medium"

                report.findings.append(Finding(
                    file=str(filepath),
                    line=line_no,
                    category="anti-pattern",
                    severity=severity,
                    message=description,
                ))


def check_todos(content: str, report: Report):
    """Count TODO and FIXME markers."""
    report.todo_count += len(re.findall(r"\bTODO\b", content))
    report.fixme_count += len(re.findall(r"\bFIXME\b", content))


def check_file_size(filepath: Path, content: str, max_lines: int, report: Report):
    """Flag files that exceed the line threshold."""
    line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    if line_count > max_lines:
        report.large_files.append(FileStats(
            path=str(filepath),
            lines=line_count,
            extension=filepath.suffix,
        ))


def check_python_imports(filepath: Path, content: str, report: Report):
    """Check Python import ordering (stdlib, third-party, local)."""
    if filepath.suffix != ".py":
        return

    import_lines = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Extract the top-level module name
            if stripped.startswith("from "):
                module = stripped.split()[1].split(".")[0]
            else:
                module = stripped.split()[1].split(".")[0]
            # Classify
            if module.startswith("."):
                group = 2  # relative / local
            elif module in _STDLIB_MODULES:
                group = 0  # stdlib
            else:
                group = 1  # third-party (heuristic)
            import_lines.append((line_no, group, module))

    # Check that groups are in non-decreasing order
    if len(import_lines) < 2:
        return

    prev_group = import_lines[0][1]
    for line_no, group, module in import_lines[1:]:
        if group < prev_group:
            report.findings.append(Finding(
                file=str(filepath),
                line=line_no,
                category="imports",
                severity="info",
                message=f"Import '{module}' appears out of order (expected stdlib, then third-party, then local)",
            ))
            break  # Only report once per file
        prev_group = group


# ---------------------------------------------------------------------------
# Main scan orchestration
# ---------------------------------------------------------------------------

def scan_directory(directory: Path, max_file_lines: int) -> Report:
    """Run all checks on every scannable file in the directory."""
    report = Report(directory=str(directory))

    for filepath in iter_files(directory):
        content = read_file_safe(filepath)
        if content is None:
            continue

        report.files_scanned += 1
        rel_path = filepath.relative_to(directory)

        check_secrets(rel_path, content, report)
        check_anti_patterns(rel_path, content, report)
        check_todos(content, report)
        check_file_size(rel_path, content, max_file_lines, report)
        check_python_imports(rel_path, content, report)

    return report


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_ICONS = {
    "critical": "[CRIT]",
    "high":     "[HIGH]",
    "medium":   "[MED] ",
    "low":      "[LOW] ",
    "info":     "[INFO]",
}


def print_text_report(report: Report):
    """Print a human-readable report to stdout."""
    print("=" * 70)
    print("  PRE-REVIEW AUTOMATED CHECK REPORT")
    print("=" * 70)
    print(f"  Directory:     {report.directory}")
    print(f"  Files scanned: {report.files_scanned}")
    print(f"  TODOs:         {report.todo_count}")
    print(f"  FIXMEs:        {report.fixme_count}")
    print()

    if report.large_files:
        print("-" * 70)
        print("  LARGE FILES (consider splitting)")
        print("-" * 70)
        for fs in sorted(report.large_files, key=lambda x: -x.lines):
            print(f"    {fs.lines:>5} lines  {fs.path}")
        print()

    if report.findings:
        # Sort by severity, then file, then line
        sorted_findings = sorted(
            report.findings,
            key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.file, f.line),
        )

        print("-" * 70)
        print("  FINDINGS")
        print("-" * 70)
        for f in sorted_findings:
            icon = SEVERITY_ICONS.get(f.severity, "[???]")
            print(f"  {icon}  {f.file}:{f.line}")
            print(f"          {f.message}")
        print()

    # Summary
    print("-" * 70)
    print("  SUMMARY")
    print("-" * 70)
    print(f"    Critical: {report.critical_count}")
    print(f"    High:     {report.high_count}")
    print(f"    Medium:   {report.medium_count}")
    print(f"    Total:    {len(report.findings)}")
    print()

    if report.critical_count > 0:
        print("  ** CRITICAL issues found — these MUST be resolved before merge. **")
    elif report.high_count > 0:
        print("  ** HIGH severity issues found — review carefully before merge. **")
    elif report.medium_count > 0:
        print("  ** MEDIUM issues found — consider addressing in this PR. **")
    else:
        print("  No blocking issues found. Proceed with human review.")

    print("=" * 70)


def print_json_report(report: Report):
    """Print a JSON report to stdout."""
    data = {
        "directory": report.directory,
        "files_scanned": report.files_scanned,
        "todo_count": report.todo_count,
        "fixme_count": report.fixme_count,
        "summary": {
            "critical": report.critical_count,
            "high": report.high_count,
            "medium": report.medium_count,
            "total": len(report.findings),
        },
        "large_files": [asdict(f) for f in report.large_files],
        "findings": [asdict(f) for f in report.findings],
    }
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run automated pre-review checks on a codebase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python review_pr.py ./src
  python review_pr.py ./src --max-file-lines 400
  python review_pr.py ./src --json
  python review_pr.py ./src --json | jq '.findings[] | select(.severity == "critical")'
        """,
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Path to the directory to scan",
    )
    parser.add_argument(
        "--max-file-lines",
        type=int,
        default=DEFAULT_MAX_FILE_LINES,
        help=f"Flag files exceeding this line count (default: {DEFAULT_MAX_FILE_LINES})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON instead of a human-readable table",
    )
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"Error: '{args.directory}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    report = scan_directory(args.directory.resolve(), args.max_file_lines)

    if args.json_output:
        print_json_report(report)
    else:
        print_text_report(report)

    # Exit with non-zero if critical or high findings exist
    if report.critical_count > 0:
        sys.exit(2)
    elif report.high_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
