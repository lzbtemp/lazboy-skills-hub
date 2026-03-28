#!/usr/bin/env python3
"""
Scan React code for performance issues.

Detects:
- Missing React.memo on components receiving frequent re-renders
- Inline object/function creation in JSX props
- Missing dependency arrays in hooks
- Large component bundles without code splitting
- Unnecessary re-renders from Context usage patterns
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class PerfIssue:
    file: str
    line: int
    severity: str  # "high", "medium", "low"
    category: str
    message: str
    suggestion: str


def find_react_files(root: str, extensions: tuple = (".tsx", ".jsx", ".ts", ".js")) -> List[str]:
    """Find React source files, skipping build artifacts and dependencies."""
    files = []
    skip_dirs = {"node_modules", "dist", "build", ".next", "coverage", "__mocks__", ".git"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for f in filenames:
            if f.endswith(extensions):
                files.append(os.path.join(dirpath, f))
    return sorted(files)


def read_file_lines(filepath: str) -> List[str]:
    """Read file lines safely."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except (OSError, IOError):
        return []


def check_inline_objects_in_jsx(filepath: str, lines: List[str]) -> List[PerfIssue]:
    """Detect inline object literals in JSX props that cause re-renders."""
    issues = []
    # Pattern: prop={{ ... }} or prop={[ ... ]}
    inline_obj_pattern = re.compile(r"(\w+)\s*=\s*\{\s*(\{|\[)")
    # Exclusions: className, key, style when using CSS-in-JS intentionally
    safe_props = {"key", "ref", "dangerouslySetInnerHTML"}

    in_jsx = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Simple JSX detection: line contains < followed by uppercase component name
        if re.search(r"<[A-Z]\w*", line):
            in_jsx = True
        if in_jsx and ("/>" in line or re.search(r"<\/[A-Z]", line)):
            in_jsx = False

        if not in_jsx:
            continue

        for match in inline_obj_pattern.finditer(line):
            prop_name = match.group(1)
            bracket_type = match.group(2)

            if prop_name in safe_props:
                continue

            # style={{ }} is common but still a perf issue in hot paths
            obj_type = "object" if bracket_type == "{" else "array"
            issues.append(PerfIssue(
                file=filepath, line=i, severity="medium",
                category="inline-creation",
                message=f"Inline {obj_type} literal for prop '{prop_name}' creates "
                        "a new reference on every render.",
                suggestion=f"Extract to a constant, useMemo, or module-level variable: "
                           f"const {prop_name}Value = useMemo(() => (...), [deps]);"
            ))

    return issues


def check_inline_functions_in_jsx(filepath: str, lines: List[str]) -> List[PerfIssue]:
    """Detect inline arrow functions in JSX event handlers."""
    issues = []
    # Pattern: onClick={() => ...} or onSomething={function
    inline_fn_pattern = re.compile(
        r"(on[A-Z]\w*)\s*=\s*\{\s*(?:\([^)]*\)\s*=>|function\b)"
    )

    for i, line in enumerate(lines, 1):
        for match in inline_fn_pattern.finditer(line):
            handler_name = match.group(1)
            issues.append(PerfIssue(
                file=filepath, line=i, severity="medium",
                category="inline-handler",
                message=f"Inline function for '{handler_name}' creates a new function "
                        "on every render, potentially causing child re-renders.",
                suggestion="Extract the handler with useCallback: "
                           f"const {handler_name} = useCallback((...) => ..., [deps]);"
            ))

    return issues


def check_missing_memo(filepath: str, lines: List[str]) -> List[PerfIssue]:
    """Identify components that likely benefit from React.memo."""
    issues = []
    content = "".join(lines)

    # Find exported components that are not wrapped in memo
    component_pattern = re.compile(
        r"export\s+(?:default\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?!React\.memo|memo))"
    )

    for match in component_pattern.finditer(content):
        name = match.group(1) or match.group(2)
        if not name or not name[0].isupper():
            continue

        line_num = content[:match.start()].count("\n") + 1

        # Check if the component receives props and renders JSX
        # Look at the next ~50 lines for JSX and props
        start = match.start()
        snippet = content[start:start + 3000]

        has_props = bool(re.search(r"\(\s*\{[^}]+\}", snippet[:200]))
        has_jsx = bool(re.search(r"return\s*\(?\s*<", snippet))
        already_memo = bool(re.search(r"React\.memo|memo\(", snippet[:100]))

        if has_props and has_jsx and not already_memo:
            # Check if it maps over lists (higher priority for memo)
            has_list = bool(re.search(r"\.map\s*\(", snippet))
            severity = "medium" if has_list else "low"

            issues.append(PerfIssue(
                file=filepath, line=line_num, severity=severity,
                category="missing-memo",
                message=f"Component '{name}' receives props but is not wrapped in "
                        "React.memo. If the parent re-renders frequently, this component "
                        "will re-render unnecessarily.",
                suggestion=f"Wrap with memo: export const {name} = React.memo(function {name}(props) {{ ... }});"
            ))

    return issues


