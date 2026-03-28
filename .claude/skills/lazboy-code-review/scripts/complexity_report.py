#!/usr/bin/env python3
"""
Cyclomatic complexity report generator.

Analyzes Python files using AST parsing and JavaScript/TypeScript files using
regex-based heuristics to estimate cyclomatic complexity per function.

Usage:
    python complexity_report.py /path/to/directory
    python complexity_report.py /path/to/directory --threshold 10 --json
"""

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD = 10  # Flag functions at or above this complexity

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "coverage", ".terraform", ".eggs",
    "vendor", "target",
}

PYTHON_EXTENSIONS = {".py"}
JS_TS_EXTENSIONS = {".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FunctionComplexity:
    file: str
    function_name: str
    line: int
    complexity: int
    language: str

    @property
    def rating(self) -> str:
        if self.complexity <= 5:
            return "A"  # Simple
        elif self.complexity <= 10:
            return "B"  # Moderate
        elif self.complexity <= 20:
            return "C"  # Complex
        elif self.complexity <= 50:
            return "D"  # Very complex
        else:
            return "F"  # Untestable


# ---------------------------------------------------------------------------
# Python complexity via AST
# ---------------------------------------------------------------------------

class PythonComplexityVisitor(ast.NodeVisitor):
    """Calculate cyclomatic complexity for Python functions using AST.

    Cyclomatic complexity = 1 + number of decision points.

    Decision points counted:
        if, elif, for, while, except, with, assert,
        and, or, ternary (IfExp), comprehension conditions
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.results: list[FunctionComplexity] = []
        self._class_stack: list[str] = []

    def _qualified_name(self, name: str) -> str:
        if self._class_stack:
            return f"{'.'.join(self._class_stack)}.{name}"
        return name

    def _compute_complexity(self, node: ast.AST) -> int:
        """Walk the function body and count decision points."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If,)):
                complexity += 1
            elif isinstance(child, ast.For):
                complexity += 1
            elif isinstance(child, ast.While):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.IfExp):  # Ternary
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each `and`/`or` adds a decision path
                # n values means n-1 operators
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                # Count if-clauses in comprehensions
                for generator in child.generators:
                    complexity += len(generator.ifs)
                    if generator.is_async:
                        complexity += 1

        return complexity

    def visit_ClassDef(self, node: ast.ClassDef):
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node)

    def _visit_function(self, node):
        name = self._qualified_name(node.name)
        complexity = self._compute_complexity(node)
        self.results.append(FunctionComplexity(
            file=self.filepath,
            function_name=name,
            line=node.lineno,
            complexity=complexity,
            language="python",
        ))
        # Visit nested functions
        self.generic_visit(node)


def analyze_python_file(filepath: Path, rel_path: str) -> list[FunctionComplexity]:
    """Parse a Python file and return complexity for each function."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, ValueError):
        return []

    visitor = PythonComplexityVisitor(rel_path)
    visitor.visit(tree)
    return visitor.results


# ---------------------------------------------------------------------------
# JavaScript / TypeScript complexity via regex heuristics
# ---------------------------------------------------------------------------

# Pattern to detect function declarations and expressions
_JS_FUNC_PATTERNS = [
    # function name(...) {
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)"),
    # const name = (...) => {  or  const name = function(
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function"),
    # Class method: name(...) {  (with optional async, get, set, static)
    re.compile(r"^\s*(?:static\s+)?(?:async\s+)?(?:get\s+|set\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{"),
]

# Patterns that add to cyclomatic complexity in JS/TS
_JS_DECISION_PATTERNS = [
    re.compile(r"\bif\s*\("),
    re.compile(r"\belse\s+if\s*\("),
    re.compile(r"\bfor\s*\("),
    re.compile(r"\bwhile\s*\("),
    re.compile(r"\bcatch\s*\("),
    re.compile(r"\bcase\s+"),
    re.compile(r"\?\?"),        # Nullish coalescing
    re.compile(r"\?\s*[^.:?]"),  # Ternary operator (heuristic)
    re.compile(r"\&\&"),        # Short-circuit and
    re.compile(r"\|\|"),        # Short-circuit or
]


def _find_matching_brace(lines: list[str], start_idx: int) -> int:
    """Find the line index of the closing brace for a function starting at start_idx."""
    depth = 0
    for i in range(start_idx, len(lines)):
        line = lines[i]
        # Remove string contents to avoid counting braces in strings
        cleaned = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", "", line)
        # Remove single-line comments
        cleaned = re.sub(r"//.*$", "", cleaned)
        depth += cleaned.count("{") - cleaned.count("}")
        if depth <= 0 and i > start_idx:
            return i
    return len(lines) - 1


def analyze_js_ts_file(filepath: Path, rel_path: str) -> list[FunctionComplexity]:
    """Analyze a JS/TS file using regex heuristics."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return []

    lines = content.splitlines()
    results = []

    i = 0
    while i < len(lines):
        line = lines[i]
        func_name = None

        for pattern in _JS_FUNC_PATTERNS:
            match = pattern.search(line)
            if match:
                func_name = match.group(1)
                break

        if func_name:
            # Find the function body
            end_idx = _find_matching_brace(lines, i)
            body = "\n".join(lines[i:end_idx + 1])

            # Remove string literals and comments from body for analysis
            body_cleaned = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", "", body)
            body_cleaned = re.sub(r"//.*$", "", body_cleaned, flags=re.MULTILINE)
            body_cleaned = re.sub(r"/\*.*?\*/", "", body_cleaned, flags=re.DOTALL)

            complexity = 1  # Base
            for dp in _JS_DECISION_PATTERNS:
                complexity += len(dp.findall(body_cleaned))

            results.append(FunctionComplexity(
                file=rel_path,
                function_name=func_name,
                line=i + 1,
                complexity=complexity,
                language="javascript/typescript",
            ))

            i = end_idx + 1
        else:
            i += 1

    return results


