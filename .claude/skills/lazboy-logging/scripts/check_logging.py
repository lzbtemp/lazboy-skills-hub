#!/usr/bin/env python3
"""Scan code for logging issues and anti-patterns.

Detects print statements that should be logger calls, missing log levels,
sensitive data in logs, inconsistent logger naming, and other logging problems.

Usage:
    python check_logging.py /path/to/project
    python check_logging.py . --language python
    python check_logging.py /path/to/project --format json --severity WARNING
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"


@dataclass
class Finding:
    severity: Severity
    category: str
    message: str
    file: str
    line: int = 0
    snippet: str = ""

    def to_dict(self) -> dict:
        result = {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }
        if self.snippet:
            result["snippet"] = self.snippet
        return result


@dataclass
class CheckResult:
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def summary(self) -> dict[str, int]:
        counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts


# Sensitive data patterns that should never appear in logs
SENSITIVE_PATTERNS = [
    (r"password", "password"),
    (r"passwd", "password"),
    (r"api_key", "API key"),
    (r"apikey", "API key"),
    (r"api[-_]?secret", "API secret"),
    (r"secret[-_]?key", "secret key"),
    (r"access[-_]?token", "access token"),
    (r"auth[-_]?token", "auth token"),
    (r"bearer", "bearer token"),
    (r"credit[-_]?card", "credit card"),
    (r"card[-_]?number", "card number"),
    (r"cvv", "CVV"),
    (r"ssn", "SSN"),
    (r"social[-_]?security", "social security number"),
    (r"private[-_]?key", "private key"),
]


def detect_language(filepath: Path) -> Language | None:
    """Detect programming language from file extension."""
    ext = filepath.suffix.lower()
    mapping = {
        ".py": Language.PYTHON,
        ".js": Language.JAVASCRIPT,
        ".ts": Language.JAVASCRIPT,
        ".jsx": Language.JAVASCRIPT,
        ".tsx": Language.JAVASCRIPT,
        ".java": Language.JAVA,
    }
    return mapping.get(ext)


def find_source_files(project_dir: Path, language: str | None = None) -> list[Path]:
    """Find all source files in the project."""
    extensions = {
        "python": ["*.py"],
        "javascript": ["*.js", "*.ts", "*.jsx", "*.tsx"],
        "java": ["*.java"],
    }

    if language:
        patterns = extensions.get(language, [])
    else:
        patterns = [p for pats in extensions.values() for p in pats]

    files = []
    for pattern in patterns:
        files.extend(project_dir.rglob(pattern))

    # Exclude common non-source directories
    exclude_dirs = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".tox"}
    return [f for f in files if not any(d in f.parts for d in exclude_dirs)]


def read_file(filepath: Path) -> list[str]:
    """Read file and return lines."""
    try:
        return filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []


def check_print_statements(filepath: Path, lines: list[str], lang: Language, result: CheckResult) -> None:
    """Detect print statements that should be logger calls."""
    if lang == Language.PYTHON:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            # Match print() calls that are not in comments or strings used for CLI output
            if re.match(r"print\s*\(", stripped):
                # Check if this looks like debugging output
                if any(keyword in stripped.lower() for keyword in
                       ["debug", "error", "warn", "info", "log", "status", "result"]):
                    result.add(Finding(
                        severity=Severity.WARNING,
                        category="print-statement",
                        message="print() used for logging. Use logger.info/debug/warning/error instead.",
                        file=str(filepath),
                        line=i,
                        snippet=stripped[:120],
                    ))
                else:
                    result.add(Finding(
                        severity=Severity.INFO,
                        category="print-statement",
                        message="print() detected. Consider using a logger for production code.",
                        file=str(filepath),
                        line=i,
                        snippet=stripped[:120],
                    ))

    elif lang == Language.JAVASCRIPT:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            if re.match(r"console\.(log|warn|error|info|debug)\s*\(", stripped):
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="print-statement",
                    message="console.log() used instead of a proper logger (winston, pino, etc.).",
                    file=str(filepath),
                    line=i,
                    snippet=stripped[:120],
                ))

    elif lang == Language.JAVA:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r"System\.(out|err)\.(print|println)\s*\(", stripped):
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="print-statement",
                    message="System.out/err.print used. Use SLF4J logger instead.",
                    file=str(filepath),
                    line=i,
                    snippet=stripped[:120],
                ))


def check_sensitive_data(filepath: Path, lines: list[str], lang: Language, result: CheckResult) -> None:
    """Check for sensitive data being logged."""
    log_patterns = {
        Language.PYTHON: [
            r"logger\.\w+\(",
            r"logging\.\w+\(",
            r"log\.\w+\(",
            r"print\(",
        ],
        Language.JAVASCRIPT: [
            r"console\.\w+\(",
            r"logger\.\w+\(",
            r"log\.\w+\(",
            r"winston\.\w+\(",
        ],
        Language.JAVA: [
            r"log\.\w+\(",
            r"logger\.\w+\(",
            r"LOG\.\w+\(",
            r"System\.(out|err)\.\w+\(",
        ],
    }

    patterns = log_patterns.get(lang, [])

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Check if this line is a log statement
        is_log_line = any(re.search(p, stripped) for p in patterns)
        if not is_log_line:
            continue

        # Check for sensitive data patterns
        for sensitive_pattern, data_type in SENSITIVE_PATTERNS:
            if re.search(sensitive_pattern, stripped, re.IGNORECASE):
                # Avoid false positives: skip if it's just the variable name in a format string
                # without a value (e.g., "password field is required")
                result.add(Finding(
                    severity=Severity.ERROR,
                    category="sensitive-data",
                    message=f"Potential {data_type} in log output. Never log credentials or PII.",
                    file=str(filepath),
                    line=i,
                    snippet=stripped[:120],
                ))
                break  # One finding per line


def check_fstring_in_logger(filepath: Path, lines: list[str], lang: Language, result: CheckResult) -> None:
    """Check for f-strings in Python logger calls (defeats lazy evaluation)."""
    if lang != Language.PYTHON:
        return

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.match(r"logger\.\w+\(\s*f['\"]", stripped) or re.match(r"log\.\w+\(\s*f['\"]", stripped):
            result.add(Finding(
                severity=Severity.WARNING,
                category="fstring-logger",
                message="f-string in logger call defeats lazy evaluation. Use logger.info('msg', extra={...}) instead.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
            ))


def check_missing_exc_info(filepath: Path, lines: list[str], lang: Language, result: CheckResult) -> None:
    """Check for error logs missing exc_info=True (Python) or stack trace."""
    if lang == Language.PYTHON:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r"(logger|log)\.(error|exception|critical)\(", stripped):
                # Check if exc_info is present in this line or the next few lines
                context = "\n".join(lines[i - 1:min(i + 3, len(lines))])
                if "exc_info" not in context and "exception(" not in stripped:
                    # Check if we're inside an except block
                    for j in range(max(0, i - 5), i):
                        if "except" in lines[j]:
                            result.add(Finding(
                                severity=Severity.WARNING,
                                category="missing-exc-info",
                                message="Error log in except block without exc_info=True. Add exc_info=True to include traceback.",
                                file=str(filepath),
                                line=i,
                                snippet=stripped[:120],
                            ))
                            break


def check_inconsistent_logger_naming(filepath: Path, lines: list[str], lang: Language, result: CheckResult) -> None:
    """Check for inconsistent logger naming conventions."""
    if lang == Language.PYTHON:
        has_module_logger = False
        has_named_logger = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "getLogger(__name__)" in stripped:
                has_module_logger = True
            elif re.match(r"\w+\s*=\s*logging\.getLogger\(['\"]", stripped):
                has_named_logger = True
                result.add(Finding(
                    severity=Severity.INFO,
                    category="logger-naming",
                    message="Hardcoded logger name. Use logging.getLogger(__name__) for consistent naming.",
                    file=str(filepath),
                    line=i,
                    snippet=stripped[:120],
                ))

    elif lang == Language.JAVA:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Check for manual logger creation instead of @Slf4j
            if re.search(r"LoggerFactory\.getLogger\(", stripped):
                content = "\n".join(lines)
                if "@Slf4j" not in content:
                    result.add(Finding(
                        severity=Severity.INFO,
                        category="logger-naming",
                        message="Manual LoggerFactory.getLogger() call. Consider using @Slf4j annotation.",
                        file=str(filepath),
                        line=i,
                        snippet=stripped[:120],
                    ))


def check_catch_and_log_only(filepath: Path, lines: list[str], lang: Language, result: CheckResult) -> None:
    """Check for catch blocks that log but don't re-raise or handle."""
    if lang == Language.PYTHON:
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith("except") and ":" in stripped:
                # Look at the except block body
                block_lines = []
                indent = len(lines[i]) - len(lines[i].lstrip())
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() == "":
                        j += 1
                        continue
                    current_indent = len(lines[j]) - len(lines[j].lstrip())
                    if current_indent <= indent and lines[j].strip():
                        break
                    block_lines.append(lines[j].strip())
                    j += 1

                has_log = any("logger." in l or "logging." in l or "log." in l for l in block_lines)
                has_raise = any(l.startswith("raise") for l in block_lines)
                has_return = any(l.startswith("return") for l in block_lines)

                if has_log and not has_raise and not has_return and len(block_lines) <= 3:
                    result.add(Finding(
                        severity=Severity.WARNING,
                        category="catch-log-only",
                        message="Exception caught and logged but not re-raised or handled. This silently swallows errors.",
                        file=str(filepath),
                        line=i + 1,
                        snippet=stripped[:120],
                    ))
                i = j
            else:
                i += 1