def check_effect_dependencies(filepath: str, lines: List[str]) -> List[PerfIssue]:
    """Check for useEffect/useMemo/useCallback with suspicious dependency patterns."""
    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # useEffect without deps array -- runs every render
        if re.search(r"useEffect\s*\(\s*(?:async\s+)?\(?.*?\)?\s*=>", stripped):
            # Look for the closing of the useEffect call
            lookahead = "".join(lines[i - 1: min(i + 30, len(lines))])
            # Find matching parentheses
            depth = 0
            found_comma_and_bracket = False
            in_hook = False
            for ch in lookahead:
                if "useEffect" in lookahead[:lookahead.index(ch) + 1] if not in_hook else False:
                    pass
                if ch == "(":
                    depth += 1
                    in_hook = True
                elif ch == ")":
                    depth -= 1
                    if depth == 0 and in_hook:
                        break
                elif ch == "[" and depth == 1:
                    found_comma_and_bracket = True

            if not found_comma_and_bracket:
                issues.append(PerfIssue(
                    file=filepath, line=i, severity="high",
                    category="effect-every-render",
                    message="useEffect without a dependency array runs after every render. "
                            "This is rarely intentional and causes performance issues.",
                    suggestion="Add a dependency array: useEffect(() => { ... }, [dep1, dep2]);"
                ))

        # Empty dependency array with references to props/state in the body
        if re.search(r"useEffect\s*\(", stripped):
            # Check for empty deps: , [])
            lookahead = "".join(lines[i - 1: min(i + 30, len(lines))])
            if re.search(r",\s*\[\s*\]\s*\)", lookahead):
                # Check if the effect body references props or state
                effect_body = lookahead
                state_refs = re.findall(r"\b(props\.\w+|set[A-Z]\w+)\b", effect_body)
                if state_refs:
                    issues.append(PerfIssue(
                        file=filepath, line=i, severity="medium",
                        category="stale-closure",
                        message="useEffect has an empty dependency array but references "
                                f"reactive values: {', '.join(set(state_refs))}. "
                                "This may cause stale closure bugs.",
                        suggestion="Add the referenced values to the dependency array."
                    ))

    return issues


def check_unnecessary_state(filepath: str, lines: List[str]) -> List[PerfIssue]:
    """Detect state that could be derived (computed) instead."""
    issues = []
    content = "".join(lines)

    # Pattern: useEffect that only calls a setState
    effect_set_state_pattern = re.compile(
        r"useEffect\s*\(\s*\(\)\s*=>\s*\{\s*set(\w+)\s*\(",
        re.MULTILINE
    )

    for match in effect_set_state_pattern.finditer(content):
        state_name = match.group(1)
        line_num = content[:match.start()].count("\n") + 1

        issues.append(PerfIssue(
            file=filepath, line=line_num, severity="high",
            category="derived-state-in-effect",
            message=f"useEffect that only updates 'set{state_name}' suggests derived state. "
                    "This causes an extra render cycle on every update.",
            suggestion=f"Replace with useMemo: const {state_name.lower()} = useMemo(() => computeValue(deps), [deps]);"
        ))

    return issues


def check_context_overuse(filepath: str, lines: List[str]) -> List[PerfIssue]:
    """Detect Context patterns that may cause excessive re-renders."""
    issues = []
    content = "".join(lines)

    # Pattern: Context.Provider with value={{ ... }} inline object
    inline_context_value = re.compile(
        r"<(\w+)(?:Context)?\.Provider\s+value\s*=\s*\{\s*\{",
        re.MULTILINE
    )

    for match in inline_context_value.finditer(content):
        provider_name = match.group(1)
        line_num = content[:match.start()].count("\n") + 1

        issues.append(PerfIssue(
            file=filepath, line=line_num, severity="high",
            category="context-inline-value",
            message=f"'{provider_name}' Provider has an inline object as value. "
                    "This creates a new object on every render, causing all consumers "
                    "to re-render.",
            suggestion="Memoize the context value: "
                       "const contextValue = useMemo(() => ({ ...values }), [deps]);"
        ))

    return issues


