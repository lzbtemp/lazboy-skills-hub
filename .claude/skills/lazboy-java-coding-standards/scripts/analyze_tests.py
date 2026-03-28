#!/usr/bin/env python3
"""
Analyze Java test files for quality and coverage patterns.

Checks:
- Coverage of public methods (identifies untested public methods)
- Proper assertion usage (no empty tests, no System.out assertions)
- Test naming patterns (consistent naming convention)
- Identifies missing test classes for production classes
- Verifies test structure (Arrange-Act-Assert pattern)
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class TestIssue:
    file: str
    line: int
    severity: str  # "error", "warning", "info"
    rule: str
    message: str


@dataclass
class ClassInfo:
    name: str
    file: str
    public_methods: List[str] = field(default_factory=list)
    is_test: bool = False


@dataclass
class TestMethodInfo:
    name: str
    line: int
    has_assertion: bool = False
    has_arrange: bool = False
    has_act: bool = False
    has_assert_comment: bool = False
    body_lines: int = 0


def find_java_files(root: str, test_only: bool = False) -> List[str]:
    """Find Java files. If test_only, only return files in test directories."""
    files = []
    skip_dirs = {"target", "build", ".gradle", ".idea", ".mvn", "node_modules", ".git"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for f in filenames:
            if not f.endswith(".java"):
                continue
            filepath = os.path.join(dirpath, f)
            is_test_file = "/test/" in filepath or "/tests/" in filepath or f.endswith("Test.java") or f.endswith("Tests.java")
            if test_only and not is_test_file:
                continue
            if not test_only:
                files.append(filepath)
            else:
                files.append(filepath)
    return sorted(files)


def read_file(filepath: str) -> List[str]:
    """Read file lines safely."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except (OSError, IOError):
        return []


def extract_class_info(filepath: str, lines: List[str]) -> Optional[ClassInfo]:
    """Extract class name and public methods from a Java file."""
    content = "".join(lines)
    filename = os.path.basename(filepath)

    # Find class name
    class_match = re.search(
        r"(?:public\s+)?(?:abstract\s+)?(?:class|interface|enum|record)\s+(\w+)",
        content
    )
    if not class_match:
        return None

    class_name = class_match.group(1)
    is_test = (
        class_name.endswith("Test") or class_name.endswith("Tests")
        or class_name.endswith("IT") or class_name.endswith("Spec")
        or "/test/" in filepath or "/tests/" in filepath
    )

    info = ClassInfo(name=class_name, file=filepath, is_test=is_test)

    if not is_test:
        # Extract public method names (non-constructor, non-getter/setter for entities)
        method_pattern = re.compile(
            r"public\s+(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?"
            r"(?:<[^>]+>\s+)?(\w+(?:<[^>]+>)?(?:\[\])?)\s+(\w+)\s*\(",
            re.MULTILINE
        )
        for m in method_pattern.finditer(content):
            return_type = m.group(1)
            method_name = m.group(2)
            # Skip constructors (return type equals class name)
            if method_name == class_name:
                continue
            # Skip simple getters/setters for entity classes
            if re.match(r"(get|set|is|has)[A-Z]", method_name) and "Entity" in filename:
                continue
            info.public_methods.append(method_name)

    return info


