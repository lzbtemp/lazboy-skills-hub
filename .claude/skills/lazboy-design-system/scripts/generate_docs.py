#!/usr/bin/env python3
"""
generate_docs.py — Component Documentation Generator

Parses TypeScript/TSX files for exported Props interfaces and generates
Markdown documentation including prop names, types, defaults, and JSDoc comments.

Usage:
    python generate_docs.py ./src/components --output-dir ./docs
    python generate_docs.py ./src/components/Button.tsx --output-dir ./docs
    python generate_docs.py ./src --output-dir ./docs --pattern "**/*Props.ts"
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PropDefinition:
    """A single prop extracted from an interface."""

    name: str
    type: str
    required: bool
    default: str | None = None
    description: str = ""


@dataclass
class InterfaceDefinition:
    """A parsed TypeScript Props interface."""

    name: str
    props: list[PropDefinition] = field(default_factory=list)
    description: str = ""
    extends: list[str] = field(default_factory=list)
    source_file: str = ""


# ---------------------------------------------------------------------------
# TypeScript Parser
# ---------------------------------------------------------------------------

# Regex patterns for parsing TypeScript interfaces and JSDoc comments.

# Matches an exported interface block, capturing:
#   group(1) = JSDoc comment before the interface (optional)
#   group(2) = interface name
#   group(3) = extends clause (optional)
#   group(4) = interface body
INTERFACE_RE = re.compile(
    r"(?P<jsdoc>/\*\*[\s\S]*?\*/\s*)?"
    r"(?:export\s+)?interface\s+(?P<name>\w+Props\w*)"
    r"(?:\s+extends\s+(?P<extends>[^{]+))?"
    r"\s*\{(?P<body>[^}]*(?:\{[^}]*\}[^}]*)*)\}",
    re.MULTILINE,
)

# Matches a single prop line inside an interface body, capturing:
#   group(jsdoc) = JSDoc comment
#   group(name)  = prop name
#   group(opt)   = ? if optional
#   group(type)  = type annotation
PROP_RE = re.compile(
    r"(?P<jsdoc>/\*\*[\s\S]*?\*/\s*)?"
    r"(?P<name>\w+)(?P<opt>\?)?\s*:\s*(?P<type>[^;/]+);",
    re.MULTILINE,
)

# Extracts the text content from a JSDoc comment block.
JSDOC_TEXT_RE = re.compile(
    r"/\*\*\s*([\s\S]*?)\s*\*/",
)

# Matches @default tags in JSDoc.
DEFAULT_RE = re.compile(r"@default\w*\s+(.+)")

# Matches default value assignments in destructuring patterns.
DESTRUCTURE_DEFAULT_RE = re.compile(
    r"(\w+)\s*=\s*(['\"]?\w+['\"]?|true|false|\d+(?:\.\d+)?)"
)


def extract_jsdoc_text(jsdoc: str | None) -> str:
    """Extract plain text from a JSDoc comment, stripping * prefixes."""
    if not jsdoc:
        return ""
    match = JSDOC_TEXT_RE.search(jsdoc)
    if not match:
        return ""
    raw = match.group(1)
    # Strip leading * on each line and @tags
    lines = []
    for line in raw.splitlines():
        cleaned = re.sub(r"^\s*\*\s?", "", line).strip()
        if cleaned.startswith("@"):
            continue
        if cleaned:
            lines.append(cleaned)
    return " ".join(lines)


def extract_jsdoc_default(jsdoc: str | None) -> str | None:
    """Extract @default value from a JSDoc comment."""
    if not jsdoc:
        return None
    match = DEFAULT_RE.search(jsdoc)
    return match.group(1).strip() if match else None


def parse_interface(match: re.Match, source_file: str) -> InterfaceDefinition:
    """Parse a single interface match into an InterfaceDefinition."""
    jsdoc = match.group("jsdoc")
    name = match.group("name")
    extends_raw = match.group("extends")
    body = match.group("body")

    extends = []
    if extends_raw:
        # Handle things like Omit<HTMLAttributes<HTMLInputElement>, 'size'>
        # Simple split won't work; collect top-level comma-separated items
        extends = _split_top_level(extends_raw)

    description = extract_jsdoc_text(jsdoc)

    props = parse_props(body)

    return InterfaceDefinition(
        name=name,
        props=props,
        description=description,
        extends=[e.strip() for e in extends],
        source_file=source_file,
    )


def parse_props(body: str) -> list[PropDefinition]:
    """Parse all prop definitions from an interface body string."""
    props: list[PropDefinition] = []

    for prop_match in PROP_RE.finditer(body):
        jsdoc = prop_match.group("jsdoc")
        name = prop_match.group("name")
        optional = prop_match.group("opt") is not None
        raw_type = prop_match.group("type").strip()

        description = extract_jsdoc_text(jsdoc)
        default = extract_jsdoc_default(jsdoc)

        props.append(
            PropDefinition(
                name=name,
                type=raw_type,
                required=not optional,
                default=default,
                description=description,
            )
        )

    return props


def extract_defaults_from_destructuring(source: str) -> dict[str, str]:
    """
    Scan component function bodies for destructured default values.
    E.g., { variant = 'solid', size = 'md' } => {'variant': "'solid'", 'size': "'md'"}
    """
    defaults: dict[str, str] = {}
    for match in DESTRUCTURE_DEFAULT_RE.finditer(source):
        prop_name = match.group(1)
        default_val = match.group(2)
        defaults[prop_name] = default_val
    return defaults


def _split_top_level(s: str) -> list[str]:
    """Split a string by top-level commas (not inside angle brackets)."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in s:
        if char in "<(":
            depth += 1
        elif char in ">)":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    remainder = "".join(current).strip()
    if remainder:
        parts.append(remainder)
    return parts


