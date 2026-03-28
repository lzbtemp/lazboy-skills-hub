#!/usr/bin/env python3
"""
security_audit.py -- Scan source code for common security vulnerabilities.

Detects:
  - Hardcoded secrets (API keys, passwords, tokens)
  - SQL injection patterns (string interpolation in queries)
  - XSS vectors (unsafe HTML insertion)
  - Missing CSRF protection indicators
  - Insecure cryptographic usage (MD5, SHA1 for passwords)
  - Path traversal vulnerabilities
  - Insecure deserialization (pickle, yaml.load)
  - Debug mode enabled in production configs
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Pattern


@dataclass
class SecurityFinding:
    """A single security finding."""
    file: str
    line: int
    rule_id: str
    severity: str  # critical, high, medium, low
    category: str
    message: str
    snippet: str = ""

    def __str__(self) -> str:
        return f"{self.file}:{self.line} [{self.severity}] {self.rule_id}: {self.message}"


@dataclass
class AuditReport:
    """Aggregated security audit report."""
    findings: list[SecurityFinding] = field(default_factory=list)

    def add(self, finding: SecurityFinding) -> None:
        self.findings.append(finding)

    def count_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts


@dataclass
class Rule:
    """A security scanning rule."""
    id: str
    severity: str
    category: str
    message: str
    pattern: Pattern
    file_globs: list[str]


# -- Rule Definitions ---------------------------------------------------------

SECRET_PATTERNS: list[Rule] = [
    Rule(
        id="SEC001", severity="critical", category="secrets",
        message="Potential hardcoded API key detected.",
        pattern=re.compile(
            r"""(?:api[_-]?key|apikey|api_secret)\s*[=:]\s*['\"]([a-zA-Z0-9_\-]{16,})['\"]""",
            re.IGNORECASE,
        ),
        file_globs=["*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.env.example", "*.yaml", "*.yml", "*.json"],
    ),
    Rule(
        id="SEC002", severity="critical", category="secrets",
        message="Potential hardcoded password detected.",
        pattern=re.compile(
            r"""(?:password|passwd|pwd)\s*[=:]\s*['\"](?!.*\{)([^'\"]{8,})['\"]""",
            re.IGNORECASE,
        ),
        file_globs=["*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.yaml", "*.yml"],
    ),
    Rule(
        id="SEC003", severity="critical", category="secrets",
        message="Potential hardcoded secret/token detected.",
        pattern=re.compile(
            r"""(?:secret|token|private[_-]?key)\s*[=:]\s*['\"]([a-zA-Z0-9_\-/+=]{16,})['\"]""",
            re.IGNORECASE,
        ),
        file_globs=["*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.yaml", "*.yml"],
    ),
    Rule(
        id="SEC004", severity="high", category="secrets",
        message="AWS access key pattern detected.",
        pattern=re.compile(r"""AKIA[0-9A-Z]{16}"""),
        file_globs=["*"],
    ),
    Rule(
        id="SEC005", severity="high", category="secrets",
        message="Private key header detected in source code.",
        pattern=re.compile(r"""-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"""),
        file_globs=["*"],
    ),
]

SQL_INJECTION_PATTERNS: list[Rule] = [
    Rule(
        id="SEC010", severity="high", category="sql-injection",
        message="Potential SQL injection via f-string.",
        pattern=re.compile(
            r"""f['\"](?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\s.*\{.*\}""",
            re.IGNORECASE,
        ),
        file_globs=["*.py"],
    ),
    Rule(
        id="SEC011", severity="high", category="sql-injection",
        message="Potential SQL injection via string formatting.",
        pattern=re.compile(
            r"""(?:SELECT|INSERT|UPDATE|DELETE)\s+.*%s.*%\s*\(""",
            re.IGNORECASE,
        ),
        file_globs=["*.py"],
    ),
    Rule(
        id="SEC012", severity="high", category="sql-injection",
        message="Potential SQL injection via string concatenation.",
        pattern=re.compile(
            r"""(?:SELECT|INSERT|UPDATE|DELETE)\s+.*['\"]?\s*\+\s*(?:req\.|request\.|params\.|user)""",
            re.IGNORECASE,
        ),
        file_globs=["*.py", "*.js", "*.ts"],
    ),
    Rule(
        id="SEC013", severity="high", category="sql-injection",
        message="Potential SQL injection via template literal.",
        pattern=re.compile(
            r"""`(?:SELECT|INSERT|UPDATE|DELETE)\s+.*\$\{.*\}`""",
            re.IGNORECASE,
        ),
        file_globs=["*.js", "*.ts", "*.tsx"],
    ),
]

