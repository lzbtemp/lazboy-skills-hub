#!/usr/bin/env python3
"""
check_python_style.py -- Scan Python files for non-Pythonic patterns.

Detects:
  - Manual loop appends instead of comprehensions
  - Bare except clauses
  - Mutable default arguments
  - String concatenation in loops
  - Missing type hints on public functions
  - type() comparisons instead of isinstance()
  - == None / != None instead of is None / is not None
  - Manual file open without context manager
  - range(len(...)) anti-pattern
  - if len(x) == 0 instead of if not x
"""

import argparse
import ast
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StyleIssue:
    """Represents a detected style issue."""
    file: str
    line: int
    rule: str
    message: str
    severity: str = "warning"

    def __str__(self) -> str:
        return f"{self.file}:{self.line} [{self.severity}] {self.rule}: {self.message}"


@dataclass
class StyleReport:
    """Aggregated report of all style issues."""
    issues: list[StyleIssue] = field(default_factory=list)

    def add(self, issue: StyleIssue) -> None:
        self.issues.append(issue)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


class PythonStyleChecker(ast.NodeVisitor):
    """AST visitor that detects non-Pythonic patterns."""

    MUTABLE_DEFAULTS = (ast.List, ast.Dict, ast.Set, ast.Call)

    def __init__(self, filepath: str, source_lines: list[str]) -> None:
        self.filepath = filepath
        self.source_lines = source_lines
        self.report = StyleReport()
        self._in_loop = False
        self._loop_targets: list[str] = []

    def _add(self, line: int, rule: str, message: str, severity: str = "warning") -> None:
        self.report.add(StyleIssue(
            file=self.filepath, line=line, rule=rule,
            message=message, severity=severity,
        ))

    # -- Bare except ----------------------------------------------------------

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self._add(node.lineno, "W001-bare-except",
                      "Bare 'except:' catches SystemExit and KeyboardInterrupt. "
                      "Use 'except Exception:' instead.", "error")
        self.generic_visit(node)

    # -- Mutable default arguments --------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_mutable_defaults(node)
        self._check_missing_type_hints(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _check_mutable_defaults(self, node: ast.FunctionDef) -> None:
        for default in node.args.defaults + node.args.kw_defaults:
            if default is None:
                continue
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self._add(node.lineno, "W002-mutable-default",
                          f"Mutable default argument in '{node.name}()'. "
                          "Use None and assign inside the function.", "error")

    # -- Missing type hints ---------------------------------------------------

    def _check_missing_type_hints(self, node: ast.FunctionDef) -> None:
        if node.name.startswith("_"):
            return
        if node.returns is None:
            self._add(node.lineno, "W003-missing-return-type",
                      f"Public function '{node.name}()' is missing a return type hint.")
        for arg in node.args.args:
            if arg.arg == "self" or arg.arg == "cls":
                continue
            if arg.annotation is None:
                self._add(node.lineno, "W004-missing-param-type",
                          f"Parameter '{arg.arg}' in '{node.name}()' is missing a type hint.")

    # -- Loop anti-patterns ---------------------------------------------------

    def visit_For(self, node: ast.For) -> None:
        self._check_range_len(node)
        self._check_loop_append(node)
        self._check_string_concat_in_loop(node)
        self._check_len_comparison(node)

        old_in_loop = self._in_loop
        self._in_loop = True
        self.generic_visit(node)
        self._in_loop = old_in_loop

    def visit_While(self, node: ast.While) -> None:
        self._check_string_concat_in_loop_body(node.body, node.lineno)
        old_in_loop = self._in_loop
        self._in_loop = True
        self.generic_visit(node)
        self._in_loop = old_in_loop

    def _check_range_len(self, node: ast.For) -> None:
        """Detect for i in range(len(x)) -- suggest enumerate."""
        if not isinstance(node.iter, ast.Call):
            return
        func = node.iter.func
        if not (isinstance(func, ast.Name) and func.id == "range"):
            return
        if len(node.iter.args) != 1:
            return
        arg = node.iter.args[0]
        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "len":
            self._add(node.lineno, "W005-range-len",
                      "Use 'enumerate()' instead of 'range(len(...))'.")

    def _check_loop_append(self, node: ast.For) -> None:
        """Detect manual list.append in a simple for loop -- suggest comprehension."""
        if len(node.body) != 1:
            return
        stmt = node.body[0]
        if not isinstance(stmt, ast.Expr):
            return
        call = stmt.value
        if not isinstance(call, ast.Call):
            return
        if not isinstance(call.func, ast.Attribute):
            return
        if call.func.attr == "append" and len(call.args) == 1:
            if not node.orelse:
                self._add(node.lineno, "W006-loop-append",
                          "Simple loop with .append() can likely be a list comprehension.")

    def _check_string_concat_in_loop(self, node: ast.For) -> None:
        self._check_string_concat_in_loop_body(node.body, node.lineno)

    def _check_string_concat_in_loop_body(self, body: list, loop_line: int) -> None:
        """Detect string += in loop body."""
        for stmt in body:
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
                if isinstance(stmt.value, (ast.Constant, ast.JoinedStr, ast.Name)):
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        self._add(loop_line, "W007-string-concat-loop",
                                  "String concatenation in a loop is O(n^2). Use ''.join() instead.")

    def _check_len_comparison(self, node: ast.For) -> None:
        """Check for if len(x) == 0 patterns in loop test (while loops)."""
        pass  # Handled in visit_Compare

    # -- Comparison anti-patterns ---------------------------------------------

    def visit_Compare(self, node: ast.Compare) -> None:
        self._check_none_comparison(node)
        self._check_type_comparison(node)
        self._check_len_zero(node)
        self.generic_visit(node)

    def _check_none_comparison(self, node: ast.Compare) -> None:
        """Detect == None or != None."""
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(comparator, ast.Constant) and comparator.value is None:
                if isinstance(op, ast.Eq):
                    self._add(node.lineno, "W008-none-equality",
                              "Use 'is None' instead of '== None'.")
                elif isinstance(op, ast.NotEq):
                    self._add(node.lineno, "W009-none-inequality",
                              "Use 'is not None' instead of '!= None'.")

    def _check_type_comparison(self, node: ast.Compare) -> None:
        """Detect type(x) == SomeType."""
        if isinstance(node.left, ast.Call):
            func = node.left.func
            if isinstance(func, ast.Name) and func.id == "type":
                for op in node.ops:
                    if isinstance(op, (ast.Eq, ast.Is)):
                        self._add(node.lineno, "W010-type-comparison",
                                  "Use isinstance() instead of type() comparison.")

    def _check_len_zero(self, node: ast.Compare) -> None:
        """Detect if len(x) == 0 or if len(x) > 0."""
        if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name):
            if node.left.func.id == "len":
                for op, comp in zip(node.ops, node.comparators):
                    if isinstance(comp, ast.Constant) and comp.value == 0:
                        if isinstance(op, ast.Eq):
                            self._add(node.lineno, "W011-len-zero",
                                      "Use 'if not x' instead of 'if len(x) == 0'.")
                        elif isinstance(op, ast.Gt):
                            self._add(node.lineno, "W012-len-nonzero",
                                      "Use 'if x' instead of 'if len(x) > 0'.")

    # -- File open without context manager ------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == "open":
                self._add(node.lineno, "W013-open-no-with",
                          "Use 'with open(...)' instead of assigning to a variable.")
        self.generic_visit(node)


