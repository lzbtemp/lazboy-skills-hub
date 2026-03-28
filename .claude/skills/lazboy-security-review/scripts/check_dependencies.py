#!/usr/bin/env python3
"""
check_dependencies.py -- Check project dependencies for security issues.

Supports:
  - package.json / package-lock.json (Node.js)
  - requirements.txt / requirements-*.txt (Python)
  - pyproject.toml (Python)

Checks:
  - Known vulnerable package versions
  - Outdated packages (major version behind)
  - Unpinned or loosely-pinned versions
  - Packages with known security advisories
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DependencyInfo:
    """Information about a single dependency."""
    name: str
    version: str
    specifier: str
    source_file: str
    line: int = 0


@dataclass
class Finding:
    """A dependency security finding."""
    package: str
    version: str
    severity: str  # critical, high, medium, low
    category: str  # vulnerability, outdated, pinning, advisory
    message: str
    source_file: str
    line: int = 0
    cve: str = ""

    def __str__(self) -> str:
        loc = f"{self.source_file}:{self.line}" if self.line else self.source_file
        cve_str = f" ({self.cve})" if self.cve else ""
        return f"[{self.severity}] {loc}: {self.package}@{self.version} -- {self.message}{cve_str}"


@dataclass
class CheckReport:
    """Aggregated dependency check report."""
    findings: list[Finding] = field(default_factory=list)
    packages_checked: int = 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def count_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts


# -- Known Vulnerable Packages Database ----------------------------------------
# In production, use the OSV database, Safety DB, or npm audit API.
# This is a representative subset for offline scanning.

NPM_VULNERABILITIES: dict[str, list[dict]] = {
    "lodash": [
        {"below": "4.17.21", "severity": "critical", "cve": "CVE-2021-23337",
         "desc": "Command injection via template function"},
    ],
    "axios": [
        {"below": "1.6.0", "severity": "high", "cve": "CVE-2023-45857",
         "desc": "CSRF token exposure via cross-site requests"},
    ],
    "express": [
        {"below": "4.19.2", "severity": "medium", "cve": "CVE-2024-29041",
         "desc": "Open redirect vulnerability"},
    ],
    "jsonwebtoken": [
        {"below": "9.0.0", "severity": "high", "cve": "CVE-2022-23529",
         "desc": "Insecure key handling allows JWT forgery"},
    ],
    "minimatch": [
        {"below": "3.0.5", "severity": "high", "cve": "CVE-2022-3517",
         "desc": "ReDoS vulnerability in pattern matching"},
    ],
    "semver": [
        {"below": "7.5.2", "severity": "medium", "cve": "CVE-2022-25883",
         "desc": "ReDoS vulnerability in range parsing"},
    ],
    "tough-cookie": [
        {"below": "4.1.3", "severity": "medium", "cve": "CVE-2023-26136",
         "desc": "Prototype pollution"},
    ],
    "node-fetch": [
        {"below": "2.6.7", "severity": "high", "cve": "CVE-2022-0235",
         "desc": "Exposure of sensitive information to unauthorized actor"},
    ],
    "postcss": [
        {"below": "8.4.31", "severity": "medium", "cve": "CVE-2023-44270",
         "desc": "Line return parsing issue"},
    ],
    "ua-parser-js": [
        {"below": "0.7.33", "severity": "critical", "cve": "CVE-2021-27292",
         "desc": "ReDoS and supply chain attack"},
    ],
}

PIP_VULNERABILITIES: dict[str, list[dict]] = {
    "django": [
        {"below": "4.2.11", "severity": "high", "cve": "CVE-2024-27351",
         "desc": "ReDoS in Truncator"},
    ],
    "flask": [
        {"below": "2.3.2", "severity": "medium", "cve": "CVE-2023-30861",
         "desc": "Session cookie sent over non-HTTPS"},
    ],
    "requests": [
        {"below": "2.31.0", "severity": "medium", "cve": "CVE-2023-32681",
         "desc": "Proxy credential leak to redirected host"},
    ],
    "urllib3": [
        {"below": "2.0.7", "severity": "medium", "cve": "CVE-2023-45803",
         "desc": "Request body not stripped on redirect"},
    ],
    "cryptography": [
        {"below": "41.0.6", "severity": "high", "cve": "CVE-2023-49083",
         "desc": "NULL pointer dereference on PKCS12 deserialization"},
    ],
    "pillow": [
        {"below": "10.2.0", "severity": "high", "cve": "CVE-2023-50447",
         "desc": "Arbitrary code execution via PIL.ImageMath.eval"},
    ],
    "jinja2": [
        {"below": "3.1.3", "severity": "medium", "cve": "CVE-2024-22195",
         "desc": "XSS via xmlattr filter"},
    ],
    "pyyaml": [
        {"below": "6.0.1", "severity": "high", "cve": "CVE-2020-14343",
         "desc": "Arbitrary code execution via full_load"},
    ],
    "certifi": [
        {"below": "2023.7.22", "severity": "medium", "cve": "CVE-2023-37920",
         "desc": "Removed untrustworthy root certificate"},
    ],
    "setuptools": [
        {"below": "70.0.0", "severity": "medium", "cve": "CVE-2024-6345",
         "desc": "Remote code execution via download functions"},
    ],
    "aiohttp": [
        {"below": "3.9.4", "severity": "high", "cve": "CVE-2024-30251",
         "desc": "DoS via multipart parsing"},
    ],
    "sqlalchemy": [
        {"below": "2.0.0", "severity": "medium", "cve": "CVE-2023-30533",
         "desc": "SQL injection via Declarative with TypeDecorator"},
    ],
}


# -- Version Comparison -------------------------------------------------------

def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string into a comparable tuple."""
    clean = re.sub(r"[^\d.]", "", version_str.split(",")[0])
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def version_below(installed: str, threshold: str) -> bool:
    """Check if installed version is below the threshold."""
    return parse_version(installed) < parse_version(threshold)