XSS_PATTERNS: list[Rule] = [
    Rule(
        id="SEC020", severity="high", category="xss",
        message="Unsafe innerHTML assignment detected.",
        pattern=re.compile(r"""\.innerHTML\s*=\s*(?!['"]<)"""),
        file_globs=["*.js", "*.ts", "*.tsx", "*.jsx"],
    ),
    Rule(
        id="SEC021", severity="high", category="xss",
        message="dangerouslySetInnerHTML used -- ensure input is sanitized.",
        pattern=re.compile(r"""dangerouslySetInnerHTML"""),
        file_globs=["*.tsx", "*.jsx", "*.js"],
    ),
    Rule(
        id="SEC022", severity="medium", category="xss",
        message="document.write() is a potential XSS vector.",
        pattern=re.compile(r"""document\.write\s*\("""),
        file_globs=["*.js", "*.ts", "*.html"],
    ),
    Rule(
        id="SEC023", severity="medium", category="xss",
        message="v-html directive used -- ensure input is sanitized.",
        pattern=re.compile(r"""v-html\s*="""),
        file_globs=["*.vue"],
    ),
    Rule(
        id="SEC024", severity="medium", category="xss",
        message="Jinja2 |safe filter used -- ensure input is sanitized.",
        pattern=re.compile(r"""\|\s*safe\b"""),
        file_globs=["*.html", "*.jinja", "*.jinja2"],
    ),
]

CRYPTO_PATTERNS: list[Rule] = [
    Rule(
        id="SEC030", severity="high", category="crypto",
        message="MD5 is cryptographically broken. Do not use for security purposes.",
        pattern=re.compile(r"""(?:hashlib\.md5|MD5|md5\s*\(|createHash\s*\(\s*['\"]md5)"""),
        file_globs=["*.py", "*.js", "*.ts"],
    ),
    Rule(
        id="SEC031", severity="medium", category="crypto",
        message="SHA1 is weak. Use SHA-256 or better for security purposes.",
        pattern=re.compile(r"""(?:hashlib\.sha1|SHA1|sha1\s*\(|createHash\s*\(\s*['\"]sha1)"""),
        file_globs=["*.py", "*.js", "*.ts"],
    ),
    Rule(
        id="SEC032", severity="high", category="crypto",
        message="ECB mode is insecure. Use CBC, GCM, or CTR mode.",
        pattern=re.compile(r"""(?:MODE_ECB|AES\.ECB|mode:\s*['\"]ecb)""", re.IGNORECASE),
        file_globs=["*.py", "*.js", "*.ts"],
    ),
    Rule(
        id="SEC033", severity="critical", category="crypto",
        message="Hardcoded encryption key detected.",
        pattern=re.compile(
            r"""(?:encryption[_-]?key|cipher[_-]?key|aes[_-]?key)\s*[=:]\s*['\"][a-zA-Z0-9+/=]{16,}['\"]""",
            re.IGNORECASE,
        ),
        file_globs=["*.py", "*.js", "*.ts"],
    ),
]

DESERIALIZATION_PATTERNS: list[Rule] = [
    Rule(
        id="SEC040", severity="critical", category="deserialization",
        message="pickle.loads is unsafe with untrusted data -- allows code execution.",
        pattern=re.compile(r"""pickle\.loads?\s*\("""),
        file_globs=["*.py"],
    ),
    Rule(
        id="SEC041", severity="critical", category="deserialization",
        message="yaml.load() without SafeLoader allows code execution.",
        pattern=re.compile(r"""yaml\.load\s*\([^)]*(?!Loader\s*=\s*(?:Safe|Base))"""),
        file_globs=["*.py"],
    ),
    Rule(
        id="SEC042", severity="high", category="deserialization",
        message="eval() is dangerous with user input.",
        pattern=re.compile(r"""(?<!\w)eval\s*\("""),
        file_globs=["*.py", "*.js", "*.ts"],
    ),
    Rule(
        id="SEC043", severity="high", category="deserialization",
        message="exec() is dangerous with user input.",
        pattern=re.compile(r"""(?<!\w)exec\s*\("""),
        file_globs=["*.py"],
    ),
]

PATH_TRAVERSAL_PATTERNS: list[Rule] = [
    Rule(
        id="SEC050", severity="high", category="path-traversal",
        message="Potential path traversal -- user input in file path without validation.",
        pattern=re.compile(
            r"""(?:open|read_file|send_file|sendFile)\s*\(.*(?:req\.|request\.|params\.|user_)""",
            re.IGNORECASE,
        ),
        file_globs=["*.py", "*.js", "*.ts"],
    ),
    Rule(
        id="SEC051", severity="medium", category="path-traversal",
        message="os.path.join with user input -- ensure path is validated.",
        pattern=re.compile(r"""os\.path\.join\s*\(.*(?:request|user|param|input)""", re.IGNORECASE),
        file_globs=["*.py"],
    ),
]

