#!/usr/bin/env python3
"""
Source Code Security Scanner

Scans source code for common security issues including hardcoded secrets,
dangerous functions, SQL injection patterns, insecure cryptography, and
open redirects.

Usage:
    python security_scan.py /path/to/project
    python security_scan.py /path/to/project --severity high
    python security_scan.py /path/to/project --output report.json --format json
    python security_scan.py /path/to/project --exclude node_modules .git dist
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Finding:
    rule_id: str
    severity: str  # critical, high, medium, low, info
    category: str
    title: str
    description: str
    file_path: str
    line_number: int
    line_content: str
    recommendation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanResult:
    scan_dir: str
    scan_time: str
    files_scanned: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def summary(self) -> dict:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts


# --- Rule Definitions ---

SECRET_PATTERNS = [
    {
        "id": "SEC001",
        "name": "AWS Access Key",
        "pattern": r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}",
        "severity": "critical",
        "description": "AWS Access Key ID found in source code",
    },
    {
        "id": "SEC002",
        "name": "AWS Secret Key",
        "pattern": r"""(?:aws_secret_access_key|aws_secret_key|secret_key)\s*[=:]\s*['"][A-Za-z0-9/+=]{40}['"]""",
        "severity": "critical",
        "description": "AWS Secret Access Key found in source code",
    },
    {
        "id": "SEC003",
        "name": "GitHub Token",
        "pattern": r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}",
        "severity": "critical",
        "description": "GitHub personal access token found in source code",
    },
    {
        "id": "SEC004",
        "name": "Generic API Key",
        "pattern": r"""(?:api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*['"][A-Za-z0-9_\-]{20,}['"]""",
        "severity": "high",
        "description": "Potential API key found in source code",
    },
    {
        "id": "SEC005",
        "name": "Private Key",
        "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "severity": "critical",
        "description": "Private key found in source code",
    },
    {
        "id": "SEC006",
        "name": "Hardcoded Password",
        "pattern": r"""(?:password|passwd|pwd|secret)\s*[=:]\s*['"][^'"]{8,}['"]""",
        "severity": "high",
        "description": "Possible hardcoded password found in source code",
    },
    {
        "id": "SEC007",
        "name": "Database Connection String",
        "pattern": r"""(?:postgres|mysql|mongodb|redis|amqp)(?:ql)?://[^\s'"]+:[^\s'"]+@[^\s'"]+""",
        "severity": "critical",
        "description": "Database connection string with credentials found",
    },
    {
        "id": "SEC008",
        "name": "JWT Token",
        "pattern": r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        "severity": "high",
        "description": "Hardcoded JWT token found in source code",
    },
    {
        "id": "SEC009",
        "name": "Slack Webhook",
        "pattern": r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+",
        "severity": "high",
        "description": "Slack webhook URL found in source code",
    },
    {
        "id": "SEC010",
        "name": "Google API Key",
        "pattern": r"AIza[0-9A-Za-z_-]{35}",
        "severity": "high",
        "description": "Google API key found in source code",
    },
]

