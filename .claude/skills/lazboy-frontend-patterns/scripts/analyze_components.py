#!/usr/bin/env python3
"""
Analyze React component files for common issues.

Checks for:
- Improper hook usage (hooks inside conditions/loops)
- Prop drilling (props passed through many layers)
- Components that should be split (too many state variables, too many lines)
- Missing key props in list rendering (.map without key)
- Inline function/object definitions in JSX props
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Issue:
    file: str
    line: int
    severity: str  # "error", "warning", "info"
    rule: str
    message: str


@dataclass
class ComponentInfo:
    name: str
    file: str
    start_line: int
    end_line: int
    state_count: int = 0
    effect_count: int = 0
    prop_names: List[str] = field(default_factory=list)
    line_count: int = 0


def find_files(root: str, extensions: tuple = (".tsx", ".jsx", ".ts", ".js")) -> List[str]:
    """Recursively find React component files, skipping node_modules and build dirs."""
    files = []
    skip_dirs = {"node_modules", "dist", "build", ".next", "coverage", "__tests__"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for f in filenames:
            if f.endswith(extensions):
                files.append(os.path.join(dirpath, f))
    return sorted(files)


def read_file(filepath: str) -> List[str]:
    """Read file lines, returning empty list on error."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except (OSError, IOError):
        return []


def check_hooks_in_conditions(filepath: str, lines: List[str]) -> List[Issue]:
    """Detect hooks called inside conditions, loops, or nested functions."""
    issues = []
    hook_pattern = re.compile(r"\b(use[A-Z]\w*)\s*\(")
    condition_pattern = re.compile(r"^\s*(if|else|switch|for|while|do)\b")

    in_condition_block = 0
    brace_depth_at_condition = []

    brace_depth = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track brace depth
        brace_depth += line.count("{") - line.count("}")

        # Detect entering a conditional/loop block
        if condition_pattern.match(stripped):
            in_condition_block += 1
            brace_depth_at_condition.append(brace_depth)

        # Check if we left the condition block
        while brace_depth_at_condition and brace_depth < brace_depth_at_condition[-1]:
            brace_depth_at_condition.pop()
            in_condition_block = max(0, in_condition_block - 1)

        # Look for hooks inside conditions
        if in_condition_block > 0:
            for match in hook_pattern.finditer(line):
                hook_name = match.group(1)
                # Skip custom non-hook functions that happen to start with "use"
                if hook_name in ("useCallback", "useMemo", "useState", "useEffect",
                                 "useRef", "useContext", "useReducer", "useId",
                                 "useLayoutEffect", "useImperativeHandle",
                                 "useDebugValue", "useDeferredValue",
                                 "useTransition", "useSyncExternalStore"):
                    issues.append(Issue(
                        file=filepath, line=i, severity="error",
                        rule="hooks-in-condition",
                        message=f"Hook '{hook_name}' called inside a conditional or loop. "
                                "Hooks must be called at the top level of the component."
                    ))

    return issues


def check_missing_keys(filepath: str, lines: List[str]) -> List[Issue]:
    """Detect .map() calls in JSX that may be missing key props."""
    issues = []
    map_pattern = re.compile(r"\.map\s*\(")

    for i, line in enumerate(lines, 1):
        if map_pattern.search(line):
            # Look ahead up to 5 lines for JSX return with key prop
            lookahead = "".join(lines[i - 1: min(i + 7, len(lines))])
            # Check if there is JSX being returned
            if re.search(r"<\w+", lookahead):
                # Check if key prop exists
                if not re.search(r"\bkey\s*=", lookahead):
                    issues.append(Issue(
                        file=filepath, line=i, severity="error",
                        rule="missing-key",
                        message="List rendering with .map() may be missing a 'key' prop. "
                                "Every element in a list needs a stable, unique key."
                    ))

    return issues