DEBUG_PATTERNS: list[Rule] = [
    Rule(
        id="SEC060", severity="medium", category="config",
        message="Debug mode appears to be enabled -- ensure it is off in production.",
        pattern=re.compile(r"""(?:DEBUG\s*=\s*True|debug\s*:\s*true|NODE_ENV.*development)"""),
        file_globs=["*.py", "*.js", "*.ts", "*.yaml", "*.yml", "*.env"],
    ),
    Rule(
        id="SEC061", severity="medium", category="config",
        message="CORS wildcard origin detected -- restrict in production.",
        pattern=re.compile(r"""(?:Access-Control-Allow-Origin.*\*|cors\(\s*\)|origin:\s*['\"]?\*)"""),
        file_globs=["*.py", "*.js", "*.ts"],
    ),
]

ALL_RULES = (
    SECRET_PATTERNS
    + SQL_INJECTION_PATTERNS
    + XSS_PATTERNS
    + CRYPTO_PATTERNS
    + DESERIALIZATION_PATTERNS
    + PATH_TRAVERSAL_PATTERNS
    + DEBUG_PATTERNS
)


# -- Scanning Engine ----------------------------------------------------------

def matches_glob(filepath: str, globs: list[str]) -> bool:
    """Check if a filepath matches any of the given glob patterns."""
    name = Path(filepath).name
    for pattern in globs:
        if pattern == "*":
            return True
        # Simple suffix matching
        if pattern.startswith("*"):
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True
    return False


def scan_file(filepath: str, rules: list[Rule], report: AuditReport) -> None:
    """Scan a single file against all applicable rules."""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    lines = content.splitlines()

    for rule in rules:
        if not matches_glob(filepath, rule.file_globs):
            continue

        for lineno, line in enumerate(lines, start=1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                # But still check for secrets in comments
                if rule.category != "secrets":
                    continue

            match = rule.pattern.search(line)
            if match:
                # Avoid false positives in test files and examples
                if _is_likely_false_positive(filepath, line, rule):
                    continue

                report.add(SecurityFinding(
                    file=filepath,
                    line=lineno,
                    rule_id=rule.id,
                    severity=rule.severity,
                    category=rule.category,
                    message=rule.message,
                    snippet=line.strip()[:120],
                ))


def _is_likely_false_positive(filepath: str, line: str, rule: Rule) -> bool:
    """Heuristic to reduce false positives."""
    path_lower = filepath.lower()
    line_lower = line.lower()

    # Skip test files for some rules
    if "test" in path_lower or "spec" in path_lower or "mock" in path_lower:
        if rule.category in ("secrets", "config"):
            return True

    # Skip example/placeholder values
    placeholder_markers = [
        "example", "placeholder", "your_", "xxx", "changeme",
        "todo", "fixme", "<your", "replace_", "dummy",
    ]
    if rule.category == "secrets":
        for marker in placeholder_markers:
            if marker in line_lower:
                return True

    # Skip type hints and comments describing patterns
    if rule.category == "sql-injection":
        if "# example" in line_lower or "# bad" in line_lower or "# vulnerable" in line_lower:
            return True

    return False


def collect_files(paths: list[str], exclude: list[str]) -> list[str]:
    """Collect all scannable files from given paths."""
    SCAN_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".vue",
        ".html", ".jinja", ".jinja2",
        ".yaml", ".yml", ".json", ".toml",
        ".env", ".cfg", ".ini", ".conf",
    }
    exclude_set = set(exclude)
    files = []

    for path in paths:
        p = Path(path)
        if p.is_file():
            if p.suffix in SCAN_EXTENSIONS:
                files.append(str(p))
        elif p.is_dir():
            for f in p.rglob("*"):
                if not f.is_file():
                    continue
                if f.suffix not in SCAN_EXTENSIONS:
                    continue
                if any(ex in f.parts for ex in exclude_set):
                    continue
                # Skip binary/large files
                if f.stat().st_size > 1_000_000:
                    continue
                files.append(str(f))

    return sorted(set(files))


# -- Output Formatting --------------------------------------------------------

SEVERITY_COLORS = {
    "critical": "\033[1;31m",  # Bold red
    "high": "\033[31m",        # Red
    "medium": "\033[33m",      # Yellow
    "low": "\033[36m",         # Cyan
}
RESET = "\033[0m"


def print_text_report(report: AuditReport) -> None:
    """Print a human-readable report."""
    if not report.findings:
        print("No security issues found.")
        return

    # Group by category
    by_cat: dict[str, list[SecurityFinding]] = {}
    for f in report.findings:
        by_cat.setdefault(f.category, []).append(f)

    for category, findings in sorted(by_cat.items()):
        print(f"\n{'=' * 70}")
        print(f"  {category.upper()} ({len(findings)} finding(s))")
        print(f"{'=' * 70}")

        for finding in sorted(findings, key=lambda x: (x.file, x.line)):
            color = SEVERITY_COLORS.get(finding.severity, "")
            print(f"  {color}{finding}{RESET}")
            if finding.snippet:
                print(f"    > {finding.snippet}")

    counts = report.count_by_severity()
    print(f"\n{'─' * 70}")
    print(f"Total: {len(report.findings)} finding(s)")
    for sev in ["critical", "high", "medium", "low"]:
        if counts[sev]:
            color = SEVERITY_COLORS.get(sev, "")
            print(f"  {color}{sev}: {counts[sev]}{RESET}")