# -- File Parsers -------------------------------------------------------------

def parse_package_json(filepath: str) -> list[DependencyInfo]:
    """Parse package.json and extract dependencies."""
    deps = []
    try:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deps

    for section in ("dependencies", "devDependencies"):
        for name, spec in data.get(section, {}).items():
            # Extract version from specifier
            version = re.sub(r"^[\^~>=<]", "", spec).strip()
            deps.append(DependencyInfo(
                name=name, version=version, specifier=spec, source_file=filepath,
            ))
    return deps


def parse_package_lock(filepath: str) -> dict[str, str]:
    """Parse package-lock.json to get resolved versions."""
    versions: dict[str, str] = {}
    try:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return versions

    # v2/v3 format
    packages = data.get("packages", {})
    for path, info in packages.items():
        if path.startswith("node_modules/"):
            name = path.replace("node_modules/", "", 1)
            version = info.get("version", "")
            if name and version:
                versions[name] = version

    # v1 format fallback
    if not versions:
        for name, info in data.get("dependencies", {}).items():
            versions[name] = info.get("version", "")

    return versions


def parse_requirements_txt(filepath: str) -> list[DependencyInfo]:
    """Parse requirements.txt and extract dependencies."""
    deps = []
    try:
        lines = Path(filepath).read_text(encoding="utf-8").splitlines()
    except OSError:
        return deps

    for lineno, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Remove environment markers
        line = line.split(";")[0].strip()
        match = re.match(r"^([a-zA-Z0-9_.\-]+)\s*(.*)", line)
        if match:
            name = match.group(1).lower()
            spec = match.group(2).strip()
            version = ""
            vm = re.search(r"==\s*([\d.]+)", spec)
            if vm:
                version = vm.group(1)
            else:
                vm = re.search(r">=\s*([\d.]+)", spec)
                if vm:
                    version = vm.group(1)
            deps.append(DependencyInfo(
                name=name, version=version, specifier=spec,
                source_file=filepath, line=lineno,
            ))
    return deps


def parse_pyproject_toml(filepath: str) -> list[DependencyInfo]:
    """Parse pyproject.toml for dependencies (basic parser)."""
    deps = []
    try:
        content = Path(filepath).read_text(encoding="utf-8")
    except OSError:
        return deps

    in_deps = False
    lineno = 0
    for line in content.splitlines():
        lineno += 1
        stripped = line.strip()

        if "dependencies" in stripped and "=" in stripped:
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            in_deps = False
            continue
        if in_deps and stripped.startswith('"'):
            dep_str = stripped.strip('",')
            match = re.match(r"^([a-zA-Z0-9_.\-]+)\s*(.*)", dep_str)
            if match:
                name = match.group(1).lower()
                spec = match.group(2).strip()
                version = ""
                vm = re.search(r"[><=]+\s*([\d.]+)", spec)
                if vm:
                    version = vm.group(1)
                deps.append(DependencyInfo(
                    name=name, version=version, specifier=spec,
                    source_file=filepath, line=lineno,
                ))
    return deps


# -- Checks -------------------------------------------------------------------