def check_missing_log_level(filepath: Path, lines: list[str], lang: Language, result: CheckResult) -> None:
    """Check for incorrect log level usage."""
    if lang == Language.PYTHON:
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Check for logging.log() without level
            if re.match(r"logging\.(log|warn)\(", stripped):
                if "logging.warn(" in stripped:
                    result.add(Finding(
                        severity=Severity.INFO,
                        category="log-level",
                        message="Use logging.warning() instead of logging.warn() (deprecated).",
                        file=str(filepath),
                        line=i,
                        snippet=stripped[:120],
                    ))


def run_checks(project_dir: Path, language: str | None = None, verbose: bool = False) -> CheckResult:
    """Run all logging checks on the project."""
    result = CheckResult()
    files = find_source_files(project_dir, language)
    result.files_scanned = len(files)

    if verbose:
        print(f"Scanning {len(files)} source files...", file=sys.stderr)

    for filepath in files:
        lang = detect_language(filepath)
        if lang is None:
            continue

        lines = read_file(filepath)
        if not lines:
            continue

        if verbose:
            print(f"  Checking: {filepath.name}", file=sys.stderr)

        check_print_statements(filepath, lines, lang, result)
        check_sensitive_data(filepath, lines, lang, result)
        check_fstring_in_logger(filepath, lines, lang, result)
        check_missing_exc_info(filepath, lines, lang, result)
        check_inconsistent_logger_naming(filepath, lines, lang, result)
        check_catch_and_log_only(filepath, lines, lang, result)
        check_missing_log_level(filepath, lines, lang, result)

    return result


