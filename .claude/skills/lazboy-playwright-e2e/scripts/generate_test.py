#!/usr/bin/env python3
"""
Playwright Test Generator

Generates a Playwright test file scaffold with a page object and test cases
following best practices.

Usage:
    python generate_test.py --page Login --url /login \
        --interactions 'fill:Email:user@test.com' 'fill:Password:secret' 'click:Sign in' 'assert:Dashboard'
    python generate_test.py --page ProductList --url /products \
        --interactions 'click:Add to cart' 'assert:Cart updated'
    python generate_test.py --page Settings --url /settings --output tests/
"""

import argparse
import os
import re
import sys
from datetime import datetime
from typing import NamedTuple


class Interaction(NamedTuple):
    action: str       # click, fill, assert, navigate, check, uncheck, select, hover
    target: str       # Element name or text
    value: str = ""   # Value for fill/select actions


def parse_interaction(raw: str) -> Interaction:
    """
    Parse interaction string in format 'action:target[:value]'.

    Examples:
        'click:Submit'          -> Interaction('click', 'Submit')
        'fill:Email:user@test'  -> Interaction('fill', 'Email', 'user@test')
        'assert:Dashboard'      -> Interaction('assert', 'Dashboard')
        'select:Country:US'     -> Interaction('select', 'Country', 'US')
        'check:Remember me'     -> Interaction('check', 'Remember me')
    """
    parts = raw.split(":", 2)
    if len(parts) < 2:
        print(f"Warning: Invalid interaction format '{raw}'. Expected 'action:target[:value]'")
        return Interaction("click", raw)

    action = parts[0].strip().lower()
    target = parts[1].strip()
    value = parts[2].strip() if len(parts) > 2 else ""

    valid_actions = {"click", "fill", "assert", "navigate", "check", "uncheck", "select", "hover"}
    if action not in valid_actions:
        print(f"Warning: Unknown action '{action}'. Valid actions: {sorted(valid_actions)}")

    return Interaction(action, target, value)


def to_pascal_case(name: str) -> str:
    """Convert a string to PascalCase."""
    name = re.sub(r"[^a-zA-Z0-9]", " ", name)
    return "".join(word.capitalize() for word in name.split())


def to_camel_case(name: str) -> str:
    """Convert a string to camelCase."""
    pascal = to_pascal_case(name)
    return pascal[0].lower() + pascal[1:] if pascal else ""


def to_kebab_case(name: str) -> str:
    """Convert a string to kebab-case."""
    name = re.sub(r"[^a-zA-Z0-9]", " ", name)
    return "-".join(word.lower() for word in name.split())


def generate_locator_code(target: str) -> str:
    """Generate the best Playwright locator for a target element name."""
    target_lower = target.lower()

    # Form fields: use getByLabel
    form_keywords = {"email", "password", "username", "name", "phone", "address",
                     "search", "query", "message", "description", "title", "url"}
    if any(kw in target_lower for kw in form_keywords):
        return f"page.getByLabel('{target}')"

    # Buttons: use getByRole
    button_keywords = {"submit", "cancel", "save", "delete", "close", "ok",
                       "confirm", "sign", "log", "send", "create", "add", "remove",
                       "update", "edit", "reset", "back", "next", "continue"}
    if any(kw in target_lower for kw in button_keywords):
        return f"page.getByRole('button', {{ name: '{target}' }})"

    # Links
    link_keywords = {"link", "home", "about", "contact", "help", "more"}
    if any(kw in target_lower for kw in link_keywords):
        return f"page.getByRole('link', {{ name: '{target}' }})"

    # Headings
    if target_lower.startswith("heading:"):
        heading_text = target.split(":", 1)[1].strip()
        return f"page.getByRole('heading', {{ name: '{heading_text}' }})"

    # Default: use getByText for assertions, getByRole('button') for clicks
    return f"page.getByText('{target}')"