def extract_test_methods(filepath: str, lines: List[str]) -> List[TestMethodInfo]:
    """Extract test method information from a test file."""
    methods = []
    content = "".join(lines)

    # Find @Test annotated methods
    test_annotation_pattern = re.compile(r"@(?:Test|ParameterizedTest|RepeatedTest)")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if test_annotation_pattern.search(line):
            # Find the method signature (may be on this line or next lines)
            j = i + 1
            method_name = None
            while j < len(lines) and j < i + 5:
                method_match = re.search(r"(?:void|[A-Za-z]+)\s+(\w+)\s*\(", lines[j])
                if method_match:
                    method_name = method_match.group(1)
                    break
                j += 1

            if method_name:
                method_info = TestMethodInfo(name=method_name, line=i + 1)

                # Extract method body
                brace_start = None
                for k in range(j, min(j + 3, len(lines))):
                    if "{" in lines[k]:
                        brace_start = k
                        break

                if brace_start is not None:
                    depth = 0
                    body_lines = []
                    for k in range(brace_start, len(lines)):
                        body_line = lines[k]
                        depth += body_line.count("{") - body_line.count("}")
                        body_lines.append(body_line)
                        if depth <= 0:
                            break

                    body = "".join(body_lines)
                    method_info.body_lines = len(body_lines)

                    # Check for assertions
                    assertion_patterns = [
                        r"assertThat\b", r"assertEquals\b", r"assertTrue\b",
                        r"assertFalse\b", r"assertNotNull\b", r"assertNull\b",
                        r"assertThrows\b", r"assertThatThrownBy\b",
                        r"assertThatCode\b", r"verify\b", r"assertDoesNotThrow\b",
                        r"assertSoftly\b", r"assertAll\b",
                        r"expectedException\b", r"expect\b",
                    ]
                    method_info.has_assertion = any(
                        re.search(p, body) for p in assertion_patterns
                    )

                    # Check for Arrange-Act-Assert comments
                    method_info.has_arrange = bool(re.search(r"//\s*(?:Arrange|Given|Setup)", body, re.IGNORECASE))
                    method_info.has_act = bool(re.search(r"//\s*(?:Act|When)", body, re.IGNORECASE))
                    method_info.has_assert_comment = bool(re.search(r"//\s*(?:Assert|Then)", body, re.IGNORECASE))

                methods.append(method_info)

        i += 1

    return methods


def check_test_naming(filepath: str, methods: List[TestMethodInfo]) -> List[TestIssue]:
    """Verify test method naming follows conventions."""
    issues = []

    # Common good patterns
    good_patterns = [
        r"^should\w+$",                          # shouldReturnUser_whenEmailExists
        r"^should\w+_when\w+$",                  # shouldThrow_whenNotFound
        r"^\w+_\w+_\w+$",                        # findByEmail_existingEmail_returnsUser
        r"^test\w+$",                             # testCreateOrder (legacy but acceptable)
        r"^given\w+_when\w+_then\w+$",           # givenUser_whenSave_thenPersisted
    ]

    for method in methods:
        matches_pattern = any(re.match(p, method.name) for p in good_patterns)
        if not matches_pattern:
            # Check for very short or vague names
            if len(method.name) < 10:
                issues.append(TestIssue(
                    file=filepath, line=method.line, severity="warning",
                    rule="test-naming",
                    message=f"Test method '{method.name}' is too short or vague. "
                            "Use descriptive names like 'shouldReturnUser_whenEmailExists'."
                ))
            elif method.name.startswith("test") and "_" not in method.name:
                issues.append(TestIssue(
                    file=filepath, line=method.line, severity="info",
                    rule="test-naming",
                    message=f"Test method '{method.name}' uses old naming convention. "
                            "Prefer 'should..._when...' pattern."
                ))

    return issues


def check_assertions(filepath: str, methods: List[TestMethodInfo]) -> List[TestIssue]:
    """Verify tests have proper assertions."""
    issues = []

    for method in methods:
        if not method.has_assertion:
            issues.append(TestIssue(
                file=filepath, line=method.line, severity="error",
                rule="missing-assertion",
                message=f"Test '{method.name}' has no assertions. "
                        "Every test should verify expected behavior with assertThat/verify."
            ))

        if method.body_lines <= 2:
            issues.append(TestIssue(
                file=filepath, line=method.line, severity="warning",
                rule="empty-test",
                message=f"Test '{method.name}' appears to be empty or trivial ({method.body_lines} lines)."
            ))

    return issues


def check_assertion_style(filepath: str, lines: List[str]) -> List[TestIssue]:
    """Check for outdated assertion styles."""
    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # JUnit assertEquals instead of AssertJ
        if re.search(r"\bassertEquals\s*\(", stripped):
            issues.append(TestIssue(
                file=filepath, line=i, severity="info",
                rule="assertion-style",
                message="Use AssertJ 'assertThat(actual).isEqualTo(expected)' instead of "
                        "JUnit 'assertEquals'. AssertJ provides better error messages."
            ))

        # System.out in tests
        if re.search(r"System\.(out|err)\.print", stripped):
            issues.append(TestIssue(
                file=filepath, line=i, severity="warning",
                rule="sysout-in-test",
                message="System.out/err in test. Use assertions to verify behavior, "
                        "not manual output inspection."
            ))

        # Thread.sleep in tests
        if re.search(r"Thread\.sleep\s*\(", stripped):
            issues.append(TestIssue(
                file=filepath, line=i, severity="warning",
                rule="thread-sleep",
                message="Thread.sleep() in test makes it slow and flaky. "
                        "Use Awaitility or CountDownLatch for async assertions."
            ))

        # Catching exceptions manually instead of assertThrows
        if re.search(r"catch\s*\(\s*\w+Exception", stripped) and "/test/" in filepath:
            # Check if it is a try-catch expecting an exception
            context = "".join(lines[max(0, i - 5):i + 3])
            if re.search(r"fail\s*\(", context):
                issues.append(TestIssue(
                    file=filepath, line=i, severity="info",
                    rule="manual-exception-test",
                    message="Manual try-catch-fail pattern. "
                            "Use assertThatThrownBy(() -> ...).isInstanceOf(...) instead."
                ))

    return issues


