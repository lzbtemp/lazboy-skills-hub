#!/usr/bin/env python3
"""
Secret Detection Script

Detects hardcoded secrets, credentials, and sensitive tokens in source files
using regex pattern matching and entropy analysis.

Usage:
    python detect_secrets.py /path/to/project
    python detect_secrets.py /path/to/project --entropy
    python detect_secrets.py /path/to/project --output secrets.json
    python detect_secrets.py /path/to/project --baseline .secrets-baseline.json
"""

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SecretFinding:
    rule_id: str
    name: str
    severity: str
    file_path: str
    line_number: int
    line_content: str
    matched_text: str  # Redacted version of the match
    confidence: str    # high, medium, low


# --- Secret Patterns ---

SECRET_RULES = [
    # AWS
    {
        "id": "SECRET-001",
        "name": "AWS Access Key ID",
        "pattern": r"(?:^|[^A-Za-z0-9])(?P<secret>(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16})(?:[^A-Za-z0-9]|$)",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-002",
        "name": "AWS Secret Access Key",
        "pattern": r"""(?:aws_secret_access_key|aws_secret_key|secret_key|AWS_SECRET)\s*[=:]\s*['"]?(?P<secret>[A-Za-z0-9/+=]{40})['"]?""",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-003",
        "name": "AWS Session Token",
        "pattern": r"""(?:aws_session_token|AWS_SESSION_TOKEN)\s*[=:]\s*['"]?(?P<secret>[A-Za-z0-9/+=]{100,})['"]?""",
        "severity": "critical",
        "confidence": "high",
    },
    # GitHub
    {
        "id": "SECRET-010",
        "name": "GitHub Personal Access Token",
        "pattern": r"(?:^|[^A-Za-z0-9_])(?P<secret>ghp_[A-Za-z0-9_]{36,})(?:[^A-Za-z0-9_]|$)",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-011",
        "name": "GitHub OAuth Access Token",
        "pattern": r"(?:^|[^A-Za-z0-9_])(?P<secret>gho_[A-Za-z0-9_]{36,})(?:[^A-Za-z0-9_]|$)",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-012",
        "name": "GitHub App Token",
        "pattern": r"(?:^|[^A-Za-z0-9_])(?P<secret>(?:ghu|ghs|ghr)_[A-Za-z0-9_]{36,})(?:[^A-Za-z0-9_]|$)",
        "severity": "critical",
        "confidence": "high",
    },
    # Google
    {
        "id": "SECRET-020",
        "name": "Google API Key",
        "pattern": r"(?:^|[^A-Za-z0-9_-])(?P<secret>AIza[0-9A-Za-z_-]{35})(?:[^A-Za-z0-9_-]|$)",
        "severity": "high",
        "confidence": "high",
    },
    {
        "id": "SECRET-021",
        "name": "Google OAuth Client Secret",
        "pattern": r"""(?:client_secret)\s*[=:]\s*['"](?P<secret>GOCSPX-[A-Za-z0-9_-]{28})['"]""",
        "severity": "critical",
        "confidence": "high",
    },
    # Stripe
    {
        "id": "SECRET-030",
        "name": "Stripe Live Secret Key",
        "pattern": r"(?:^|[^A-Za-z0-9_])(?P<secret>sk_live_[A-Za-z0-9]{24,})(?:[^A-Za-z0-9_]|$)",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-031",
        "name": "Stripe Live Publishable Key",
        "pattern": r"(?:^|[^A-Za-z0-9_])(?P<secret>pk_live_[A-Za-z0-9]{24,})(?:[^A-Za-z0-9_]|$)",
        "severity": "medium",
        "confidence": "high",
    },
    # Slack
    {
        "id": "SECRET-040",
        "name": "Slack Bot Token",
        "pattern": r"(?P<secret>xoxb-[0-9]{10,}-[0-9]{10,}-[A-Za-z0-9]{24,})",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-041",
        "name": "Slack Webhook URL",
        "pattern": r"(?P<secret>https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+)",
        "severity": "high",
        "confidence": "high",
    },
    # Generic
    {
        "id": "SECRET-050",
        "name": "Generic API Key Assignment",
        "pattern": r"""(?:api[_-]?key|apikey|api[_-]?secret|api[_-]?token)\s*[=:]\s*['"](?P<secret>[A-Za-z0-9_\-]{20,})['"]""",
        "severity": "high",
        "confidence": "medium",
    },
    {
        "id": "SECRET-051",
        "name": "Generic Secret Assignment",
        "pattern": r"""(?:secret[_-]?key|auth[_-]?token|access[_-]?token|bearer[_-]?token)\s*[=:]\s*['"](?P<secret>[A-Za-z0-9_\-/.+=]{20,})['"]""",
        "severity": "high",
        "confidence": "medium",
    },
    {
        "id": "SECRET-052",
        "name": "Hardcoded Password",
        "pattern": r"""(?:password|passwd|pwd)\s*[=:]\s*['"](?P<secret>[^'"]{8,})['"]""",
        "severity": "high",
        "confidence": "medium",
    },
    # Private Keys
    {
        "id": "SECRET-060",
        "name": "RSA Private Key",
        "pattern": r"(?P<secret>-----BEGIN RSA PRIVATE KEY-----)",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-061",
        "name": "OpenSSH Private Key",
        "pattern": r"(?P<secret>-----BEGIN OPENSSH PRIVATE KEY-----)",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-062",
        "name": "PGP Private Key",
        "pattern": r"(?P<secret>-----BEGIN PGP PRIVATE KEY BLOCK-----)",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-063",
        "name": "EC Private Key",
        "pattern": r"(?P<secret>-----BEGIN EC PRIVATE KEY-----)",
        "severity": "critical",
        "confidence": "high",
    },
    # Database Connection Strings
    {
        "id": "SECRET-070",
        "name": "PostgreSQL Connection String",
        "pattern": r"""(?P<secret>postgres(?:ql)?://[^\s'"]+:[^\s'"]+@[^\s'"]+)""",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-071",
        "name": "MySQL Connection String",
        "pattern": r"""(?P<secret>mysql://[^\s'"]+:[^\s'"]+@[^\s'"]+)""",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-072",
        "name": "MongoDB Connection String",
        "pattern": r"""(?P<secret>mongodb(?:\+srv)?://[^\s'"]+:[^\s'"]+@[^\s'"]+)""",
        "severity": "critical",
        "confidence": "high",
    },
    {
        "id": "SECRET-073",
        "name": "Redis Connection String",
        "pattern": r"""(?P<secret>redis://:[^\s'"]+@[^\s'"]+)""",
        "severity": "critical",
        "confidence": "high",
    },
    # JWT
    {
        "id": "SECRET-080",
        "name": "JWT Token",
        "pattern": r"(?P<secret>eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})",
        "severity": "high",
        "confidence": "medium",
    },
    # SendGrid
    {
        "id": "SECRET-090",
        "name": "SendGrid API Key",
        "pattern": r"(?P<secret>SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43})",
        "severity": "critical",
        "confidence": "high",
    },
    # Twilio
    {
        "id": "SECRET-091",
        "name": "Twilio API Key",
        "pattern": r"(?P<secret>SK[0-9a-fA-F]{32})",
        "severity": "critical",
        "confidence": "medium",
    },
    # NPM Token
    {
        "id": "SECRET-092",
        "name": "npm Token",
        "pattern": r"""(?:_authToken|NPM_TOKEN)\s*[=:]\s*['"]?(?P<secret>npm_[A-Za-z0-9]{36,})['"]?""",
        "severity": "critical",
        "confidence": "high",
    },
]


