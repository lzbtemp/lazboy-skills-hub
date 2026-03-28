#!/usr/bin/env python3
"""
Analyze code complexity metrics for TypeScript/JavaScript files.

Checks:
- Cyclomatic complexity per function
- Function length (lines)
- File length (lines)
- Nesting depth
- Parameter count per function

Usage:
    python complexity_check.py /path/to/src
    python complexity_check.py /path/to/src --max-complexity 10 --max-lines 50
    python complexity_check.py /path/to/src --json
    python complexity_check.py /path/to/file.ts
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# --- Configuration defaults ---

DEFAULT_MAX_CYCLOMATIC = 10
DEFAULT_MAX_FUNCTION_LINES = 50
DEFAULT_MAX_FILE_LINES = 300
DEFAULT_MAX_NESTING = 4
DEFAULT_MAX_PARAMS = 4


@dataclass
class FunctionMetrics:
    name: str
    file: str
    start_line: int
    end_line: int
    line_count: int
    cyclomatic_complexity: int
    max_nesting_depth: int
    parameter_count: int
    violations: list = field(default_factory=list)


@dataclass
class FileMetrics:
    file: str
    line_count: int
    function_count: int
    functions: list = field(default_factory=list)
    violations: list = field(default_factory=list)


@dataclass
class Violation:
    file: str
    line: int
    metric: str
    value: int
    threshold: int
    message: str
    function_name: Optional[str] = None


# --- Complexity calculation ---

# Patterns that increase cyclomatic complexity
COMPLEXITY_PATTERNS = [
    re.compile(r'\bif\s*\('),
    re.compile(r'\belse\s+if\s*\('),
    re.compile(r'\bwhile\s*\('),
    re.compile(r'\bfor\s*\('),
    re.compile(r'\bcase\s+'),
    re.compile(r'\bcatch\s*\('),
    re.compile(r'\?\?'),          # Nullish coalescing
    re.compile(r'\?\s*\.'),       # Optional chaining (counted as branching point)
    re.compile(r'\?\s*[^.:?]'),   # Ternary operator (but not ?. or ??)
    re.compile(r'\|\|'),          # Logical OR
    re.compile(r'&&'),            # Logical AND
]

# Patterns that increase nesting depth
NESTING_INCREASE = {'{'}
NESTING_DECREASE = {'}'}

# Function detection patterns
FUNCTION_PATTERNS = [
    # Named function declaration: function foo(...) or async function foo(...)
    re.compile(
        r'(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*'
        r'(?:<[^>]*>)?\s*\(([^)]*)\)'
    ),
    # Arrow function assigned to const: const foo = (...) =>
    re.compile(
        r'(?:export\s+)?(?:const|let)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*'
        r'(?::\s*[^=]+)?\s*=\s*(?:async\s+)?'
        r'(?:\(([^)]*)\)|([A-Za-z_$][A-Za-z0-9_$]*))\s*(?::\s*[^=]+)?\s*=>'
    ),
    # Class method: foo(...) { or async foo(...) {
    re.compile(
        r'(?:async\s+)?([A-Za-z_$][A-Za-z0-9_$]*)\s*'
        r'(?:<[^>]*>)?\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\s*\{'
    ),
]


def count_parameters(params_str: str) -> int:
    """Count the number of parameters in a function parameter string."""
    if not params_str or not params_str.strip():
        return 0

    # Remove type annotations (simplified) and default values
    # Count commas at the top level (not inside generics or objects)
    depth = 0
    count = 1  # At least 1 param if string is non-empty
    for char in params_str:
        if char in ('(', '<', '{', '['):
            depth += 1
        elif char in (')', '>', '}', ']'):
            depth -= 1
        elif char == ',' and depth == 0:
            count += 1

    return count


def calculate_cyclomatic_complexity(lines: list) -> int:
    """Calculate cyclomatic complexity for a set of code lines."""
    complexity = 1  # Base complexity

    for line in lines:
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        for pattern in COMPLEXITY_PATTERNS:
            complexity += len(pattern.findall(line))

    return complexity


def calculate_max_nesting(lines: list) -> int:
    """Calculate the maximum nesting depth in a set of code lines."""
    max_depth = 0
    current_depth = 0
    in_string = False
    string_char = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        for i, char in enumerate(stripped):
            # Track string literals
            if char in ('"', "'", '`') and (i == 0 or stripped[i - 1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                continue

            if in_string:
                continue

            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth = max(0, current_depth - 1)

    return max_depth


def find_function_end(lines: list, start_idx: int) -> int:
    """Find the end line of a function by tracking brace depth."""
    depth = 0
    found_open = False
    in_string = False
    string_char = None

    for i in range(start_idx, len(lines)):
        for j, char in enumerate(lines[i]):
            # Track strings
            if char in ('"', "'", '`') and (j == 0 or lines[i][j - 1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                continue

            if in_string:
                continue

            if char == '{':
                depth += 1
                found_open = True
            elif char == '}':
                depth -= 1
                if found_open and depth == 0:
                    return i

    return len(lines) - 1


def extract_functions(filepath: Path, content: str) -> list:
    """Extract function boundaries and metadata from a file."""
    lines = content.splitlines()
    functions = []
    processed_lines = set()  # Avoid double-counting same function

    for line_idx, line in enumerate(lines):
        if line_idx in processed_lines:
            continue

        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        for pattern in FUNCTION_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue

            name = match.group(1)
            # Get parameters (could be group 2 or group 3 depending on pattern)
            params_str = ""
            for g in range(2, len(match.groups()) + 1):
                if match.group(g) is not None:
                    params_str = match.group(g)
                    break

            # Skip common non-function matches
            if name in ("if", "else", "while", "for", "switch", "catch", "return",
                        "import", "export", "from", "require", "new", "throw", "typeof",
                        "instanceof", "delete", "void", "yield", "await"):
                continue

            # Find the function body
            end_idx = find_function_end(lines, line_idx)
            func_lines = lines[line_idx:end_idx + 1]
            line_count = len(func_lines)

            # Skip trivial one-liners
            if line_count <= 1:
                continue

            param_count = count_parameters(params_str)
            complexity = calculate_cyclomatic_complexity(func_lines)
            nesting = calculate_max_nesting(func_lines)

            functions.append(FunctionMetrics(
                name=name,
                file=str(filepath),
                start_line=line_idx + 1,
                end_line=end_idx + 1,
                line_count=line_count,
                cyclomatic_complexity=complexity,
                max_nesting_depth=nesting,
                parameter_count=param_count,
            ))

            processed_lines.add(line_idx)
            break

    return functions


def analyze_file(filepath: Path, config: dict) -> FileMetrics:
    """Analyze a single file for complexity metrics."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return FileMetrics(file=str(filepath), line_count=0, function_count=0)

    lines = content.splitlines()
    line_count = len(lines)
    violations = []

    # Check file length
    if line_count > config["max_file_lines"]:
        violations.append(Violation(
            file=str(filepath),
            line=0,
            metric="file_length",
            value=line_count,
            threshold=config["max_file_lines"],
            message=f"File has {line_count} lines (max: {config['max_file_lines']})",
        ))

    # Extract and analyze functions
    functions = extract_functions(filepath, content)

    for func in functions:
        # Cyclomatic complexity
        if func.cyclomatic_complexity > config["max_complexity"]:
            v = Violation(
                file=str(filepath),
                line=func.start_line,
                metric="cyclomatic_complexity",
                value=func.cyclomatic_complexity,
                threshold=config["max_complexity"],
                message=f"Function '{func.name}' has complexity {func.cyclomatic_complexity} (max: {config['max_complexity']})",
                function_name=func.name,
            )
            violations.append(v)
            func.violations.append(asdict(v))

        # Function length
        if func.line_count > config["max_function_lines"]:
            v = Violation(
                file=str(filepath),
                line=func.start_line,
                metric="function_length",
                value=func.line_count,
                threshold=config["max_function_lines"],
                message=f"Function '{func.name}' is {func.line_count} lines (max: {config['max_function_lines']})",
                function_name=func.name,
            )
            violations.append(v)
            func.violations.append(asdict(v))

        # Nesting depth
        if func.max_nesting_depth > config["max_nesting"]:
            v = Violation(
                file=str(filepath),
                line=func.start_line,
                metric="nesting_depth",
                value=func.max_nesting_depth,
                threshold=config["max_nesting"],
                message=f"Function '{func.name}' has nesting depth {func.max_nesting_depth} (max: {config['max_nesting']})",
                function_name=func.name,
            )
            violations.append(v)
            func.violations.append(asdict(v))

        # Parameter count
        if func.parameter_count > config["max_params"]:
            v = Violation(
                file=str(filepath),
                line=func.start_line,
                metric="parameter_count",
                value=func.parameter_count,
                threshold=config["max_params"],
                message=f"Function '{func.name}' has {func.parameter_count} parameters (max: {config['max_params']})",
                function_name=func.name,
            )
            violations.append(v)
            func.violations.append(asdict(v))

    return FileMetrics(
        file=str(filepath),
        line_count=line_count,
        function_count=len(functions),
        functions=[asdict(f) for f in functions],
        violations=[asdict(v) for v in violations],
    )