# ---------------------------------------------------------------------------
# Directory scanning
# ---------------------------------------------------------------------------

def iter_source_files(directory: Path):
    """Yield all Python and JS/TS source files."""
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower()
            if ext in PYTHON_EXTENSIONS or ext in JS_TS_EXTENSIONS:
                yield fpath


def analyze_directory(directory: Path) -> list[FunctionComplexity]:
    """Analyze all source files in a directory tree."""
    all_results = []

    for filepath in iter_source_files(directory):
        rel_path = str(filepath.relative_to(directory))
        ext = filepath.suffix.lower()

        if ext in PYTHON_EXTENSIONS:
            all_results.extend(analyze_python_file(filepath, rel_path))
        elif ext in JS_TS_EXTENSIONS:
            all_results.extend(analyze_js_ts_file(filepath, rel_path))

    return all_results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_text_report(
    results: list[FunctionComplexity],
    threshold: int,
    directory: str,
    show_all: bool,
):
    """Print a human-readable complexity report."""
    # Sort by complexity descending
    sorted_results = sorted(results, key=lambda r: -r.complexity)

    above_threshold = [r for r in sorted_results if r.complexity >= threshold]
    below_threshold = [r for r in sorted_results if r.complexity < threshold]

    print("=" * 78)
    print("  CYCLOMATIC COMPLEXITY REPORT")
    print("=" * 78)
    print(f"  Directory:  {directory}")
    print(f"  Threshold:  {threshold}")
    print(f"  Functions:  {len(results)} analyzed")
    print(f"  Above threshold: {len(above_threshold)}")
    print()

    # Distribution summary
    ratings = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for r in results:
        ratings[r.rating] += 1

    print("-" * 78)
    print("  COMPLEXITY DISTRIBUTION")
    print("-" * 78)
    print(f"    A (1-5)    Simple         {ratings['A']:>5}  {'#' * min(ratings['A'], 50)}")
    print(f"    B (6-10)   Moderate       {ratings['B']:>5}  {'#' * min(ratings['B'], 50)}")
    print(f"    C (11-20)  Complex        {ratings['C']:>5}  {'#' * min(ratings['C'], 50)}")
    print(f"    D (21-50)  Very complex   {ratings['D']:>5}  {'#' * min(ratings['D'], 50)}")
    print(f"    F (51+)    Untestable     {ratings['F']:>5}  {'#' * min(ratings['F'], 50)}")
    print()

    if above_threshold:
        print("-" * 78)
        print(f"  FUNCTIONS ABOVE THRESHOLD (complexity >= {threshold})")
        print("-" * 78)
        print(f"  {'Rating':<8} {'Complexity':>10}  {'Function':<35} {'Location'}")
        print(f"  {'------':<8} {'----------':>10}  {'--------':<35} {'--------'}")
        for r in above_threshold:
            loc = f"{r.file}:{r.line}"
            print(f"  {r.rating:<8} {r.complexity:>10}  {r.function_name:<35} {loc}")
        print()

    if show_all and below_threshold:
        print("-" * 78)
        print(f"  ALL OTHER FUNCTIONS (complexity < {threshold})")
        print("-" * 78)
        print(f"  {'Rating':<8} {'Complexity':>10}  {'Function':<35} {'Location'}")
        print(f"  {'------':<8} {'----------':>10}  {'--------':<35} {'--------'}")
        for r in below_threshold:
            loc = f"{r.file}:{r.line}"
            print(f"  {r.rating:<8} {r.complexity:>10}  {r.function_name:<35} {loc}")
        print()

    # Averages
    if results:
        avg = sum(r.complexity for r in results) / len(results)
        max_r = sorted_results[0]
        print("-" * 78)
        print("  STATISTICS")
        print("-" * 78)
        print(f"    Average complexity:  {avg:.1f}")
        print(f"    Median complexity:   {sorted_results[len(sorted_results)//2].complexity}")
        print(f"    Most complex:        {max_r.function_name} ({max_r.complexity}) in {max_r.file}:{max_r.line}")
        print()

    # Recommendations
    print("-" * 78)
    print("  RECOMMENDATIONS")
    print("-" * 78)
    if not above_threshold:
        print("    All functions are within acceptable complexity. No action required.")
    else:
        print(f"    {len(above_threshold)} function(s) exceed the threshold of {threshold}.")
        print("    Consider the following refactoring strategies:")
        print()
        print("    - Extract helper functions for distinct logical blocks")
        print("    - Replace nested conditionals with early returns / guard clauses")
        print("    - Use lookup tables or strategy patterns instead of long switch/if chains")
        print("    - Break complex boolean expressions into named intermediate variables")
        print("    - Consider the Single Responsibility Principle: does this function do too much?")
    print()
    print("=" * 78)