# --- Entropy Analysis ---


def shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not data:
        return 0.0
    frequency = {}
    for char in data:
        frequency[char] = frequency.get(char, 0) + 1
    length = len(data)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in frequency.values()
    )


def find_high_entropy_strings(line: str, threshold: float = 4.5) -> list[str]:
    """Find strings in a line with high Shannon entropy (potential secrets)."""
    # Extract quoted strings and assignment values
    string_pattern = r"""['"]([A-Za-z0-9_/+=\-.]{16,})['"]"""
    matches = re.findall(string_pattern, line)

    high_entropy = []
    for match in matches:
        entropy = shannon_entropy(match)
        if entropy >= threshold and len(match) >= 16:
            high_entropy.append(match)

    return high_entropy


# --- Scanner ---


SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php",
    ".cs", ".yml", ".yaml", ".json", ".xml", ".env", ".cfg", ".conf",
    ".ini", ".toml", ".properties", ".sh", ".bash", ".zsh",
    ".tf", ".hcl", ".dockerfile",
}

SKIP_DIRS = {
    "node_modules", ".git", ".svn", "__pycache__", ".tox", ".mypy_cache",
    "venv", ".venv", "env", "dist", "build", ".next", "coverage",
    ".pytest_cache", "vendor", ".terraform", ".cache",
}

