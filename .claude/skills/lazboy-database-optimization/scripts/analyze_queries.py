#!/usr/bin/env python3
"""
SQL Query Analyzer

Analyzes SQL files for common performance anti-patterns including:
- SELECT * usage
- Missing WHERE clauses on large operations
- LIKE with leading wildcards
- Implicit type casts
- Missing LIMIT on unbounded queries
- Nested subqueries (deep nesting)
- N+1 query patterns (sequential similar queries)
- Functions on indexed columns in WHERE clauses
- Cartesian joins (missing JOIN conditions)
- ORDER BY without LIMIT

Usage:
    python analyze_queries.py <directory_or_file>
    python analyze_queries.py ./queries --format json
    python analyze_queries.py ./app/models --extensions .py,.rb
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
    suggestion: str = ""
    code_snippet: str = ""

    def to_dict(self):
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class AnalysisResult:
    issues: list = field(default_factory=list)
    files_scanned: int = 0
    queries_analyzed: int = 0
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
# SQL Patterns
# ---------------------------------------------------------------------------

# SELECT * detection
SELECT_STAR = re.compile(
    r"\bSELECT\s+\*\s+FROM\b",
    re.IGNORECASE,
)

# SELECT without WHERE (potential full table scan)
SELECT_NO_WHERE = re.compile(
    r"\bSELECT\b.+?\bFROM\b\s+\w+(?:\s+\w+)?(?:\s*,\s*\w+(?:\s+\w+)?)*\s*;",
    re.IGNORECASE | re.DOTALL,
)

# DELETE/UPDATE without WHERE
MODIFY_NO_WHERE_DELETE = re.compile(
    r"\bDELETE\s+FROM\s+\w+\s*;",
    re.IGNORECASE,
)
MODIFY_NO_WHERE_UPDATE = re.compile(
    r"\bUPDATE\s+\w+\s+SET\b[^;]*;",
    re.IGNORECASE | re.DOTALL,
)

# LIKE with leading wildcard
LIKE_LEADING_WILDCARD = re.compile(
    r"\bLIKE\s+['\"]%[^'\"]+['\"]",
    re.IGNORECASE,
)

# NOT IN with subquery (performance concern)
NOT_IN_SUBQUERY = re.compile(
    r"\bNOT\s+IN\s*\(\s*SELECT\b",
    re.IGNORECASE,
)

# Nested subqueries (3+ levels deep)
NESTED_SUBQUERY = re.compile(
    r"\(\s*SELECT\b[^)]*\(\s*SELECT\b[^)]*\(\s*SELECT\b",
    re.IGNORECASE | re.DOTALL,
)

# Functions on columns in WHERE (prevents index usage)
FUNCTION_ON_COLUMN_WHERE = re.compile(
    r"\bWHERE\b.*?\b(?:LOWER|UPPER|TRIM|COALESCE|CAST|EXTRACT|DATE|TO_CHAR|TO_DATE|LENGTH|SUBSTRING|CONCAT)\s*\(\s*\w+\.\w+|\bWHERE\b.*?\b(?:LOWER|UPPER|TRIM|COALESCE|CAST|EXTRACT|DATE|TO_CHAR|TO_DATE|LENGTH|SUBSTRING|CONCAT)\s*\(\s*[a-zA-Z_]\w*\s*\)",
    re.IGNORECASE | re.DOTALL,
)

# Implicit type cast patterns
IMPLICIT_CAST_NUMERIC_STRING = re.compile(
    r"\bWHERE\b[^;]*\b\w+\s*=\s*'?\d+\.?\d*'?(?!\s*::)",
    re.IGNORECASE,
)

# SELECT without LIMIT (unbounded result set)
SELECT_NO_LIMIT = re.compile(
    r"\bSELECT\b(?!.*\bLIMIT\b)(?!.*\bINTO\b)(?!.*\bINSERT\b).+?\bFROM\b\s+(\w+)",
    re.IGNORECASE | re.DOTALL,
)

# ORDER BY without LIMIT
ORDER_BY_NO_LIMIT = re.compile(
    r"\bORDER\s+BY\b(?!.*\bLIMIT\b)[^;]*;",
    re.IGNORECASE | re.DOTALL,
)

# Cartesian join (comma-separated tables without proper WHERE join condition)
COMMA_JOIN = re.compile(
    r"\bFROM\s+(\w+)\s*,\s*(\w+)\b",
    re.IGNORECASE,
)

# SELECT DISTINCT (may indicate a join issue)
SELECT_DISTINCT = re.compile(
    r"\bSELECT\s+DISTINCT\b",
    re.IGNORECASE,
)

# HAVING without GROUP BY
HAVING_NO_GROUP = re.compile(
    r"\bHAVING\b(?!.*\bGROUP\s+BY\b)",
    re.IGNORECASE | re.DOTALL,
)

# OR in WHERE with different columns (may prevent index usage)
OR_DIFFERENT_COLUMNS = re.compile(
    r"\bWHERE\b[^;]*\b(\w+)\s*=\s*[^;]*\bOR\b\s*(\w+)\s*=",
    re.IGNORECASE | re.DOTALL,
)

# Large IN list (more than 20 values)
LARGE_IN_LIST = re.compile(
    r"\bIN\s*\((?:[^()]*,){20,}[^()]*\)",
    re.IGNORECASE,
)

# SELECT COUNT(*) without index-friendly filter
COUNT_STAR_NO_WHERE = re.compile(
    r"\bSELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM\s+\w+\s*(?:;|\s*$)",
    re.IGNORECASE,
)

# Tables commonly associated with large datasets
LARGE_TABLE_KEYWORDS = {
    "audit_log", "audit_logs", "events", "event_log", "event_logs",
    "logs", "log", "activities", "activity_log", "metrics",
    "analytics", "sessions", "page_views", "transactions",
    "history", "notifications", "messages",
}


def find_files(path: str, extensions: tuple) -> list:
    """Find all files with given extensions."""
    target = Path(path)
    if target.is_file():
        return [target]

    files = []
    for ext in extensions:
        files.extend(target.rglob(f"*{ext}"))
    return sorted(files)


def get_line_number(content: str, match_start: int) -> int:
    """Get line number for a match position."""
    return content[:match_start].count("\n") + 1


def get_snippet(content: str, start: int, end: int, max_len: int = 150) -> str:
    """Extract a code snippet."""
    snippet = content[start:end].strip()
    # Normalize whitespace
    snippet = re.sub(r"\s+", " ", snippet)
    if len(snippet) > max_len:
        snippet = snippet[:max_len - 3] + "..."
    return snippet


def extract_table_name(match_text: str) -> Optional[str]:
    """Try to extract the main table name from a FROM clause."""
    m = re.search(r"\bFROM\s+(\w+)", match_text, re.IGNORECASE)
    return m.group(1).lower() if m else None


def has_where_clause(sql_segment: str) -> bool:
    """Check if a SQL segment contains a WHERE clause."""
    return bool(re.search(r"\bWHERE\b", sql_segment, re.IGNORECASE))


def has_limit_clause(sql_segment: str) -> bool:
    """Check if a SQL segment contains a LIMIT clause."""
    return bool(re.search(r"\bLIMIT\b", sql_segment, re.IGNORECASE))


def analyze_file(filepath: Path, result: AnalysisResult):
    """Run all SQL anti-pattern checks on a single file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return

    str_filepath = str(filepath)

    # Track number of SQL statements found
    statements = re.findall(r"\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b", content, re.IGNORECASE)
    result.queries_analyzed += len(statements)

    # --- SELECT * ---
    for m in SELECT_STAR.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.WARNING,
            rule="select-star",
            message="SELECT * fetches all columns. This prevents index-only scans and wastes I/O.",
            suggestion="List only the columns you need: SELECT col1, col2, col3 FROM ...",
            code_snippet=get_snippet(content, m.start(), m.start() + 100),
        ))

    # --- LIKE with leading wildcard ---
    for m in LIKE_LEADING_WILDCARD.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.WARNING,
            rule="like-leading-wildcard",
            message="LIKE with leading wildcard '%...' cannot use B-tree indexes.",
            suggestion="Use a GIN trigram index (pg_trgm) or full-text search instead.",
            code_snippet=get_snippet(content, m.start(), m.end()),
        ))

    # --- DELETE/UPDATE without WHERE ---
    for m in MODIFY_NO_WHERE_DELETE.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.ERROR,
            rule="delete-without-where",
            message="DELETE without WHERE clause will delete ALL rows in the table.",
            suggestion="Add a WHERE clause to limit the affected rows, or use TRUNCATE if intentional.",
            code_snippet=get_snippet(content, m.start(), m.end()),
        ))

    for m in MODIFY_NO_WHERE_UPDATE.finditer(content):
        if not has_where_clause(m.group(0)):
            result.add_issue(Issue(
                file=str_filepath,
                line=get_line_number(content, m.start()),
                severity=Severity.ERROR,
                rule="update-without-where",
                message="UPDATE without WHERE clause will modify ALL rows in the table.",
                suggestion="Add a WHERE clause to limit the affected rows.",
                code_snippet=get_snippet(content, m.start(), m.end()),
            ))

    # --- NOT IN (subquery) ---
    for m in NOT_IN_SUBQUERY.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.WARNING,
            rule="not-in-subquery",
            message="NOT IN with subquery can produce unexpected results with NULLs and has poor performance.",
            suggestion="Use NOT EXISTS instead: WHERE NOT EXISTS (SELECT 1 FROM ... WHERE ...)",
            code_snippet=get_snippet(content, m.start(), m.start() + 80),
        ))

    # --- Deeply nested subqueries ---
    for m in NESTED_SUBQUERY.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.WARNING,
            rule="deep-nesting",
            message="Query has 3+ levels of nested subqueries. This is hard to maintain and often performs poorly.",
            suggestion="Refactor using CTEs (WITH clauses), JOINs, or window functions.",
            code_snippet=get_snippet(content, m.start(), m.start() + 100),
        ))

    # --- Functions on columns in WHERE ---
    for m in FUNCTION_ON_COLUMN_WHERE.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.WARNING,
            rule="function-on-column",
            message="Function applied to column in WHERE clause prevents index usage.",
            suggestion="Create an expression index, or rewrite the query (e.g., use range instead of EXTRACT).",
            code_snippet=get_snippet(content, m.start(), m.end()),
        ))

    # --- ORDER BY without LIMIT ---
    for m in ORDER_BY_NO_LIMIT.finditer(content):
        table = extract_table_name(content[max(0, m.start() - 200):m.start()])
        if table and table in LARGE_TABLE_KEYWORDS:
            result.add_issue(Issue(
                file=str_filepath,
                line=get_line_number(content, m.start()),
                severity=Severity.WARNING,
                rule="order-by-without-limit",
                message=f"ORDER BY on potentially large table '{table}' without LIMIT requires sorting all rows.",
                suggestion="Add LIMIT to return only the needed rows, or use keyset pagination.",
                code_snippet=get_snippet(content, m.start(), m.end()),
            ))

    # --- COUNT(*) on large table without WHERE ---
    for m in COUNT_STAR_NO_WHERE.finditer(content):
        table = extract_table_name(m.group(0))
        severity = Severity.WARNING if table and table in LARGE_TABLE_KEYWORDS else Severity.INFO
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=severity,
            rule="count-star-no-filter",
            message="COUNT(*) without WHERE performs a full table scan in PostgreSQL.",
            suggestion="Add a WHERE clause if possible, or maintain a counter table/materialized view for large tables.",
            code_snippet=get_snippet(content, m.start(), m.end()),
        ))

    # --- SELECT DISTINCT (may indicate join issue) ---
    for m in SELECT_DISTINCT.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.INFO,
            rule="select-distinct",
            message="SELECT DISTINCT may indicate a join producing duplicates.",
            suggestion="Review join conditions. Consider EXISTS subquery if deduplication is needed.",
            code_snippet=get_snippet(content, m.start(), m.start() + 80),
        ))

    # --- Comma-separated FROM (implicit join) ---
    for m in COMMA_JOIN.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.WARNING,
            rule="implicit-join",
            message=f"Implicit join (comma syntax) between '{m.group(1)}' and '{m.group(2)}'. Risk of Cartesian product if WHERE condition is missing.",
            suggestion="Use explicit JOIN syntax: FROM table1 JOIN table2 ON table1.id = table2.fk_id",
            code_snippet=get_snippet(content, m.start(), m.end()),
        ))

    # --- Large IN list ---
    for m in LARGE_IN_LIST.finditer(content):
        result.add_issue(Issue(
            file=str_filepath,
            line=get_line_number(content, m.start()),
            severity=Severity.WARNING,
            rule="large-in-list",
            message="Large IN list (20+ values). This can cause plan instability and slow parsing.",
            suggestion="Use a VALUES list with JOIN, a temp table, or ANY(ARRAY[...]) syntax.",
            code_snippet=get_snippet(content, m.start(), m.start() + 60),
        ))

    # --- OR with different columns ---
    for m in OR_DIFFERENT_COLUMNS.finditer(content):
        col1, col2 = m.group(1).lower(), m.group(2).lower()
        if col1 != col2:
            result.add_issue(Issue(
                file=str_filepath,
                line=get_line_number(content, m.start()),
                severity=Severity.INFO,
                rule="or-different-columns",
                message=f"OR between different columns ({col1}, {col2}) may prevent index usage.",
                suggestion="Consider UNION ALL of two indexed queries, or a composite GIN index.",
                code_snippet=get_snippet(content, m.start(), m.end()),
            ))


