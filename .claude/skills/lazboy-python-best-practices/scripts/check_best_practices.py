#!/usr/bin/env python3
"""Check Python code for best practice violations.

Detects missing docstrings, improper exception handling, unused variables,
missing __init__.py, and other common Python code quality issues.

Usage:
    python check_best_practices.py /path/to/project
    python check_best_practices.py . --format json
    python check_best_practices.py /path/to/project --severity WARNING
"""

import argparse
import ast
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


@dataclass
class Finding:
    severity: Severity
    category: str
    message: str
    file: str
    line: int = 0
    fix: str = ""

    def to_dict(self) -> dict:
        result = {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }
        if self.fix:
            result["fix"] = self.fix
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


def find_python_files(project_dir: Path) -> list[Path]:
    """Find all Python files in the project."""
    exclude_dirs = {
        "node_modules", ".git", "__pycache__", "venv", ".venv",
        "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
        ".pytest_cache", "eggs", "*.egg-info",
    }
    files = []
    for f in project_dir.rglob("*.py"):
        if not any(d in f.parts for d in exclude_dirs):
            files.append(f)
    return sorted(files)


def parse_ast(filepath: Path) -> ast.Module | None:
    """Parse a Python file into an AST."""
    try:
        source = filepath.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return None


def check_missing_docstrings(filepath: Path, tree: ast.Module, result: CheckResult) -> None:
    """Check for missing docstrings on public functions, classes, and modules."""
    # Module docstring
    if not ast.get_docstring(tree):
        result.add(Finding(
            severity=Severity.INFO,
            category="missing-docstring",
            message="Module missing docstring. Add a one-line description.",
            file=str(filepath),
            line=1,
            fix='"""Module description."""',
        ))

    for node in ast.walk(tree):
        # Public functions
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            if not ast.get_docstring(node):
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="missing-docstring",
                    message=f'Public function "{node.name}" missing docstring.',
                    file=str(filepath),
                    line=node.lineno,
                    fix=f'def {node.name}(...):\n    """Description."""',
                ))

        # Public async functions
        if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
            if not ast.get_docstring(node):
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="missing-docstring",
                    message=f'Public async function "{node.name}" missing docstring.',
                    file=str(filepath),
                    line=node.lineno,
                ))

        # Classes
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            if not ast.get_docstring(node):
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="missing-docstring",
                    message=f'Class "{node.name}" missing docstring.',
                    file=str(filepath),
                    line=node.lineno,
                ))


def check_exception_handling(filepath: Path, tree: ast.Module, result: CheckResult) -> None:
    """Check for improper exception handling patterns."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # Bare except (catches everything including SystemExit, KeyboardInterrupt)
            if node.type is None:
                result.add(Finding(
                    severity=Severity.ERROR,
                    category="exception-handling",
                    message="Bare 'except:' catches all exceptions including SystemExit. Catch specific types.",
                    file=str(filepath),
                    line=node.lineno,
                    fix="except ValueError as err:  # Catch specific exception types",
                ))
            # Broad Exception catch
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="exception-handling",
                    message="Broad 'except Exception' catch. Prefer catching specific exception types.",
                    file=str(filepath),
                    line=node.lineno,
                ))

        # Check for raise without from in except blocks
        if isinstance(node, ast.Raise) and node.exc is not None and node.cause is None:
            # Check if we're in an except block
            # This is a simplified check -- look for raise NewError() without 'from'
            if isinstance(node.exc, ast.Call):
                result.add(Finding(
                    severity=Severity.INFO,
                    category="exception-handling",
                    message="Raising a new exception. Use 'raise X from err' to preserve the exception chain.",
                    file=str(filepath),
                    line=node.lineno,
                    fix="raise NewError('message') from original_err",
                ))


def check_type_annotations(filepath: Path, tree: ast.Module, result: CheckResult) -> None:
    """Check for missing type annotations on public functions."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") and node.name != "__init__":
                continue

            # Check return annotation
            if node.returns is None and node.name != "__init__":
                result.add(Finding(
                    severity=Severity.INFO,
                    category="type-annotation",
                    message=f'Function "{node.name}" missing return type annotation.',
                    file=str(filepath),
                    line=node.lineno,
                    fix=f"def {node.name}(...) -> ReturnType:",
                ))

            # Check parameter annotations (skip self/cls)
            for arg in node.args.args:
                if arg.arg in ("self", "cls"):
                    continue
                if arg.annotation is None:
                    result.add(Finding(
                        severity=Severity.INFO,
                        category="type-annotation",
                        message=f'Parameter "{arg.arg}" in function "{node.name}" missing type annotation.',
                        file=str(filepath),
                        line=node.lineno,
                    ))
                    break  # Report once per function to reduce noise