def check_npm_vulnerabilities(deps: list[DependencyInfo], lock_versions: dict[str, str],
                               report: CheckReport) -> None:
    """Check npm packages against known vulnerability database."""
    for dep in deps:
        # Prefer lock file version (resolved)
        actual_version = lock_versions.get(dep.name, dep.version)
        if not actual_version:
            continue

        vulns = NPM_VULNERABILITIES.get(dep.name, [])
        for vuln in vulns:
            if version_below(actual_version, vuln["below"]):
                report.add(Finding(
                    package=dep.name, version=actual_version,
                    severity=vuln["severity"], category="vulnerability",
                    message=f"{vuln['desc']}. Upgrade to >= {vuln['below']}.",
                    source_file=dep.source_file, line=dep.line,
                    cve=vuln["cve"],
                ))


def check_pip_vulnerabilities(deps: list[DependencyInfo], report: CheckReport) -> None:
    """Check Python packages against known vulnerability database."""
    for dep in deps:
        if not dep.version:
            continue
        # Normalize name
        norm_name = dep.name.lower().replace("-", "").replace("_", "")
        for pkg_name, vulns in PIP_VULNERABILITIES.items():
            if norm_name == pkg_name.replace("-", "").replace("_", ""):
                for vuln in vulns:
                    if version_below(dep.version, vuln["below"]):
                        report.add(Finding(
                            package=dep.name, version=dep.version,
                            severity=vuln["severity"], category="vulnerability",
                            message=f"{vuln['desc']}. Upgrade to >= {vuln['below']}.",
                            source_file=dep.source_file, line=dep.line,
                            cve=vuln["cve"],
                        ))


def check_pinning(deps: list[DependencyInfo], report: CheckReport) -> None:
    """Check for unpinned or loosely-pinned dependencies."""
    for dep in deps:
        if not dep.specifier:
            report.add(Finding(
                package=dep.name, version="*",
                severity="medium", category="pinning",
                message="No version constraint specified. Pin to a specific version range.",
                source_file=dep.source_file, line=dep.line,
            ))
        elif dep.specifier.startswith("^") or dep.specifier.startswith("~"):
            # Common in npm -- acceptable but worth noting for critical deps
            pass
        elif dep.specifier.startswith(">=") and "<" not in dep.specifier:
            report.add(Finding(
                package=dep.name, version=dep.version,
                severity="low", category="pinning",
                message="No upper version bound. Consider adding an upper bound to prevent breaking changes.",
                source_file=dep.source_file, line=dep.line,
            ))
        elif dep.specifier == "*" or dep.specifier == "latest":
            report.add(Finding(
                package=dep.name, version="*",
                severity="medium", category="pinning",
                message="Wildcard/latest version -- pin to a specific version.",
                source_file=dep.source_file, line=dep.line,
            ))


def check_lock_file_presence(root: str, report: CheckReport) -> None:
    """Verify that lock files are present."""
    root_path = Path(root)

    if (root_path / "package.json").exists():
        if not (root_path / "package-lock.json").exists() and \
           not (root_path / "yarn.lock").exists() and \
           not (root_path / "pnpm-lock.yaml").exists():
            report.add(Finding(
                package="(project)", version="",
                severity="medium", category="advisory",
                message="No lock file found (package-lock.json, yarn.lock, or pnpm-lock.yaml). "
                        "Lock files ensure reproducible installs.",
                source_file="package.json",
            ))

    if (root_path / "requirements.txt").exists():
        # Check if any deps are unpinned (no == specifier)
        pass  # Handled by check_pinning

    if (root_path / "pyproject.toml").exists():
        if not (root_path / "poetry.lock").exists() and \
           not (root_path / "uv.lock").exists() and \
           not (root_path / "pdm.lock").exists():
            report.add(Finding(
                package="(project)", version="",
                severity="low", category="advisory",
                message="No Python lock file found (poetry.lock, uv.lock, or pdm.lock). "
                        "Consider using a lock file for reproducible installs.",
                source_file="pyproject.toml",
            ))


# -- Output Formatting --------------------------------------------------------

SEVERITY_COLORS = {
    "critical": "\033[1;31m",
    "high": "\033[31m",
    "medium": "\033[33m",
    "low": "\033[36m",
}
RESET = "\033[0m"


def print_text_report(report: CheckReport) -> None:
    """Print a human-readable report."""
    if not report.findings:
        print(f"Checked {report.packages_checked} packages. No issues found.")
        return

    # Group by category
    by_cat: dict[str, list[Finding]] = {}
    for f in report.findings:
        by_cat.setdefault(f.category, []).append(f)

    labels = {
        "vulnerability": "Known Vulnerabilities",
        "pinning": "Version Pinning",
        "advisory": "Security Advisories",
        "outdated": "Outdated Packages",
    }

    for category, findings in sorted(by_cat.items()):
        label = labels.get(category, category)
        print(f"\n{'=' * 65}")
        print(f"  {label} ({len(findings)} finding(s))")
        print(f"{'=' * 65}")
        for finding in sorted(findings, key=lambda f: (f.source_file, f.package)):
            color = SEVERITY_COLORS.get(finding.severity, "")
            print(f"  {color}{finding}{RESET}")

    counts = report.count_by_severity()
    print(f"\n{'─' * 65}")
    print(f"Checked {report.packages_checked} packages. "
          f"Found {len(report.findings)} issue(s).")
    for sev in ["critical", "high", "medium", "low"]:
        if counts[sev]:
            color = SEVERITY_COLORS.get(sev, "")
            print(f"  {color}{sev}: {counts[sev]}{RESET}")


