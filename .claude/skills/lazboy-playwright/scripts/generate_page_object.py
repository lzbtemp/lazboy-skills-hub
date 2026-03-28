#!/usr/bin/env python3
"""Generate Playwright Page Object Model classes from HTML files.

Analyzes HTML structure to extract interactive elements and generates
TypeScript POM classes with locators, actions, and assertions.

Usage:
    python generate_page_object.py --html /path/to/page.html --name ProductPage
    python generate_page_object.py --html /path/to/page.html --name CheckoutPage --output ./tests/checkout/
    python generate_page_object.py --html /path/to/page.html --name LoginPage --base-class BasePage
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent, indent


@dataclass
class LocatorInfo:
    name: str
    selector_type: str  # role, label, testid, text, css
    selector_value: str
    element_type: str  # button, input, link, heading, text, generic
    role: str = ""
    label: str = ""
    testid: str = ""

    def to_playwright_locator(self) -> str:
        """Generate Playwright locator code."""
        if self.selector_type == "role":
            if self.label:
                return f"this.page.getByRole('{self.role}', {{ name: '{self.label}' }})"
            return f"this.page.getByRole('{self.role}')"
        elif self.selector_type == "label":
            return f"this.page.getByLabel('{self.selector_value}')"
        elif self.selector_type == "testid":
            return f"this.page.getByTestId('{self.selector_value}')"
        elif self.selector_type == "text":
            return f"this.page.getByText('{self.selector_value}')"
        else:
            return f"this.page.locator('{self.selector_value}')"


@dataclass
class PageObjectModel:
    name: str
    url_path: str = ""
    locators: list[LocatorInfo] = field(default_factory=list)
    forms: list[dict] = field(default_factory=list)


def sanitize_name(text: str) -> str:
    """Convert text to a valid camelCase identifier."""
    # Remove special characters
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    words = cleaned.strip().split()
    if not words:
        return "element"
    # camelCase
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def parse_html_file(filepath: Path) -> str:
    """Read and return HTML content."""
    try:
        return filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def extract_locators(html: str) -> list[LocatorInfo]:
    """Extract interactive elements from HTML and generate locator info."""
    locators = []
    seen_names: set[str] = set()

    def add_locator(loc: LocatorInfo) -> None:
        # Deduplicate
        if loc.name in seen_names:
            loc.name = f"{loc.name}_{len(seen_names)}"
        seen_names.add(loc.name)
        locators.append(loc)

    # Extract buttons
    button_pattern = re.compile(
        r'<button[^>]*>(.*?)</button>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in button_pattern.finditer(html):
        full_tag = html[match.start():match.end()]
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        testid = _extract_attr(full_tag, "data-testid")

        if testid:
            name = sanitize_name(testid)
            add_locator(LocatorInfo(
                name=f"{name}Button",
                selector_type="testid",
                selector_value=testid,
                element_type="button",
                testid=testid,
            ))
        elif text:
            name = sanitize_name(text)
            add_locator(LocatorInfo(
                name=f"{name}Button",
                selector_type="role",
                selector_value=f"button[name='{text}']",
                element_type="button",
                role="button",
                label=text,
            ))

    # Extract links
    link_pattern = re.compile(
        r'<a[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in link_pattern.finditer(html):
        full_tag = html[match.start():match.end()]
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        href = _extract_attr(full_tag, "href")

        if text:
            name = sanitize_name(text)
            add_locator(LocatorInfo(
                name=f"{name}Link",
                selector_type="role",
                selector_value=f"link[name='{text}']",
                element_type="link",
                role="link",
                label=text,
            ))

    # Extract inputs (with labels)
    input_pattern = re.compile(
        r'<input[^>]*>',
        re.IGNORECASE,
    )
    for match in input_pattern.finditer(html):
        full_tag = match.group(0)
        input_type = _extract_attr(full_tag, "type") or "text"
        input_id = _extract_attr(full_tag, "id")
        input_name = _extract_attr(full_tag, "name")
        placeholder = _extract_attr(full_tag, "placeholder")
        testid = _extract_attr(full_tag, "data-testid")
        aria_label = _extract_attr(full_tag, "aria-label")

        # Find associated label
        label_text = ""
        if input_id:
            label_match = re.search(
                rf'<label[^>]*for=["\']?{re.escape(input_id)}["\']?[^>]*>(.*?)</label>',
                html, re.IGNORECASE | re.DOTALL,
            )
            if label_match:
                label_text = re.sub(r"<[^>]+>", "", label_match.group(1)).strip()

        if input_type in ("submit", "button"):
            value = _extract_attr(full_tag, "value") or "Submit"
            name = sanitize_name(value)
            add_locator(LocatorInfo(
                name=f"{name}Button",
                selector_type="role",
                selector_value=f"button[name='{value}']",
                element_type="button",
                role="button",
                label=value,
            ))
        elif input_type == "checkbox":
            label = label_text or aria_label or input_name or "checkbox"
            name = sanitize_name(label)
            add_locator(LocatorInfo(
                name=f"{name}Checkbox",
                selector_type="role",
                selector_value=f"checkbox[name='{label}']",
                element_type="input",
                role="checkbox",
                label=label,
            ))
        else:
            # Text-like inputs
            if label_text:
                name = sanitize_name(label_text)
                add_locator(LocatorInfo(
                    name=f"{name}Input",
                    selector_type="label",
                    selector_value=label_text,
                    element_type="input",
                    label=label_text,
                ))
            elif testid:
                name = sanitize_name(testid)
                add_locator(LocatorInfo(
                    name=f"{name}Input",
                    selector_type="testid",
                    selector_value=testid,
                    element_type="input",
                    testid=testid,
                ))
            elif placeholder:
                name = sanitize_name(placeholder)
                add_locator(LocatorInfo(
                    name=f"{name}Input",
                    selector_type="role",
                    selector_value=f"textbox[name='{placeholder}']",
                    element_type="input",
                    role="textbox",
                    label=placeholder,
                ))
            elif aria_label:
                name = sanitize_name(aria_label)
                add_locator(LocatorInfo(
                    name=f"{name}Input",
                    selector_type="label",
                    selector_value=aria_label,
                    element_type="input",
                    label=aria_label,
                ))

    # Extract select elements
    select_pattern = re.compile(r'<select[^>]*>', re.IGNORECASE)
    for match in select_pattern.finditer(html):
        full_tag = match.group(0)
        select_id = _extract_attr(full_tag, "id")
        testid = _extract_attr(full_tag, "data-testid")
        aria_label = _extract_attr(full_tag, "aria-label")

        label_text = ""
        if select_id:
            label_match = re.search(
                rf'<label[^>]*for=["\']?{re.escape(select_id)}["\']?[^>]*>(.*?)</label>',
                html, re.IGNORECASE | re.DOTALL,
            )
            if label_match:
                label_text = re.sub(r"<[^>]+>", "", label_match.group(1)).strip()

        selector_label = label_text or aria_label or testid or "select"
        name = sanitize_name(selector_label)
        if label_text:
            add_locator(LocatorInfo(
                name=f"{name}Select",
                selector_type="label",
                selector_value=label_text,
                element_type="input",
                label=label_text,
            ))
        elif testid:
            add_locator(LocatorInfo(
                name=f"{name}Select",
                selector_type="testid",
                selector_value=testid,
                element_type="input",
                testid=testid,
            ))

    # Extract headings
    heading_pattern = re.compile(
        r'<h([1-6])[^>]*>(.*?)</h\1>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in heading_pattern.finditer(html):
        level = match.group(1)
        text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if text:
            name = sanitize_name(text)
            add_locator(LocatorInfo(
                name=f"{name}Heading",
                selector_type="role",
                selector_value=f"heading[name='{text}']",
                element_type="heading",
                role="heading",
                label=text,
            ))

    # Extract elements with data-testid
    testid_pattern = re.compile(r'data-testid=["\']([^"\']+)["\']', re.IGNORECASE)
    existing_testids = {loc.testid for loc in locators if loc.testid}
    for match in testid_pattern.finditer(html):
        testid = match.group(1)
        if testid not in existing_testids:
            name = sanitize_name(testid)
            add_locator(LocatorInfo(
                name=f"{name}Element",
                selector_type="testid",
                selector_value=testid,
                element_type="generic",
                testid=testid,
            ))

    return locators


def _extract_attr(tag: str, attr_name: str) -> str:
    """Extract attribute value from an HTML tag string."""
    match = re.search(rf'{attr_name}=["\']([^"\']*)["\']', tag, re.IGNORECASE)
    return match.group(1) if match else ""


def generate_page_object_ts(pom: PageObjectModel, base_class: str = "BasePage") -> str:
    """Generate TypeScript Page Object class."""
    lines = []

    # Imports
    lines.append(f'import {{ type Page, type Locator, expect }} from "@playwright/test";')
    if base_class != "Page":
        lines.append(f'import {{ {base_class} }} from "../{base_class.lower().replace("page", "-page")}";')
    lines.append("")

    # Class definition
    lines.append(f"export class {pom.name} extends {base_class} {{")
    lines.append("")

    # Locator declarations
    lines.append("  // --- Locators ---")
    for loc in pom.locators:
        lines.append(f"  readonly {loc.name}: Locator;")
    lines.append("")

    # Constructor
    lines.append("  constructor(page: Page) {")
    lines.append("    super(page);")
    for loc in pom.locators:
        lines.append(f"    this.{loc.name} = {loc.to_playwright_locator()};")
    lines.append("  }")
    lines.append("")

    # Navigation
    if pom.url_path:
        lines.append("  // --- Navigation ---")
        lines.append(f"  async goto(): Promise<void> {{")
        lines.append(f'    await this.page.goto("{pom.url_path}");')
        lines.append(f'    await this.page.waitForLoadState("networkidle");')
        lines.append(f"  }}")
        lines.append("")

    # Actions
    lines.append("  // --- Actions ---")
    for loc in pom.locators:
        if loc.element_type == "button":
            lines.append(f"  async click{loc.name[0].upper()}{loc.name[1:]}(): Promise<void> {{")
            lines.append(f"    await this.{loc.name}.click();")
            lines.append(f"  }}")
            lines.append("")
        elif loc.element_type == "input" and loc.role != "checkbox":
            param_name = loc.name.replace("Input", "").replace("Select", "")
            lines.append(f"  async fill{loc.name[0].upper()}{loc.name[1:]}(value: string): Promise<void> {{")
            lines.append(f"    await this.{loc.name}.fill(value);")
            lines.append(f"  }}")
            lines.append("")
        elif loc.element_type == "link":
            lines.append(f"  async click{loc.name[0].upper()}{loc.name[1:]}(): Promise<void> {{")
            lines.append(f"    await this.{loc.name}.click();")
            lines.append(f"  }}")
            lines.append("")

    # Assertions
    lines.append("  // --- Assertions ---")
    for loc in pom.locators:
        assert_name = loc.name[0].upper() + loc.name[1:]
        if loc.element_type == "heading":
            lines.append(f"  async expect{assert_name}Visible(): Promise<void> {{")
            lines.append(f"    await expect(this.{loc.name}).toBeVisible();")
            lines.append(f"  }}")
            lines.append("")
        elif loc.element_type == "button":
            lines.append(f"  async expect{assert_name}Enabled(): Promise<void> {{")
            lines.append(f"    await expect(this.{loc.name}).toBeEnabled();")
            lines.append(f"  }}")
            lines.append("")
            lines.append(f"  async expect{assert_name}Disabled(): Promise<void> {{")
            lines.append(f"    await expect(this.{loc.name}).toBeDisabled();")
            lines.append(f"  }}")
            lines.append("")

    # Generic page-loaded assertion
    lines.append("  async expectPageLoaded(): Promise<void> {")
    # Use the first heading or first locator
    heading_locs = [l for l in pom.locators if l.element_type == "heading"]
    if heading_locs:
        lines.append(f"    await expect(this.{heading_locs[0].name}).toBeVisible();")
    elif pom.locators:
        lines.append(f"    await expect(this.{pom.locators[0].name}).toBeVisible();")
    else:
        lines.append(f'    await this.page.waitForLoadState("networkidle");')
    lines.append("  }")
    lines.append("")

    lines.append("}")
    return "\n".join(lines)


def generate_spec_ts(pom: PageObjectModel) -> str:
    """Generate a starter spec file for the page object."""
    class_file = pom.name[0].lower() + re.sub(r"([A-Z])", r"-\1", pom.name[1:]).lower()
    if class_file.endswith("-page"):
        class_file = class_file  # keep as is
    else:
        class_file = class_file + "-page"

    lines = []
    lines.append(f'import {{ test, expect }} from "../fixtures";')
    lines.append(f'import {{ {pom.name} }} from "./{class_file}";')
    lines.append("")
    lines.append(f'test.describe("{pom.name.replace("Page", " Page")}", () => {{')
    lines.append(f"  let page: {pom.name};")
    lines.append("")
    lines.append(f"  test.beforeEach(async ({{ page: browserPage }}) => {{")
    lines.append(f"    page = new {pom.name}(browserPage);")
    if pom.url_path:
        lines.append(f"    await page.goto();")
    lines.append(f"  }});")
    lines.append("")

    lines.append(f'  test("page loads successfully", {{ tag: ["@smoke"] }}, async () => {{')
    lines.append(f"    await page.expectPageLoaded();")
    lines.append(f"  }});")
    lines.append("")

    # Generate a test for each heading
    for loc in pom.locators:
        if loc.element_type == "heading":
            assert_name = loc.name[0].upper() + loc.name[1:]
            lines.append(f'  test("displays {loc.label}", {{ tag: ["@critical"] }}, async () => {{')
            lines.append(f"    await page.expect{assert_name}Visible();")
            lines.append(f"  }});")
            lines.append("")

    lines.append("  // TODO: Add feature-specific tests")
    lines.append("});")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Playwright Page Object Model classes from HTML files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --html page.html --name ProductPage
  %(prog)s --html checkout.html --name CheckoutPage --output ./tests/checkout/
  %(prog)s --html login.html --name LoginPage --url /login --base-class BasePage
  %(prog)s --html page.html --name ProductPage --dry-run
        """,
    )
    parser.add_argument(
        "--html",
        type=Path,
        required=True,
        help="Path to the HTML file to analyze",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Page Object class name (e.g., ProductPage, CheckoutPage)",
    )
    parser.add_argument(
        "--url",
        default="",
        help="URL path for the page (e.g., /products, /checkout)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("."),
        help="Output directory for generated files (default: current directory)",
    )
    parser.add_argument(
        "--base-class",
        default="BasePage",
        help="Base class to extend (default: BasePage)",
    )
    parser.add_argument(
        "--with-spec",
        action="store_true",
        default=True,
        help="Also generate a starter spec file (default: true)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated code to stdout without writing files",
    )

    args = parser.parse_args()

    if not args.html.exists():
        print(f"Error: HTML file not found: {args.html}", file=sys.stderr)
        sys.exit(1)

    html_content = parse_html_file(args.html)
    locators = extract_locators(html_content)

    if not locators:
        print("Warning: No interactive elements found in the HTML.", file=sys.stderr)

    print(f"Found {len(locators)} elements:")
    for loc in locators:
        print(f"  {loc.element_type:10s} {loc.name} ({loc.selector_type})")
    print()

    pom = PageObjectModel(
        name=args.name,
        url_path=args.url,
        locators=locators,
    )

    # Generate page object
    page_ts = generate_page_object_ts(pom, base_class=args.base_class)

    # Generate file name from class name
    file_name = args.name[0].lower() + re.sub(r"([A-Z])", r"-\1", args.name[1:]).lower()
    if not file_name.endswith("-page"):
        file_name += "-page"

    if args.dry_run:
        print(f"=== {file_name}.ts ===")
        print(page_ts)
        if args.with_spec:
            print(f"\n=== {file_name.replace('-page', '')}.spec.ts ===")
            print(generate_spec_ts(pom))
    else:
        output_dir = args.output.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        page_file = output_dir / f"{file_name}.ts"
        page_file.write_text(page_ts, encoding="utf-8")
        print(f"Created: {page_file}")

        if args.with_spec:
            spec_file = output_dir / f"{file_name.replace('-page', '')}.spec.ts"
            spec_file.write_text(generate_spec_ts(pom), encoding="utf-8")
            print(f"Created: {spec_file}")

    print(f"\nGenerated Page Object: {args.name} with {len(locators)} locators")


if __name__ == "__main__":
    main()