# ---------------------------------------------------------------------------
# File Processing
# ---------------------------------------------------------------------------


def process_file(path: Path) -> list[InterfaceDefinition]:
    """Process a single .ts/.tsx file and return found interfaces."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"  Warning: Could not read {path}: {e}", file=sys.stderr)
        return []

    interfaces: list[InterfaceDefinition] = []
    defaults = extract_defaults_from_destructuring(source)

    for match in INTERFACE_RE.finditer(source):
        iface = parse_interface(match, str(path))

        # Merge destructured defaults into props that don't have a JSDoc @default
        for prop in iface.props:
            if prop.default is None and prop.name in defaults:
                prop.default = defaults[prop.name]

        interfaces.append(iface)

    return interfaces


def find_source_files(path: Path, pattern: str = "**/*.tsx") -> list[Path]:
    """Find all matching TypeScript files in the given path."""
    if path.is_file():
        return [path]
    files = sorted(path.glob(pattern))
    # Also include .ts files
    if "tsx" in pattern:
        ts_pattern = pattern.replace(".tsx", ".ts")
        files.extend(sorted(path.glob(ts_pattern)))
    return files


# ---------------------------------------------------------------------------
# Markdown Generator
# ---------------------------------------------------------------------------


def generate_markdown(iface: InterfaceDefinition) -> str:
    """Generate a Markdown documentation section for one interface."""
    lines: list[str] = []

    component_name = iface.name.replace("Props", "").replace("OwnProps", "")
    lines.append(f"# {component_name}")
    lines.append("")

    if iface.description:
        lines.append(iface.description)
        lines.append("")

    if iface.extends:
        lines.append(f"**Extends:** `{'`, `'.join(iface.extends)}`")
        lines.append("")

    lines.append(f"**Source:** `{iface.source_file}`")
    lines.append("")

    if not iface.props:
        lines.append("_No props defined in this interface._")
        lines.append("")
        return "\n".join(lines)

    # Props table
    lines.append("## Props")
    lines.append("")
    lines.append("| Prop | Type | Default | Required | Description |")
    lines.append("|------|------|---------|----------|-------------|")

    for prop in iface.props:
        type_str = f"`{_escape_pipes(prop.type)}`"
        default_str = f"`{prop.default}`" if prop.default else "—"
        required_str = "Yes" if prop.required else "No"
        desc = _escape_pipes(prop.description) if prop.description else "—"
        lines.append(
            f"| `{prop.name}` | {type_str} | {default_str} | {required_str} | {desc} |"
        )

    lines.append("")
    return "\n".join(lines)


def generate_index(interfaces: list[InterfaceDefinition]) -> str:
    """Generate an index/table-of-contents page listing all components."""
    lines: list[str] = []
    lines.append("# Component API Documentation")
    lines.append("")
    lines.append(f"_Auto-generated on {_timestamp()}_")
    lines.append("")
    lines.append("## Components")
    lines.append("")

    for iface in sorted(interfaces, key=lambda i: i.name):
        component_name = iface.name.replace("Props", "").replace("OwnProps", "")
        filename = _slugify(component_name) + ".md"
        prop_count = len(iface.props)
        lines.append(f"- [{component_name}](./{filename}) — {prop_count} props")

    lines.append("")
    return "\n".join(lines)


def _escape_pipes(s: str) -> str:
    """Escape pipe characters for Markdown tables."""
    return s.replace("|", "\\|")


def _slugify(s: str) -> str:
    """Convert a PascalCase name to a kebab-case slug."""
    # Insert hyphens before uppercase letters, then lowercase
    slug = re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", s)
    return slug.lower().strip("-")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Markdown docs from TypeScript Props interfaces."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to a .tsx/.ts file or a directory to scan.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("./docs/components"),
        help="Output directory for Markdown files (default: ./docs/components).",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="**/*.tsx",
        help="Glob pattern for finding source files (default: **/*.tsx).",
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="Write all documentation into a single file instead of per-component files.",
    )
    args = parser.parse_args()

    source_files = find_source_files(args.input, args.pattern)
    if not source_files:
        print(f"No files matched in {args.input} with pattern '{args.pattern}'")
        sys.exit(1)

    print(f"Scanning {len(source_files)} file(s) ...")

    all_interfaces: list[InterfaceDefinition] = []
    for fpath in source_files:
        interfaces = process_file(fpath)
        if interfaces:
            print(f"  {fpath.name}: found {len(interfaces)} interface(s)")
            all_interfaces.extend(interfaces)

    if not all_interfaces:
        print("No Props interfaces found.")
        sys.exit(0)

    print(f"\nFound {len(all_interfaces)} interface(s) total.")

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.single_file:
        # Write everything to one file
        content_parts = [
            f"# Component API Documentation\n\n_Auto-generated on {_timestamp()}_\n\n---\n"
        ]
        for iface in sorted(all_interfaces, key=lambda i: i.name):
            content_parts.append(generate_markdown(iface))
            content_parts.append("---\n")

        out_path = args.output_dir / "components.md"
        out_path.write_text("\n".join(content_parts), encoding="utf-8")
        print(f"\nWritten: {out_path}")
    else:
        # Write per-component files
        for iface in all_interfaces:
            component_name = iface.name.replace("Props", "").replace("OwnProps", "")
            filename = _slugify(component_name) + ".md"
            out_path = args.output_dir / filename
            out_path.write_text(generate_markdown(iface), encoding="utf-8")
            print(f"  Written: {out_path}")

        # Write index
        index_path = args.output_dir / "index.md"
        index_path.write_text(generate_index(all_interfaces), encoding="utf-8")
        print(f"  Written: {index_path}")

    print(f"\nDone. {len(all_interfaces)} component(s) documented.")


if __name__ == "__main__":
    main()
