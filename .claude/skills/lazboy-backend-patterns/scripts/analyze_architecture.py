#!/usr/bin/env python3
"""
Analyze a Node.js/Express project structure for architectural patterns.

Checks for proper layering (routes/controllers/services/repositories),
identifies anti-patterns like business logic in controllers, and reports
structural issues.

Usage:
    python analyze_architecture.py /path/to/project
    python analyze_architecture.py /path/to/project --strict
    python analyze_architecture.py /path/to/project --json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    severity: str
    category: str
    message: str
    file: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ArchitectureReport:
    project_path: str
    has_layered_architecture: bool = False
    layers_found: list = field(default_factory=list)
    layers_missing: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    file_count: int = 0
    summary: dict = field(default_factory=dict)


# --- Detection patterns ---

EXPECTED_LAYERS = {
    "routes": ["routes", "router", "api"],
    "controllers": ["controllers", "controller", "handlers"],
    "services": ["services", "service"],
    "repositories": ["repositories", "repository", "repos", "dal", "data"],
}

LAYER_ALTERNATIVES = {
    "middleware": ["middleware", "middlewares"],
    "validators": ["validators", "validation", "schemas"],
    "errors": ["errors", "exceptions"],
    "types": ["types", "interfaces", "models"],
    "utils": ["utils", "lib", "helpers", "shared"],
    "config": ["config", "configuration"],
}

# Patterns that indicate business logic in a controller
BUSINESS_LOGIC_IN_CONTROLLER_PATTERNS = [
    (r'\.from\s*\(\s*[\'"]', "Direct database query in controller"),
    (r'\.query\s*\(\s*[\'"`](?:SELECT|INSERT|UPDATE|DELETE)', "Raw SQL query in controller"),
    (r'\.find(?:One|Many|ById|All)\s*\(', "Direct repository call in controller"),
    (r'\.save\s*\(', "Direct ORM save call in controller"),
    (r'\.create\s*\(\s*\{', "Direct ORM create call in controller"),
    (r'\.aggregate\s*\(\s*\[', "Direct aggregation pipeline in controller"),
    (r'if\s*\(.*\.length\s*[><=]', "Collection length check (business logic) in controller"),
    (r'for\s*\(\s*(?:const|let|var)\s+\w+\s+of\s+', "Iteration (business logic) in controller"),
]

# Patterns for common anti-patterns
ANTI_PATTERNS = {
    "select_star": (
        r'\.select\s*\(\s*[\'\"]\*[\'\"]',
        "Using SELECT * instead of selecting specific columns",
    ),
    "raw_sql_concat": (
        r'[\'"`]\s*(?:SELECT|INSERT|UPDATE|DELETE).*\$\{',
        "SQL string concatenation — risk of SQL injection",
    ),
    "console_log": (
        r'console\.\s*log\s*\(',
        "console.log in production code — use a structured logger",
    ),
    "any_type": (
        r':\s*any\b',
        "Using 'any' type — use proper interfaces or 'unknown'",
    ),
    "no_error_handling": (
        r'\.catch\s*\(\s*\(\s*\)\s*=>\s*\{\s*\}\s*\)',
        "Empty catch handler — errors are silently swallowed",
    ),
    "hardcoded_secret": (
        r'(?:password|secret|api_key|apiKey|token)\s*[=:]\s*[\'"][^\'"]{8,}[\'"]',
        "Possible hardcoded secret — use environment variables",
    ),
}

# File size thresholds
MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 50


def find_src_root(project_path: Path) -> Path:
    """Find the source root (src/ directory or project root)."""
    src_dir = project_path / "src"
    if src_dir.is_dir():
        return src_dir
    app_dir = project_path / "app"
    if app_dir.is_dir():
        return app_dir
    return project_path


def scan_directory_structure(src_root: Path) -> dict:
    """Scan for recognized architectural directories."""
    found = {}
    if not src_root.is_dir():
        return found

    for item in src_root.iterdir():
        if not item.is_dir():
            continue
        name = item.name.lower()
        for layer, aliases in {**EXPECTED_LAYERS, **LAYER_ALTERNATIVES}.items():
            if name in aliases:
                found[layer] = item
                break
    return found


def get_ts_js_files(directory: Path) -> list:
    """Recursively collect .ts, .tsx, .js, .jsx files, excluding tests and node_modules."""
    files = []
    if not directory.is_dir():
        return files

    exclude_dirs = {"node_modules", ".next", "dist", "build", "__tests__", "coverage", ".git"}
    exclude_patterns = {".test.", ".spec.", ".d.ts"}

    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for fname in filenames:
            if not any(fname.endswith(ext) for ext in (".ts", ".tsx", ".js", ".jsx")):
                continue
            if any(pat in fname for pat in exclude_patterns):
                continue
            files.append(Path(root) / fname)
    return files


def read_file_safe(filepath: Path) -> str:
    """Read file contents, handling encoding errors."""
    try:
        return filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return ""


def check_controller_antipatterns(filepath: Path, content: str) -> list:
    """Check for business logic patterns in controller files."""
    findings = []
    rel_path = str(filepath)
    lines = content.splitlines()

    for i, line in enumerate(lines, start=1):
        for pattern, message in BUSINESS_LOGIC_IN_CONTROLLER_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append(Finding(
                    severity=Severity.WARNING.value,
                    category="layering",
                    message=message,
                    file=rel_path,
                    line=i,
                    suggestion="Move this logic to the service layer",
                ))
                break  # One finding per line

    return findings


def check_antipatterns(filepath: Path, content: str) -> list:
    """Check for general anti-patterns in any source file."""
    findings = []
    rel_path = str(filepath)
    lines = content.splitlines()

    for i, line in enumerate(lines, start=1):
        for name, (pattern, message) in ANTI_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                severity = Severity.ERROR.value if name in ("raw_sql_concat", "hardcoded_secret") else Severity.WARNING.value
                findings.append(Finding(
                    severity=severity,
                    category="anti-pattern",
                    message=message,
                    file=rel_path,
                    line=i,
                ))

    return findings


def check_file_size(filepath: Path, content: str) -> list:
    """Check if the file exceeds recommended line count."""
    findings = []
    lines = content.splitlines()
    if len(lines) > MAX_FILE_LINES:
        findings.append(Finding(
            severity=Severity.WARNING.value,
            category="complexity",
            message=f"File has {len(lines)} lines (recommended max: {MAX_FILE_LINES})",
            file=str(filepath),
            suggestion="Consider splitting into smaller, focused modules",
        ))
    return findings


def check_function_length(filepath: Path, content: str) -> list:
    """Check for functions exceeding the recommended line count."""
    findings = []
    func_pattern = re.compile(
        r'(?:export\s+)?(?:async\s+)?function\s+(\w+)|'
        r'(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(?.*?\)?\s*=>'
    )
    lines = content.splitlines()

    # Simple heuristic: track brace depth for each function
    in_function = False
    func_name = ""
    func_start = 0
    brace_depth = 0

    for i, line in enumerate(lines, start=1):
        if not in_function:
            match = func_pattern.search(line)
            if match:
                func_name = match.group(1) or match.group(2) or "anonymous"
                func_start = i
                brace_depth = line.count("{") - line.count("}")
                if brace_depth > 0:
                    in_function = True
        else:
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                func_length = i - func_start
                if func_length > MAX_FUNCTION_LINES:
                    findings.append(Finding(
                        severity=Severity.WARNING.value,
                        category="complexity",
                        message=f"Function '{func_name}' is {func_length} lines (recommended max: {MAX_FUNCTION_LINES})",
                        file=str(filepath),
                        line=func_start,
                        suggestion="Break into smaller, focused functions",
                    ))
                in_function = False

    return findings


def is_controller_file(filepath: Path) -> bool:
    """Determine if a file is a controller based on its path or name."""
    path_str = str(filepath).lower()
    return "controller" in path_str or "handler" in path_str


def analyze_project(project_path: Path, strict: bool = False) -> ArchitectureReport:
    """Run the full architectural analysis."""
    report = ArchitectureReport(project_path=str(project_path))

    src_root = find_src_root(project_path)
    if not src_root.is_dir():
        report.findings.append(Finding(
            severity=Severity.ERROR.value,
            category="structure",
            message="Could not find source directory (src/ or project root)",
            file=str(project_path),
        ))
        return report

    # 1. Scan directory structure
    found_dirs = scan_directory_structure(src_root)
    for layer in EXPECTED_LAYERS:
        if layer in found_dirs:
            report.layers_found.append(layer)
        else:
            report.layers_missing.append(layer)

    report.has_layered_architecture = len(report.layers_found) >= 3

    if not report.has_layered_architecture:
        report.findings.append(Finding(
            severity=Severity.WARNING.value,
            category="structure",
            message=f"Incomplete layered architecture. Found: {report.layers_found}. Missing: {report.layers_missing}",
            file=str(src_root),
            suggestion="Organize code into controllers/, services/, repositories/ directories",
        ))

    # Check for bonus layers
    for layer_name, layer_path in found_dirs.items():
        if layer_name in LAYER_ALTERNATIVES:
            report.findings.append(Finding(
                severity=Severity.INFO.value,
                category="structure",
                message=f"Found recommended directory: {layer_name}/ at {layer_path}",
                file=str(layer_path),
            ))

    # 2. Scan source files
    all_files = get_ts_js_files(src_root)
    report.file_count = len(all_files)

    for filepath in all_files:
        content = read_file_safe(filepath)
        if not content:
            continue

        # Check file size
        report.findings.extend(check_file_size(filepath, content))

        # Check function lengths
        report.findings.extend(check_function_length(filepath, content))

        # Check for general anti-patterns
        report.findings.extend(check_antipatterns(filepath, content))

        # Check controllers specifically for business logic
        if is_controller_file(filepath):
            report.findings.extend(check_controller_antipatterns(filepath, content))

    # 3. Build summary
    error_count = sum(1 for f in report.findings if f.severity == Severity.ERROR.value)
    warning_count = sum(1 for f in report.findings if f.severity == Severity.WARNING.value)
    info_count = sum(1 for f in report.findings if f.severity == Severity.INFO.value)

    report.summary = {
        "total_files_scanned": report.file_count,
        "layers_found": report.layers_found,
        "layers_missing": report.layers_missing,
        "has_layered_architecture": report.has_layered_architecture,
        "errors": error_count,
        "warnings": warning_count,
        "info": info_count,
    }

    return report


def format_text_report(report: ArchitectureReport) -> str:
    """Format the report as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("  ARCHITECTURE ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append(f"\nProject: {report.project_path}")
    lines.append(f"Files scanned: {report.file_count}")
    lines.append("")

    # Architecture status
    if report.has_layered_architecture:
        lines.append("[PASS] Layered architecture detected")
    else:
        lines.append("[FAIL] Layered architecture NOT detected")

    lines.append(f"  Layers found:   {', '.join(report.layers_found) or 'none'}")
    lines.append(f"  Layers missing: {', '.join(report.layers_missing) or 'none'}")
    lines.append("")

    # Findings grouped by severity
    for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO]:
        filtered = [f for f in report.findings if f.severity == severity.value]
        if not filtered:
            continue

        label = severity.value.upper()
        lines.append(f"\n--- {label}S ({len(filtered)}) ---\n")
        for f in filtered:
            loc = f.file
            if f.line:
                loc += f":{f.line}"
            lines.append(f"  [{label}] {f.category}: {f.message}")
            lines.append(f"         at {loc}")
            if f.suggestion:
                lines.append(f"         -> {f.suggestion}")
            lines.append("")

    # Summary
    s = report.summary
    lines.append("-" * 70)
    lines.append(f"  Errors: {s.get('errors', 0)}  |  Warnings: {s.get('warnings', 0)}  |  Info: {s.get('info', 0)}")
    lines.append("-" * 70)

    return "\n".join(lines)