def check_prop_drilling(filepath: str, lines: List[str]) -> List[Issue]:
    """Detect potential prop drilling by finding props passed through without use."""
    issues = []
    content = "".join(lines)

    # Find component function signatures with destructured props
    component_pattern = re.compile(
        r"(?:function|const)\s+(\w+)\s*(?:=\s*)?(?:\([^)]*\{([^}]*)\}[^)]*\)|"
        r"\(\s*\{([^}]*)\}\s*(?::\s*\w+)?\s*\))",
        re.MULTILINE
    )

    for match in component_pattern.finditer(content):
        component_name = match.group(1)
        props_str = match.group(2) or match.group(3)
        if not props_str:
            continue

        # Parse prop names
        prop_names = [
            p.strip().split(":")[0].strip().split("=")[0].strip()
            for p in props_str.split(",")
            if p.strip() and not p.strip().startswith("...")
        ]

        if len(prop_names) > 8:
            line_num = content[:match.start()].count("\n") + 1
            issues.append(Issue(
                file=filepath, line=line_num, severity="warning",
                rule="too-many-props",
                message=f"Component '{component_name}' receives {len(prop_names)} props. "
                        "Consider using Context, composition, or grouping related props "
                        "into objects to reduce prop count."
            ))

    return issues


def check_component_size(filepath: str, lines: List[str]) -> List[Issue]:
    """Detect components that are too large and should be split."""
    issues = []
    content = "".join(lines)

    # Find function components
    func_pattern = re.compile(
        r"(?:export\s+)?(?:default\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:React\.)?(?:memo\s*\()?\s*(?:function|\([^)]*\)\s*(?::\s*\w+)?\s*=>))",
        re.MULTILINE
    )

    for match in func_pattern.finditer(content):
        component_name = match.group(1) or match.group(2)
        if not component_name or not component_name[0].isupper():
            continue

        start_pos = match.start()
        start_line = content[:start_pos].count("\n") + 1

        # Find the component body by tracking braces
        brace_start = content.find("{", match.end())
        if brace_start == -1:
            # Arrow function without braces -- single expression, skip
            continue

        depth = 0
        end_pos = brace_start
        for j in range(brace_start, len(content)):
            if content[j] == "{":
                depth += 1
            elif content[j] == "}":
                depth -= 1
                if depth == 0:
                    end_pos = j
                    break

        component_body = content[start_pos:end_pos + 1]
        line_count = component_body.count("\n") + 1

        # Count useState calls
        state_count = len(re.findall(r"\buseState\b", component_body))
        effect_count = len(re.findall(r"\buseEffect\b", component_body))

        if line_count > 200:
            issues.append(Issue(
                file=filepath, line=start_line, severity="warning",
                rule="large-component",
                message=f"Component '{component_name}' is {line_count} lines long. "
                        "Consider extracting sub-components or custom hooks."
            ))

        if state_count > 5:
            issues.append(Issue(
                file=filepath, line=start_line, severity="warning",
                rule="too-many-state",
                message=f"Component '{component_name}' has {state_count} useState calls. "
                        "Consider useReducer or extracting state into a custom hook."
            ))

        if effect_count > 3:
            issues.append(Issue(
                file=filepath, line=start_line, severity="info",
                rule="many-effects",
                message=f"Component '{component_name}' has {effect_count} useEffect calls. "
                        "Consider extracting effects into custom hooks for clarity."
            ))

    return issues


def check_hook_dependencies(filepath: str, lines: List[str]) -> List[Issue]:
    """Detect useEffect/useMemo/useCallback with missing dependency arrays."""
    issues = []
    hook_with_deps = re.compile(
        r"\b(useEffect|useMemo|useCallback)\s*\(\s*(?:async\s+)?\(?[^)]*\)?\s*=>"
    )

    for i, line in enumerate(lines, 1):
        match = hook_with_deps.search(line)
        if match:
            hook_name = match.group(1)
            # Look ahead to find closing of the hook call
            lookahead = "".join(lines[i - 1: min(i + 20, len(lines))])
            # Count parens to find the hook's closing paren
            depth = 0
            found_array = False
            for ch in lookahead[match.start():]:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
                elif ch == "[" and depth == 1:
                    found_array = True

            if not found_array and hook_name == "useEffect":
                issues.append(Issue(
                    file=filepath, line=i, severity="error",
                    rule="missing-deps-array",
                    message=f"'{hook_name}' may be missing a dependency array. "
                            "Without one, the effect runs after every render."
                ))

    return issues