# Files that commonly contain non-secret patterns
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", "go.sum",
}

PLACEHOLDER_PATTERNS = [
    r"your[-_]",
    r"example",
    r"placeholder",
    r"changeme",
    r"xxx+",
    r"todo",
    r"fixme",
    r"replace[-_]me",
    r"insert[-_]",
    r"\$\{",
    r"<[A-Z_]+>",
    r"process\.env\.",
    r"os\.environ",
    r"getenv",
]


def is_placeholder(value: str) -> bool:
    """Check if a matched value is a placeholder or environment variable reference."""
    lower = value.lower()
    return any(re.search(p, lower) for p in PLACEHOLDER_PATTERNS)


def redact_secret(text: str) -> str:
    """Redact a secret, showing only first and last 4 characters."""
    if len(text) <= 8:
        return "*" * len(text)
    return text[:4] + "*" * (len(text) - 8) + text[-4:]


def scan_file(
    filepath: str,
    rules: list[dict],
    use_entropy: bool = False,
    entropy_threshold: float = 4.5,
) -> list[SecretFinding]:
    """Scan a single file for secrets."""
    findings = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return findings

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        # Pattern-based detection
        for rule in rules:
            try:
                match = re.search(rule["pattern"], line, re.IGNORECASE)
                if match:
                    secret_value = match.group("secret") if "secret" in match.groupdict() else match.group(0)

                    # Skip placeholders
                    if is_placeholder(secret_value):
                        continue

                    # Skip test keys (Stripe test keys, etc.)
                    if secret_value.startswith(("sk_test_", "pk_test_", "rk_test_")):
                        continue

                    findings.append(SecretFinding(
                        rule_id=rule["id"],
                        name=rule["name"],
                        severity=rule["severity"],
                        file_path=filepath,
                        line_number=line_num,
                        line_content=stripped[:200],
                        matched_text=redact_secret(secret_value),
                        confidence=rule["confidence"],
                    ))
            except re.error:
                continue

        # Entropy-based detection
        if use_entropy:
            high_entropy_strings = find_high_entropy_strings(stripped, entropy_threshold)
            for hs in high_entropy_strings:
                # Avoid duplicate findings (already caught by pattern rules)
                if any(f.line_number == line_num for f in findings):
                    continue

                if is_placeholder(hs):
                    continue

                findings.append(SecretFinding(
                    rule_id="ENTROPY-001",
                    name="High Entropy String",
                    severity="medium",
                    file_path=filepath,
                    line_number=line_num,
                    line_content=stripped[:200],
                    matched_text=redact_secret(hs),
                    confidence="low",
                ))

    return findings


def scan_directory(
    directory: str,
    use_entropy: bool = False,
    entropy_threshold: float = 4.5,
    exclude_dirs: Optional[set[str]] = None,
) -> tuple[list[SecretFinding], int]:
    """Scan a directory tree for secrets."""
    exclude = exclude_dirs or set()
    all_findings = []
    files_scanned = 0

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in (SKIP_DIRS | exclude)]

        for filename in files:
            if filename in SKIP_FILES:
                continue

            filepath = os.path.join(root, filename)
            ext = Path(filepath).suffix.lower()

            if ext not in SCAN_EXTENSIONS:
                # Also scan .env files regardless of extension
                if not filename.startswith(".env"):
                    continue

            # Skip large files
            try:
                if os.path.getsize(filepath) > 500_000:
                    continue
            except OSError:
                continue

            files_scanned += 1
            findings = scan_file(
                filepath, SECRET_RULES,
                use_entropy=use_entropy,
                entropy_threshold=entropy_threshold,
            )
            all_findings.extend(findings)

    # Sort by severity
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    all_findings.sort(
        key=lambda f: severity_order.get(f.severity, 0), reverse=True
    )

    return all_findings, files_scanned


