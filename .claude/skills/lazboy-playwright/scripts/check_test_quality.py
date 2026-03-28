#!/usr/bin/env python3
"""Analyze Playwright test files for anti-patterns and quality issues.

Checks for hardcoded waits, missing assertions, flaky selectors,
missing test isolation, and other common Playwright test problems.

Usage:
    python check_test_quality.py /path/to/tests
    python check_test_quality.py . --format json
    python check_test_quality.py /path/to/tests --severity WARNING
"""

import argparse
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
    snippet: str = ""
    fix: str = ""

    def to_dict(self) -> dict:
        result = {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }
        if self.snippet:
            result["snippet"] = self.snippet
        if self.fix:
            result["fix"] = self.fix
        return result


@dataclass
class CheckResult:
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    total_tests: int = 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def summary(self) -> dict[str, int]:
        counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts


def find_test_files(project_dir: Path) -> list[Path]:
    """Find Playwright test files (.spec.ts, .spec.js, .test.ts, .test.js)."""
    patterns = ["**/*.spec.ts", "**/*.spec.js", "**/*.test.ts", "**/*.test.js"]
    files = []
    for pattern in patterns:
        files.extend(project_dir.rglob(pattern.lstrip("**/")))

    exclude_dirs = {"node_modules", ".git", "dist", "build"}
    return sorted(set(
        f for f in files if not any(d in f.parts for d in exclude_dirs)
    ))


def read_file(filepath: Path) -> list[str]:
    """Read file and return lines."""
    try:
        return filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []


def count_tests(lines: list[str]) -> int:
    """Count the number of test() calls in the file."""
    count = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"test\s*\(", stripped) or re.match(r"test\.\w+\s*\(", stripped):
            count += 1
    return count