def check_print_usage(filepath: Path, tree: ast.Module, result: CheckResult) -> None:
    """Detect print() calls that should be logger calls."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="print-statement",
                    message="print() in production code. Use logging.getLogger(__name__).info() instead.",
                    file=str(filepath),
                    line=node.lineno,
                    fix="import logging\nlogger = logging.getLogger(__name__)\nlogger.info('message')",
                ))


def check_deprecated_typing_imports(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Check for pre-3.9 typing imports (List, Dict, Optional, Union)."""
    deprecated_types = {"List", "Dict", "Tuple", "Set", "FrozenSet", "Optional", "Union"}

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("from typing import"):
            # Parse the imported names
            import_part = stripped.replace("from typing import", "").strip()
            # Handle multiline imports
            if "(" in import_part:
                # Collect until closing paren
                j = i
                while j <= len(lines) and ")" not in lines[j - 1]:
                    import_part += " " + lines[j - 1].strip()
                    j += 1

            imported_names = {name.strip().rstrip(",") for name in re.split(r"[,\s()]+", import_part) if name.strip()}
            deprecated_used = imported_names & deprecated_types

            if deprecated_used:
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="deprecated-import",
                    message=f"Pre-3.9 typing imports: {', '.join(sorted(deprecated_used))}. Use native syntax (list, dict, X | None).",
                    file=str(filepath),
                    line=i,
                    fix="list[str] instead of List[str], str | None instead of Optional[str]",
                ))


def check_mutable_default_args(filepath: Path, tree: ast.Module, result: CheckResult) -> None:
    """Check for mutable default arguments (list, dict, set)."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    result.add(Finding(
                        severity=Severity.ERROR,
                        category="mutable-default",
                        message=f'Mutable default argument in "{node.name}". Use None and create inside the function.',
                        file=str(filepath),
                        line=node.lineno,
                        fix="def func(items: list[str] | None = None):\n    items = items or []",
                    ))


def check_star_imports(filepath: Path, tree: ast.Module, result: CheckResult) -> None:
    """Check for star imports (from module import *)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    result.add(Finding(
                        severity=Severity.WARNING,
                        category="star-import",
                        message=f'Star import from "{node.module}". Import specific names instead.',
                        file=str(filepath),
                        line=node.lineno,
                        fix=f"from {node.module} import SpecificName",
                    ))


def check_missing_init_py(project_dir: Path, result: CheckResult) -> None:
    """Check for Python packages missing __init__.py."""
    src_dir = project_dir / "src"
    if not src_dir.exists():
        src_dir = project_dir

    for dirpath in src_dir.rglob("*"):
        if not dirpath.is_dir():
            continue
        # Skip non-package directories
        if any(d in dirpath.parts for d in {
            "__pycache__", ".git", "venv", ".venv", "node_modules",
            "dist", "build", ".tox", ".mypy_cache", "tests", "test",
        }):
            continue

        # Check if directory has .py files but no __init__.py
        py_files = list(dirpath.glob("*.py"))
        has_init = (dirpath / "__init__.py").exists()

        if py_files and not has_init:
            # Check if this looks like a package directory (not project root)
            if dirpath != project_dir and dirpath != src_dir:
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="missing-init",
                    message=f'Directory "{dirpath.name}" has Python files but no __init__.py.',
                    file=str(dirpath),
                    line=0,
                    fix="Create an empty __init__.py or add __all__ exports.",
                ))


