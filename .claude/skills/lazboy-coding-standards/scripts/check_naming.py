#!/usr/bin/env python3
"""
Check naming convention violations in TypeScript/JavaScript files.

Scans source files for naming convention violations:
- camelCase for variables and functions
- PascalCase for React components, classes, interfaces, and types
- UPPER_SNAKE_CASE for constants
- camelCase with 'use' prefix for custom hooks

Usage:
    python check_naming.py /path/to/src
    python check_naming.py /path/to/src --strict
    python check_naming.py /path/to/src --json
    python check_naming.py /path/to/src --fix-suggestions
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Violation:
    file: str
    line: int
    column: int
    name: str
    expected_convention: str
    actual_pattern: str
    message: str
    suggestion: Optional[str] = None


# --- Pattern helpers ---

def is_camel_case(name: str) -> bool:
    """Check if a name is camelCase (starts lowercase, no underscores except leading _)."""
    if not name:
        return False
    # Allow leading underscore for private convention
    clean = name.lstrip("_")
    if not clean:
        return True
    return clean[0].islower() and "_" not in clean


def is_pascal_case(name: str) -> bool:
    """Check if a name is PascalCase (starts uppercase, no underscores)."""
    if not name:
        return False
    return name[0].isupper() and "_" not in name


def is_upper_snake_case(name: str) -> bool:
    """Check if a name is UPPER_SNAKE_CASE."""
    if not name:
        return False
    return name == name.upper() and re.match(r'^[A-Z][A-Z0-9_]*$', name) is not None


def to_camel_case(name: str) -> str:
    """Convert a name to camelCase."""
    if "_" in name:
        parts = name.lower().split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])
    if name[0].isupper():
        return name[0].lower() + name[1:]
    return name


def to_pascal_case(name: str) -> str:
    """Convert a name to PascalCase."""
    if "_" in name:
        return "".join(p.capitalize() for p in name.split("_"))
    return name[0].upper() + name[1:]


def to_upper_snake(name: str) -> str:
    """Convert a name to UPPER_SNAKE_CASE."""
    result = re.sub(r'([A-Z])', r'_\1', name).upper()
    return result.lstrip("_")


# --- Exclusions ---

# Common identifiers that should be excluded from checks
EXCLUDED_NAMES = {
    # Single-char loop variables
    "i", "j", "k", "n", "x", "y", "z", "e", "t", "v", "p", "a", "b",
    # Common destructured names from libraries
    "React", "useState", "useEffect", "useCallback", "useMemo", "useRef",
    "useContext", "useReducer", "useLayoutEffect", "useImperativeHandle",
    # Common imports
    "express", "router", "app", "db", "req", "res", "next", "err",
    # Type keywords used as names
    "string", "number", "boolean", "null", "undefined", "void", "any", "never",
    "unknown",
}

# File-level patterns to skip
SKIP_FILE_PATTERNS = {
    "node_modules", ".next", "dist", "build", "coverage", ".git",
    "__mocks__", "__fixtures__",
}


def should_skip_file(filepath: Path) -> bool:
    """Check if a file should be skipped based on its path."""
    parts = filepath.parts
    return any(skip in parts for skip in SKIP_FILE_PATTERNS)


def is_test_file(filepath: Path) -> bool:
    """Check if the file is a test file."""
    name = filepath.name
    return ".test." in name or ".spec." in name or "__tests__" in str(filepath)


def is_component_file(filepath: Path) -> bool:
    """Check if the file is likely a React component (PascalCase .tsx)."""
    return filepath.suffix == ".tsx" and filepath.stem[0].isupper()


# --- Scanning patterns ---

# Regex patterns for extracting declarations
PATTERNS = {
    "const_declaration": re.compile(
        r'(?:export\s+)?const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*(?::\s*[^=]+)?\s*='
    ),
    "let_declaration": re.compile(
        r'(?:export\s+)?let\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*(?::\s*[^=]+)?\s*='
    ),
    "function_declaration": re.compile(
        r'(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*[<(]'
    ),
    "class_declaration": re.compile(
        r'(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)'
    ),
    "interface_declaration": re.compile(
        r'(?:export\s+)?interface\s+([A-Za-z_$][A-Za-z0-9_$]*)'
    ),
    "type_declaration": re.compile(
        r'(?:export\s+)?type\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*(?:<[^>]*>)?\s*='
    ),
    "enum_declaration": re.compile(
        r'(?:export\s+)?(?:const\s+)?enum\s+([A-Za-z_$][A-Za-z0-9_$]*)'
    ),
}

# Pattern to detect if a const is a React component (arrow function returning JSX)
REACT_COMPONENT_PATTERN = re.compile(
    r'(?:export\s+)?const\s+([A-Z][A-Za-z0-9]*)\s*(?::\s*[^=]+)?\s*=\s*(?:React\.)?(?:memo|forwardRef)?\s*\(?'
)

# Pattern to detect if a const is assigned a primitive literal (likely a true constant)
CONST_LITERAL_PATTERN = re.compile(
    r"const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*(?::\s*[^=]+)?\s*=\s*(?:[\'\"`\d]|true|false|null)"
)

# Pattern for custom hooks
HOOK_PATTERN = re.compile(
    r'(?:export\s+)?(?:const|function)\s+(use[A-Z][A-Za-z0-9]*)'
)


def detect_actual_pattern(name: str) -> str:
    """Describe the current naming pattern of an identifier."""
    if is_upper_snake_case(name):
        return "UPPER_SNAKE_CASE"
    if is_pascal_case(name):
        return "PascalCase"
    if is_camel_case(name):
        return "camelCase"
    if "_" in name and name != name.upper():
        return "snake_case"
    return "mixed/unclear"


def check_variable(name: str, line_text: str, filepath: Path) -> Optional[str]:
    """Check if a variable name follows the correct convention.
    Returns expected convention if violated, None if OK."""
    if name in EXCLUDED_NAMES or len(name) <= 1:
        return None

    # Check if it looks like a constant (UPPER_SNAKE_CASE with const + literal)
    if is_upper_snake_case(name):
        return None  # UPPER_SNAKE is valid for const

    # Check if it is a React component (PascalCase + arrow function)
    if is_pascal_case(name) and filepath.suffix in (".tsx", ".jsx"):
        return None  # PascalCase OK for components

    # Check for a class instance or constructor result (PascalCase OK for type names)
    if is_pascal_case(name) and re.search(r'=\s*new\s+', line_text):
        return None

    # Standard variable: should be camelCase
    if not is_camel_case(name) and not is_upper_snake_case(name) and not is_pascal_case(name):
        return "camelCase"

    # If it has underscores but is not UPPER_SNAKE_CASE, it is snake_case — wrong
    if "_" in name and not is_upper_snake_case(name) and not name.startswith("_"):
        return "camelCase or UPPER_SNAKE_CASE"

    return None


def check_function(name: str) -> Optional[str]:
    """Check if a function name follows camelCase convention."""
    if name in EXCLUDED_NAMES or len(name) <= 1:
        return None
    if not is_camel_case(name):
        # Exception: PascalCase for React components defined as functions
        if is_pascal_case(name):
            return None  # Allow PascalCase for component functions
        return "camelCase"
    return None


def check_class(name: str) -> Optional[str]:
    """Check if a class name follows PascalCase convention."""
    if not is_pascal_case(name):
        return "PascalCase"
    return None


def check_interface(name: str) -> Optional[str]:
    """Check if an interface name follows PascalCase convention.
    Also flags the I- prefix anti-pattern."""
    if not is_pascal_case(name):
        return "PascalCase"
    if re.match(r'^I[A-Z]', name) and name != "I":
        return "PascalCase without I- prefix (e.g., User instead of IUser)"
    return None


def check_type_alias(name: str) -> Optional[str]:
    """Check if a type alias follows PascalCase convention."""
    if not is_pascal_case(name):
        return "PascalCase"
    return None


def check_enum(name: str) -> Optional[str]:
    """Check if an enum name follows PascalCase convention."""
    if not is_pascal_case(name):
        return "PascalCase"
    return None


def check_hook(name: str) -> Optional[str]:
    """Check if a custom hook follows the use* camelCase convention."""
    if not name.startswith("use"):
        return "camelCase with 'use' prefix"
    if not is_camel_case(name):
        return "camelCase with 'use' prefix (e.g., useDebounce)"
    return None


def check_component_file_name(filepath: Path) -> Optional[Violation]:
    """Check if a component file uses PascalCase naming."""
    if filepath.suffix not in (".tsx", ".jsx"):
        return None

    stem = filepath.stem
    # If the file exports a component, the filename should be PascalCase
    # Heuristic: .tsx files that are NOT hooks and NOT utilities
    if stem.startswith("use") or stem[0].islower():
        # Could be a hook file or utility — check content later
        return None

    if not is_pascal_case(stem):
        return Violation(
            file=str(filepath),
            line=0,
            column=0,
            name=filepath.name,
            expected_convention="PascalCase",
            actual_pattern=detect_actual_pattern(stem),
            message=f"Component file '{filepath.name}' should use PascalCase naming",
            suggestion=f"Rename to '{to_pascal_case(stem)}{filepath.suffix}'",
        )
    return None


def scan_file(filepath: Path, strict: bool = False) -> list:
    """Scan a single file for naming convention violations."""
    violations = []

    if should_skip_file(filepath):
        return violations

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return violations

    lines = content.splitlines()
    rel_path = str(filepath)

    # Check file name
    fname_violation = check_component_file_name(filepath)
    if fname_violation:
        violations.append(fname_violation)

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        # Skip import/export lines
        if stripped.startswith("import ") or stripped.startswith("export {"):
            continue

        # Check function declarations
        match = PATTERNS["function_declaration"].search(line)
        if match:
            name = match.group(1)
            expected = check_function(name)
            if expected:
                violations.append(Violation(
                    file=rel_path, line=i, column=match.start(1) + 1,
                    name=name,
                    expected_convention=expected,
                    actual_pattern=detect_actual_pattern(name),
                    message=f"Function '{name}' should be {expected}",
                    suggestion=f"Rename to '{to_camel_case(name)}'",
                ))
            continue

        # Check class declarations
        match = PATTERNS["class_declaration"].search(line)
        if match:
            name = match.group(1)
            expected = check_class(name)
            if expected:
                violations.append(Violation(
                    file=rel_path, line=i, column=match.start(1) + 1,
                    name=name,
                    expected_convention=expected,
                    actual_pattern=detect_actual_pattern(name),
                    message=f"Class '{name}' should be {expected}",
                    suggestion=f"Rename to '{to_pascal_case(name)}'",
                ))
            continue

        # Check interface declarations
        match = PATTERNS["interface_declaration"].search(line)
        if match:
            name = match.group(1)
            expected = check_interface(name)
            if expected:
                violations.append(Violation(
                    file=rel_path, line=i, column=match.start(1) + 1,
                    name=name,
                    expected_convention=expected,
                    actual_pattern=detect_actual_pattern(name),
                    message=f"Interface '{name}' should be {expected}",
                    suggestion=f"Rename to '{name[1:]}'" if name.startswith("I") else f"Rename to '{to_pascal_case(name)}'",
                ))
            continue

        # Check type declarations
        match = PATTERNS["type_declaration"].search(line)
        if match:
            name = match.group(1)
            expected = check_type_alias(name)
            if expected:
                violations.append(Violation(
                    file=rel_path, line=i, column=match.start(1) + 1,
                    name=name,
                    expected_convention=expected,
                    actual_pattern=detect_actual_pattern(name),
                    message=f"Type '{name}' should be {expected}",
                    suggestion=f"Rename to '{to_pascal_case(name)}'",
                ))
            continue

        # Check enum declarations
        match = PATTERNS["enum_declaration"].search(line)
        if match:
            name = match.group(1)
            expected = check_enum(name)
            if expected:
                violations.append(Violation(
                    file=rel_path, line=i, column=match.start(1) + 1,
                    name=name,
                    expected_convention=expected,
                    actual_pattern=detect_actual_pattern(name),
                    message=f"Enum '{name}' should be {expected}",
                    suggestion=f"Rename to '{to_pascal_case(name)}'",
                ))
            continue

        # Check const/let declarations
        for decl_type in ("const_declaration", "let_declaration"):
            match = PATTERNS[decl_type].search(line)
            if match:
                name = match.group(1)

                # Check if it is a hook
                if name.startswith("use") and name[3:4].isupper():
                    expected = check_hook(name)
                    if expected:
                        violations.append(Violation(
                            file=rel_path, line=i, column=match.start(1) + 1,
                            name=name,
                            expected_convention=expected,
                            actual_pattern=detect_actual_pattern(name),
                            message=f"Hook '{name}' should be {expected}",
                        ))
                    break

                expected = check_variable(name, line, filepath)
                if expected:
                    violations.append(Violation(
                        file=rel_path, line=i, column=match.start(1) + 1,
                        name=name,
                        expected_convention=expected,
                        actual_pattern=detect_actual_pattern(name),
                        message=f"Variable '{name}' should be {expected}",
                        suggestion=f"Rename to '{to_camel_case(name)}'",
                    ))
                break

    return violations


def collect_files(root: Path) -> list:
    """Collect all TypeScript/JavaScript files for scanning."""
    files = []
    exclude_dirs = {"node_modules", ".next", "dist", "build", "coverage", ".git"}
    extensions = {".ts", ".tsx", ".js", ".jsx"}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in extensions and ".d.ts" not in fname:
                files.append(fpath)
    return files


def format_text(violations: list, files_scanned: int) -> str:
    """Format violations as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("  NAMING CONVENTION CHECK")
    lines.append("=" * 70)
    lines.append(f"\nFiles scanned: {files_scanned}")
    lines.append(f"Violations found: {len(violations)}\n")

    if not violations:
        lines.append("No naming convention violations found.")
        return "\n".join(lines)

    # Group by file
    by_file = {}
    for v in violations:
        by_file.setdefault(v.file, []).append(v)

    for filepath, file_violations in sorted(by_file.items()):
        lines.append(f"\n  {filepath}")
        lines.append("  " + "-" * 60)
        for v in file_violations:
            loc = f"  L{v.line}:{v.column}" if v.line else "  "
            lines.append(f"  {loc}  {v.message}")
            lines.append(f"          Expected: {v.expected_convention}  |  Found: {v.actual_pattern}")
            if v.suggestion:
                lines.append(f"          -> {v.suggestion}")

    lines.append(f"\n{'=' * 70}")
    lines.append(f"  Total: {len(violations)} violation(s) in {len(by_file)} file(s)")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_json_output(violations: list, files_scanned: int) -> str:
    """Format violations as JSON."""
    return json.dumps({
        "files_scanned": files_scanned,
        "violation_count": len(violations),
        "violations": [asdict(v) for v in violations],
    }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Check naming convention violations in TypeScript/JavaScript files.",
    )
    parser.add_argument(
        "path",
        help="File or directory to scan",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode with additional checks",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        help="Include suggested renames in the output",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Additional directory names to exclude from scanning",
    )

    args = parser.parse_args()
    target = Path(args.path).resolve()

    if not target.exists():
        print(f"Error: '{target}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Add custom exclusions
    for excl in args.exclude:
        SKIP_FILE_PATTERNS.add(excl)

    # Collect files
    if target.is_file():
        files = [target]
    else:
        files = collect_files(target)

    if not files:
        print(f"No TypeScript/JavaScript files found in '{target}'", file=sys.stderr)
        sys.exit(0)

    # Scan
    all_violations = []
    for fpath in files:
        violations = scan_file(fpath, strict=args.strict)
        if not args.fix_suggestions:
            for v in violations:
                v.suggestion = None
        all_violations.extend(violations)

    # Output
    if args.output_json:
        print(format_json_output(all_violations, len(files)))
    else:
        print(format_text(all_violations, len(files)))

    # Exit code
    sys.exit(1 if all_violations else 0)


if __name__ == "__main__":
    main()