DANGEROUS_FUNCTION_PATTERNS = [
    {
        "id": "SEC101",
        "name": "eval() usage",
        "pattern": r"\beval\s*\(",
        "severity": "high",
        "description": "eval() executes arbitrary code and is a common injection vector",
        "languages": ["python", "javascript", "typescript"],
        "recommendation": "Use JSON.parse() for data, ast.literal_eval() for Python literals, or refactor to avoid dynamic code execution",
    },
    {
        "id": "SEC102",
        "name": "exec() usage",
        "pattern": r"\bexec\s*\(",
        "severity": "high",
        "description": "exec() executes arbitrary code strings",
        "languages": ["python"],
        "recommendation": "Avoid exec(). Use a whitelist of allowed operations or a sandboxed interpreter",
    },
    {
        "id": "SEC103",
        "name": "innerHTML assignment",
        "pattern": r"\.innerHTML\s*=",
        "severity": "medium",
        "description": "innerHTML can introduce XSS vulnerabilities if content is not sanitized",
        "languages": ["javascript", "typescript"],
        "recommendation": "Use textContent for plain text or sanitize with DOMPurify before using innerHTML",
    },
    {
        "id": "SEC104",
        "name": "dangerouslySetInnerHTML",
        "pattern": r"dangerouslySetInnerHTML",
        "severity": "medium",
        "description": "React's dangerouslySetInnerHTML bypasses XSS protection",
        "languages": ["javascript", "typescript", "jsx", "tsx"],
        "recommendation": "Sanitize input with DOMPurify before using dangerouslySetInnerHTML",
    },
    {
        "id": "SEC105",
        "name": "Shell command execution",
        "pattern": r"""(?:os\.system|os\.popen|subprocess\.call|subprocess\.Popen|subprocess\.run)\s*\(.*shell\s*=\s*True""",
        "severity": "high",
        "description": "Shell command execution with shell=True can lead to command injection",
        "languages": ["python"],
        "recommendation": "Use subprocess.run() with a list of arguments and shell=False",
    },
    {
        "id": "SEC106",
        "name": "document.write()",
        "pattern": r"document\.write\s*\(",
        "severity": "medium",
        "description": "document.write() can introduce XSS and performance issues",
        "languages": ["javascript", "typescript"],
        "recommendation": "Use DOM manipulation methods (createElement, appendChild) instead",
    },
    {
        "id": "SEC107",
        "name": "Pickle deserialization",
        "pattern": r"pickle\.loads?\s*\(",
        "severity": "high",
        "description": "Pickle deserialization of untrusted data allows arbitrary code execution",
        "languages": ["python"],
        "recommendation": "Use JSON or a safe serialization format for untrusted data",
    },
    {
        "id": "SEC108",
        "name": "YAML unsafe load",
        "pattern": r"yaml\.load\s*\([^)]*\)\s*(?!.*Loader)",
        "severity": "high",
        "description": "yaml.load() without a safe Loader allows arbitrary code execution",
        "languages": ["python"],
        "recommendation": "Use yaml.safe_load() or yaml.load(data, Loader=yaml.SafeLoader)",
    },
]

SQL_INJECTION_PATTERNS = [
    {
        "id": "SEC201",
        "name": "SQL string concatenation",
        "pattern": r"""(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\s+.*['"]\s*\+\s*(?:req\.|request\.|params\.|args\.)""",
        "severity": "high",
        "description": "SQL query constructed with string concatenation of user input",
        "recommendation": "Use parameterized queries or prepared statements",
    },
    {
        "id": "SEC202",
        "name": "SQL f-string/format",
        "pattern": r"""(?:execute|query|raw)\s*\(\s*f['"].*(?:SELECT|INSERT|UPDATE|DELETE)""",
        "severity": "high",
        "description": "SQL query using f-string interpolation",
        "recommendation": "Use parameterized queries: cursor.execute('SELECT ... WHERE id = %s', (user_id,))",
    },
    {
        "id": "SEC203",
        "name": "SQL string format",
        "pattern": r"""(?:execute|query)\s*\(\s*['"].*(?:SELECT|INSERT|UPDATE|DELETE).*['"]\.format\(""",
        "severity": "high",
        "description": "SQL query using .format() string interpolation",
        "recommendation": "Use parameterized queries instead of string formatting",
    },
]