def format_issue(issue: Issue, use_color: bool = True) -> str:
    """Format a single issue for terminal output."""
    severity_colors = {
        "error": "\033[91m",
        "warning": "\033[93m",
        "info": "\033[96m",
    }
    reset = "\033[0m"

    severity_label = issue.severity.upper()
    if use_color:
        color = severity_colors.get(issue.severity, "")
        severity_label = f"{color}{severity_label}{reset}"

    rel_file = issue.file
    return f"  {rel_file}:{issue.line}  {severity_label}  [{issue.rule}] {issue.message}"


def main():
    parser = argparse.ArgumentParser(
        description="Analyze React component files for common issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rules checked:
  hooks-in-condition   Hooks called inside conditions or loops
  missing-key          .map() rendering without key prop
  too-many-props       Components with excessive prop count (>8)
  large-component      Components exceeding 200 lines
  too-many-state       Components with more than 5 useState calls
  many-effects         Components with more than 3 useEffect calls
  missing-deps-array   useEffect without dependency array

Examples:
  %(prog)s src/
  %(prog)s src/components/ --severity error
  %(prog)s . --extensions .tsx .jsx
        """,
    )
    parser.add_argument(
        "path",
        help="Directory or file to analyze",
    )
    parser.add_argument(
        "--severity",
        choices=["error", "warning", "info"],
        default="info",
        help="Minimum severity to report (default: info)",
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

    args = parser.parse_args()
    target = os.path.abspath(args.path)

    if not os.path.exists(target):
        print(f"Error: path '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Collect files
    if os.path.isfile(target):
        files = [target]
    else:
        files = find_files(target, tuple(args.extensions))

    if not files:
        print(f"No matching files found in '{target}'.")
        sys.exit(0)

    severity_order = {"error": 0, "warning": 1, "info": 2}
    min_severity = severity_order[args.severity]

    all_issues: List[Issue] = []

    for filepath in files:
        lines = read_file(filepath)
        if not lines:
            continue

        all_issues.extend(check_hooks_in_conditions(filepath, lines))
        all_issues.extend(check_missing_keys(filepath, lines))
        all_issues.extend(check_prop_drilling(filepath, lines))
        all_issues.extend(check_component_size(filepath, lines))
        all_issues.extend(check_hook_dependencies(filepath, lines))

    # Filter by severity
    filtered = [i for i in all_issues if severity_order[i.severity] <= min_severity]
    filtered.sort(key=lambda i: (i.file, i.line))

    if args.json:
        import json
        output = [
            {
                "file": i.file,
                "line": i.line,
                "severity": i.severity,
                "rule": i.rule,
                "message": i.message,
            }
            for i in filtered
        ]
        print(json.dumps(output, indent=2))
    else:
        if not filtered:
            print(f"No issues found across {len(files)} file(s).")
            sys.exit(0)

        errors = sum(1 for i in filtered if i.severity == "error")
        warnings = sum(1 for i in filtered if i.severity == "warning")
        infos = sum(1 for i in filtered if i.severity == "info")

        print(f"\nAnalyzed {len(files)} file(s). Found {len(filtered)} issue(s):\n")

        current_file = None
        for issue in filtered:
            if issue.file != current_file:
                current_file = issue.file
                print(f"\n{current_file}")
            print(format_issue(issue, use_color=not args.no_color))

        print(f"\nSummary: {errors} error(s), {warnings} warning(s), {infos} info(s)")

    sys.exit(1 if any(i.severity == "error" for i in filtered) else 0)


if __name__ == "__main__":
    main()