def format_text(result: CheckResult, project_dir: Path) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append(f"Logging Check: {project_dir}")
    lines.append("=" * 60)
    lines.append(f"Files scanned: {result.files_scanned}")

    summary = result.summary()
    lines.append(f"Findings: {summary['ERROR']} errors, {summary['WARNING']} warnings, {summary['INFO']} info")
    lines.append("-" * 60)

    if not result.findings:
        lines.append("\nNo logging issues found.")
        return "\n".join(lines)

    categories: dict[str, list[Finding]] = {}
    for f in result.findings:
        categories.setdefault(f.category, []).append(f)

    for category, findings in sorted(categories.items()):
        lines.append(f"\n[{category.upper().replace('-', ' ')}]")
        for f in findings:
            lines.append(f"  {f.severity.value:7s} {f.file}:{f.line}")
            lines.append(f"          {f.message}")
            if f.snippet:
                lines.append(f"          > {f.snippet}")

    return "\n".join(lines)


def format_json(result: CheckResult) -> str:
    """Format results as JSON."""
    return json.dumps({
        "files_scanned": result.files_scanned,
        "summary": result.summary(),
        "findings": [f.to_dict() for f in result.findings],
    }, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan code for logging issues: print statements, sensitive data, missing log levels, and more.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s . --language python
  %(prog)s /path/to/project --format json
  %(prog)s . --severity WARNING --verbose
        """,
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to the project directory to scan",
    )
    parser.add_argument(
        "--language", "-l",
        choices=["python", "javascript", "java"],
        default=None,
        help="Limit scan to a specific language (default: all supported)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--severity", "-s",
        choices=["ERROR", "WARNING", "INFO"],
        default="INFO",
        help="Minimum severity to report (default: INFO)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show progress during scan",
    )

    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = run_checks(project_dir, language=args.language, verbose=args.verbose)

    # Filter by severity
    severity_order = {"ERROR": 3, "WARNING": 2, "INFO": 1}
    min_severity = severity_order[args.severity]
    result.findings = [
        f for f in result.findings
        if severity_order[f.severity.value] >= min_severity
    ]

    if args.format == "json":
        print(format_json(result))
    else:
        print(format_text(result, project_dir))

    if any(f.severity == Severity.ERROR for f in result.findings):
        sys.exit(1)


if __name__ == "__main__":
    main()