INSECURE_CRYPTO_PATTERNS = [
    {
        "id": "SEC301",
        "name": "MD5 for password hashing",
        "pattern": r"""(?:hashlib\.md5|MD5|md5)\s*\(.*(?:password|passwd|pwd|secret)""",
        "severity": "critical",
        "description": "MD5 is cryptographically broken and unsuitable for password hashing",
        "recommendation": "Use bcrypt, argon2, or scrypt for password hashing",
    },
    {
        "id": "SEC302",
        "name": "SHA1 for password hashing",
        "pattern": r"""(?:hashlib\.sha1|SHA1|sha1)\s*\(.*(?:password|passwd|pwd|secret)""",
        "severity": "critical",
        "description": "SHA1 is too fast and unsuitable for password hashing",
        "recommendation": "Use bcrypt, argon2, or scrypt for password hashing",
    },
    {
        "id": "SEC303",
        "name": "Weak random for security",
        "pattern": r"""(?:Math\.random|random\.random|random\.randint)\s*\(.*(?:token|secret|key|session|nonce|salt)""",
        "severity": "high",
        "description": "Weak PRNG used for security-sensitive value",
        "recommendation": "Use crypto.randomBytes (Node) or secrets.token_hex (Python) for cryptographic randomness",
    },
    {
        "id": "SEC304",
        "name": "DES encryption",
        "pattern": r"(?:DES|TripleDES|3DES)\b",
        "severity": "medium",
        "description": "DES/3DES is deprecated; use AES-256",
        "recommendation": "Migrate to AES-256-GCM or ChaCha20-Poly1305",
    },
]

OPEN_REDIRECT_PATTERNS = [
    {
        "id": "SEC401",
        "name": "Open redirect",
        "pattern": r"""(?:redirect|location\.href|window\.location)\s*[=(]\s*(?:req\.|request\.|params\.|query\.|searchParams)""",
        "severity": "medium",
        "description": "Redirect destination derived from user input without validation",
        "recommendation": "Validate redirect URLs against an allowlist of trusted domains",
    },
]

MISCONFIGURATION_PATTERNS = [
    {
        "id": "SEC501",
        "name": "Debug mode enabled",
        "pattern": r"""(?:DEBUG|debug)\s*[=:]\s*(?:True|true|1|'true')""",
        "severity": "medium",
        "description": "Debug mode appears to be enabled",
        "recommendation": "Ensure DEBUG is False in production configurations",
    },
    {
        "id": "SEC502",
        "name": "CORS wildcard",
        "pattern": r"""(?:Access-Control-Allow-Origin|cors.*origin)\s*[=:]\s*['"]\*['"]""",
        "severity": "medium",
        "description": "CORS configured with wildcard origin",
        "recommendation": "Specify exact allowed origins instead of wildcard",
    },
    {
        "id": "SEC503",
        "name": "TLS verification disabled",
        "pattern": r"""(?:verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['"]0|rejectUnauthorized\s*:\s*false)""",
        "severity": "high",
        "description": "TLS certificate verification is disabled",
        "recommendation": "Enable TLS verification; fix certificate issues instead of bypassing verification",
    },
]


# --- Scanner ---


SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb",
    ".php", ".cs", ".yml", ".yaml", ".json", ".xml", ".env",
    ".cfg", ".conf", ".ini", ".toml", ".tf", ".hcl",
}

SKIP_DIRS = {
    "node_modules", ".git", ".svn", "__pycache__", ".tox", ".mypy_cache",
    "venv", ".venv", "env", ".env", "dist", "build", ".next",
    "coverage", ".pytest_cache", "vendor", ".terraform",
}


def should_scan_file(filepath: str, exclude_dirs: set[str]) -> bool:
    """Determine if a file should be scanned."""
    path = Path(filepath)

    # Check extension
    if path.suffix.lower() not in SCAN_EXTENSIONS:
        return False

    # Check excluded directories
    parts = set(path.parts)
    if parts & (SKIP_DIRS | exclude_dirs):
        return False

    # Skip very large files (likely generated or data)
    try:
        if path.stat().st_size > 1_000_000:  # 1 MB
            return False
    except OSError:
        return False

    return True