def check_file(filepath: str) -> StyleReport:
    """Parse and check a single Python file."""
    try:
        source = Path(filepath).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        report = StyleReport()
        report.add(StyleIssue(filepath, 0, "E000-read-error", str(e), "error"))
        return report

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        report = StyleReport()
        report.add(StyleIssue(filepath, e.lineno or 0, "E001-syntax-error", str(e), "error"))
        return report

    lines = source.splitlines()
    checker = PythonStyleChecker(filepath, lines)
    checker.visit(tree)

    # Line-based checks (not AST)
    _check_lines(filepath, lines, checker.report)

    return checker.report


def _check_lines(filepath: str, lines: list[str], report: StyleReport) -> None:
    """Line-by-line checks for patterns hard to detect via AST."""
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Check for # type: ignore without specific code
        if "# type: ignore" in stripped and "[" not in stripped.split("# type: ignore")[1][:5]:
            if "# type: ignore[" not in stripped:
                report.add(StyleIssue(
                    filepath, i, "W014-broad-type-ignore",
                    "Use specific '# type: ignore[error-code]' instead of blanket ignore."))

        # Check for print() in non-script files
        if stripped.startswith("print(") and not filepath.endswith("__main__.py"):
            # Only flag if it looks like debug output
            if "debug" in stripped.lower() or "todo" in stripped.lower():
                report.add(StyleIssue(
                    filepath, i, "W015-debug-print",
                    "Debug print() found. Use logging instead."))


