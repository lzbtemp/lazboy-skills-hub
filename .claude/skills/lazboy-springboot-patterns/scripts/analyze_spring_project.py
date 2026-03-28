#!/usr/bin/env python3
"""Analyze a Spring Boot project for common issues and best practice violations.

Checks controller/service/repository layers, identifies missing @Transactional,
finds N+1 query risks, and checks for proper exception handling.

Usage:
    python analyze_spring_project.py /path/to/spring-boot-project
    python analyze_spring_project.py . --verbose
    python analyze_spring_project.py /path/to/project --format json
"""

import argparse
import json
import os
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

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }


@dataclass
class AnalysisResult:
    findings: list[Finding] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def summary(self) -> dict[str, int]:
        counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts


def find_java_files(project_dir: Path) -> list[Path]:
    """Find all Java source files in src/main/java."""
    java_files = []
    src_main = project_dir / "src" / "main" / "java"
    if not src_main.exists():
        # Fall back to searching the whole project
        src_main = project_dir
    for f in src_main.rglob("*.java"):
        java_files.append(f)
    return java_files


def read_file_lines(filepath: Path) -> list[str]:
    """Read file and return lines."""
    try:
        return filepath.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []


def check_field_injection(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Check for @Autowired field injection (should use constructor injection)."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.match(r"@Autowired\s*$", stripped):
            # Check if next non-empty line is a field (not a constructor or method)
            for j in range(i, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith("//"):
                    if "(" not in next_line and "private" in next_line:
                        result.add(Finding(
                            severity=Severity.WARNING,
                            category="dependency-injection",
                            message="Field injection with @Autowired detected. Use constructor injection with @RequiredArgsConstructor instead.",
                            file=str(filepath),
                            line=i,
                        ))
                    break


def check_transactional_on_controllers(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Check for @Transactional on controller classes or methods."""
    content = "\n".join(lines)
    is_controller = bool(re.search(r"@(Rest)?Controller", content))
    if not is_controller:
        return

    for i, line in enumerate(lines, 1):
        if "@Transactional" in line:
            result.add(Finding(
                severity=Severity.ERROR,
                category="transaction-management",
                message="@Transactional found on controller. Transactions should be managed in the service layer.",
                file=str(filepath),
                line=i,
            ))


def check_missing_transactional_on_services(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Check service methods that modify data but lack @Transactional."""
    content = "\n".join(lines)
    is_service = bool(re.search(r"@Service", content))
    if not is_service:
        return

    has_any_transactional = "@Transactional" in content
    modifying_patterns = [r"\.save\(", r"\.delete", r"\.update", r"\.saveAll\(", r"\.saveAndFlush\("]

    for i, line in enumerate(lines, 1):
        for pattern in modifying_patterns:
            if re.search(pattern, line):
                # Check if the enclosing method has @Transactional
                # Look backwards for method signature and annotation
                found_transactional = False
                for j in range(max(0, i - 10), i):
                    if "@Transactional" in lines[j]:
                        found_transactional = True
                        break
                if not found_transactional and not has_any_transactional:
                    result.add(Finding(
                        severity=Severity.WARNING,
                        category="transaction-management",
                        message=f"Data-modifying operation without @Transactional. Add @Transactional to the service method.",
                        file=str(filepath),
                        line=i,
                    ))
                break  # Only report once per line


def check_readonly_transactional(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Check for read-only methods that should use @Transactional(readOnly = true)."""
    content = "\n".join(lines)
    is_service = bool(re.search(r"@Service", content))
    if not is_service:
        return

    read_patterns = [r"\.find", r"\.get", r"\.list", r"\.count", r"\.exists"]
    for i, line in enumerate(lines, 1):
        for pattern in read_patterns:
            if re.search(pattern, line) and "repository" in line.lower():
                # Check if method has @Transactional(readOnly = true)
                found_readonly = False
                for j in range(max(0, i - 10), i):
                    if "readOnly" in lines[j] and "@Transactional" in lines[j]:
                        found_readonly = True
                        break
                if not found_readonly:
                    # Only emit INFO, since it may be inside a write transaction
                    result.add(Finding(
                        severity=Severity.INFO,
                        category="transaction-management",
                        message="Read-only query without @Transactional(readOnly = true). Consider adding it for performance.",
                        file=str(filepath),
                        line=i,
                    ))
                break


def check_n_plus_one_risks(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Identify potential N+1 query risks in repository and service code."""
    content = "\n".join(lines)

    # Check for lazy collections accessed in loops
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Pattern: iterating over a collection that might be lazy-loaded
        if re.search(r"for\s*\(.*\.get\w+\(\)\s*:", stripped):
            result.add(Finding(
                severity=Severity.WARNING,
                category="n-plus-one",
                message="Potential N+1 query: iterating over a lazily-loaded collection. Use @EntityGraph or JOIN FETCH.",
                file=str(filepath),
                line=i,
            ))

        # Pattern: findAll followed by accessing relationships
        if "findAll()" in stripped or "findBy" in stripped:
            # Check subsequent lines for relationship access
            for j in range(i, min(i + 5, len(lines))):
                if re.search(r"\.get\w+\(\)\s*\.", lines[j]):
                    result.add(Finding(
                        severity=Severity.WARNING,
                        category="n-plus-one",
                        message="Potential N+1: query result followed by relationship traversal. Consider JOIN FETCH or @EntityGraph.",
                        file=str(filepath),
                        line=i,
                    ))
                    break

    # Check for EAGER fetch type
    for i, line in enumerate(lines, 1):
        if "FetchType.EAGER" in line:
            result.add(Finding(
                severity=Severity.WARNING,
                category="n-plus-one",
                message="FetchType.EAGER detected. Use LAZY by default and fetch explicitly when needed.",
                file=str(filepath),
                line=i,
            ))


def check_exception_handling(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Check for broad exception catching and missing exception chaining."""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Broad exception catch
        if re.match(r"catch\s*\(\s*Exception\s+\w+\s*\)", stripped):
            # Check if it's in a @ControllerAdvice (which is acceptable)
            content = "\n".join(lines)
            if "@ControllerAdvice" not in content and "@RestControllerAdvice" not in content:
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="exception-handling",
                    message="Broad 'catch (Exception e)' detected. Catch specific exceptions instead.",
                    file=str(filepath),
                    line=i,
                ))

        # Raw Optional.get() usage
        if ".get()" in stripped and "Optional" in "\n".join(lines[max(0, i - 5):i]):
            result.add(Finding(
                severity=Severity.ERROR,
                category="exception-handling",
                message="Raw Optional.get() detected. Use orElseThrow(), map(), or orElse() instead.",
                file=str(filepath),
                line=i,
            ))


def check_controller_logic(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Check for business logic in controllers (should be in services)."""
    content = "\n".join(lines)
    is_controller = bool(re.search(r"@(Rest)?Controller", content))
    if not is_controller:
        return

    business_patterns = [
        (r"\.save\(", "Repository .save() call in controller"),
        (r"\.delete\w*\(", "Repository .delete() call in controller"),
        (r"if\s*\(.*\.is\w+\(\).*\)\s*\{", "Complex conditional logic in controller"),
        (r"for\s*\(", "Loop in controller"),
        (r"while\s*\(", "Loop in controller"),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, desc in business_patterns:
            if re.search(pattern, line.strip()):
                # Skip if it's just calling service.delete()
                if "service" in line.lower() or "Service" in line:
                    continue
                result.add(Finding(
                    severity=Severity.WARNING,
                    category="architecture",
                    message=f"Business logic in controller: {desc}. Move to service layer.",
                    file=str(filepath),
                    line=i,
                ))
                break


def check_missing_validation(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Check for missing @Valid on request body parameters."""
    content = "\n".join(lines)
    is_controller = bool(re.search(r"@(Rest)?Controller", content))
    if not is_controller:
        return

    for i, line in enumerate(lines, 1):
        if "@RequestBody" in line and "@Valid" not in line:
            result.add(Finding(
                severity=Severity.WARNING,
                category="validation",
                message="@RequestBody without @Valid. Add @Valid to enable bean validation.",
                file=str(filepath),
                line=i,
            ))


def check_missing_controller_advice(java_files: list[Path], result: AnalysisResult) -> None:
    """Check if the project has a global exception handler."""
    has_advice = False
    for f in java_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if "@ControllerAdvice" in content or "@RestControllerAdvice" in content:
            has_advice = True
            break
    if not has_advice and java_files:
        result.add(Finding(
            severity=Severity.WARNING,
            category="exception-handling",
            message="No @ControllerAdvice found. Add a global exception handler.",
            file=str(java_files[0].parent),
            line=0,
        ))


def check_layer_statistics(java_files: list[Path], result: AnalysisResult) -> None:
    """Count controllers, services, repositories and report layer stats."""
    controllers = 0
    services = 0
    repositories = 0
    entities = 0

    for f in java_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"@(Rest)?Controller", content):
            controllers += 1
        if "@Service" in content:
            services += 1
        if re.search(r"extends\s+(Jpa|Crud|PagingAndSorting)Repository", content):
            repositories += 1
        if "@Entity" in content:
            entities += 1

    result.stats = {
        "controllers": controllers,
        "services": services,
        "repositories": repositories,
        "entities": entities,
        "total_java_files": len(java_files),
    }

    if controllers > 0 and services == 0:
        result.add(Finding(
            severity=Severity.ERROR,
            category="architecture",
            message=f"Found {controllers} controller(s) but no @Service classes. Add a service layer.",
            file="project",
            line=0,
        ))


def check_mutable_dtos(filepath: Path, lines: list[str], result: AnalysisResult) -> None:
    """Check for mutable DTOs (should use records or immutable classes)."""
    content = "\n".join(lines)
    filename = filepath.name.lower()

    if ("dto" in filename or "request" in filename or "response" in filename):
        if "class " in content and "record " not in content:
            has_setter = bool(re.search(r"(public\s+void\s+set\w+|@Setter|@Data)", content))
            if has_setter:
                result.add(Finding(
                    severity=Severity.INFO,
                    category="architecture",
                    message="Mutable DTO detected. Consider using Java records or immutable classes.",
                    file=str(filepath),
                    line=1,
                ))


def analyze_project(project_dir: Path, verbose: bool = False) -> AnalysisResult:
    """Run all analyses on the project."""
    result = AnalysisResult()
    java_files = find_java_files(project_dir)

    if not java_files:
        print(f"No Java files found in {project_dir}", file=sys.stderr)
        return result

    if verbose:
        print(f"Found {len(java_files)} Java files to analyze.", file=sys.stderr)

    # Project-level checks
    check_layer_statistics(java_files, result)
    check_missing_controller_advice(java_files, result)

    # File-level checks
    for filepath in java_files:
        lines = read_file_lines(filepath)
        if not lines:
            continue

        if verbose:
            print(f"  Analyzing: {filepath.name}", file=sys.stderr)

        check_field_injection(filepath, lines, result)
        check_transactional_on_controllers(filepath, lines, result)
        check_missing_transactional_on_services(filepath, lines, result)
        check_readonly_transactional(filepath, lines, result)
        check_n_plus_one_risks(filepath, lines, result)
        check_exception_handling(filepath, lines, result)
        check_controller_logic(filepath, lines, result)
        check_missing_validation(filepath, lines, result)
        check_mutable_dtos(filepath, lines, result)

    return result


def format_text(result: AnalysisResult, project_dir: Path) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append(f"Spring Boot Project Analysis: {project_dir}")
    lines.append("=" * 60)

    if result.stats:
        lines.append("\nProject Statistics:")
        for key, value in result.stats.items():
            lines.append(f"  {key.replace('_', ' ').title()}: {value}")

    summary = result.summary()
    lines.append(f"\nFindings: {summary['ERROR']} errors, {summary['WARNING']} warnings, {summary['INFO']} info")
    lines.append("-" * 60)

    if not result.findings:
        lines.append("\nNo issues found. Project looks good!")
        return "\n".join(lines)

    # Group by category
    categories: dict[str, list[Finding]] = {}
    for f in result.findings:
        categories.setdefault(f.category, []).append(f)

    for category, findings in sorted(categories.items()):
        lines.append(f"\n[{category.upper()}]")
        for f in findings:
            loc = f"{f.file}:{f.line}" if f.line > 0 else f.file
            lines.append(f"  {f.severity.value:7s} {loc}")
            lines.append(f"          {f.message}")

    return "\n".join(lines)


def format_json(result: AnalysisResult) -> str:
    """Format results as JSON."""
    return json.dumps({
        "stats": result.stats,
        "summary": result.summary(),
        "findings": [f.to_dict() for f in result.findings],
    }, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a Spring Boot project for common issues and best practice violations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/spring-boot-project
  %(prog)s . --verbose
  %(prog)s /path/to/project --format json
  %(prog)s /path/to/project --severity WARNING
        """,
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to the Spring Boot project root directory",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed progress during analysis",
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

    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = analyze_project(project_dir, verbose=args.verbose)

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

    # Exit with error code if any ERROR-level findings
    if any(f.severity == Severity.ERROR for f in result.findings):
        sys.exit(1)


if __name__ == "__main__":
    main()