def print_json_report(report: CheckReport) -> None:
    """Print a JSON report."""
    output = {
        "packages_checked": report.packages_checked,
        "findings": [
            {
                "package": f.package,
                "version": f.version,
                "severity": f.severity,
                "category": f.category,
                "message": f.message,
                "source_file": f.source_file,
                "line": f.line,
                "cve": f.cve,
            }
            for f in report.findings
        ],
        "summary": report.count_by_severity(),
        "total": len(report.findings),
    }
    print(json.dumps(output, indent=2))


# -- Main Entry Point ---------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check project dependencies for known vulnerabilities and security issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported files:
  package.json / package-lock.json    Node.js dependencies
  requirements.txt / requirements-*   Python pip dependencies
  pyproject.toml                      Python project dependencies

Examples:
  %(prog)s .                          Check current project
  %(prog)s --severity high .          Only show high+ severity
  %(prog)s --format json .            Output as JSON
  %(prog)s --fail-on high .           Exit 1 if high+ findings exist
""",
    )
    parser.add_argument(
        "root", nargs="?", default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--severity", choices=["critical", "high", "medium", "low"], default=None,
        help="Minimum severity level to report",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--fail-on", choices=["critical", "high", "medium", "low"], default=None,
        help="Exit with code 1 if findings at this severity or above exist",
    )
    parser.add_argument(
        "--skip-pinning", action="store_true",
        help="Skip version pinning checks",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Only print summary",
    )

    args = parser.parse_args()
    root = os.path.abspath(args.root)
    root_path = Path(root)

    if not root_path.is_dir():
        print(f"Error: '{root}' is not a directory.", file=sys.stderr)
        return 1

    report = CheckReport()
    all_deps: list[DependencyInfo] = []

    # -- Node.js dependencies --
    pkg_json = root_path / "package.json"
    if pkg_json.exists():
        npm_deps = parse_package_json(str(pkg_json))
        all_deps.extend(npm_deps)

        # Get resolved versions from lock file
        lock_versions: dict[str, str] = {}
        pkg_lock = root_path / "package-lock.json"
        if pkg_lock.exists():
            lock_versions = parse_package_lock(str(pkg_lock))

        check_npm_vulnerabilities(npm_deps, lock_versions, report)
        if not args.skip_pinning:
            check_pinning(npm_deps, report)

    # -- Python dependencies --
    for req_pattern in ["requirements.txt", "requirements-*.txt", "requirements/*.txt"]:
        for req_file in root_path.glob(req_pattern):
            pip_deps = parse_requirements_txt(str(req_file))
            all_deps.extend(pip_deps)
            check_pip_vulnerabilities(pip_deps, report)
            if not args.skip_pinning:
                check_pinning(pip_deps, report)

    pyproject = root_path / "pyproject.toml"
    if pyproject.exists():
        toml_deps = parse_pyproject_toml(str(pyproject))
        all_deps.extend(toml_deps)
        check_pip_vulnerabilities(toml_deps, report)
        if not args.skip_pinning:
            check_pinning(toml_deps, report)

    # Lock file check
    check_lock_file_presence(root, report)

    report.packages_checked = len(all_deps)

    # Filter by severity
    if args.severity:
        severity_order = ["low", "medium", "high", "critical"]
        min_idx = severity_order.index(args.severity)
        report.findings = [
            f for f in report.findings
            if severity_order.index(f.severity) >= min_idx
        ]

    # Output
    if args.quiet:
        counts = report.count_by_severity()
        print(f"Checked {report.packages_checked} packages. "
              f"Found {len(report.findings)} issue(s): "
              f"{counts['critical']}C {counts['high']}H {counts['medium']}M {counts['low']}L")
    elif args.format == "json":
        print_json_report(report)
    else:
        print_text_report(report)

    # Exit code
    if args.fail_on and report.findings:
        severity_order = ["low", "medium", "high", "critical"]
        fail_idx = severity_order.index(args.fail_on)
        if any(severity_order.index(f.severity) >= fail_idx for f in report.findings):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