def scan_file(filepath: str, all_rules: list[dict]) -> list[Finding]:
    """Scan a single file against all rules."""
    findings = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return findings

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments (basic heuristic)
        if stripped.startswith(("#", "//", "/*", "*", "<!--")):
            # Still scan for secrets in comments (often left there by mistake)
            pass

        for rule in all_rules:
            pattern = rule["pattern"]
            try:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip false positives in test/example files for some rules
                    if _is_false_positive(filepath, line, rule):
                        continue

                    findings.append(Finding(
                        rule_id=rule["id"],
                        severity=rule["severity"],
                        category=_get_category(rule["id"]),
                        title=rule["name"],
                        description=rule["description"],
                        file_path=filepath,
                        line_number=line_num,
                        line_content=stripped[:200],  # Truncate long lines
                        recommendation=rule.get(
                            "recommendation",
                            "Review and remediate this finding"
                        ),
                    ))
            except re.error:
                continue

    return findings


def _get_category(rule_id: str) -> str:
    """Map rule ID prefix to category."""
    prefix = rule_id[:5]
    categories = {
        "SEC00": "Hardcoded Secrets",
        "SEC01": "Hardcoded Secrets",
        "SEC10": "Dangerous Functions",
        "SEC20": "SQL Injection",
        "SEC30": "Insecure Cryptography",
        "SEC40": "Open Redirect",
        "SEC50": "Misconfiguration",
    }
    for p, cat in categories.items():
        if rule_id.startswith(p):
            return cat
    return "Other"


def _is_false_positive(filepath: str, line: str, rule: dict) -> bool:
    """Basic false positive filtering."""
    path_lower = filepath.lower()

    # Test files often contain example patterns
    if rule["id"].startswith("SEC0"):  # Secrets
        # Skip if it looks like a placeholder
        placeholders = {
            "your-api-key", "xxx", "placeholder", "example",
            "changeme", "todo", "fixme", "replace_me",
            "sk_test_", "pk_test_",  # Stripe test keys are okay
        }
        line_lower = line.lower()
        if any(p in line_lower for p in placeholders):
            return True

    # Skip documentation and test files for some rules
    if any(part in path_lower for part in ["/test", "/spec", "/example", "readme", ".md"]):
        if rule["id"] in {"SEC501"}:  # DEBUG in test config is fine
            return True

    return False


def scan_directory(
    directory: str,
    exclude_dirs: Optional[set[str]] = None,
    min_severity: Optional[str] = None,
) -> ScanResult:
    """Scan a directory for security issues."""
    exclude = exclude_dirs or set()
    all_rules = (
        SECRET_PATTERNS
        + DANGEROUS_FUNCTION_PATTERNS
        + SQL_INJECTION_PATTERNS
        + INSECURE_CRYPTO_PATTERNS
        + OPEN_REDIRECT_PATTERNS
        + MISCONFIGURATION_PATTERNS
    )

    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    min_level = severity_order.get(min_severity or "info", 0)

    result = ScanResult(
        scan_dir=os.path.abspath(directory),
        scan_time=datetime.now().isoformat(),
        files_scanned=0,
    )

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in (SKIP_DIRS | exclude)]

        for filename in files:
            filepath = os.path.join(root, filename)
            if not should_scan_file(filepath, exclude):
                continue

            result.files_scanned += 1
            file_findings = scan_file(filepath, all_rules)

            # Filter by severity
            for finding in file_findings:
                if severity_order.get(finding.severity, 0) >= min_level:
                    result.findings.append(finding)

    # Sort by severity (critical first)
    result.findings.sort(
        key=lambda f: severity_order.get(f.severity, 0), reverse=True
    )

    return result


# --- Output ---


