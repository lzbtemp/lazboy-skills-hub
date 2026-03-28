#!/usr/bin/env python3
"""
Test Coverage Report Generator

Parses coverage output files (lcov, coverage.py JSON, Istanbul JSON) and
generates a summary report with per-file coverage, identifies uncovered
files, and flags files below a configurable threshold.

Usage:
    python coverage_report.py --input coverage/lcov.info --format lcov
    python coverage_report.py --input coverage.json --format coverage-py
    python coverage_report.py --input coverage/coverage-final.json --format istanbul
    python coverage_report.py --input coverage/lcov.info --threshold 80 --output report.md
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FileCoverage:
    file_path: str
    lines_total: int = 0
    lines_covered: int = 0
    branches_total: int = 0
    branches_covered: int = 0
    functions_total: int = 0
    functions_covered: int = 0

    @property
    def line_coverage(self) -> float:
        if self.lines_total == 0:
            return 100.0
        return (self.lines_covered / self.lines_total) * 100

    @property
    def branch_coverage(self) -> float:
        if self.branches_total == 0:
            return 100.0
        return (self.branches_covered / self.branches_total) * 100

    @property
    def function_coverage(self) -> float:
        if self.functions_total == 0:
            return 100.0
        return (self.functions_covered / self.functions_total) * 100

    @property
    def uncovered_lines(self) -> int:
        return self.lines_total - self.lines_covered


@dataclass
class CoverageReport:
    files: list[FileCoverage] = field(default_factory=list)
    source_format: str = ""

    @property
    def total_lines(self) -> int:
        return sum(f.lines_total for f in self.files)

    @property
    def covered_lines(self) -> int:
        return sum(f.lines_covered for f in self.files)

    @property
    def total_line_coverage(self) -> float:
        if self.total_lines == 0:
            return 100.0
        return (self.covered_lines / self.total_lines) * 100

    @property
    def total_branches(self) -> int:
        return sum(f.branches_total for f in self.files)

    @property
    def covered_branches(self) -> int:
        return sum(f.branches_covered for f in self.files)

    @property
    def total_branch_coverage(self) -> float:
        if self.total_branches == 0:
            return 100.0
        return (self.covered_branches / self.total_branches) * 100

    @property
    def total_functions(self) -> int:
        return sum(f.functions_total for f in self.files)

    @property
    def covered_functions(self) -> int:
        return sum(f.functions_covered for f in self.files)

    @property
    def total_function_coverage(self) -> float:
        if self.total_functions == 0:
            return 100.0
        return (self.covered_functions / self.total_functions) * 100


# --- Parsers ---


def parse_lcov(filepath: str) -> CoverageReport:
    """Parse LCOV format coverage data."""
    report = CoverageReport(source_format="lcov")

    with open(filepath, "r") as f:
        content = f.read()

    current_file: Optional[FileCoverage] = None

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("SF:"):
            # Source file
            current_file = FileCoverage(file_path=line[3:])

        elif line.startswith("LF:") and current_file:
            # Lines found (total)
            current_file.lines_total = int(line[3:])

        elif line.startswith("LH:") and current_file:
            # Lines hit (covered)
            current_file.lines_covered = int(line[3:])

        elif line.startswith("BRF:") and current_file:
            # Branches found
            current_file.branches_total = int(line[4:])

        elif line.startswith("BRH:") and current_file:
            # Branches hit
            current_file.branches_covered = int(line[4:])

        elif line.startswith("FNF:") and current_file:
            # Functions found
            current_file.functions_total = int(line[4:])

        elif line.startswith("FNH:") and current_file:
            # Functions hit
            current_file.functions_covered = int(line[4:])

        elif line == "end_of_record" and current_file:
            report.files.append(current_file)
            current_file = None

    return report


def parse_coverage_py_json(filepath: str) -> CoverageReport:
    """Parse coverage.py JSON format."""
    report = CoverageReport(source_format="coverage.py")

    with open(filepath, "r") as f:
        data = json.load(f)

    # coverage.py JSON format
    files_data = data.get("files", {})
    for file_path, file_info in files_data.items():
        summary = file_info.get("summary", {})
        fc = FileCoverage(
            file_path=file_path,
            lines_total=summary.get("num_statements", 0),
            lines_covered=summary.get("covered_lines", 0),
            branches_total=summary.get("num_branches", 0),
            branches_covered=summary.get("covered_branches", 0),
        )
        report.files.append(fc)

    # Alternative: totals-only format
    if not files_data and "totals" in data:
        totals = data["totals"]
        fc = FileCoverage(
            file_path="(total)",
            lines_total=totals.get("num_statements", 0),
            lines_covered=totals.get("covered_lines", 0),
            branches_total=totals.get("num_branches", 0),
            branches_covered=totals.get("covered_branches", 0),
        )
        report.files.append(fc)

    return report


def parse_istanbul_json(filepath: str) -> CoverageReport:
    """Parse Istanbul/NYC JSON format (coverage-final.json)."""
    report = CoverageReport(source_format="istanbul")

    with open(filepath, "r") as f:
        data = json.load(f)

    for file_path, file_info in data.items():
        # Statement coverage
        stmt_map = file_info.get("statementMap", {})
        stmt_counts = file_info.get("s", {})
        lines_total = len(stmt_map)
        lines_covered = sum(1 for v in stmt_counts.values() if v > 0)

        # Branch coverage
        branch_map = file_info.get("branchMap", {})
        branch_counts = file_info.get("b", {})
        branches_total = sum(len(locations) for locations in branch_counts.values())
        branches_covered = sum(
            1 for locations in branch_counts.values()
            for count in locations if count > 0
        )

        # Function coverage
        fn_map = file_info.get("fnMap", {})
        fn_counts = file_info.get("f", {})
        functions_total = len(fn_map)
        functions_covered = sum(1 for v in fn_counts.values() if v > 0)

        fc = FileCoverage(
            file_path=file_path,
            lines_total=lines_total,
            lines_covered=lines_covered,
            branches_total=branches_total,
            branches_covered=branches_covered,
            functions_total=functions_total,
            functions_covered=functions_covered,
        )
        report.files.append(fc)

    return report


# --- Report Generation ---


def generate_markdown_report(
    report: CoverageReport,
    threshold: float = 80.0,
    project_root: str = "",
) -> str:
    """Generate a markdown coverage report."""
    lines = [
        "# Test Coverage Report",
        f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Source format**: {report.source_format}",
        f"**Files**: {len(report.files)}",
        f"**Threshold**: {threshold}%",
        "",
    ]

    # Overall summary
    lines.append("## Summary\n")
    total_pct = report.total_line_coverage
    status = "PASS" if total_pct >= threshold else "FAIL"
    status_icon = "+" if total_pct >= threshold else "-"

    lines.append("| Metric | Covered | Total | Percentage | Status |")
    lines.append("|--------|---------|-------|------------|--------|")
    lines.append(
        f"| **Lines** | {report.covered_lines:,} | {report.total_lines:,} | "
        f"**{total_pct:.1f}%** | {status} |"
    )
    if report.total_branches > 0:
        branch_status = "PASS" if report.total_branch_coverage >= threshold else "FAIL"
        lines.append(
            f"| **Branches** | {report.covered_branches:,} | {report.total_branches:,} | "
            f"**{report.total_branch_coverage:.1f}%** | {branch_status} |"
        )
    if report.total_functions > 0:
        func_status = "PASS" if report.total_function_coverage >= threshold else "FAIL"
        lines.append(
            f"| **Functions** | {report.covered_functions:,} | {report.total_functions:,} | "
            f"**{report.total_function_coverage:.1f}%** | {func_status} |"
        )

    # Files below threshold
    below_threshold = [
        f for f in report.files
        if f.line_coverage < threshold and f.lines_total > 0
    ]
    below_threshold.sort(key=lambda f: f.line_coverage)

    if below_threshold:
        lines.append(f"\n## Files Below {threshold}% Threshold ({len(below_threshold)} files)\n")
        lines.append("| File | Lines | Coverage | Uncovered | Gap |")
        lines.append("|------|-------|----------|-----------|-----|")
        for fc in below_threshold:
            relative_path = _relative_path(fc.file_path, project_root)
            gap = threshold - fc.line_coverage
            lines.append(
                f"| `{relative_path}` | {fc.lines_covered}/{fc.lines_total} | "
                f"**{fc.line_coverage:.1f}%** | {fc.uncovered_lines} | -{gap:.1f}% |"
            )

    # All files table
    all_files = sorted(report.files, key=lambda f: f.line_coverage)
    if all_files:
        lines.append(f"\n## Per-File Coverage ({len(all_files)} files)\n")
        lines.append("| File | Lines | Line % | Branches | Branch % | Functions | Func % |")
        lines.append("|------|-------|--------|----------|----------|-----------|--------|")
        for fc in all_files:
            relative_path = _relative_path(fc.file_path, project_root)
            # Bold files below threshold
            name = f"**`{relative_path}`**" if fc.line_coverage < threshold else f"`{relative_path}`"
            branch_str = f"{fc.branches_covered}/{fc.branches_total}" if fc.branches_total > 0 else "-"
            branch_pct = f"{fc.branch_coverage:.1f}%" if fc.branches_total > 0 else "-"
            func_str = f"{fc.functions_covered}/{fc.functions_total}" if fc.functions_total > 0 else "-"
            func_pct = f"{fc.function_coverage:.1f}%" if fc.functions_total > 0 else "-"

            lines.append(
                f"| {name} | {fc.lines_covered}/{fc.lines_total} | "
                f"{fc.line_coverage:.1f}% | {branch_str} | {branch_pct} | "
                f"{func_str} | {func_pct} |"
            )

    # Uncovered files (0% coverage)
    uncovered = [f for f in report.files if f.lines_covered == 0 and f.lines_total > 0]
    if uncovered:
        lines.append(f"\n## Uncovered Files ({len(uncovered)} files)\n")
        lines.append("These files have 0% test coverage:\n")
        for fc in uncovered:
            relative_path = _relative_path(fc.file_path, project_root)
            lines.append(f"- `{relative_path}` ({fc.lines_total} lines)")

    # Recommendations
    lines.append("\n## Recommendations\n")
    if below_threshold:
        lines.append(
            f"- **{len(below_threshold)} files** are below the {threshold}% threshold. "
            f"Prioritize adding tests for files with the most uncovered lines."
        )
    if uncovered:
        lines.append(
            f"- **{len(uncovered)} files** have zero coverage. Consider whether these "
            f"files contain untested logic or are generated/configuration files."
        )
    total_uncovered = report.total_lines - report.covered_lines
    if total_uncovered > 0:
        lines.append(
            f"- **{total_uncovered:,} lines** remain uncovered across the project."
        )
    if total_pct >= threshold:
        lines.append(f"- Overall coverage ({total_pct:.1f}%) meets the {threshold}% threshold.")

    return "\n".join(lines)


def generate_console_report(
    report: CoverageReport,
    threshold: float = 80.0,
    project_root: str = "",
) -> str:
    """Generate a console-friendly coverage report."""
    lines = []

    lines.append(f"\nTest Coverage Summary")
    lines.append("=" * 70)
    lines.append(
        f"Lines:     {report.covered_lines:>6,} / {report.total_lines:>6,}  "
        f"({report.total_line_coverage:>5.1f}%)"
    )
    if report.total_branches > 0:
        lines.append(
            f"Branches:  {report.covered_branches:>6,} / {report.total_branches:>6,}  "
            f"({report.total_branch_coverage:>5.1f}%)"
        )
    if report.total_functions > 0:
        lines.append(
            f"Functions: {report.covered_functions:>6,} / {report.total_functions:>6,}  "
            f"({report.total_function_coverage:>5.1f}%)"
        )
    lines.append("=" * 70)

    status = "PASS" if report.total_line_coverage >= threshold else "FAIL"
    lines.append(f"Threshold: {threshold}%  |  Status: {status}")

    # Files below threshold
    below = [f for f in report.files if f.line_coverage < threshold and f.lines_total > 0]
    if below:
        below.sort(key=lambda f: f.line_coverage)
        lines.append(f"\nFiles below {threshold}%:")
        lines.append("-" * 70)
        lines.append(f"{'File':<50} {'Coverage':>8}  {'Lines':>10}")
        lines.append("-" * 70)
        for fc in below[:20]:  # Show top 20
            relative_path = _relative_path(fc.file_path, project_root)
            # Truncate long paths
            if len(relative_path) > 48:
                relative_path = "..." + relative_path[-45:]
            lines.append(
                f"{relative_path:<50} {fc.line_coverage:>7.1f}%  "
                f"{fc.lines_covered:>4}/{fc.lines_total:<4}"
            )
        if len(below) > 20:
            lines.append(f"  ... and {len(below) - 20} more files")

    lines.append("")
    return "\n".join(lines)


def _relative_path(file_path: str, project_root: str) -> str:
    """Make a file path relative to the project root."""
    if project_root:
        try:
            return os.path.relpath(file_path, project_root)
        except ValueError:
            pass
    return file_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate test coverage summary report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported formats:
  lcov        - LCOV info format (lcov.info)
  coverage-py - coverage.py JSON format (coverage json output)
  istanbul    - Istanbul/NYC JSON format (coverage-final.json)

Examples:
  %(prog)s --input coverage/lcov.info --format lcov
  %(prog)s --input .coverage.json --format coverage-py --threshold 90
  %(prog)s --input coverage-final.json --format istanbul --output report.md
        """,
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to coverage data file",
    )
    parser.add_argument(
        "--format", "-f", required=True,
        choices=["lcov", "coverage-py", "istanbul"],
        help="Coverage data format",
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=80.0,
        help="Minimum coverage percentage threshold (default: 80)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path for markdown report",
    )
    parser.add_argument(
        "--project-root", "-r", default="",
        help="Project root for relative file paths",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output summary as JSON",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    # Parse coverage data
    if args.format == "lcov":
        report = parse_lcov(args.input)
    elif args.format == "coverage-py":
        report = parse_coverage_py_json(args.input)
    elif args.format == "istanbul":
        report = parse_istanbul_json(args.input)
    else:
        print(f"Error: Unknown format: {args.format}")
        sys.exit(1)

    if not report.files:
        print("Warning: No coverage data found in the input file")
        sys.exit(0)

    # Print console report
    console_report = generate_console_report(report, args.threshold, args.project_root)
    print(console_report)

    # Generate markdown report
    if args.output:
        md_report = generate_markdown_report(report, args.threshold, args.project_root)
        with open(args.output, "w") as f:
            f.write(md_report)
        print(f"Markdown report saved to: {args.output}")

    # JSON output
    if args.json:
        summary = {
            "total_files": len(report.files),
            "total_lines": report.total_lines,
            "covered_lines": report.covered_lines,
            "line_coverage": round(report.total_line_coverage, 2),
            "total_branches": report.total_branches,
            "covered_branches": report.covered_branches,
            "branch_coverage": round(report.total_branch_coverage, 2),
            "total_functions": report.total_functions,
            "covered_functions": report.covered_functions,
            "function_coverage": round(report.total_function_coverage, 2),
            "threshold": args.threshold,
            "passes_threshold": report.total_line_coverage >= args.threshold,
            "files_below_threshold": sum(
                1 for f in report.files
                if f.line_coverage < args.threshold and f.lines_total > 0
            ),
        }
        print(json.dumps(summary, indent=2))

    # Exit code based on threshold
    if report.total_line_coverage < args.threshold:
        sys.exit(1)


if __name__ == "__main__":
    main()