def format_json_report(report: ArchitectureReport) -> str:
    """Format the report as JSON."""
    data = {
        "project_path": report.project_path,
        "has_layered_architecture": report.has_layered_architecture,
        "layers_found": report.layers_found,
        "layers_missing": report.layers_missing,
        "file_count": report.file_count,
        "summary": report.summary,
        "findings": [asdict(f) for f in report.findings],
    }
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a Node.js/Express project for architectural patterns and anti-patterns.",
    )
    parser.add_argument(
        "project_path",
        help="Path to the project root directory",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (non-zero exit code on warnings)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output report as JSON",
    )
    parser.add_argument(
        "--max-file-lines",
        type=int,
        default=MAX_FILE_LINES,
        help=f"Maximum recommended file length in lines (default: {MAX_FILE_LINES})",
    )
    parser.add_argument(
        "--max-function-lines",
        type=int,
        default=MAX_FUNCTION_LINES,
        help=f"Maximum recommended function length in lines (default: {MAX_FUNCTION_LINES})",
    )

    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.is_dir():
        print(f"Error: '{project_path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Apply custom thresholds
    global MAX_FILE_LINES, MAX_FUNCTION_LINES
    MAX_FILE_LINES = args.max_file_lines
    MAX_FUNCTION_LINES = args.max_function_lines

    report = analyze_project(project_path, strict=args.strict)

    if args.output_json:
        print(format_json_report(report))
    else:
        print(format_text_report(report))

    # Exit code
    error_count = report.summary.get("errors", 0)
    warning_count = report.summary.get("warnings", 0)

    if error_count > 0:
        sys.exit(1)
    if args.strict and warning_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
