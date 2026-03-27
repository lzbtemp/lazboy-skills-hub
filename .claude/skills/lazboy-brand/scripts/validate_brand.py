#!/usr/bin/env python3
"""
La-Z-Boy Brand Validator
========================
Scans CSS and HTML files for off-brand colors and non-approved fonts.

Usage:
    python validate_brand.py path/to/file.css
    python validate_brand.py path/to/file.html
    python validate_brand.py path/to/directory/

Output:
    Prints a report of brand violations with line numbers.
    Exits with code 0 if no violations, 1 if violations found.
"""

import sys
import os
import re

# ── Brand-approved colors ────────────────────────────────────────────────────
APPROVED_COLORS = {
    "#1b3a6b": "Comfort Blue (primary)",
    "#c0392b": "Burnt Vermilion (accent)",
    "#8faf8a": "Soft Celadon (secondary)",
    "#faf8f5": "Warm White (background)",
    "#2c2c2c": "Charcoal (text)",
    "#cc0000": "La-Z-Boy Red (legacy only)",
    "#ffffff": "White (reversed text)",
    "#000000": "Black (one-color logo)",
}

# Colors that are known off-brand mistakes
FLAGGED_COLORS = {
    "#ff0000": "Pure red — use Burnt Vermilion (#C0392B) instead",
    "#0000ff": "Pure blue — use Comfort Blue (#1B3A6B) instead",
    "#ffffff": "NOTE: Pure white is approved only for reversed text — use Warm White (#FAF8F5) for backgrounds",
    "#f0f0f0": "Light grey — not in brand palette, use Warm White (#FAF8F5)",
    "#333333": "Dark grey — use Charcoal (#2C2C2C) instead",
    "#336699": "Generic blue — use Comfort Blue (#1B3A6B) instead",
}

# ── Approved font keywords ───────────────────────────────────────────────────
APPROVED_FONT_KEYWORDS = [
    "helvetica neue",
    "helvetica",
    "arial",
    "sans-serif",
    "whitney",  # legacy only
]

FLAGGED_FONT_KEYWORDS = [
    "times new roman",
    "georgia",
    "serif",
    "comic sans",
    "impact",
    "verdana",
    "trebuchet",
    "courier",
]

# ── Helpers ──────────────────────────────────────────────────────────────────
def normalize_hex(hex_str):
    """Normalize hex to lowercase 6-char format."""
    hex_str = hex_str.lower().strip()
    if len(hex_str) == 4:  # #abc -> #aabbcc
        hex_str = "#" + "".join(c * 2 for c in hex_str[1:])
    return hex_str

def extract_hex_colors(text):
    """Find all hex color codes in text."""
    return re.findall(r'#[0-9a-fA-F]{3,6}\b', text)

def extract_font_families(text):
    """Find font-family declarations."""
    return re.findall(r'font-family\s*:\s*([^;}\n]+)', text, re.IGNORECASE)

def scan_file(filepath):
    """Scan a single file and return violations."""
    violations = []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return [{"line": 0, "type": "error", "message": f"Could not read file: {e}"}]

    for i, line in enumerate(lines, 1):
        line_lower = line.lower()

        # Check hex colors
        for hex_color in extract_hex_colors(line):
            normalized = normalize_hex(hex_color)
            if normalized not in APPROVED_COLORS:
                if normalized in FLAGGED_COLORS:
                    violations.append({
                        "line": i,
                        "type": "warning",
                        "message": f"Off-brand color {hex_color}: {FLAGGED_COLORS[normalized]}"
                    })
                else:
                    violations.append({
                        "line": i,
                        "type": "error",
                        "message": f"Unapproved color {hex_color} — not in La-Z-Boy brand palette"
                    })

        # Check font families
        for font_decl in extract_font_families(line):
            font_lower = font_decl.lower()
            for flagged in FLAGGED_FONT_KEYWORDS:
                if flagged in font_lower:
                    violations.append({
                        "line": i,
                        "type": "error",
                        "message": f"Non-brand font '{flagged}' found — use Helvetica Neue or approved fallback"
                    })

        # Check for hardcoded color values instead of CSS variables
        if re.search(r'color\s*:\s*#', line_lower) and '--color-' not in line_lower:
            violations.append({
                "line": i,
                "type": "warning",
                "message": "Hardcoded color value detected — consider using CSS custom properties (--color-*)"
            })

    return violations

def scan_path(path):
    """Scan a file or directory recursively."""
    results = {}

    if os.path.isfile(path):
        if path.endswith(('.css', '.scss', '.html', '.htm', '.jsx', '.tsx')):
            results[path] = scan_file(path)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            # Skip node_modules and build dirs
            dirs[:] = [d for d in dirs if d not in ('node_modules', 'dist', 'build', '.git')]
            for filename in files:
                if filename.endswith(('.css', '.scss', '.html', '.htm', '.jsx', '.tsx')):
                    filepath = os.path.join(root, filename)
                    results[filepath] = scan_file(filepath)
    else:
        print(f"Error: {path} is not a file or directory")
        sys.exit(1)

    return results

def print_report(results):
    """Print a human-readable report."""
    total_errors = 0
    total_warnings = 0

    print("\n" + "="*60)
    print("  La-Z-Boy Brand Validator Report")
    print("="*60)

    for filepath, violations in results.items():
        if not violations:
            print(f"\n✅ {filepath} — No violations")
            continue

        errors = [v for v in violations if v['type'] == 'error']
        warnings = [v for v in violations if v['type'] == 'warning']
        total_errors += len(errors)
        total_warnings += len(warnings)

        print(f"\n📄 {filepath}")
        print(f"   {len(errors)} error(s), {len(warnings)} warning(s)")

        for v in violations:
            icon = "❌" if v['type'] == 'error' else "⚠️ "
            print(f"   {icon} Line {v['line']}: {v['message']}")

    print("\n" + "="*60)
    print(f"  Total: {total_errors} error(s), {total_warnings} warning(s)")
    print("="*60 + "\n")

    return total_errors

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    results = scan_path(path)
    error_count = print_report(results)
    sys.exit(0 if error_count == 0 else 1)
