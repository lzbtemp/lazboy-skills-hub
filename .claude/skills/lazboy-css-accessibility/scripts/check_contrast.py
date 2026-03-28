#!/usr/bin/env python3
"""
Color Contrast Checker

Checks WCAG 2.1 color contrast ratios between two colors.
Calculates relative luminance and contrast ratio, then reports
pass/fail for WCAG AA and AAA levels across normal text, large text,
and UI components.

Usage:
    python check_contrast.py <foreground_hex> <background_hex>
    python check_contrast.py "#1a1a1a" "#ffffff"
    python check_contrast.py 0055b8 ffffff --format json
    python check_contrast.py --suggest "#777777" "#ffffff"

Examples:
    python check_contrast.py "#333333" "#ffffff"
    python check_contrast.py 0055b8 fff
    python check_contrast.py --batch pairs.csv
"""

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class ContrastResult:
    foreground: str
    background: str
    contrast_ratio: float
    foreground_luminance: float
    background_luminance: float
    aa_normal_text: bool      # 4.5:1
    aa_large_text: bool       # 3:1
    aa_ui_components: bool    # 3:1
    aaa_normal_text: bool     # 7:1
    aaa_large_text: bool      # 4.5:1


def parse_hex_color(color_str: str) -> tuple[int, int, int]:
    """Parse a hex color string into (R, G, B) tuple with values 0-255.

    Accepts formats: #RRGGBB, RRGGBB, #RGB, RGB
    """
    color = color_str.strip().lstrip("#")

    if len(color) == 3:
        color = "".join(c * 2 for c in color)

    if len(color) != 6:
        raise ValueError(
            f"Invalid hex color: '{color_str}'. Expected format: #RRGGBB, RRGGBB, #RGB, or RGB."
        )

    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        raise ValueError(f"Invalid hex characters in color: '{color_str}'.")

    return (r, g, b)


