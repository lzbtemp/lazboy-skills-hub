#!/usr/bin/env python3
"""
Scan Java files for style and coding standard violations.

Checks:
- Naming conventions (classes, methods, fields, constants)
- Missing Optional for nullable return types
- Raw type usage (List instead of List<T>)
- Old-style for loops that should be streams
- Field injection (@Autowired on fields) instead of constructor injection
- Mutable DTOs (setters on DTO classes)
- Magic numbers
- String concatenation in log statements
- Broad exception catches
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Set


@dataclass
class StyleIssue:
    file: str
    line: int
    severity: str  # "error", "warning", "info"
    rule: str
    message: str


def find_java_files(root: str) -> List[str]:
    """Recursively find Java source files, skipping build directories."""
    files = []
    skip_dirs = {"target", "build", ".gradle", ".idea", ".mvn", "node_modules", ".git"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for f in filenames:
            if f.endswith(".java"):
                files.append(os.path.join(dirpath, f))
    return sorted(files)


def read_file(filepath: str) -> List[str]:
    """Read file lines safely."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except (OSError, IOError):
        return []


def check_naming_conventions(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Check class, method, field, and constant naming conventions."""
    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments and annotations
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("@"):
            continue

        # Class/interface/enum/record names must be PascalCase
        class_match = re.match(
            r"(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:abstract\s+)?"
            r"(?:sealed\s+)?(?:class|interface|enum|record)\s+(\w+)",
            stripped
        )
        if class_match:
            name = class_match.group(1)
            if not re.match(r"^[A-Z][a-zA-Z0-9]*$", name):
                issues.append(StyleIssue(
                    file=filepath, line=i, severity="error",
                    rule="class-naming",
                    message=f"Class/interface '{name}' should use PascalCase (e.g., '{name[0].upper() + name[1:]}')."
                ))

        # Constants: static final fields should be UPPER_SNAKE_CASE
        const_match = re.match(
            r"\s*(?:public|private|protected)?\s*static\s+final\s+\w+(?:<[^>]+>)?\s+(\w+)\s*=",
            stripped
        )
        if const_match:
            name = const_match.group(1)
            # Allow logger names (log, logger, LOG)
            if name.lower() in ("log", "logger"):
                continue
            # serialVersionUID is conventional
            if name == "serialVersionUID":
                continue
            if not re.match(r"^[A-Z][A-Z0-9_]*$", name):
                issues.append(StyleIssue(
                    file=filepath, line=i, severity="warning",
                    rule="constant-naming",
                    message=f"Constant '{name}' should use UPPER_SNAKE_CASE "
                            f"(e.g., '{re.sub(r'([a-z])([A-Z])', r'\\1_\\2', name).upper()}')."
                ))

        # Method names should be camelCase
        method_match = re.match(
            r"\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?"
            r"(?:<[^>]+>\s+)?(?:\w+(?:<[^>]+>)?(?:\[\])?)\s+(\w+)\s*\(",
            stripped
        )
        if method_match:
            name = method_match.group(1)
            # Skip constructors (same name as class), and common patterns
            if name[0].isupper():
                continue
            if not re.match(r"^[a-z][a-zA-Z0-9]*$", name):
                issues.append(StyleIssue(
                    file=filepath, line=i, severity="warning",
                    rule="method-naming",
                    message=f"Method '{name}' should use camelCase."
                ))

    return issues


def check_raw_types(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Detect raw generic type usage."""
    issues = []
    # Common generic types that should always have type parameters
    generic_types = {"List", "Map", "Set", "Collection", "Optional", "Stream",
                     "Iterator", "Iterable", "Comparable", "Supplier", "Function",
                     "Consumer", "Predicate", "Future", "CompletableFuture"}

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("import"):
            continue

        for gtype in generic_types:
            # Match raw type usage: "List list", "Map map", "new ArrayList()"
            # But not "List<String>" or "List.of()"
            raw_patterns = [
                # Declaration: List myList or List myList =
                rf"\b{gtype}\s+\w+\s*[=;,)]",
                # new ArrayList() without type param
                rf"new\s+{gtype}\s*\(\)",
            ]
            for pattern in raw_patterns:
                if re.search(pattern, line):
                    # Make sure it is not actually parameterized (check for < after type name)
                    # Better check: ensure no <> follows the type name on this line
                    type_pos = line.find(gtype)
                    after_type = line[type_pos + len(gtype):].lstrip()
                    if not after_type.startswith("<"):
                        issues.append(StyleIssue(
                            file=filepath, line=i, severity="warning",
                            rule="raw-type",
                            message=f"Raw type '{gtype}' used without type parameter. "
                                    f"Use '{gtype}<T>' for type safety."
                        ))
                        break  # One issue per line per type

    return issues


def check_old_style_loops(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Detect traditional for loops that could be replaced with streams."""
    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Traditional indexed for loop: for (int i = 0; i < list.size(); i++)
        if re.match(r"for\s*\(\s*int\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*\w+\.(size|length)", stripped):
            issues.append(StyleIssue(
                file=filepath, line=i, severity="info",
                rule="prefer-stream",
                message="Traditional indexed for-loop could potentially be replaced with "
                        "a stream pipeline or enhanced for-each loop."
            ))

        # Enhanced for loop with simple add to another collection
        if re.match(r"for\s*\(\s*\w+(?:<[^>]+>)?\s+\w+\s*:\s*\w+\s*\)", stripped):
            # Look ahead for simple body: just an add/put or simple transformation
            if i < len(lines):
                next_line = lines[i].strip() if i < len(lines) else ""
                body_lines = []
                # Collect body (simple single-statement body)
                if next_line == "{":
                    j = i + 1
                    while j < len(lines) and lines[j].strip() != "}":
                        body_lines.append(lines[j].strip())
                        j += 1
                elif not next_line.startswith("{"):
                    body_lines = [next_line]

                if len(body_lines) == 1:
                    body = body_lines[0]
                    if re.match(r"\w+\.add\(", body) or re.match(r"if\s*\(.*\)\s*\w+\.add\(", body):
                        issues.append(StyleIssue(
                            file=filepath, line=i, severity="info",
                            rule="prefer-stream",
                            message="Simple for-each with collection.add() could be replaced "
                                    "with stream().filter().collect(toList())."
                        ))

    return issues


def check_field_injection(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Detect @Autowired field injection -- prefer constructor injection."""
    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "@Autowired":
            # Check if the next non-empty line is a field (not a constructor or method)
            for j in range(i, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if not next_line or next_line.startswith("@"):
                    continue
                # If it is a field declaration (has type and name, ends with ;)
                if next_line.endswith(";") and not "(" in next_line:
                    issues.append(StyleIssue(
                        file=filepath, line=i, severity="warning",
                        rule="field-injection",
                        message="Field injection with @Autowired is discouraged. "
                                "Use constructor injection for better testability and immutability."
                    ))
                break

    return issues


def check_log_concatenation(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Detect string concatenation in log statements."""
    issues = []
    log_concat_pattern = re.compile(r"log\.\w+\s*\(\s*\".*\"\s*\+")

    for i, line in enumerate(lines, 1):
        if log_concat_pattern.search(line):
            issues.append(StyleIssue(
                file=filepath, line=i, severity="warning",
                rule="log-concatenation",
                message="String concatenation in log statement. "
                        "Use parameterized logging: log.info(\"message key={}\", value);"
            ))

    return issues


def check_broad_catches(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Detect overly broad exception catches."""
    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # catch (Exception e) or catch (Throwable t)
        broad_match = re.match(r"}\s*catch\s*\(\s*(Exception|Throwable)\s+\w+\s*\)", stripped)
        if not broad_match:
            broad_match = re.match(r"catch\s*\(\s*(Exception|Throwable)\s+\w+\s*\)", stripped)

        if broad_match:
            exception_type = broad_match.group(1)
            # Check if the catch body is empty or just swallows
            if i < len(lines):
                next_lines = "".join(lines[i:i + 3]).strip()
                if re.match(r"^\s*\}\s*$", next_lines) or not next_lines:
                    issues.append(StyleIssue(
                        file=filepath, line=i, severity="error",
                        rule="swallowed-exception",
                        message=f"Caught '{exception_type}' appears to be swallowed. "
                                "Always log or rethrow exceptions."
                    ))
                else:
                    issues.append(StyleIssue(
                        file=filepath, line=i, severity="warning",
                        rule="broad-catch",
                        message=f"Broad catch of '{exception_type}'. "
                                "Prefer catching specific exception types."
                    ))

    return issues


def check_magic_numbers(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Detect magic numbers in logic (excluding common values like 0, 1, -1)."""
    issues = []
    allowed_numbers = {"0", "1", "-1", "2", "0.0", "1.0", "0L", "1L", "100"}

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments, imports, annotations, constant declarations
        if (stripped.startswith("//") or stripped.startswith("*")
                or stripped.startswith("import") or stripped.startswith("@")
                or "static final" in stripped):
            continue

        # Skip test files -- magic numbers are acceptable in test data
        if "Test" in os.path.basename(filepath):
            continue

        # Find numeric literals in comparisons and assignments
        numbers = re.findall(r"(?<![.\w])(\d+\.?\d*[LlFfDd]?)(?![.\w])", line)
        for num in numbers:
            clean = num.rstrip("LlFfDd")
            if clean not in allowed_numbers and len(clean) > 1:
                # Skip array indices and common patterns
                context = line[max(0, line.index(num) - 10):line.index(num) + len(num) + 10]
                if re.search(r"\[\s*" + re.escape(num), context):
                    continue
                issues.append(StyleIssue(
                    file=filepath, line=i, severity="info",
                    rule="magic-number",
                    message=f"Magic number '{num}' should be extracted to a named constant."
                ))
                break  # One per line

    return issues


def check_missing_optional(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Detect methods that return null instead of Optional."""
    issues = []
    content = "".join(lines)

    # Find methods that contain "return null"
    method_pattern = re.compile(
        r"(?:public|protected)\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)\s*\{",
        re.MULTILINE
    )

    for match in method_pattern.finditer(content):
        return_type = match.group(1)
        method_name = match.group(2)

        # Skip void and primitive return types
        if return_type in ("void", "int", "long", "double", "float", "boolean", "byte", "char", "short"):
            continue
        # Skip methods already returning Optional
        if return_type.startswith("Optional"):
            continue

        # Check if method body contains "return null"
        start = match.end()
        depth = 1
        end = start
        for j in range(start, min(start + 2000, len(content))):
            if content[j] == "{":
                depth += 1
            elif content[j] == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break

        method_body = content[start:end]
        if re.search(r"\breturn\s+null\s*;", method_body):
            line_num = content[:match.start()].count("\n") + 1
            # Only flag find/get methods as they are most likely to benefit
            if re.match(r"(find|get|lookup|fetch|load|resolve)", method_name):
                issues.append(StyleIssue(
                    file=filepath, line=line_num, severity="warning",
                    rule="missing-optional",
                    message=f"Method '{method_name}' returns null. Consider returning "
                            f"Optional<{return_type}> instead for explicit null handling."
                ))

    return issues


def check_mutable_dtos(filepath: str, lines: List[str]) -> List[StyleIssue]:
    """Detect DTO classes with setter methods."""
    issues = []
    filename = os.path.basename(filepath)

    # Check if this is likely a DTO
    is_dto = any(pattern in filename for pattern in ("Dto", "DTO", "Request", "Response", "Event"))
    if not is_dto:
        content = "".join(lines)
        is_dto = bool(re.search(r"class\s+\w*(?:Dto|DTO|Request|Response|Event)\b", content))

    if not is_dto:
        return issues

    for i, line in enumerate(lines, 1):
        setter_match = re.match(r"\s*public\s+void\s+(set\w+)\s*\(", line.strip())
        if setter_match:
            setter_name = setter_match.group(1)
            issues.append(StyleIssue(
                file=filepath, line=i, severity="warning",
                rule="mutable-dto",
                message=f"Setter '{setter_name}' on a DTO class. "
                        "Prefer records or immutable classes for DTOs."
            ))

    return issues


def format_issue(issue: StyleIssue, use_color: bool = True) -> str:
    """Format a single issue for terminal output."""
    colors = {"error": "\033[91m", "warning": "\033[93m", "info": "\033[96m"}
    reset = "\033[0m"

    sev = issue.severity.upper()
    if use_color:
        sev = f"{colors.get(issue.severity, '')}{sev}{reset}"

    return f"  {issue.file}:{issue.line}  {sev}  [{issue.rule}] {issue.message}"


def main():
    parser = argparse.ArgumentParser(
        description="Scan Java files for coding style issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rules checked:
  class-naming        Classes/interfaces not in PascalCase
  constant-naming     Constants not in UPPER_SNAKE_CASE
  method-naming       Methods not in camelCase
  raw-type            Generic types used without type parameters
  prefer-stream       For loops that could be stream pipelines
  field-injection     @Autowired on fields instead of constructors
  log-concatenation   String concatenation in log statements
  broad-catch         Catching Exception/Throwable broadly
  swallowed-exception Caught exceptions that are silently discarded
  magic-number        Numeric literals that should be named constants
  missing-optional    Find/get methods returning null instead of Optional
  mutable-dto         Setter methods on DTO classes

Examples:
  %(prog)s src/main/java/
  %(prog)s . --severity warning
  %(prog)s src/ --rules raw-type field-injection
        """,
    )
    parser.add_argument("path", help="Directory or file to scan")
    parser.add_argument(
        "--severity",
        choices=["error", "warning", "info"],
        default="info",
        help="Minimum severity to report (default: info)",
    )
    parser.add_argument(
        "--rules",
        nargs="+",
        help="Only check specific rules (e.g., --rules raw-type field-injection)",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()
    target = os.path.abspath(args.path)

    if not os.path.exists(target):
        print(f"Error: path '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if os.path.isfile(target):
        files = [target]
    else:
        files = find_java_files(target)

    if not files:
        print(f"No Java files found in '{target}'.")
        sys.exit(0)

    severity_rank = {"error": 0, "warning": 1, "info": 2}
    min_sev = severity_rank[args.severity]
    active_rules: Set[str] | None = set(args.rules) if args.rules else None

    all_checks = [
        check_naming_conventions,
        check_raw_types,
        check_old_style_loops,
        check_field_injection,
        check_log_concatenation,
        check_broad_catches,
        check_magic_numbers,
        check_missing_optional,
        check_mutable_dtos,
    ]

    all_issues: List[StyleIssue] = []

    for filepath in files:
        lines = read_file(filepath)
        if not lines:
            continue
        for check_fn in all_checks:
            all_issues.extend(check_fn(filepath, lines))

    # Filter
    filtered = [
        i for i in all_issues
        if severity_rank[i.severity] <= min_sev
        and (active_rules is None or i.rule in active_rules)
    ]
    filtered.sort(key=lambda i: (i.file, i.line))

    if args.json:
        import json
        output = [
            {"file": i.file, "line": i.line, "severity": i.severity,
             "rule": i.rule, "message": i.message}
            for i in filtered
        ]
        print(json.dumps(output, indent=2))
    else:
        if not filtered:
            print(f"No style issues found across {len(files)} Java file(s).")
            sys.exit(0)

        errors = sum(1 for i in filtered if i.severity == "error")
        warnings = sum(1 for i in filtered if i.severity == "warning")
        infos = sum(1 for i in filtered if i.severity == "info")

        print(f"\nScanned {len(files)} Java file(s). Found {len(filtered)} issue(s):\n")

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