def check_hardcoded_waits(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Detect hardcoded waitForTimeout / setTimeout / sleep calls."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if "waitForTimeout" in stripped:
            # Extract the timeout value
            match = re.search(r"waitForTimeout\(\s*(\d+)\s*\)", stripped)
            timeout = int(match.group(1)) if match else 0
            result.add(Finding(
                severity=Severity.ERROR if timeout >= 1000 else Severity.WARNING,
                category="hardcoded-wait",
                message=f"Hardcoded wait of {timeout}ms. Use expect() auto-retry or waitForLoadState instead.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
                fix="await expect(locator).toBeVisible(); // or page.waitForLoadState('networkidle')",
            ))

        if re.search(r"setTimeout\s*\(", stripped) and "test" not in filepath.name:
            result.add(Finding(
                severity=Severity.WARNING,
                category="hardcoded-wait",
                message="setTimeout used in test. Use Playwright's built-in waiting mechanisms.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
            ))

        if "page.waitForEvent" not in stripped and re.search(r"\.wait\s*\(\s*\d+\s*\)", stripped):
            result.add(Finding(
                severity=Severity.WARNING,
                category="hardcoded-wait",
                message="Manual wait detected. Prefer Playwright's auto-retry assertions.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
            ))


def check_missing_assertions(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Detect test blocks that have no assertions."""
    in_test = False
    test_start_line = 0
    brace_depth = 0
    has_expect = False
    test_name = ""

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Detect test start
        test_match = re.match(r"test\s*\(\s*['\"](.+?)['\"]", stripped)
        if test_match and not in_test:
            in_test = True
            test_start_line = i
            has_expect = False
            test_name = test_match.group(1)
            brace_depth = 0

        if in_test:
            brace_depth += stripped.count("{") - stripped.count("}")

            if "expect(" in stripped or "expect." in stripped:
                has_expect = True
            if "toBeVisible" in stripped or "toHaveText" in stripped:
                has_expect = True
            if "toContainText" in stripped or "toHaveURL" in stripped:
                has_expect = True
            if "toBeEnabled" in stripped or "toBeDisabled" in stripped:
                has_expect = True
            if "toHaveAttribute" in stripped or "toHaveCount" in stripped:
                has_expect = True

            # Test block ended
            if brace_depth <= 0 and i > test_start_line:
                if not has_expect:
                    result.add(Finding(
                        severity=Severity.ERROR,
                        category="missing-assertion",
                        message=f'Test "{test_name}" has no assertions. Every test should verify expected behavior.',
                        file=str(filepath),
                        line=test_start_line,
                        fix="Add expect() assertions to verify the expected outcome.",
                    ))
                in_test = False


def check_flaky_selectors(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Detect CSS selectors and nth-child that are prone to flakiness."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # CSS class selectors (fragile)
        if re.search(r"locator\s*\(\s*['\"]\.[\w-]+['\"]", stripped):
            # Allow data-testid selectors
            if "data-testid" not in stripped and "getBy" not in stripped:
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="flaky-selector",
                    message="CSS class selector is fragile. Use getByRole, getByLabel, or getByTestId instead.",
                    file=str(filepath),
                    line=i,
                    snippet=stripped[:120],
                    fix="page.getByRole('button', { name: 'Submit' }) or page.getByTestId('my-element')",
                ))

        # XPath selectors
        if re.search(r"locator\s*\(\s*['\"]//", stripped):
            result.add(Finding(
                severity=Severity.WARNING,
                category="flaky-selector",
                message="XPath selector is fragile and hard to maintain. Use Playwright locators instead.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
            ))

        # nth-child / :nth-of-type (positional selectors)
        if re.search(r"nth-child|nth-of-type|:nth\(", stripped):
            result.add(Finding(
                severity=Severity.WARNING,
                category="flaky-selector",
                message="Positional selector (nth-child) is brittle. Use data-testid or role-based selectors.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
            ))

        # Complex CSS selectors with multiple combinators
        css_match = re.search(r"locator\s*\(\s*['\"]([^'\"]+)['\"]", stripped)
        if css_match:
            selector = css_match.group(1)
            combinators = len(re.findall(r"\s+>\s+|\s+~\s+|\s+\+\s+", selector))
            if combinators >= 2 and "getBy" not in stripped:
                result.add(Finding(
                    severity=Severity.INFO,
                    category="flaky-selector",
                    message="Deeply nested CSS selector is fragile. Simplify or use data-testid.",
                    file=str(filepath),
                    line=i,
                    snippet=stripped[:120],
                ))


def check_hardcoded_urls(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Detect hardcoded URLs that should use baseURL."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.search(r"(goto|navigate)\s*\(\s*['\"]https?://", stripped):
            result.add(Finding(
                severity=Severity.WARNING,
                category="hardcoded-url",
                message="Hardcoded URL detected. Use relative paths with baseURL from playwright.config.ts.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
                fix='await page.goto("/products"); // Uses baseURL from config',
            ))

        if re.search(r"localhost:\d+", stripped) and "config" not in filepath.name.lower():
            result.add(Finding(
                severity=Severity.WARNING,
                category="hardcoded-url",
                message="Hardcoded localhost URL. Use baseURL from config or environment variables.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
            ))


def check_hardcoded_credentials(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Detect hardcoded credentials in test files."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Password-like strings
        if re.search(r"(password|passwd|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]", stripped, re.IGNORECASE):
            # Skip if it's referencing an env var
            if "process.env" not in stripped and "env." not in stripped.lower():
                result.add(Finding(
                    severity=Severity.ERROR,
                    category="hardcoded-credentials",
                    message="Hardcoded credential detected. Use environment variables: process.env.TEST_PASSWORD",
                    file=str(filepath),
                    line=i,
                    snippet=stripped[:80] + "...",
                ))


def check_missing_test_isolation(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Check for test isolation issues (shared state, missing cleanup)."""
    content = "\n".join(lines)

    # Check for page-level variables modified across tests (shared state)
    has_let_page = bool(re.search(r"let\s+\w+\s*:", content))
    has_beforeeach = bool(re.search(r"test\.beforeEach|beforeEach", content))

    if has_let_page and not has_beforeeach:
        result.add(Finding(
            severity=Severity.WARNING,
            category="test-isolation",
            message="Mutable test state without beforeEach. Tests may depend on execution order.",
            file=str(filepath),
            line=1,
            fix="Add test.beforeEach to reset state before each test.",
        ))

    # Check for test.describe.serial (tests depend on order)
    for i, line in enumerate(lines, 1):
        if "describe.serial" in line:
            result.add(Finding(
                severity=Severity.INFO,
                category="test-isolation",
                message="Serial test execution detected. Ensure tests truly need ordering.",
                file=str(filepath),
                line=i,
            ))


def check_missing_wait_after_navigation(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Check for navigation without waiting for load state."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if re.search(r"\.goto\s*\(", stripped):
            # Check next 3 lines for waitForLoadState
            has_wait = False
            for j in range(i, min(i + 3, len(lines))):
                if "waitForLoadState" in lines[j] or "waitForURL" in lines[j]:
                    has_wait = True
                    break
                if "expect" in lines[j]:
                    # expect auto-retries, so this is acceptable
                    has_wait = True
                    break
            if not has_wait:
                result.add(Finding(
                    severity=Severity.INFO,
                    category="missing-wait",
                    message="Navigation without waitForLoadState. Add waitForLoadState('networkidle') for dynamic pages.",
                    file=str(filepath),
                    line=i,
                    snippet=stripped[:120],
                    fix='await page.waitForLoadState("networkidle");',
                ))


def check_missing_tags(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Check for tests without tags (makes filtering difficult)."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        test_match = re.match(r"test\s*\(\s*['\"](.+?)['\"]", stripped)
        if test_match:
            # Check if the test has a tag object
            # Look for { tag: [...] } in the same or next line
            context = stripped
            if i < len(lines):
                context += lines[i]
            if "tag:" not in context and "@" not in context:
                result.add(Finding(
                    severity=Severity.INFO,
                    category="missing-tags",
                    message=f'Test "{test_match.group(1)}" has no tags. Add tags for filtering: {{ tag: ["@smoke"] }}',
                    file=str(filepath),
                    line=i,
                ))


def check_import_from_playwright_test(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Check if tests import from @playwright/test instead of local fixtures."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.search(r"from\s+['\"]@playwright/test['\"]", stripped):
            result.add(Finding(
                severity=Severity.INFO,
                category="import-pattern",
                message='Import from "@playwright/test" detected. Import from local fixtures for custom setup.',
                file=str(filepath),
                line=i,
                fix='import { test, expect } from "./fixtures";',
            ))


def check_no_retry_on_flaky(filepath: Path, lines: list[str], result: CheckResult) -> None:
    """Check for test.fixme or test.skip that may indicate unresolved flakiness."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if "test.fixme" in stripped:
            result.add(Finding(
                severity=Severity.WARNING,
                category="skipped-test",
                message="test.fixme found. Investigate and fix rather than leaving tests disabled.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
            ))
        elif "test.skip" in stripped:
            result.add(Finding(
                severity=Severity.INFO,
                category="skipped-test",
                message="test.skip found. Ensure this is intentional and documented.",
                file=str(filepath),
                line=i,
                snippet=stripped[:120],
            ))


def run_checks(project_dir: Path, verbose: bool = False) -> CheckResult:
    """Run all checks on Playwright test files."""
    result = CheckResult()
    files = find_test_files(project_dir)
    result.files_scanned = len(files)

    if verbose:
        print(f"Found {len(files)} test files.", file=sys.stderr)

    for filepath in files:
        lines = read_file(filepath)
        if not lines:
            continue

        result.total_tests += count_tests(lines)

        if verbose:
            print(f"  Checking: {filepath.name}", file=sys.stderr)

        check_hardcoded_waits(filepath, lines, result)
        check_missing_assertions(filepath, lines, result)
        check_flaky_selectors(filepath, lines, result)
        check_hardcoded_urls(filepath, lines, result)
        check_hardcoded_credentials(filepath, lines, result)
        check_missing_test_isolation(filepath, lines, result)
        check_missing_wait_after_navigation(filepath, lines, result)
        check_missing_tags(filepath, lines, result)
        check_import_from_playwright_test(filepath, lines, result)
        check_no_retry_on_flaky(filepath, lines, result)

    return result


def format_text(result: CheckResult, project_dir: Path) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append(f"Playwright Test Quality Check: {project_dir}")
    lines.append("=" * 60)
    lines.append(f"Files scanned: {result.files_scanned}")
    lines.append(f"Tests found: {result.total_tests}")

    summary = result.summary()
    lines.append(f"Findings: {summary['ERROR']} errors, {summary['WARNING']} warnings, {summary['INFO']} info")
    lines.append("-" * 60)

    if not result.findings:
        lines.append("\nNo issues found. Tests look good!")
        return "\n".join(lines)

    categories: dict[str, list[Finding]] = {}
    for f in result.findings:
        categories.setdefault(f.category, []).append(f)

    for category, findings in sorted(categories.items()):
        lines.append(f"\n[{category.upper().replace('-', ' ')}]")
        for f in findings:
            lines.append(f"  {f.severity.value:7s} {f.file}:{f.line}")
            lines.append(f"          {f.message}")
            if f.snippet:
                lines.append(f"          > {f.snippet}")
            if f.fix:
                lines.append(f"          Fix: {f.fix}")

    return "\n".join(lines)


def format_json(result: CheckResult) -> str:
    """Format results as JSON."""
    return json.dumps({
        "files_scanned": result.files_scanned,
        "total_tests": result.total_tests,
        "summary": result.summary(),
        "findings": [f.to_dict() for f in result.findings],
    }, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Playwright test files for anti-patterns: hardcoded waits, missing assertions, flaky selectors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/tests
  %(prog)s . --format json
  %(prog)s /path/to/tests --severity WARNING
  %(prog)s . --verbose
        """,
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to the test directory or project root",
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