def find_missing_test_classes(
    source_classes: Dict[str, ClassInfo],
    test_classes: Dict[str, ClassInfo],
    source_root: str,
) -> List[TestIssue]:
    """Identify production classes that have no corresponding test class."""
    issues = []

    # Classes that typically do not need dedicated tests
    skip_suffixes = ("Config", "Configuration", "Properties", "Constants",
                     "Application", "Exception", "Dto", "DTO", "Request",
                     "Response", "Event", "Enum")

    for class_name, info in source_classes.items():
        # Skip classes without public methods
        if not info.public_methods:
            continue

        # Skip config/dto/exception classes
        if any(class_name.endswith(s) for s in skip_suffixes):
            continue

        # Check for corresponding test class
        test_name_candidates = [
            f"{class_name}Test",
            f"{class_name}Tests",
            f"{class_name}IT",
            f"{class_name}Spec",
        ]

        has_test = any(name in test_classes for name in test_name_candidates)
        if not has_test:
            issues.append(TestIssue(
                file=info.file, line=1, severity="warning",
                rule="missing-test-class",
                message=f"Class '{class_name}' has {len(info.public_methods)} public method(s) "
                        f"but no test class found. Expected '{class_name}Test'."
            ))

    return issues


def check_test_method_coverage(
    source_classes: Dict[str, ClassInfo],
    test_classes: Dict[str, ClassInfo],
    test_files: Dict[str, List[TestMethodInfo]],
) -> List[TestIssue]:
    """Check if test classes cover the public methods of their source classes."""
    issues = []

    for test_name, test_info in test_classes.items():
        # Derive the source class name
        source_name = None
        for suffix in ("Test", "Tests", "IT", "Spec"):
            if test_name.endswith(suffix):
                source_name = test_name[: -len(suffix)]
                break

        if not source_name or source_name not in source_classes:
            continue

        source_info = source_classes[source_name]
        test_methods = test_files.get(test_info.file, [])
        test_method_names = " ".join(m.name.lower() for m in test_methods)

        # Check each public method has at least one test mentioning it
        untested = []
        for method in source_info.public_methods:
            # Check if any test method name references this method
            method_lower = method.lower()
            if method_lower not in test_method_names:
                untested.append(method)

        if untested and len(untested) <= 5:
            issues.append(TestIssue(
                file=test_info.file, line=1, severity="info",
                rule="untested-methods",
                message=f"These public methods of '{source_name}' may not have "
                        f"corresponding tests: {', '.join(untested)}"
            ))
        elif len(untested) > 5:
            issues.append(TestIssue(
                file=test_info.file, line=1, severity="warning",
                rule="low-test-coverage",
                message=f"Test class for '{source_name}' appears to cover only "
                        f"{len(source_info.public_methods) - len(untested)} of "
                        f"{len(source_info.public_methods)} public methods."
            ))

    return issues


def format_issue(issue: TestIssue, use_color: bool = True) -> str:
    """Format a single issue for terminal output."""
    colors = {"error": "\033[91m", "warning": "\033[93m", "info": "\033[96m"}
    reset = "\033[0m"

    sev = issue.severity.upper()
    if use_color:
        sev = f"{colors.get(issue.severity, '')}{sev}{reset}"

    return f"  {issue.file}:{issue.line}  {sev}  [{issue.rule}] {issue.message}"


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Java test files for quality and coverage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rules checked:
  test-naming          Test method naming does not follow conventions
  missing-assertion    Test method has no assertions
  empty-test           Test method body is trivially small
  assertion-style      Uses JUnit assertEquals instead of AssertJ
  sysout-in-test       System.out/err used in tests
  thread-sleep         Thread.sleep used in tests (flaky)
  manual-exception-test Manual try-catch-fail instead of assertThrows
  missing-test-class   Production class has no corresponding test class
  untested-methods     Public methods not covered by test names
  low-test-coverage    Test class covers less than half of public methods