def linearize_channel(srgb_value: int) -> float:
    """Convert an 8-bit sRGB channel value to linear RGB.

    Per WCAG 2.1 relative luminance definition:
    https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    """
    s = srgb_value / 255.0
    if s <= 0.04045:
        return s / 12.92
    else:
        return math.pow((s + 0.055) / 1.055, 2.4)


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance of a color.

    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    where R, G, B are linearized sRGB values.
    """
    r_lin = linearize_channel(r)
    g_lin = linearize_channel(g)
    b_lin = linearize_channel(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(l1: float, l2: float) -> float:
    """Calculate contrast ratio between two relative luminance values.

    ratio = (L_lighter + 0.05) / (L_darker + 0.05)
    Result is between 1:1 and 21:1.
    """
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_contrast(foreground: str, background: str) -> ContrastResult:
    """Check contrast between two hex colors and return results."""
    fg_rgb = parse_hex_color(foreground)
    bg_rgb = parse_hex_color(background)

    fg_lum = relative_luminance(*fg_rgb)
    bg_lum = relative_luminance(*bg_rgb)
    ratio = contrast_ratio(fg_lum, bg_lum)

    return ContrastResult(
        foreground=foreground,
        background=background,
        contrast_ratio=round(ratio, 2),
        foreground_luminance=round(fg_lum, 4),
        background_luminance=round(bg_lum, 4),
        aa_normal_text=ratio >= 4.5,
        aa_large_text=ratio >= 3.0,
        aa_ui_components=ratio >= 3.0,
        aaa_normal_text=ratio >= 7.0,
        aaa_large_text=ratio >= 4.5,
    )


def suggest_accessible_color(color_hex: str, background_hex: str, target_ratio: float = 4.5) -> Optional[str]:
    """Suggest an adjusted foreground color that meets the target contrast ratio.

    Darkens or lightens the foreground color to reach the target ratio.
    """
    fg_rgb = parse_hex_color(color_hex)
    bg_rgb = parse_hex_color(background_hex)
    bg_lum = relative_luminance(*bg_rgb)

    current_ratio = contrast_ratio(relative_luminance(*fg_rgb), bg_lum)
    if current_ratio >= target_ratio:
        return color_hex  # Already passing

    # Determine if we need to darken or lighten
    fg_lum = relative_luminance(*fg_rgb)
    need_lighter = fg_lum < bg_lum  # fg is darker, but still fails; if bg is dark, lighten fg

    # Binary search for the right adjustment factor
    best_color = None
    for step in range(100):
        factor = step / 100.0

        if bg_lum > 0.5:
            # Light background: darken the foreground
            adjusted = tuple(max(0, int(c * (1 - factor))) for c in fg_rgb)
        else:
            # Dark background: lighten the foreground
            adjusted = tuple(min(255, int(c + (255 - c) * factor)) for c in fg_rgb)

        adj_lum = relative_luminance(*adjusted)
        adj_ratio = contrast_ratio(adj_lum, bg_lum)

        if adj_ratio >= target_ratio:
            best_color = "#{:02x}{:02x}{:02x}".format(*adjusted)
            break

    return best_color


def format_text(result: ContrastResult) -> str:
    """Format result as human-readable text."""
    lines = []
    lines.append("=" * 55)
    lines.append("COLOR CONTRAST CHECK")
    lines.append("=" * 55)
    lines.append(f"Foreground:  {result.foreground}")
    lines.append(f"Background:  {result.background}")
    lines.append(f"Contrast:    {result.contrast_ratio}:1")
    lines.append(f"FG Luminance: {result.foreground_luminance}")
    lines.append(f"BG Luminance: {result.background_luminance}")
    lines.append("-" * 55)
    lines.append(f"{'Check':<30} {'Ratio':<10} {'Result':<10}")
    lines.append("-" * 55)

    checks = [
        ("AA Normal Text (>= 4.5:1)", "4.5:1", result.aa_normal_text),
        ("AA Large Text (>= 3:1)", "3:1", result.aa_large_text),
        ("AA UI Components (>= 3:1)", "3:1", result.aa_ui_components),
        ("AAA Normal Text (>= 7:1)", "7:1", result.aaa_normal_text),
        ("AAA Large Text (>= 4.5:1)", "4.5:1", result.aaa_large_text),
    ]

    for label, required, passed in checks:
        status = "PASS" if passed else "FAIL"
        lines.append(f"  {label:<28} {required:<10} {status}")

    lines.append("=" * 55)

    # Overall assessment
    if result.aa_normal_text:
        if result.aaa_normal_text:
            lines.append("RESULT: Meets WCAG AAA for all text sizes.")
        else:
            lines.append("RESULT: Meets WCAG AA for all text sizes.")
    elif result.aa_large_text:
        lines.append("RESULT: Meets WCAG AA for large text only (>= 18pt or >= 14pt bold).")
    else:
        lines.append("RESULT: FAILS all WCAG contrast requirements.")

    lines.append("=" * 55)
    return "\n".join(lines)


def format_json_output(result: ContrastResult) -> str:
    """Format result as JSON."""
    output = {
        "foreground": result.foreground,
        "background": result.background,
        "contrast_ratio": result.contrast_ratio,
        "foreground_luminance": result.foreground_luminance,
        "background_luminance": result.background_luminance,
        "wcag_aa": {
            "normal_text": {"required": "4.5:1", "pass": result.aa_normal_text},
            "large_text": {"required": "3:1", "pass": result.aa_large_text},
            "ui_components": {"required": "3:1", "pass": result.aa_ui_components},
        },
        "wcag_aaa": {
            "normal_text": {"required": "7:1", "pass": result.aaa_normal_text},
            "large_text": {"required": "4.5:1", "pass": result.aaa_large_text},
        },
    }
    return json.dumps(output, indent=2)


def process_batch(csv_path: str, output_format: str) -> int:
    """Process a CSV file of color pairs. CSV columns: foreground, background."""
    exit_code = 0
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            results = []
            for row_num, row in enumerate(reader, 1):
                if len(row) < 2:
                    print(f"Warning: Skipping row {row_num} (need 2 columns).", file=sys.stderr)
                    continue
                fg, bg = row[0].strip(), row[1].strip()
                if not fg or not bg or fg.startswith("#") and fg == "foreground":
                    continue  # Skip header rows
                try:
                    result = check_contrast(fg, bg)
                    results.append(result)
                    if not result.aa_normal_text:
                        exit_code = 1
                except ValueError as e:
                    print(f"Error on row {row_num}: {e}", file=sys.stderr)

            if output_format == "json":
                print(json.dumps([json.loads(format_json_output(r)) for r in results], indent=2))
            else:
                for result in results:
                    print(format_text(result))
                    print()

    except FileNotFoundError:
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(2)
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(2)

    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Check WCAG 2.1 color contrast ratio between two colors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "#333333" "#ffffff"          Check dark text on white background
  %(prog)s 0055b8 ffffff --format json  Output as JSON
  %(prog)s --suggest "#999" "#fff"      Suggest accessible alternative
  %(prog)s --batch pairs.csv            Check multiple pairs from CSV
        """,
    )
    parser.add_argument(
        "foreground",
        nargs="?",
        help="Foreground (text) color in hex format (#RRGGBB or RRGGBB).",
    )
    parser.add_argument(
        "background",
        nargs="?",
        help="Background color in hex format (#RRGGBB or RRGGBB).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--suggest",
        nargs=2,
        metavar=("FOREGROUND", "BACKGROUND"),
        help="Suggest an accessible foreground color for the given pair.",
    )
    parser.add_argument(
        "--batch",
        metavar="CSV_FILE",
        help="Check multiple color pairs from a CSV file (columns: foreground, background).",
    )
    parser.add_argument(
        "--target-ratio",
        type=float,
        default=4.5,
        help="Target contrast ratio for --suggest (default: 4.5).",
    )

    args = parser.parse_args()

    # Handle batch mode
    if args.batch:
        exit_code = process_batch(args.batch, args.format)
        sys.exit(exit_code)

    # Handle suggest mode
    if args.suggest:
        fg, bg = args.suggest
        try:
            result = check_contrast(fg, bg)
            print(format_text(result))
            if not result.aa_normal_text:
                suggestion = suggest_accessible_color(fg, bg, args.target_ratio)
                if suggestion:
                    print(f"\nSuggested foreground: {suggestion}")
                    new_result = check_contrast(suggestion, bg)
                    print(f"New contrast ratio: {new_result.contrast_ratio}:1")
                else:
                    print("\nCould not find a suitable alternative color.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)
        sys.exit(0)

    # Standard two-color check
    if not args.foreground or not args.background:
        parser.error("Two color arguments are required (foreground and background).")

    try:
        result = check_contrast(args.foreground, args.background)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        print(format_json_output(result))
    else:
        print(format_text(result))

    # Exit with non-zero if it fails AA for normal text
    sys.exit(0 if result.aa_normal_text else 1)


if __name__ == "__main__":
    main()