# --- Baseline Management ---


def load_baseline(path: str) -> set[str]:
    """Load a baseline file of known/accepted findings."""
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        data = json.load(f)
    return {
        f"{item['rule_id']}:{item['file_path']}:{item['line_number']}"
        for item in data.get("known_findings", [])
    }


def save_baseline(findings: list[SecretFinding], path: str) -> None:
    """Save current findings as a baseline."""
    data = {
        "generated": datetime.now().isoformat(),
        "known_findings": [
            {
                "rule_id": f.rule_id,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "name": f.name,
            }
            for f in findings
        ],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def filter_baseline(
    findings: list[SecretFinding], baseline: set[str]
) -> list[SecretFinding]:
    """Remove findings that are in the baseline."""
    return [
        f for f in findings
        if f"{f.rule_id}:{f.file_path}:{f.line_number}" not in baseline
    ]


# --- Output ---


def print_findings(findings: list[SecretFinding], files_scanned: int) -> None:
    """Print findings to stdout."""
    severity_colors = {
        "critical": "\033[91m",
        "high": "\033[93m",
        "medium": "\033[33m",
        "low": "\033[36m",
    }
    reset = "\033[0m"

    print(f"\nSecret Detection Results")
    print(f"{'=' * 60}")
    print(f"Files scanned: {files_scanned}")
    print(f"Secrets found: {len(findings)}")
    print()

    if not findings:
        print("No secrets detected.")
        return

    # Group by file
    by_file: dict[str, list[SecretFinding]] = {}
    for f in findings:
        by_file.setdefault(f.file_path, []).append(f)

    for filepath, file_findings in by_file.items():
        print(f"  {filepath}")
        for f in file_findings:
            color = severity_colors.get(f.severity, "")
            conf = f"[{f.confidence}]" if f.confidence != "high" else ""
            print(
                f"    {color}{f.severity.upper()}{reset} "
                f"Line {f.line_number}: {f.name} "
                f"({f.matched_text}) {conf}"
            )
        print()


def output_json(
    findings: list[SecretFinding], files_scanned: int, filepath: str
) -> None:
    """Output findings as JSON."""
    data = {
        "scan_time": datetime.now().isoformat(),
        "files_scanned": files_scanned,
        "total_findings": len(findings),
        "findings": [asdict(f) for f in findings],
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect hardcoded secrets in source code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s . --entropy --entropy-threshold 4.0
  %(prog)s . --output secrets.json
  %(prog)s . --baseline .secrets-baseline.json
  %(prog)s . --create-baseline .secrets-baseline.json
        """,
    )
    parser.add_argument(
        "directory",
        help="Directory to scan",
    )
    parser.add_argument(
        "--entropy", action="store_true",
        help="Enable entropy-based detection (finds high-entropy strings)",
    )
    parser.add_argument(
        "--entropy-threshold", type=float, default=4.5,
        help="Minimum Shannon entropy to flag (default: 4.5)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path for JSON results",
    )
    parser.add_argument(
        "--baseline", "-b",
        help="Baseline file of known/accepted findings to exclude",
    )
    parser.add_argument(
        "--create-baseline",
        help="Create a baseline file from current scan results",
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

    # Scan
    exclude = set(args.exclude)
    findings, files_scanned = scan_directory(
        args.directory,
        use_entropy=args.entropy,
        entropy_threshold=args.entropy_threshold,
        exclude_dirs=exclude,
    )

    # Apply baseline
    if args.baseline:
        baseline = load_baseline(args.baseline)
        original_count = len(findings)
        findings = filter_baseline(findings, baseline)
        suppressed = original_count - len(findings)
        if suppressed:
            print(f"Suppressed {suppressed} known findings from baseline")

    # Create baseline if requested
    if args.create_baseline:
        save_baseline(findings, args.create_baseline)
        print(f"Baseline saved to: {args.create_baseline}")

    # Output
    print_findings(findings, files_scanned)

    if args.output:
        output_json(findings, files_scanned, args.output)
        print(f"JSON results saved to: {args.output}")

    # Exit with non-zero if critical/high findings
    critical_high = sum(
        1 for f in findings if f.severity in ("critical", "high")
    )
    if critical_high > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