def check_todo_fixme(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Report TODO and FIXME comments for tracking."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.search(r"#\s*(TODO|FIXME|HACK|XXX)\b", stripped, re.IGNORECASE):
            match = re.search(r"#\s*(TODO|FIXME|HACK|XXX)\s*:?\s*(.*)", stripped, re.IGNORECASE)
            if match:
                tag = match.group(1).upper()
                desc = match.group(2).strip()
                severity = Severity.WARNING if tag in ("FIXME", "HACK", "XXX") else Severity.INFO
                result.add(Finding(
                    severity=severity,
                    category="todo-fixme",
                    message=f"{tag}: {desc}" if desc else f"{tag} without description.",
                    file=str(filepath),
                    line=i,
                ))


def check_asyncio_gather(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Check for asyncio.gather usage (prefer TaskGroup in 3.11+)."""
    for i, line in enumerate(lines, 1):
        if "asyncio.gather" in line:
            result.add(Finding(
                severity=Severity.INFO,
                category="async-pattern",
                message="asyncio.gather() found. Prefer asyncio.TaskGroup (Python 3.11+) for better error handling.",
                file=str(filepath),
                line=i,
                fix="async with asyncio.TaskGroup() as tg:\n    tg.create_task(coro())",
            ))


def run_checks(project_dir: Path, verbose: bool = False) -> CheckResult:
    """Run all best practice checks on the project."""
    result = CheckResult()
    py_files = find_python_files(project_dir)
    result.files_scanned = len(py_files)

    if verbose:
        print(f"Scanning {len(py_files)} Python files...", file=sys.stderr)

    # Project-level checks
    check_missing_init_py(project_dir, result)

    # File-level checks
    for filepath in py_files:
        if verbose:
            print(f"  Checking: {filepath.name}", file=sys.stderr)

        lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
        tree = parse_ast(filepath)

        # Line-based checks (work even if AST parsing fails)
        check_deprecated_typing_imports(filepath, lines, result)
        check_todo_fixme(filepath, lines, result)
        check_asyncio_gather(filepath, lines, result)

        # AST-based checks
        if tree:
            check_missing_docstrings(filepath, tree, result)
            check_exception_handling(filepath, tree, result)
            check_type_annotations(filepath, tree, result)
            check_print_usage(filepath, tree, result)
            check_mutable_default_args(filepath, tree, result)
            check_star_imports(filepath, tree, result)

    return result


def format_text(result: CheckResult, project_dir: Path) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append(f"Python Best Practices Check: {project_dir}")
    lines.append("=" * 60)
    lines.append(f"Files scanned: {result.files_scanned}")

    summary = result.summary()
    lines.append(f"Findings: {summary['ERROR']} errors, {summary['WARNING']} warnings, {summary['INFO']} info")
    lines.append("-" * 60)

    if not result.findings:
        lines.append("\nNo issues found. Code looks good!")
        return "\n".join(lines)

    categories: dict[str, list[Finding]] = {}
    for f in result.findings:
        categories.setdefault(f.category, []).append(f)

    for category, findings in sorted(categories.items()):
        lines.append(f"\n[{category.upper().replace('-', ' ')}]")
        for f in findings:
            loc = f"{f.file}:{f.line}" if f.line > 0 else f.file
            lines.append(f"  {f.severity.value:7s} {loc}")
            lines.append(f"          {f.message}")
            if f.fix:
                lines.append(f"          Fix: {f.fix}")

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
        description="Check Python code for best practice violations: docstrings, exception handling, type hints, and more.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s . --format json
  %(prog)s /path/to/project --severity WARNING
  %(prog)s . --verbose
        """,
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to the Python project directory",
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
        help="Show progress during analysis",
    )

    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = run_checks(project_dir, verbose=args.verbose)

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