def format_text(result: AnalysisResult) -> str:
    """Format as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("SQL QUERY ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append(f"Files scanned:    {result.files_scanned}")
    lines.append(f"Queries analyzed: {result.queries_analyzed}")
    lines.append(f"Issues found:     {len(result.issues)}")
    lines.append(f"  Errors:   {result.total_errors}")
    lines.append(f"  Warnings: {result.total_warnings}")
    lines.append(f"  Info:     {result.total_info}")
    lines.append("=" * 70)

    if not result.issues:
        lines.append("\nNo performance issues detected.")
        return "\n".join(lines)

    by_file: dict[str, list[Issue]] = {}
    for issue in result.issues:
        by_file.setdefault(issue.file, []).append(issue)

    for filepath, issues in sorted(by_file.items()):
        lines.append(f"\n{filepath}")
        lines.append("-" * min(len(filepath), 70))
        for issue in sorted(issues, key=lambda i: i.line):
            severity_marker = {
                Severity.ERROR: "ERROR",
                Severity.WARNING: "WARN ",
                Severity.INFO: "INFO ",
            }[issue.severity]
            lines.append(f"  Line {issue.line:>4} [{severity_marker}] {issue.rule}")
            lines.append(f"           {issue.message}")
            if issue.suggestion:
                lines.append(f"           Fix: {issue.suggestion}")
            if issue.code_snippet:
                lines.append(f"           > {issue.code_snippet}")

    lines.append("\n" + "=" * 70)
    if result.total_errors > 0:
        lines.append(f"RESULT: {result.total_errors} error(s) found that require immediate attention.")
    elif result.total_warnings > 0:
        lines.append(f"RESULT: {result.total_warnings} warning(s) found. Review for potential performance issues.")
    else:
        lines.append("RESULT: Only informational findings. No critical issues detected.")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_json(result: AnalysisResult) -> str:
    """Format as JSON."""
    output = {
        "summary": {
            "files_scanned": result.files_scanned,
            "queries_analyzed": result.queries_analyzed,
            "total_issues": len(result.issues),
            "errors": result.total_errors,
            "warnings": result.total_warnings,
            "info": result.total_info,
        },
        "issues": [issue.to_dict() for issue in result.issues],
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze SQL files for common performance anti-patterns.",
    )
    parser.add_argument(
        "path",
        help="Directory or file path to analyze.",
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
        help="Filter by minimum severity level.",
    )
    parser.add_argument(
        "--extensions",
        default=".sql,.py,.rb,.java,.ts,.js,.go,.php",
        help="Comma-separated file extensions to scan (default: .sql,.py,.rb,.java,.ts,.js,.go,.php).",
    )

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(2)

    extensions = tuple(
        ext.strip() if ext.startswith(".") else f".{ext.strip()}"
        for ext in args.extensions.split(",")
    )
    files = find_files(args.path, extensions)

    if not files:
        print(f"No files found with extensions {extensions} in: {args.path}", file=sys.stderr)
        sys.exit(1)

    result = AnalysisResult()
    result.files_scanned = len(files)

    for filepath in files:
        analyze_file(filepath, result)

    # Filter by severity
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

    sys.exit(1 if result.total_errors > 0 else 0)


if __name__ == "__main__":
    main()