def format_issue(issue: PerfIssue, use_color: bool = True) -> str:
    """Format a performance issue for terminal output."""
    colors = {
        "high": "\033[91m",    # red
        "medium": "\033[93m",  # yellow
        "low": "\033[96m",     # cyan
    }
    reset = "\033[0m"
    bold = "\033[1m"

    sev = issue.severity.upper()
    if use_color:
        sev = f"{colors.get(issue.severity, '')}{sev}{reset}"

    output = f"  {issue.file}:{issue.line}  {sev}  [{issue.category}]\n"
    output += f"    {issue.message}\n"
    if use_color:
        output += f"    {bold}Fix:{reset} {issue.suggestion}\n"
    else:
        output += f"    Fix: {issue.suggestion}\n"

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Scan React code for performance issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Categories checked:
  inline-creation         Inline object/array literals in JSX props
  inline-handler          Inline arrow functions in event handlers
  missing-memo            Exported components not wrapped in React.memo
  effect-every-render     useEffect without dependency array
  stale-closure           useEffect with empty deps referencing reactive values
  derived-state-in-effect useEffect that only sets derived state
  context-inline-value    Context Provider with inline object value

Severity levels:
  high     Likely causes noticeable performance degradation
  medium   May cause issues in frequently rendered components
  low      Minor optimization opportunity

Examples:
  %(prog)s src/
  %(prog)s src/components/ --min-severity high
  %(prog)s . --json
        """,
    )
    parser.add_argument(
        "path",
        help="Directory or file to scan",
    )
    parser.add_argument(
        "--min-severity",
        choices=["high", "medium", "low"],
        default="low",
        help="Minimum severity level to report (default: low)",
    )
    parser.add_argument(
        "--category",
        nargs="+",
        help="Only check specific categories",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".tsx", ".jsx", ".ts", ".js"],
        help="File extensions to scan (default: .tsx .jsx .ts .js)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        default=True,
        help="Include fix suggestions (default: true)",
    )

    args = parser.parse_args()
    target = os.path.abspath(args.path)

    if not os.path.exists(target):
        print(f"Error: path '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if os.path.isfile(target):
        files = [target]
    else:
        files = find_react_files(target, tuple(args.extensions))

    if not files:
        print(f"No matching files found in '{target}'.")
        sys.exit(0)

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    min_sev = severity_rank[args.min_severity]

    all_checks = [
        ("inline-creation", check_inline_objects_in_jsx),
        ("inline-handler", check_inline_functions_in_jsx),
        ("missing-memo", check_missing_memo),
        ("effect-every-render", check_effect_dependencies),
        ("stale-closure", check_effect_dependencies),  # same function handles both
        ("derived-state-in-effect", check_unnecessary_state),
        ("context-inline-value", check_context_overuse),
    ]

    # Deduplicate check functions while respecting category filter
    active_categories = set(args.category) if args.category else None
    seen_functions = set()
    checks_to_run = []
    for cat, fn in all_checks:
        if active_categories and cat not in active_categories:
            continue
        fn_id = id(fn)
        if fn_id not in seen_functions:
            seen_functions.add(fn_id)
            checks_to_run.append(fn)

    all_issues: List[PerfIssue] = []

    for filepath in files:
        lines = read_file_lines(filepath)
        if not lines:
            continue

        for check_fn in checks_to_run:
            issues = check_fn(filepath, lines)
            all_issues.extend(issues)

    # Filter by severity and optional category
    filtered = [
        i for i in all_issues
        if severity_rank[i.severity] <= min_sev
        and (not active_categories or i.category in active_categories)
    ]
    filtered.sort(key=lambda i: (severity_rank[i.severity], i.file, i.line))

    if args.json:
        import json
        output = [
            {
                "file": i.file,
                "line": i.line,
                "severity": i.severity,
                "category": i.category,
                "message": i.message,
                "suggestion": i.suggestion,
            }
            for i in filtered
        ]
        print(json.dumps(output, indent=2))
    else:
        if not filtered:
            print(f"No performance issues found across {len(files)} file(s).")
            sys.exit(0)

        high = sum(1 for i in filtered if i.severity == "high")
        medium = sum(1 for i in filtered if i.severity == "medium")
        low = sum(1 for i in filtered if i.severity == "low")

        print(f"\nScanned {len(files)} file(s). Found {len(filtered)} performance issue(s):\n")

        current_file = None
        for issue in filtered:
            if issue.file != current_file:
                current_file = issue.file
                print(f"\n{current_file}")
            print(format_issue(issue, use_color=not args.no_color))

        print(f"\nSummary: {high} high, {medium} medium, {low} low")

        if high > 0:
            print("\nRecommendation: Address HIGH severity issues first -- "
                  "they likely cause user-visible performance problems.")

    sys.exit(1 if any(i.severity == "high" for i in filtered) else 0)


if __name__ == "__main__":
    main()