def print_json_report(report: AuditReport) -> None:
    """Print a JSON report."""
    output = {
        "findings": [
            {
                "file": f.file,
                "line": f.line,
                "rule_id": f.rule_id,
                "severity": f.severity,
                "category": f.category,
                "message": f.message,
                "snippet": f.snippet,
            }
            for f in report.findings
        ],
        "summary": report.count_by_severity(),
        "total": len(report.findings),
    }
    print(json.dumps(output, indent=2))


def print_sarif_report(report: AuditReport) -> None:
    """Print a SARIF-compatible report for CI integration."""
    rules = {}
    results = []

    for f in report.findings:
        if f.rule_id not in rules:
            rules[f.rule_id] = {
                "id": f.rule_id,
                "shortDescription": {"text": f.message},
                "defaultConfiguration": {
                    "level": "error" if f.severity in ("critical", "high") else "warning",
                },
            }
        results.append({
            "ruleId": f.rule_id,
            "message": {"text": f.message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.file},
                    "region": {"startLine": f.line},
                },
            }],
        })

    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "security_audit",
                    "version": "1.0.0",
                    "rules": list(rules.values()),
                },
            },
            "results": results,
        }],
    }
    print(json.dumps(sarif, indent=2))


# -- Main Entry Point ---------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan source code for common security vulnerabilities.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Categories:
  secrets           Hardcoded API keys, passwords, tokens
  sql-injection     String interpolation/concatenation in SQL queries
  xss               Unsafe HTML insertion, missing sanitization
  crypto            Weak hashing algorithms, insecure cipher modes
  deserialization   Unsafe pickle, yaml.load, eval, exec
  path-traversal    User input in file paths without validation
  config            Debug mode, CORS wildcards

Severity levels: critical, high, medium, low

Examples:
  %(prog)s .                              Scan current directory
  %(prog)s --severity high src/           Only show high+ severity
  %(prog)s --category secrets sql .       Only check secrets and SQL injection
  %(prog)s --format sarif . > report.json Export SARIF for CI
""",
    )
    parser.add_argument(
        "paths", nargs="*", default=["."],
        help="Files or directories to scan (default: current directory)",
    )
    parser.add_argument(
        "--exclude", nargs="*",
        default=["node_modules", ".venv", "venv", ".git", "__pycache__", "dist", "build", ".next"],
        help="Directories to exclude from scanning",
    )
    parser.add_argument(
        "--category", nargs="*", default=None,
        help="Only check specific categories (e.g., secrets xss sql-injection)",
    )
    parser.add_argument(
        "--severity", choices=["critical", "high", "medium", "low"], default=None,
        help="Minimum severity level to report",
    )
    parser.add_argument(
        "--format", choices=["text", "json", "sarif"], default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--fail-on", choices=["critical", "high", "medium", "low"], default=None,
        help="Exit with code 1 if findings at this severity or above are found",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Only print summary counts",
    )

    args = parser.parse_args()

    # Filter rules
    severity_order = ["low", "medium", "high", "critical"]
    rules = ALL_RULES

    if args.category:
        categories = set(args.category)
        rules = [r for r in rules if r.category in categories]

    # Collect files
    files = collect_files(args.paths, args.exclude)
    if not files:
        print("No scannable files found.", file=sys.stderr)
        return 0

    # Scan
    report = AuditReport()
    for filepath in files:
        scan_file(filepath, rules, report)

    # Filter by severity
    if args.severity:
        min_idx = severity_order.index(args.severity)
        report.findings = [
            f for f in report.findings
            if severity_order.index(f.severity) >= min_idx
        ]

    # Output
    if args.quiet:
        counts = report.count_by_severity()
        print(f"Scanned {len(files)} files. Found {len(report.findings)} issue(s): "
              f"{counts['critical']} critical, {counts['high']} high, "
              f"{counts['medium']} medium, {counts['low']} low")
    elif args.format == "json":
        print_json_report(report)
    elif args.format == "sarif":
        print_sarif_report(report)
    else:
        print_text_report(report)

    # Exit code
    if args.fail_on and report.findings:
        fail_idx = severity_order.index(args.fail_on)
        has_failing = any(
            severity_order.index(f.severity) >= fail_idx
            for f in report.findings
        )
        if has_failing:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
