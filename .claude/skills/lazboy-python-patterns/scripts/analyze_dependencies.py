#!/usr/bin/env python3
"""
analyze_dependencies.py -- Analyze Python project dependencies.

Features:
  - Check for pinned vs unpinned versions in requirements files
  - Identify unused imports across the project
  - Detect circular imports between modules
  - Check for packages with known vulnerabilities (basic heuristic)
  - Validate pyproject.toml dependency specifications
"""

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DependencyIssue:
    """A single dependency-related issue."""
    category: str
    severity: str
    message: str
    file: str = ""
    line: int = 0

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.file else "project"
        return f"[{self.severity}] ({self.category}) {loc}: {self.message}"


@dataclass
class AnalysisReport:
    """Complete dependency analysis report."""
    issues: list[DependencyIssue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add(self, issue: DependencyIssue) -> None:
        self.issues.append(issue)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# -- Version Pinning Analysis -------------------------------------------------

def parse_requirements_file(filepath: str) -> list[tuple[str, str, int]]:
    """Parse a requirements.txt file, returning (package, specifier, line_no) tuples."""
    entries = []
    try:
        lines = Path(filepath).read_text(encoding="utf-8").splitlines()
    except OSError:
        return entries

    for lineno, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Handle environment markers
        line = line.split(";")[0].strip()
        # Match package name and version specifier
        match = re.match(r"^([a-zA-Z0-9_.-]+)\s*(.*)", line)
        if match:
            pkg = match.group(1).lower()
            spec = match.group(2).strip()
            entries.append((pkg, spec, lineno))
    return entries


def check_version_pinning(filepath: str, report: AnalysisReport) -> None:
    """Check if dependencies are properly pinned."""
    entries = parse_requirements_file(filepath)
    if not entries:
        return

    pinned = 0
    unpinned = 0

    for pkg, spec, lineno in entries:
        if not spec:
            report.add(DependencyIssue(
                category="pinning", severity="warning",
                message=f"Package '{pkg}' has no version constraint.",
                file=filepath, line=lineno,
            ))
            unpinned += 1
        elif spec.startswith("=="):
            pinned += 1
        elif spec.startswith(">=") and "<" not in spec:
            report.add(DependencyIssue(
                category="pinning", severity="warning",
                message=f"Package '{pkg}' has no upper bound: {spec}. "
                        "Consider adding an upper bound (e.g., >=1.0,<2.0).",
                file=filepath, line=lineno,
            ))
            unpinned += 1
        else:
            pinned += 1

    report.stats["pinned_deps"] = pinned
    report.stats["unpinned_deps"] = unpinned


def check_pyproject_dependencies(filepath: str, report: AnalysisReport) -> None:
    """Check pyproject.toml for dependency issues."""
    try:
        content = Path(filepath).read_text(encoding="utf-8")
    except OSError:
        return

    # Basic TOML parsing for dependencies section
    in_deps = False
    in_optional = False
    lineno = 0
    for line in content.splitlines():
        lineno += 1
        stripped = line.strip()

        if stripped == "[project]":
            continue
        if stripped.startswith("dependencies"):
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            in_deps = False
            continue

        if in_deps and stripped.startswith('"'):
            dep = stripped.strip('",')
            # Check for unpinned
            if re.match(r'^[a-zA-Z0-9_.-]+$', dep):
                report.add(DependencyIssue(
                    category="pinning", severity="warning",
                    message=f"Package '{dep}' in pyproject.toml has no version constraint.",
                    file=filepath, line=lineno,
                ))


# -- Unused Imports Detection -------------------------------------------------

class ImportCollector(ast.NodeVisitor):
    """Collect all imports and name usages from a Python file."""

    def __init__(self) -> None:
        self.imports: list[tuple[str, str, int]] = []  # (module, alias, lineno)
        self.used_names: set[str] = set()
        self._in_import = False

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.imports.append((alias.name, name, node.lineno))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            full = f"{module}.{alias.name}" if module else alias.name
            self.imports.append((full, name, node.lineno))

    def visit_Name(self, node: ast.Name) -> None:
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.used_names.add(node.attr)
        self.generic_visit(node)


def find_unused_imports(filepath: str, report: AnalysisReport) -> list[tuple[str, int]]:
    """Find imports that are never referenced in the file."""
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filepath)
    except (OSError, SyntaxError):
        return []

    collector = ImportCollector()
    collector.visit(tree)

    unused = []
    for module, alias, lineno in collector.imports:
        # Skip __all__ re-exports, TYPE_CHECKING imports, etc.
        if alias in collector.used_names:
            continue
        # Check if module name itself is used (e.g., import os; os.path)
        base = module.split(".")[0]
        if base in collector.used_names:
            continue
        unused.append((module, lineno))
        report.add(DependencyIssue(
            category="unused-import", severity="warning",
            message=f"Unused import: '{module}'.",
            file=filepath, line=lineno,
        ))
    return unused


# -- Circular Import Detection ------------------------------------------------

