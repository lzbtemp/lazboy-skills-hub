#!/usr/bin/env python3
"""
Accessibility Audit Script

Audits HTML and JSX files for common accessibility issues including:
- Missing alt text on images
- Missing ARIA labels on interactive elements
- Missing form labels
- Non-semantic element usage
- Click handlers without keyboard equivalents
- Missing lang attribute
- Missing skip links
- Empty links and buttons

Usage:
    python audit_accessibility.py <directory_or_file>
    python audit_accessibility.py ./src --format json
    python audit_accessibility.py ./src --severity error
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    file: str
    line: int
    severity: Severity
    rule: str
    message: str
    code_snippet: str = ""

    def to_dict(self):
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class AuditResult:
    issues: list = field(default_factory=list)
    files_scanned: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0

    def add_issue(self, issue: Issue):
        self.issues.append(issue)
        if issue.severity == Severity.ERROR:
            self.total_errors += 1
        elif issue.severity == Severity.WARNING:
            self.total_warnings += 1
        else:
            self.total_info += 1


# ---------------------------------------------------------------------------
# Regex patterns for detecting accessibility issues
# ---------------------------------------------------------------------------

# Images without alt attribute
IMG_NO_ALT = re.compile(
    r"<img\b(?![^>]*\balt\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# Images with empty alt that are NOT decorative (no role="presentation")
IMG_EMPTY_ALT_NOT_DECORATIVE = re.compile(
    r'<img\b[^>]*\balt\s*=\s*""\s*(?![^>]*role\s*=\s*"presentation")[^>]*>',
    re.IGNORECASE | re.DOTALL,
)

# Input without associated label or aria-label/aria-labelledby
INPUT_NO_LABEL = re.compile(
    r"<input\b(?![^>]*\btype\s*=\s*[\"']hidden[\"'])(?![^>]*\baria-label(?:ledby)?\s*=)(?![^>]*\bid\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# Input with id but we check for missing <label for="..."> separately
INPUT_WITH_ID = re.compile(
    r'<input\b(?![^>]*\btype\s*=\s*["\']hidden["\'])[^>]*\bid\s*=\s*["\']([^"\']+)["\'][^>]*>',
    re.IGNORECASE | re.DOTALL,
)

# Label with for attribute
LABEL_FOR = re.compile(
    r'<label\b[^>]*\bfor\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)

# Non-semantic elements used as buttons or links
DIV_SPAN_ONCLICK = re.compile(
    r"<(div|span)\b[^>]*\bon[Cc]lick\s*=",
    re.IGNORECASE | re.DOTALL,
)

# JSX onClick without onKeyDown/onKeyUp/onKeyPress
JSX_ONCLICK_NO_KEYBOARD = re.compile(
    r"<(\w+)\b[^>]*\bonClick\s*=\s*\{[^}]*\}(?![^>]*\bonKey(?:Down|Up|Press)\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# div/span with onClick but missing role and tabIndex (JSX)
JSX_DIV_CLICK_NO_ROLE = re.compile(
    r"<(div|span)\b[^>]*\bonClick\s*=(?![^>]*\brole\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# Anchor without href
ANCHOR_NO_HREF = re.compile(
    r"<a\b(?![^>]*\bhref\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# Empty anchor or button
EMPTY_INTERACTIVE = re.compile(
    r"<(a|button)\b[^>]*>\s*</(a|button)>",
    re.IGNORECASE | re.DOTALL,
)

# Button/link with only an icon (no text, no aria-label)
ICON_ONLY_INTERACTIVE = re.compile(
    r'<(a|button)\b(?![^>]*\baria-label(?:ledby)?\s*=)[^>]*>\s*<(?:i|svg|img|span)\b[^>]*(?:class\s*=\s*["\'][^"\']*icon[^"\']*["\']|aria-hidden)[^>]*/?\s*>\s*</(a|button)>',
    re.IGNORECASE | re.DOTALL,
)

# Missing html lang attribute
HTML_NO_LANG = re.compile(
    r"<html\b(?![^>]*\blang\s*=)[^>]*>",
    re.IGNORECASE,
)

# Autoplaying media
AUTOPLAY_MEDIA = re.compile(
    r"<(video|audio)\b[^>]*\bautoplay\b",
    re.IGNORECASE | re.DOTALL,
)

# Positive tabindex (anti-pattern)
POSITIVE_TABINDEX = re.compile(
    r'tabindex\s*=\s*["\']?([1-9]\d*)',
    re.IGNORECASE,
)

# iframe without title
IFRAME_NO_TITLE = re.compile(
    r"<iframe\b(?![^>]*\btitle\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# Form without accessible name
FORM_NO_LABEL = re.compile(
    r"<form\b(?![^>]*\baria-label(?:ledby)?\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# Table without caption or aria-label
TABLE_NO_CAPTION = re.compile(
    r"<table\b(?![^>]*\baria-label(?:ledby)?\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# Select without label
SELECT_NO_LABEL = re.compile(
    r"<select\b(?![^>]*\baria-label(?:ledby)?\s*=)(?![^>]*\bid\s*=)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

# Heading hierarchy check pattern
HEADING_PATTERN = re.compile(
    r"<h([1-6])\b",
    re.IGNORECASE,
)


def find_files(path: str, extensions: tuple = (".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte")) -> list:
    """Find all HTML/JSX files in the given path."""
    target = Path(path)
    if target.is_file():
        if target.suffix.lower() in extensions:
            return [target]
        return []

    files = []
    for ext in extensions:
        files.extend(target.rglob(f"*{ext}"))
    return sorted(files)


def get_line_number(content: str, match_start: int) -> int:
    """Get the line number for a match position."""
    return content[:match_start].count("\n") + 1


def get_code_snippet(content: str, match_start: int, match_end: int, context: int = 0) -> str:
    """Extract the code snippet around a match."""
    snippet = content[match_start:match_end]
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."
    return snippet.strip()


def check_heading_hierarchy(content: str, filepath: str, result: AuditResult):
    """Check that headings follow a logical hierarchy."""
    headings = [(m.group(1), m.start()) for m in HEADING_PATTERN.finditer(content)]
    prev_level = 0
    for level_str, pos in headings:
        level = int(level_str)
        if prev_level > 0 and level > prev_level + 1:
            result.add_issue(Issue(
                file=str(filepath),
                line=get_line_number(content, pos),
                severity=Severity.WARNING,
                rule="heading-hierarchy",
                message=f"Heading level skipped: h{prev_level} -> h{level}. Headings should not skip levels.",
                code_snippet=get_code_snippet(content, pos, pos + 20),
            ))
        prev_level = level


def check_label_associations(content: str, filepath: str, result: AuditResult):
    """Check that form inputs with IDs have associated labels."""
    input_ids = {m.group(1) for m in INPUT_WITH_ID.finditer(content)}
    label_fors = {m.group(1) for m in LABEL_FOR.finditer(content)}
    orphan_inputs = input_ids - label_fors

    for m in INPUT_WITH_ID.finditer(content):
        input_id = m.group(1)
        if input_id in orphan_inputs:
            # Check if input has aria-label or aria-labelledby
            snippet = m.group(0)
            if not re.search(r"aria-label(?:ledby)?\s*=", snippet, re.IGNORECASE):
                result.add_issue(Issue(
                    file=str(filepath),
                    line=get_line_number(content, m.start()),
                    severity=Severity.ERROR,
                    rule="input-missing-label",
                    message=f'Input with id="{input_id}" has no associated <label for="{input_id}"> or aria-label.',
                    code_snippet=get_code_snippet(content, m.start(), m.end()),
                ))


def check_skip_link(content: str, filepath: str, result: AuditResult):
    """Check for the presence of a skip navigation link."""
    if "<html" in content.lower() or "<!doctype" in content.lower():
        skip_pattern = re.compile(
            r'<a\b[^>]*\bhref\s*=\s*["\']#(main|content|main-content|maincontent)["\']',
            re.IGNORECASE,
        )
        if not skip_pattern.search(content):
            result.add_issue(Issue(
                file=str(filepath),
                line=1,
                severity=Severity.WARNING,
                rule="missing-skip-link",
                message="No skip navigation link found. Add a skip link targeting the main content area.",
            ))


def check_table_headers(content: str, filepath: str, result: AuditResult):
    """Check that tables have th elements."""
    table_pattern = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
    for m in table_pattern.finditer(content):
        table_content = m.group(0)
        if "<th" not in table_content.lower():
            result.add_issue(Issue(
                file=str(filepath),
                line=get_line_number(content, m.start()),
                severity=Severity.WARNING,
                rule="table-missing-headers",
                message="Table does not contain <th> header elements.",
                code_snippet=get_code_snippet(content, m.start(), min(m.start() + 80, m.end())),
            ))


def audit_file(filepath: Path, result: AuditResult):
    """Run all accessibility checks on a single file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return

    checks = [
        (IMG_NO_ALT, Severity.ERROR, "img-missing-alt",
         "Image is missing alt attribute. Add alt text or alt=\"\" for decorative images."),
        (INPUT_NO_LABEL, Severity.ERROR, "input-missing-label",
         "Input element has no id, aria-label, or aria-labelledby."),
        (DIV_SPAN_ONCLICK, Severity.ERROR, "non-semantic-interactive",
         "Non-semantic element (<div>/<span>) has onClick handler. Use <button> or <a> instead, or add role and keyboard handlers."),
        (JSX_DIV_CLICK_NO_ROLE, Severity.ERROR, "click-missing-role",
         "Element with onClick is missing a role attribute. Add role=\"button\" and tabIndex={0}."),
        (JSX_ONCLICK_NO_KEYBOARD, Severity.WARNING, "click-missing-keyboard",
         "Element has onClick but no onKeyDown/onKeyUp/onKeyPress handler. Keyboard users cannot activate this element."),
        (ANCHOR_NO_HREF, Severity.WARNING, "anchor-missing-href",
         "Anchor element is missing href attribute. Use <button> for actions or add a valid href."),
        (EMPTY_INTERACTIVE, Severity.ERROR, "empty-interactive",
         "Interactive element (link/button) has no text content. Add visible text or aria-label."),
        (ICON_ONLY_INTERACTIVE, Severity.ERROR, "icon-only-no-label",
         "Interactive element contains only an icon with no accessible name. Add aria-label."),
        (HTML_NO_LANG, Severity.ERROR, "html-missing-lang",
         "HTML element is missing lang attribute. Add lang=\"en\" (or appropriate language)."),
        (AUTOPLAY_MEDIA, Severity.WARNING, "autoplay-media",
         "Media element has autoplay attribute. Provide controls to pause/stop."),
        (POSITIVE_TABINDEX, Severity.WARNING, "positive-tabindex",
         "Positive tabindex value found. Use tabindex=\"0\" or tabindex=\"-1\" instead."),
        (IFRAME_NO_TITLE, Severity.ERROR, "iframe-missing-title",
         "Iframe is missing title attribute. Add a descriptive title."),
        (SELECT_NO_LABEL, Severity.ERROR, "select-missing-label",
         "Select element has no id, aria-label, or aria-labelledby."),
    ]

    for pattern, severity, rule, message in checks:
        for match in pattern.finditer(content):
            result.add_issue(Issue(
                file=str(filepath),
                line=get_line_number(content, match.start()),
                severity=severity,
                rule=rule,
                message=message,
                code_snippet=get_code_snippet(content, match.start(), match.end()),
            ))

    # Additional structural checks
    check_heading_hierarchy(content, filepath, result)
    check_label_associations(content, filepath, result)
    check_skip_link(content, filepath, result)
    check_table_headers(content, filepath, result)