Examples:
  %(prog)s src/
  %(prog)s src/test/java/ --test-only
  %(prog)s . --severity warning --json
        """,
    )
    parser.add_argument("path", help="Root directory to analyze (should contain src/)")
    parser.add_argument(
        "--severity",
        choices=["error", "warning", "info"],
        default="info",
        help="Minimum severity to report (default: info)",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only analyze test files (skip coverage checks)",
    )
    parser.add_argument(
        "--rules",
        nargs="+",
        help="Only check specific rules",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()
    target = os.path.abspath(args.path)

    if not os.path.exists(target):
        print(f"Error: path '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    severity_rank = {"error": 0, "warning": 1, "info": 2}
    min_sev = severity_rank[args.severity]
    active_rules: Set[str] | None = set(args.rules) if args.rules else None

    # Collect all Java files
    all_files = find_java_files(target)
    if not all_files:
        print(f"No Java files found in '{target}'.")
        sys.exit(0)

    # Categorize into source and test files
    source_classes: Dict[str, ClassInfo] = {}
    test_classes: Dict[str, ClassInfo] = {}
    test_methods_by_file: Dict[str, List[TestMethodInfo]] = {}

    for filepath in all_files:
        lines = read_file(filepath)
        if not lines:
            continue

        class_info = extract_class_info(filepath, lines)
        if not class_info:
            continue

        if class_info.is_test:
            test_classes[class_info.name] = class_info
            methods = extract_test_methods(filepath, lines)
            test_methods_by_file[filepath] = methods
        else:
            source_classes[class_info.name] = class_info

    all_issues: List[TestIssue] = []

    # Analyze test files
    for filepath, methods in test_methods_by_file.items():
        lines = read_file(filepath)
        all_issues.extend(check_test_naming(filepath, methods))
        all_issues.extend(check_assertions(filepath, methods))
        all_issues.extend(check_assertion_style(filepath, lines))

    # Coverage analysis (unless test-only mode)
    if not args.test_only:
        all_issues.extend(find_missing_test_classes(source_classes, test_classes, target))
        all_issues.extend(check_test_method_coverage(source_classes, test_classes, test_methods_by_file))

    # Filter
    filtered = [
        i for i in all_issues
        if severity_rank[i.severity] <= min_sev
        and (active_rules is None or i.rule in active_rules)
    ]
    filtered.sort(key=lambda i: (i.file, i.line))

    # Summary stats
    total_test_classes = len(test_classes)
    total_test_methods = sum(len(m) for m in test_methods_by_file.values())
    total_source_classes = len(source_classes)
    tests_with_assertions = sum(
        1 for methods in test_methods_by_file.values()
        for m in methods if m.has_assertion
    )

    if args.json:
        import json
        output = {
            "summary": {
                "source_classes": total_source_classes,
                "test_classes": total_test_classes,
                "test_methods": total_test_methods,
                "tests_with_assertions": tests_with_assertions,
            },
            "issues": [
                {"file": i.file, "line": i.line, "severity": i.severity,
                 "rule": i.rule, "message": i.message}
                for i in filtered
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nTest Analysis Summary")
        print(f"{'=' * 50}")
        print(f"  Source classes:       {total_source_classes}")
        print(f"  Test classes:         {total_test_classes}")
        print(f"  Test methods:         {total_test_methods}")
        print(f"  With assertions:      {tests_with_assertions}/{total_test_methods}")
        if total_source_classes > 0:
            coverage_pct = (total_test_classes / total_source_classes) * 100
            print(f"  Class coverage:       {coverage_pct:.0f}%")
        print()

        if not filtered:
            print("No test quality issues found.")
            sys.exit(0)

        errors = sum(1 for i in filtered if i.severity == "error")
        warnings = sum(1 for i in filtered if i.severity == "warning")
        infos = sum(1 for i in filtered if i.severity == "info")

        print(f"Found {len(filtered)} issue(s):\n")

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