def generate_page_object(
    page_name: str,
    url_path: str,
    interactions: list[Interaction],
) -> str:
    """Generate TypeScript page object class."""
    class_name = to_pascal_case(page_name) + "Page"
    file_lines = []

    file_lines.append(f"import {{ type Locator, type Page, expect }} from '@playwright/test';")
    file_lines.append("")
    file_lines.append(f"export class {class_name} {{")
    file_lines.append(f"  readonly page: Page;")

    # Collect unique elements as locator properties
    elements: dict[str, tuple[str, str]] = {}  # varName -> (locator, target)
    for interaction in interactions:
        if interaction.action == "assert":
            continue
        var_name = to_camel_case(interaction.target)
        if var_name and var_name not in elements:
            locator = generate_locator_code(interaction.target)
            # Extract just the locator part for the constructor
            elements[var_name] = (locator.replace("page.", "this.page."), interaction.target)

    for var_name in elements:
        file_lines.append(f"  readonly {var_name}: Locator;")

    file_lines.append("")
    file_lines.append(f"  constructor(page: Page) {{")
    file_lines.append(f"    this.page = page;")

    for var_name, (locator, _) in elements.items():
        file_lines.append(f"    this.{var_name} = {locator};")

    file_lines.append(f"  }}")
    file_lines.append("")

    # goto method
    file_lines.append(f"  async goto(): Promise<void> {{")
    file_lines.append(f"    await this.page.goto('{url_path}');")
    file_lines.append(f"  }}")

    # Generate action methods
    action_methods: list[tuple[str, list[str]]] = []

    fill_actions = [i for i in interactions if i.action == "fill"]
    if fill_actions:
        method_lines = []
        params = []
        for fa in fill_actions:
            param_name = to_camel_case(fa.target)
            params.append(f"{param_name}: string")
        method_lines.append(
            f"  async fillForm({', '.join(params)}): Promise<void> {{"
        )
        for fa in fill_actions:
            var_name = to_camel_case(fa.target)
            method_lines.append(f"    await this.{var_name}.fill({var_name});")
        method_lines.append(f"  }}")
        action_methods.append(("fillForm", method_lines))

    click_actions = [i for i in interactions if i.action == "click"]
    for ca in click_actions:
        var_name = to_camel_case(ca.target)
        method_name = f"click{to_pascal_case(ca.target)}"
        method_lines = [
            f"  async {method_name}(): Promise<void> {{",
            f"    await this.{var_name}.click();",
            f"  }}",
        ]
        action_methods.append((method_name, method_lines))

    check_actions = [i for i in interactions if i.action in ("check", "uncheck")]
    for ca in check_actions:
        var_name = to_camel_case(ca.target)
        method_name = f"{ca.action}{to_pascal_case(ca.target)}"
        action = "check" if ca.action == "check" else "uncheck"
        method_lines = [
            f"  async {method_name}(): Promise<void> {{",
            f"    await this.{var_name}.{action}();",
            f"  }}",
        ]
        action_methods.append((method_name, method_lines))

    for _, method_lines in action_methods:
        file_lines.append("")
        file_lines.extend(method_lines)

    file_lines.append(f"}}")
    file_lines.append("")

    return "\n".join(file_lines)