def build_import_graph(project_root: str, exclude: list[str]) -> dict[str, set[str]]:
    """Build a module-level import dependency graph."""
    graph: dict[str, set[str]] = defaultdict(set)
    root = Path(project_root)
    exclude_set = set(exclude)

    for pyfile in root.rglob("*.py"):
        parts = pyfile.parts
        if any(ex in parts for ex in exclude_set):
            continue

        try:
            source = pyfile.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue

        # Derive module name from file path
        try:
            rel = pyfile.relative_to(root)
        except ValueError:
            continue
        module_parts = list(rel.parts)
        if module_parts[-1] == "__init__.py":
            module_parts = module_parts[:-1]
        else:
            module_parts[-1] = module_parts[-1].replace(".py", "")
        module_name = ".".join(module_parts)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    graph[module_name].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    graph[module_name].add(node.module)
                elif node.module and node.level > 0:
                    # Relative import -- resolve relative to current package
                    parent_parts = module_parts[:-node.level] if node.level <= len(module_parts) else []
                    resolved = ".".join(parent_parts + [node.module]) if parent_parts else node.module
                    graph[module_name].add(resolved)

    return dict(graph)


def find_circular_imports(graph: dict[str, set[str]]) -> list[list[str]]:
    """Find all circular import chains using DFS."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    path: list[str] = []
    on_path: set[str] = set()

    def dfs(node: str) -> None:
        if node in on_path:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            # Normalize to avoid duplicates
            min_idx = cycle.index(min(cycle[:-1]))
            normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
            if normalized not in cycles:
                cycles.append(normalized)
            return
        if node in visited:
            return

        visited.add(node)
        on_path.add(node)
        path.append(node)

        for dep in graph.get(node, set()):
            if dep in graph:  # Only follow internal modules
                dfs(dep)

        path.pop()
        on_path.remove(node)

    for module in graph:
        dfs(module)

    return cycles


# -- Known Vulnerability Check ------------------------------------------------

# Basic list of packages with historically known issues.
# In production, use Safety DB, OSV, or pip-audit.
KNOWN_VULNERABLE: dict[str, dict] = {
    "pyyaml": {"below": "5.4", "cve": "CVE-2020-14343", "desc": "Arbitrary code execution via yaml.load()"},
    "urllib3": {"below": "1.26.5", "cve": "CVE-2021-33503", "desc": "ReDoS vulnerability"},
    "requests": {"below": "2.25.0", "cve": "CVE-2023-32681", "desc": "Proxy credential leak"},
    "django": {"below": "3.2.25", "cve": "CVE-2024-27351", "desc": "ReDoS in Truncator"},
    "flask": {"below": "2.3.2", "cve": "CVE-2023-30861", "desc": "Session cookie security"},
    "cryptography": {"below": "41.0.0", "cve": "CVE-2023-38325", "desc": "PKCS7 certificate parsing"},
    "pillow": {"below": "10.0.1", "cve": "CVE-2023-44271", "desc": "DoS via large images"},
    "jinja2": {"below": "3.1.3", "cve": "CVE-2024-22195", "desc": "XSS via xmlattr filter"},
    "setuptools": {"below": "65.5.1", "cve": "CVE-2022-40897", "desc": "ReDoS in package_index"},
    "certifi": {"below": "2023.7.22", "cve": "CVE-2023-37920", "desc": "Removed e-Tugra root certificate"},
}


def _parse_version(v: str) -> tuple:
    """Parse a version string into a comparable tuple."""
    parts = []
    for p in re.split(r'[.\-]', v):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_known_vulnerabilities(filepath: str, report: AnalysisReport) -> None:
    """Check requirements file for packages with known vulnerabilities."""
    entries = parse_requirements_file(filepath)
    for pkg, spec, lineno in entries:
        pkg_lower = pkg.lower().replace("-", "").replace("_", "")
        for vuln_pkg, info in KNOWN_VULNERABLE.items():
            vuln_key = vuln_pkg.replace("-", "").replace("_", "")
            if pkg_lower != vuln_key:
                continue
            # Extract version if pinned
            version_match = re.search(r'[=<>!]+\s*([\d.]+)', spec)
            if version_match:
                installed = version_match.group(1)
                if _parse_version(installed) < _parse_version(info["below"]):
                    report.add(DependencyIssue(
                        category="vulnerability", severity="error",
                        message=f"'{pkg}=={installed}' has known vulnerability "
                                f"{info['cve']}: {info['desc']}. Upgrade to >= {info['below']}.",
                        file=filepath, line=lineno,
                    ))
            elif not spec:
                report.add(DependencyIssue(
                    category="vulnerability", severity="warning",
                    message=f"'{pkg}' has known vulnerabilities in older versions. "
                            f"Pin to >= {info['below']} to ensure safety ({info['cve']}).",
                    file=filepath, line=lineno,
                ))


# -- Main Entry Point ---------------------------------------------------------

def find_requirements_files(root: str) -> list[str]:
    """Locate requirements files in the project."""
    patterns = [
        "requirements.txt",
        "requirements/*.txt",
        "requirements-*.txt",
        "requirements_*.txt",
    ]
    found = []
    root_path = Path(root)
    for pattern in patterns:
        found.extend(str(p) for p in root_path.glob(pattern))
    # Also check pyproject.toml
    pyproject = root_path / "pyproject.toml"
    if pyproject.exists():
        found.append(str(pyproject))
    return sorted(set(found))


def collect_python_files(root: str, exclude: list[str]) -> list[str]:
    """Collect all Python files in the project."""
    exclude_set = set(exclude)
    files = []
    for pyfile in Path(root).rglob("*.py"):
        if any(ex in pyfile.parts for ex in exclude_set):
            continue
        files.append(str(pyfile))
    return sorted(files)


def print_report(report: AnalysisReport, format: str = "text") -> None:
    """Print the analysis report."""
    if format == "json":
        output = {
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "message": i.message,
                    "file": i.file,
                    "line": i.line,
                }
                for i in report.issues
            ],
            "stats": report.stats,
            "summary": {
                "total": len(report.issues),
                "errors": report.error_count,
                "warnings": report.warning_count,
            },
        }
        print(json.dumps(output, indent=2))
        return

    # Group by category
    by_category: dict[str, list[DependencyIssue]] = defaultdict(list)
    for issue in report.issues:
        by_category[issue.category].append(issue)

    category_labels = {
        "pinning": "Version Pinning",
        "unused-import": "Unused Imports",
        "circular-import": "Circular Imports",
        "vulnerability": "Known Vulnerabilities",
    }

    for category, issues in sorted(by_category.items()):
        label = category_labels.get(category, category)
        print(f"\n{'=' * 60}")
        print(f" {label} ({len(issues)} issue(s))")
        print(f"{'=' * 60}")
        for issue in sorted(issues, key=lambda i: (i.file, i.line)):
            color = "\033[31m" if issue.severity == "error" else "\033[33m"
            reset = "\033[0m"
            print(f"  {color}{issue}{reset}")

    print(f"\n{'─' * 60}")
    print(f"Total: {len(report.issues)} issue(s) "
          f"({report.error_count} errors, {report.warning_count} warnings)")
    if report.stats:
        for k, v in report.stats.items():
            print(f"  {k}: {v}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Python project dependencies for issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Analysis categories:
  pinning         Check for unpinned or loosely-pinned dependencies
  unused-import   Find imports that are never used in each file
  circular        Detect circular import chains between modules
  vulnerability   Flag packages with known security vulnerabilities

Examples:
  %(prog)s .                          Analyze current directory
  %(prog)s --check pinning vuln .     Only check pinning and vulnerabilities
  %(prog)s --format json src/         Output as JSON
""",
    )
    parser.add_argument(
        "root", nargs="?", default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--check", nargs="*",
        choices=["pinning", "unused", "circular", "vuln", "all"],
        default=["all"],
        help="Which checks to run (default: all)",
    )
    parser.add_argument(
        "--exclude", nargs="*",
        default=["__pycache__", ".venv", "venv", ".git", "node_modules", ".tox", ".mypy_cache"],
        help="Directories to exclude",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--fail-on-error", action="store_true",
        help="Exit with code 1 if any errors are found",
    )

    args = parser.parse_args()
    checks = set(args.check)
    run_all = "all" in checks
    report = AnalysisReport()

    root = os.path.abspath(args.root)
    if not Path(root).is_dir():
        print(f"Error: '{root}' is not a directory.", file=sys.stderr)
        return 1

    # Find requirements files
    req_files = find_requirements_files(root)

    # 1. Version pinning check
    if run_all or "pinning" in checks:
        for req_file in req_files:
            if req_file.endswith(".toml"):
                check_pyproject_dependencies(req_file, report)
            else:
                check_version_pinning(req_file, report)

    # 2. Known vulnerabilities
    if run_all or "vuln" in checks:
        for req_file in req_files:
            if not req_file.endswith(".toml"):
                check_known_vulnerabilities(req_file, report)

    # 3. Unused imports
    if run_all or "unused" in checks:
        py_files = collect_python_files(root, args.exclude)
        report.stats["python_files_scanned"] = len(py_files)
        for pyfile in py_files:
            find_unused_imports(pyfile, report)

    # 4. Circular imports
    if run_all or "circular" in checks:
        graph = build_import_graph(root, args.exclude)
        cycles = find_circular_imports(graph)
        report.stats["modules_in_graph"] = len(graph)
        for cycle in cycles:
            chain = " -> ".join(cycle)
            report.add(DependencyIssue(
                category="circular-import", severity="error",
                message=f"Circular import chain: {chain}",
            ))

    if not report.issues:
        print("No dependency issues found.")
        return 0

    print_report(report, format=args.format)

    if args.fail_on_error and report.error_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