def format_text(result: AuditResult) -> str:
    """Format the audit result as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("ACCESSIBILITY AUDIT REPORT")
    lines.append("=" * 70)
    lines.append(f"Files scanned: {result.files_scanned}")
    lines.append(f"Issues found:  {len(result.issues)}")
    lines.append(f"  Errors:   {result.total_errors}")
    lines.append(f"  Warnings: {result.total_warnings}")
    lines.append(f"  Info:     {result.total_info}")
    lines.append("=" * 70)

    if not result.issues:
        lines.append("\nNo accessibility issues found.")
        return "\n".join(lines)

    # Group by file
    by_file: dict[str, list[Issue]] = {}
    for issue in result.issues:
        by_file.setdefault(issue.file, []).append(issue)

    for filepath, issues in sorted(by_file.items()):
        lines.append(f"\n{filepath}")
        lines.append("-" * len(filepath))
        for issue in sorted(issues, key=lambda i: i.line):
            severity_marker = {
                Severity.ERROR: "ERROR",
                Severity.WARNING: "WARN ",
                Severity.INFO: "INFO ",
            }[issue.severity]
            lines.append(f"  Line {issue.line:>4} [{severity_marker}] {issue.rule}")
            lines.append(f"           {issue.message}")
            if issue.code_snippet:
                lines.append(f"           > {issue.code_snippet}")

    lines.append("\n" + "=" * 70)
    if result.total_errors > 0:
        lines.append(f"FAIL: {result.total_errors} error(s) must be fixed for WCAG AA compliance.")
    else:
        lines.append("PASS: No errors found (warnings should still be reviewed).")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_json(result: AuditResult) -> str:
    """Format the audit result as JSON."""
    output = {
        "summary": {
            "files_scanned": result.files_scanned,
            "total_issues": len(result.issues),
            "errors": result.total_errors,
            "warnings": result.total_warnings,
            "info": result.total_info,
            "passed": result.total_errors == 0,
        },
        "issues": [issue.to_dict() for issue in result.issues],
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Audit HTML/JSX files for common accessibility issues.",
    )
    parser.add_argument(
        "path",
        help="Directory or file path to audit.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--severity",
        choices=["error", "warning", "info"],
        default=None,
        help="Filter issues by minimum severity level.",
    )
    parser.add_argument(
        "--extensions",
        default=".html,.htm,.jsx,.tsx,.vue,.svelte",
        help="Comma-separated file extensions to scan (default: .html,.htm,.jsx,.tsx,.vue,.svelte).",
    )

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(2)

    extensions = tuple(ext.strip() if ext.startswith(".") else f".{ext.strip()}" for ext in args.extensions.split(","))
    files = find_files(args.path, extensions)

    if not files:
        print(f"No files found with extensions {extensions} in: {args.path}", file=sys.stderr)
        sys.exit(1)

    result = AuditResult()
    result.files_scanned = len(files)

    for filepath in files:
        audit_file(filepath, result)

    # Filter by severity if requested
    if args.severity:
        severity_order = {"error": 0, "warning": 1, "info": 2}
        min_level = severity_order[args.severity]
        result.issues = [
            i for i in result.issues
            if severity_order[i.severity.value] <= min_level
        ]

    if args.format == "json":
        print(format_json(result))
    else:
        print(format_text(result))

    # Exit with non-zero status if errors found
    sys.exit(1 if result.total_errors > 0 else 0)


if __name__ == "__main__":
    main()