def generate_test_file(
    page_name: str,
    url_path: str,
    interactions: list[Interaction],
    page_object_import_path: str,
) -> str:
    """Generate TypeScript test file."""
    class_name = to_pascal_case(page_name) + "Page"
    fixture_var = to_camel_case(page_name) + "Page"
    file_lines = []

    file_lines.append(f"import {{ test, expect }} from '@playwright/test';")
    file_lines.append(f"import {{ {class_name} }} from '{page_object_import_path}';")
    file_lines.append("")
    file_lines.append(f"test.describe('{page_name} Page', () => {{")
    file_lines.append(f"  let {fixture_var}: {class_name};")
    file_lines.append("")
    file_lines.append(f"  test.beforeEach(async ({{ page }}) => {{")
    file_lines.append(f"    {fixture_var} = new {class_name}(page);")
    file_lines.append(f"    await {fixture_var}.goto();")
    file_lines.append(f"  }});")
    file_lines.append("")

    # Test: page loads correctly
    file_lines.append(f"  test('should load {page_name.lower()} page', async ({{ page }}) => {{")
    file_lines.append(f"    await expect(page).toHaveURL(/{re.escape(url_path)}/);")
    file_lines.append(f"  }});")

    # Test: form fill and submit (if there are fill + click actions)
    fill_actions = [i for i in interactions if i.action == "fill"]
    click_actions = [i for i in interactions if i.action == "click"]
    assert_actions = [i for i in interactions if i.action == "assert"]

    if fill_actions and click_actions:
        file_lines.append("")
        file_lines.append(
            f"  test('should complete {page_name.lower()} form', async ({{ page }}) => {{"
        )
        for fa in fill_actions:
            locator = generate_locator_code(fa.target)
            value = fa.value or f"test-{to_kebab_case(fa.target)}"
            file_lines.append(f"    await {locator}.fill('{value}');")

        for ca in click_actions:
            locator = generate_locator_code(ca.target)
            file_lines.append(f"    await {locator}.click();")

        for aa in assert_actions:
            file_lines.append(f"    await expect(page.getByText('{aa.target}')).toBeVisible();")

        file_lines.append(f"  }});")

    # Test: individual assertions
    for aa in assert_actions:
        file_lines.append("")
        target_slug = to_kebab_case(aa.target)
        file_lines.append(
            f"  test('should display {aa.target.lower()}', async ({{ page }}) => {{"
        )
        file_lines.append(
            f"    await expect(page.getByText('{aa.target}')).toBeVisible();"
        )
        file_lines.append(f"  }});")

    # Test: error validation (if form)
    if fill_actions and click_actions:
        file_lines.append("")
        file_lines.append(
            f"  test('should show validation errors for empty form', async ({{ page }}) => {{"
        )
        for ca in click_actions:
            locator = generate_locator_code(ca.target)
            file_lines.append(f"    await {locator}.click();")
        file_lines.append(f"    // Verify validation messages appear")
        file_lines.append(
            f"    // TODO: Add specific validation error assertions"
        )
        file_lines.append(f"  }});")

    file_lines.append(f"}});")
    file_lines.append("")

    return "\n".join(file_lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Playwright test file scaffolds with page objects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interaction format: 'action:target[:value]'

Actions:
  click      Click an element         'click:Submit'
  fill       Fill a form field        'fill:Email:user@test.com'
  assert     Assert text is visible   'assert:Welcome back'
  check      Check a checkbox         'check:Remember me'
  uncheck    Uncheck a checkbox       'uncheck:Notifications'
  select     Select dropdown option   'select:Country:US'
  hover      Hover over element       'hover:Menu'

Examples:
  %(prog)s --page Login --url /login \\
    --interactions 'fill:Email:user@test.com' 'fill:Password:secret' \\
    'click:Sign in' 'assert:Dashboard'

  %(prog)s --page ProductList --url /products \\
    --interactions 'click:Add to cart' 'assert:Cart updated' \\
    --output tests/e2e/
        """,
    )
    parser.add_argument(
        "--page", "-p", required=True,
        help="Page name (e.g., Login, Dashboard, ProductList)",
    )
    parser.add_argument(
        "--url", "-u", required=True,
        help="URL path for the page (e.g., /login, /products)",
    )
    parser.add_argument(
        "--interactions", "-i", nargs="*", default=[],
        help="Interaction definitions in 'action:target[:value]' format",
    )
    parser.add_argument(
        "--output", "-o", default="./tests",
        help="Output directory (default: ./tests)",
    )

    args = parser.parse_args()

    # Parse interactions
    interactions = [parse_interaction(raw) for raw in args.interactions]

    # Derive file names
    page_kebab = to_kebab_case(args.page)
    pages_dir = os.path.join(args.output, "pages")
    specs_dir = os.path.join(args.output, "specs")
    os.makedirs(pages_dir, exist_ok=True)
    os.makedirs(specs_dir, exist_ok=True)

    page_object_file = os.path.join(pages_dir, f"{page_kebab}.page.ts")
    test_file = os.path.join(specs_dir, f"{page_kebab}.spec.ts")

    # Generate page object
    page_object_code = generate_page_object(args.page, args.url, interactions)
    with open(page_object_file, "w") as f:
        f.write(page_object_code)
    print(f"Page object created: {page_object_file}")

    # Generate test file
    import_path = f"../pages/{page_kebab}.page"
    test_code = generate_test_file(args.page, args.url, interactions, import_path)
    with open(test_file, "w") as f:
        f.write(test_code)
    print(f"Test file created:   {test_file}")

    # Summary
    print(f"\nGenerated files for '{args.page}' page:")
    print(f"  Page object: {page_object_file}")
    print(f"  Test file:   {test_file}")
    if interactions:
        print(f"  Interactions: {len(interactions)}")
        for i in interactions:
            val_str = f" = '{i.value}'" if i.value else ""
            print(f"    - {i.action}: {i.target}{val_str}")


if __name__ == "__main__":
    main()