def collect_python_files(paths: list[str], exclude: list[str]) -> list[str]:
    """Collect all Python files from given paths."""
    files = []
    exclude_set = set(exclude)
    for path in paths:
        p = Path(path)
        if p.is_file() and p.suffix == ".py":
            files.append(str(p))
        elif p.is_dir():
            for pyfile in p.rglob("*.py"):
                # Skip excluded directories
                parts = pyfile.parts
                if any(ex in parts for ex in exclude_set):
                    continue
                files.append(str(pyfile))
    return sorted(files)


def print_report(report: StyleReport, show_summary: bool = True) -> None:
    """Print the style report to stdout."""
    for issue in sorted(report.issues, key=lambda i: (i.file, i.line)):
        color = "\033[31m" if issue.severity == "error" else "\033[33m"
        reset = "\033[0m"
        print(f"{color}{issue}{reset}")

    if show_summary:
        print()
        total = len(report.issues)
        print(f"Found {total} issue(s): "
              f"{report.error_count} error(s), {report.warning_count} warning(s)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Python files for non-Pythonic patterns.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rules:
  W001  Bare except clause
  W002  Mutable default argument
  W003  Missing return type hint on public function
  W004  Missing parameter type hint on public function
  W005  range(len(...)) instead of enumerate()
  W006  Simple loop append instead of comprehension
  W007  String concatenation in loop
  W008  == None instead of is None
  W009  != None instead of is not None
  W010  type() comparison instead of isinstance()
  W011  len(x) == 0 instead of not x
  W012  len(x) > 0 instead of x
  W013  open() without context manager
  W014  Blanket # type: ignore
  W015  Debug print() statement
""",
    )
    parser.add_argument(
        "paths", nargs="*", default=["."],
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--exclude", nargs="*", default=["__pycache__", ".venv", "venv", ".git", "node_modules"],
        help="Directories to exclude (default: __pycache__, .venv, venv, .git, node_modules)",
    )
    parser.add_argument(
        "--rules", nargs="*", default=None,
        help="Only check specific rules (e.g., W001 W002). Default: all rules.",
    )
    parser.add_argument(
        "--severity", choices=["all", "error", "warning"], default="all",
        help="Filter by severity level (default: all)",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--fail-on-error", action="store_true",
        help="Exit with code 1 if any errors are found",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Only print summary",
    )

    args = parser.parse_args()

    files = collect_python_files(args.paths, args.exclude)
    if not files:
        print("No Python files found.")
        return 0

    combined_report = StyleReport()
    for filepath in files:
        report = check_file(filepath)
        for issue in report.issues:
            # Filter by rules
            if args.rules:
                rule_code = issue.rule.split("-")[0]
                if rule_code not in args.rules:
                    continue
            # Filter by severity
            if args.severity != "all" and issue.severity != args.severity:
                continue
            combined_report.add(issue)

    if args.format == "json":
        import json
        output = [
            {
                "file": i.file,
                "line": i.line,
                "rule": i.rule,
                "message": i.message,
                "severity": i.severity,
            }
            for i in combined_report.issues
        ]
        print(json.dumps(output, indent=2))
    elif not args.quiet:
        print_report(combined_report)
    else:
        total = len(combined_report.issues)
        print(f"Checked {len(files)} files. "
              f"Found {total} issue(s): "
              f"{combined_report.error_count} error(s), "
              f"{combined_report.warning_count} warning(s)")

    if args.fail_on_error and combined_report.error_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