def print_json_report(
    results: list[FunctionComplexity],
    threshold: int,
    directory: str,
):
    """Print a JSON complexity report."""
    sorted_results = sorted(results, key=lambda r: -r.complexity)
    above = [r for r in sorted_results if r.complexity >= threshold]

    ratings = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for r in results:
        ratings[r.rating] += 1

    avg = sum(r.complexity for r in results) / len(results) if results else 0

    data = {
        "directory": directory,
        "threshold": threshold,
        "total_functions": len(results),
        "above_threshold": len(above),
        "statistics": {
            "average_complexity": round(avg, 1),
            "median_complexity": sorted_results[len(sorted_results) // 2].complexity if results else 0,
            "max_complexity": sorted_results[0].complexity if results else 0,
        },
        "distribution": ratings,
        "functions_above_threshold": [
            {**asdict(r), "rating": r.rating} for r in above
        ],
        "all_functions": [
            {**asdict(r), "rating": r.rating} for r in sorted_results
        ],
    }
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a cyclomatic complexity report for Python and JS/TS files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Complexity ratings:
  A (1-5)    Simple, well-structured function
  B (6-10)   Moderate complexity, acceptable
  C (11-20)  Complex, consider refactoring
  D (21-50)  Very complex, strongly recommend refactoring
  F (51+)    Untestable, must refactor

Examples:
  python complexity_report.py ./src
  python complexity_report.py ./src --threshold 15
  python complexity_report.py ./src --all --json
  python complexity_report.py ./src --json | jq '.functions_above_threshold[]'
        """,
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Path to the directory to analyze",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=f"Complexity threshold for flagging functions (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="show_all",
        help="Show all functions, not just those above the threshold",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"Error: '{args.directory}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    resolved = args.directory.resolve()
    results = analyze_directory(resolved)

    if not results:
        print(f"No Python or JavaScript/TypeScript functions found in '{resolved}'.")
        sys.exit(0)

    if args.json_output:
        print_json_report(results, args.threshold, str(resolved))
    else:
        print_text_report(results, args.threshold, str(resolved), args.show_all)

    # Exit with non-zero if any functions are above threshold
    above = [r for r in results if r.complexity >= args.threshold]
    sys.exit(1 if above else 0)


if __name__ == "__main__":
    main()