def print_findings(result: ScanResult) -> None:
    """Print findings to stdout."""
    severity_colors = {
        "critical": "\033[91m",  # Red
        "high": "\033[93m",      # Yellow
        "medium": "\033[33m",    # Orange
        "low": "\033[36m",       # Cyan
        "info": "\033[37m",      # White
    }
    reset = "\033[0m"

    print(f"\nSecurity Scan Results")
    print(f"{'=' * 60}")
    print(f"Directory: {result.scan_dir}")
    print(f"Files scanned: {result.files_scanned}")
    print(f"Total findings: {len(result.findings)}")
    print()

    summary = result.summary
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = summary[sev]
        if count > 0:
            color = severity_colors.get(sev, "")
            print(f"  {color}{sev.upper()}: {count}{reset}")
    print()

    for finding in result.findings:
        color = severity_colors.get(finding.severity, "")
        print(f"{color}[{finding.severity.upper()}]{reset} {finding.title} ({finding.rule_id})")
        print(f"  File: {finding.file_path}:{finding.line_number}")
        print(f"  Line: {finding.line_content}")
        print(f"  Fix:  {finding.recommendation}")
        print()


def output_json(result: ScanResult, filepath: str) -> None:
    """Output findings as JSON."""
    data = {
        "scan_directory": result.scan_dir,
        "scan_time": result.scan_time,
        "files_scanned": result.files_scanned,
        "summary": result.summary,
        "findings": [f.to_dict() for f in result.findings],
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def output_markdown(result: ScanResult, filepath: str) -> None:
    """Output findings as Markdown."""
    lines = [
        "# Security Scan Report",
        f"\n**Scanned**: {result.scan_dir}",
        f"**Date**: {result.scan_time}",
        f"**Files scanned**: {result.files_scanned}",
        f"**Total findings**: {len(result.findings)}",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "|----------|-------|",
    ]
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = result.summary[sev]
        lines.append(f"| {sev.upper()} | {count} |")

    if result.findings:
        lines.append("\n## Findings\n")
        lines.append("| # | Severity | Rule | File | Line | Title |")
        lines.append("|---|----------|------|------|------|-------|")
        for i, f in enumerate(result.findings, 1):
            filename = os.path.basename(f.file_path)
            lines.append(
                f"| {i} | **{f.severity.upper()}** | {f.rule_id} | "
                f"{filename} | {f.line_number} | {f.title} |"
            )

        lines.append("\n## Details\n")
        for i, f in enumerate(result.findings, 1):
            lines.append(f"### {i}. {f.title} ({f.rule_id})\n")
            lines.append(f"- **Severity**: {f.severity.upper()}")
            lines.append(f"- **Category**: {f.category}")
            lines.append(f"- **File**: `{f.file_path}:{f.line_number}`")
            lines.append(f"- **Description**: {f.description}")
            lines.append(f"- **Recommendation**: {f.recommendation}")
            lines.append(f"\n```\n{f.line_content}\n```\n")

    report = "\n".join(lines)
    with open(filepath, "w") as fout:
        fout.write(report)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan source code for security issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s . --severity high
  %(prog)s . --output report.json --format json
  %(prog)s . --exclude node_modules .git vendor
        """,
    )
    parser.add_argument(
        "directory",
        help="Directory to scan",
    )
    parser.add_argument(
        "--severity", "-s",
        choices=["critical", "high", "medium", "low", "info"],
        default="info",
        help="Minimum severity to report (default: info)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--exclude", "-e",
        nargs="*",
        default=[],
        help="Additional directories to exclude",
    )

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory")
        sys.exit(1)

    exclude = set(args.exclude)
    result = scan_directory(args.directory, exclude, args.severity)

    if args.output:
        if args.format == "json":
            output_json(result, args.output)
        elif args.format == "markdown":
            output_markdown(result, args.output)
        else:
            # Redirect text output to file
            import io
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            print_findings(result)
            text = sys.stdout.getvalue()
            sys.stdout = old_stdout
            with open(args.output, "w") as f:
                f.write(text)
        print(f"Report saved to: {args.output}")
    else:
        print_findings(result)

    # Exit with non-zero if critical/high findings
    critical_or_high = result.summary["critical"] + result.summary["high"]
    if critical_or_high > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