def collect_files(root: Path) -> list:
    """Collect TypeScript/JavaScript source files recursively."""
    files = []
    exclude_dirs = {"node_modules", ".next", "dist", "build", "coverage", ".git",
                    "__tests__", "__mocks__"}
    extensions = {".ts", ".tsx", ".js", ".jsx"}
    exclude_patterns = {".test.", ".spec.", ".d.ts"}

    if root.is_file():
        return [root] if root.suffix in extensions else []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in extensions and not any(p in fname for p in exclude_patterns):
                files.append(fpath)
    return files


def format_text_report(file_metrics: list, config: dict) -> str:
    """Format the analysis results as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("  CODE COMPLEXITY ANALYSIS")
    lines.append("=" * 70)

    total_files = len(file_metrics)
    total_functions = sum(fm.function_count for fm in file_metrics)
    total_violations = sum(len(fm.violations) for fm in file_metrics)

    lines.append(f"\nFiles analyzed:     {total_files}")
    lines.append(f"Functions found:    {total_functions}")
    lines.append(f"Violations:         {total_violations}")
    lines.append(f"\nThresholds:")
    lines.append(f"  Max cyclomatic complexity: {config['max_complexity']}")
    lines.append(f"  Max function lines:        {config['max_function_lines']}")
    lines.append(f"  Max file lines:            {config['max_file_lines']}")
    lines.append(f"  Max nesting depth:         {config['max_nesting']}")
    lines.append(f"  Max parameters:            {config['max_params']}")

    if total_violations == 0:
        lines.append("\nNo complexity violations found.")
        return "\n".join(lines)

    # Group violations by file
    lines.append("\n--- VIOLATIONS ---\n")

    for fm in file_metrics:
        if not fm.violations:
            continue

        lines.append(f"  {fm.file}  ({fm.line_count} lines, {fm.function_count} functions)")
        lines.append("  " + "-" * 60)

        for v_dict in fm.violations:
            v_line = v_dict.get("line", 0)
            msg = v_dict.get("message", "")
            metric = v_dict.get("metric", "")
            value = v_dict.get("value", 0)
            threshold = v_dict.get("threshold", 0)

            indicator = "!!" if value > threshold * 1.5 else "!"
            lines.append(f"    {indicator} L{v_line}: {msg}")

        lines.append("")

    # Summary by metric type
    lines.append("--- SUMMARY BY METRIC ---\n")
    metric_counts = {}
    for fm in file_metrics:
        for v_dict in fm.violations:
            m = v_dict.get("metric", "unknown")
            metric_counts[m] = metric_counts.get(m, 0) + 1

    metric_labels = {
        "cyclomatic_complexity": "Cyclomatic complexity",
        "function_length": "Function length",
        "file_length": "File length",
        "nesting_depth": "Nesting depth",
        "parameter_count": "Parameter count",
    }

    for metric, count in sorted(metric_counts.items()):
        label = metric_labels.get(metric, metric)
        lines.append(f"  {label}: {count} violation(s)")

    # Top offenders
    all_funcs = []
    for fm in file_metrics:
        for f_dict in fm.functions:
            all_funcs.append(f_dict)

    if all_funcs:
        lines.append("\n--- TOP 5 MOST COMPLEX FUNCTIONS ---\n")
        top_complex = sorted(all_funcs, key=lambda f: f["cyclomatic_complexity"], reverse=True)[:5]
        for f in top_complex:
            lines.append(
                f"  {f['name']}  complexity={f['cyclomatic_complexity']}  "
                f"lines={f['line_count']}  nesting={f['max_nesting_depth']}  "
                f"params={f['parameter_count']}"
            )
            lines.append(f"    at {f['file']}:{f['start_line']}")

    lines.append(f"\n{'=' * 70}")
    lines.append(f"  Total: {total_violations} violation(s) across {total_files} file(s)")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_json_report(file_metrics: list, config: dict) -> str:
    """Format the analysis results as JSON."""
    total_violations = sum(len(fm.violations) for fm in file_metrics)
    return json.dumps({
        "config": config,
        "summary": {
            "files_analyzed": len(file_metrics),
            "total_functions": sum(fm.function_count for fm in file_metrics),
            "total_violations": total_violations,
        },
        "files": [asdict(fm) for fm in file_metrics if fm.violations or fm.functions],
    }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze code complexity metrics for TypeScript/JavaScript files.",
    )
    parser.add_argument(
        "path",
        help="File or directory to analyze",
    )
    parser.add_argument(
        "--max-complexity",
        type=int,
        default=DEFAULT_MAX_CYCLOMATIC,
        help=f"Maximum cyclomatic complexity per function (default: {DEFAULT_MAX_CYCLOMATIC})",
    )
    parser.add_argument(
        "--max-function-lines",
        type=int,
        default=DEFAULT_MAX_FUNCTION_LINES,
        help=f"Maximum lines per function (default: {DEFAULT_MAX_FUNCTION_LINES})",
    )
    parser.add_argument(
        "--max-file-lines",
        type=int,
        default=DEFAULT_MAX_FILE_LINES,
        help=f"Maximum lines per file (default: {DEFAULT_MAX_FILE_LINES})",
    )
    parser.add_argument(
        "--max-nesting",
        type=int,
        default=DEFAULT_MAX_NESTING,
        help=f"Maximum nesting depth (default: {DEFAULT_MAX_NESTING})",
    )
    parser.add_argument(
        "--max-params",
        type=int,
        default=DEFAULT_MAX_PARAMS,
        help=f"Maximum parameter count per function (default: {DEFAULT_MAX_PARAMS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Use stricter thresholds (halves all defaults)",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test files in the analysis",
    )

    args = parser.parse_args()
    target = Path(args.path).resolve()

    if not target.exists():
        print(f"Error: '{target}' does not exist", file=sys.stderr)
        sys.exit(1)

    config = {
        "max_complexity": args.max_complexity,
        "max_function_lines": args.max_function_lines,
        "max_file_lines": args.max_file_lines,
        "max_nesting": args.max_nesting,
        "max_params": args.max_params,
    }

    if args.strict:
        config = {k: max(1, v // 2) for k, v in config.items()}

    # Collect files
    files = collect_files(target)

    if not args.include_tests:
        files = [f for f in files if ".test." not in f.name and ".spec." not in f.name]

    if not files:
        print(f"No TypeScript/JavaScript source files found in '{target}'", file=sys.stderr)
        sys.exit(0)

    # Analyze
    all_metrics = []
    for fpath in files:
        metrics = analyze_file(fpath, config)
        all_metrics.append(metrics)

    # Output
    if args.output_json:
        print(format_json_report(all_metrics, config))
    else:
        print(format_text_report(all_metrics, config))

    # Exit code
    total_violations = sum(len(fm.violations) for fm in all_metrics)
    sys.exit(1 if total_violations > 0 else 0)


if __name__ == "__main__":
    main()
