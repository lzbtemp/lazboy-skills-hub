#!/usr/bin/env python3
"""
React Component Generator

Scaffolds a React component with TypeScript, optional test file,
Storybook stories, and barrel export.

Usage:
    python generate_component.py --name Button --props 'variant:string' 'size:string' 'disabled:boolean'
    python generate_component.py --name UserCard --props 'user:User' 'onEdit:() => void' --no-tests
    python generate_component.py --name Modal --props 'isOpen:boolean' 'onClose:() => void' 'title:string' --output src/components
"""

import argparse
import os
import re
import sys
from typing import NamedTuple


class PropDef(NamedTuple):
    name: str
    ts_type: str
    is_optional: bool
    default_value: str


def parse_prop(raw: str) -> PropDef:
    """
    Parse a prop definition string.

    Formats:
        'name:string'              -> required string prop
        'name?:string'             -> optional string prop
        'name:string=default'      -> optional string prop with default
        'onClick:() => void'       -> callback prop
        'items:Item[]'             -> array prop
    """
    # Split name from type
    parts = raw.split(":", 1)
    if len(parts) < 2:
        return PropDef(raw, "string", True, "")

    name = parts[0].strip()
    type_and_default = parts[1].strip()

    is_optional = name.endswith("?")
    if is_optional:
        name = name[:-1]

    # Check for default value
    default_value = ""
    if "=" in type_and_default and "=>" not in type_and_default:
        type_part, default_value = type_and_default.rsplit("=", 1)
        type_and_default = type_part.strip()
        default_value = default_value.strip()
        is_optional = True

    return PropDef(name, type_and_default, is_optional, default_value)


def to_pascal_case(name: str) -> str:
    """Convert string to PascalCase."""
    name = re.sub(r"[^a-zA-Z0-9]", " ", name)
    return "".join(word.capitalize() for word in name.split())


def to_kebab_case(name: str) -> str:
    """Convert PascalCase to kebab-case."""
    # Insert hyphens before uppercase letters
    result = re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()
    return re.sub(r"[^a-z0-9-]", "-", result)


def generate_component(
    name: str,
    props: list[PropDef],
    use_css_modules: bool = True,
) -> str:
    """Generate the React component file (.tsx)."""
    pascal_name = to_pascal_case(name)
    kebab_name = to_kebab_case(name)

    lines = []
    lines.append("import { type ReactNode } from 'react';")
    if use_css_modules:
        lines.append(f"import styles from './{pascal_name}.module.css';")
    lines.append("")

    # Props interface
    lines.append(f"export interface {pascal_name}Props {{")
    for prop in props:
        optional = "?" if prop.is_optional else ""
        lines.append(f"  /** TODO: describe {prop.name} */")
        lines.append(f"  {prop.name}{optional}: {prop.ts_type};")
    # Add children if not in props
    if not any(p.name == "children" for p in props):
        lines.append("  /** Component children */")
        lines.append("  children?: ReactNode;")
    lines.append("}")
    lines.append("")

    # Component function
    # Build destructured params
    param_parts = []
    for prop in props:
        if prop.default_value:
            param_parts.append(f"{prop.name} = {prop.default_value}")
        else:
            param_parts.append(prop.name)
    if not any(p.name == "children" for p in props):
        param_parts.append("children")

    params_str = ", ".join(param_parts)

    lines.append(f"export function {pascal_name}({{ {params_str} }}: {pascal_name}Props) {{")
    lines.append(f"  return (")

    if use_css_modules:
        lines.append(f"    <div className={{styles.root}}>")
    else:
        lines.append(f"    <div>")

    if not any(p.name == "children" for p in props):
        lines.append(f"      {{children}}")
    else:
        lines.append(f"      {{/* TODO: component content */}}")

    lines.append(f"    </div>")
    lines.append(f"  );")
    lines.append(f"}}")
    lines.append("")

    return "\n".join(lines)


def generate_test(name: str, props: list[PropDef]) -> str:
    """Generate the test file (.test.tsx)."""
    pascal_name = to_pascal_case(name)

    lines = []
    lines.append("import { render, screen } from '@testing-library/react';")
    lines.append("import userEvent from '@testing-library/user-event';")
    lines.append(f"import {{ {pascal_name} }} from './{pascal_name}';")
    lines.append("")

    # Build default props
    lines.append(f"const defaultProps: React.ComponentProps<typeof {pascal_name}> = {{")
    for prop in props:
        if prop.is_optional:
            continue
        default = _get_test_default(prop)
        lines.append(f"  {prop.name}: {default},")
    lines.append("};")
    lines.append("")

    # Helper render function
    lines.append(
        f"function renderComponent(overrides: Partial<React.ComponentProps<typeof {pascal_name}>> = {{}}) {{"
    )
    lines.append(f"  return render(<{pascal_name} {{...defaultProps}} {{...overrides}} />);")
    lines.append("}")
    lines.append("")

    # Test suite
    lines.append(f"describe('{pascal_name}', () => {{")

    # Render test
    lines.append(f"  it('renders without crashing', () => {{")
    lines.append(f"    renderComponent();")
    lines.append(f"  }});")
    lines.append("")

    # Children test
    if not any(p.name == "children" for p in props):
        lines.append(f"  it('renders children', () => {{")
        lines.append(f"    renderComponent({{ children: 'Hello World' }});")
        lines.append(f"    expect(screen.getByText('Hello World')).toBeInTheDocument();")
        lines.append(f"  }});")
        lines.append("")

    # Prop-specific tests
    for prop in props:
        if prop.ts_type.startswith("()") or "=>" in prop.ts_type:
            # Callback prop test
            lines.append(f"  it('calls {prop.name} when triggered', async () => {{")
            lines.append(f"    const {prop.name} = jest.fn();")
            lines.append(f"    renderComponent({{ {prop.name} }});")
            lines.append(f"    // TODO: trigger the interaction that calls {prop.name}")
            lines.append(f"    // expect({prop.name}).toHaveBeenCalled();")
            lines.append(f"  }});")
            lines.append("")
        elif prop.ts_type == "boolean":
            lines.append(f"  it('handles {prop.name} prop', () => {{")
            lines.append(f"    renderComponent({{ {prop.name}: true }});")
            lines.append(f"    // TODO: assert behavior when {prop.name} is true")
            lines.append(f"  }});")
            lines.append("")
        elif prop.ts_type == "string" and not prop.is_optional:
            lines.append(f"  it('renders {prop.name}', () => {{")
            lines.append(f"    renderComponent({{ {prop.name}: 'test-value' }});")
            lines.append(f"    // TODO: assert {prop.name} is rendered")
            lines.append(f"  }});")
            lines.append("")

    # Accessibility test
    lines.append(f"  it('meets accessibility requirements', async () => {{")
    lines.append(f"    const {{ container }} = renderComponent();")
    lines.append(f"    // TODO: Add axe accessibility check")
    lines.append(f"    // const results = await axe(container);")
    lines.append(f"    // expect(results).toHaveNoViolations();")
    lines.append(f"  }});")

    lines.append("});")
    lines.append("")

    return "\n".join(lines)


def generate_stories(name: str, props: list[PropDef]) -> str:
    """Generate the Storybook stories file (.stories.tsx)."""
    pascal_name = to_pascal_case(name)

    lines = []
    lines.append("import type { Meta, StoryObj } from '@storybook/react';")
    lines.append(f"import {{ {pascal_name} }} from './{pascal_name}';")
    lines.append("")

    lines.append(f"const meta: Meta<typeof {pascal_name}> = {{")
    lines.append(f"  title: 'Components/{pascal_name}',")
    lines.append(f"  component: {pascal_name},")
    lines.append(f"  tags: ['autodocs'],")
    lines.append(f"  argTypes: {{")
    for prop in props:
        if prop.ts_type == "string":
            lines.append(f"    {prop.name}: {{ control: 'text' }},")
        elif prop.ts_type == "boolean":
            lines.append(f"    {prop.name}: {{ control: 'boolean' }},")
        elif prop.ts_type.startswith("'") or "|" in prop.ts_type:
            # Union type -- use radio/select control
            options = [o.strip().strip("'\"") for o in prop.ts_type.split("|")]
            options_str = ", ".join(f"'{o}'" for o in options)
            lines.append(
                f"    {prop.name}: {{ control: 'radio', options: [{options_str}] }},"
            )
        elif prop.ts_type == "number":
            lines.append(f"    {prop.name}: {{ control: 'number' }},")
    lines.append(f"  }},")
    lines.append(f"}};")
    lines.append("")
    lines.append(f"export default meta;")
    lines.append(f"type Story = StoryObj<typeof {pascal_name}>;")
    lines.append("")

    # Default story
    lines.append("export const Default: Story = {")
    lines.append("  args: {")
    for prop in props:
        if prop.is_optional:
            continue
        default = _get_story_default(prop)
        lines.append(f"    {prop.name}: {default},")
    if not any(p.name == "children" for p in props):
        lines.append(f"    children: '{pascal_name} content',")
    lines.append("  },")
    lines.append("};")
    lines.append("")

    # Variant stories for common prop patterns
    for prop in props:
        if prop.ts_type == "boolean":
            variant_name = to_pascal_case(prop.name)
            lines.append(f"export const With{variant_name}: Story = {{")
            lines.append(f"  args: {{")
            lines.append(f"    ...Default.args,")
            lines.append(f"    {prop.name}: true,")
            lines.append(f"  }},")
            lines.append(f"}};")
            lines.append("")
        elif "|" in prop.ts_type and "=>" not in prop.ts_type:
            options = [o.strip().strip("'\"") for o in prop.ts_type.split("|")]
            for option in options[:3]:  # Limit to first 3 variants
                variant_name = to_pascal_case(option)
                lines.append(f"export const {variant_name}: Story = {{")
                lines.append(f"  args: {{")
                lines.append(f"    ...Default.args,")
                lines.append(f"    {prop.name}: '{option}',")
                lines.append(f"  }},")
                lines.append(f"}};")
                lines.append("")

    return "\n".join(lines)


def generate_css_module(name: str) -> str:
    """Generate a CSS module file."""
    return f""".root {{
  /* {to_pascal_case(name)} styles */
}}
"""


def generate_barrel_export(name: str) -> str:
    """Generate the barrel export (index.ts)."""
    pascal_name = to_pascal_case(name)
    return f"export {{ {pascal_name} }} from './{pascal_name}';\nexport type {{ {pascal_name}Props }} from './{pascal_name}';\n"


def _get_test_default(prop: PropDef) -> str:
    """Get a reasonable test default value for a prop type."""
    ts_type = prop.ts_type.strip()
    if ts_type == "string":
        return f"'test-{prop.name}'"
    elif ts_type == "number":
        return "0"
    elif ts_type == "boolean":
        return "false"
    elif ts_type.startswith("()") or "=>" in ts_type:
        return "jest.fn()"
    elif ts_type.endswith("[]"):
        return "[]"
    elif "|" in ts_type and "=>" not in ts_type:
        first_option = ts_type.split("|")[0].strip().strip("'\"")
        return f"'{first_option}'"
    else:
        return f"{{}} as any  // TODO: provide {ts_type} value"


def _get_story_default(prop: PropDef) -> str:
    """Get a reasonable Storybook default value for a prop type."""
    ts_type = prop.ts_type.strip()
    if ts_type == "string":
        return f"'Example {prop.name}'"
    elif ts_type == "number":
        return "42"
    elif ts_type == "boolean":
        return "false"
    elif ts_type.startswith("()") or "=>" in ts_type:
        return f"() => console.log('{prop.name} called')"
    elif ts_type.endswith("[]"):
        return "[]"
    elif "|" in ts_type and "=>" not in ts_type:
        first_option = ts_type.split("|")[0].strip().strip("'\"")
        return f"'{first_option}'"
    else:
        return "undefined as any  // TODO"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a React component scaffold with TypeScript",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prop format: 'name:type', 'name?:type' (optional), 'name:type=default'

Type examples:
  string, number, boolean, ReactNode
  'primary' | 'secondary'    (union type)
  () => void                  (callback)
  (value: string) => void     (callback with args)
  User                        (custom type)
  Item[]                      (array)

Examples:
  %(prog)s --name Button --props 'variant:string=primary' 'size:string' 'disabled?:boolean'
  %(prog)s --name Modal --props 'isOpen:boolean' 'onClose:() => void' 'title:string'
  %(prog)s --name DataTable --props 'data:Row[]' 'onSort:(column: string) => void' --no-stories
        """,
    )
    parser.add_argument(
        "--name", "-n", required=True,
        help="Component name in PascalCase (e.g., Button, UserCard, DataTable)",
    )
    parser.add_argument(
        "--props", "-p", nargs="*", default=[],
        help="Prop definitions in 'name:type' format",
    )
    parser.add_argument(
        "--output", "-o", default="./src/components",
        help="Base output directory (default: ./src/components)",
    )
    parser.add_argument(
        "--no-tests", action="store_true",
        help="Skip generating test file",
    )
    parser.add_argument(
        "--no-stories", action="store_true",
        help="Skip generating Storybook stories file",
    )
    parser.add_argument(
        "--no-css-module", action="store_true",
        help="Skip generating CSS module file",
    )
    parser.add_argument(
        "--flat", action="store_true",
        help="Generate files without a component subdirectory",
    )

    args = parser.parse_args()

    pascal_name = to_pascal_case(args.name)
    props = [parse_prop(p) for p in args.props]

    # Create output directory
    if args.flat:
        component_dir = args.output
    else:
        component_dir = os.path.join(args.output, pascal_name)
    os.makedirs(component_dir, exist_ok=True)

    # Generate files
    files_created = []

    # Component file
    component_path = os.path.join(component_dir, f"{pascal_name}.tsx")
    with open(component_path, "w") as f:
        f.write(generate_component(args.name, props, not args.no_css_module))
    files_created.append(component_path)

    # CSS module
    if not args.no_css_module:
        css_path = os.path.join(component_dir, f"{pascal_name}.module.css")
        with open(css_path, "w") as f:
            f.write(generate_css_module(args.name))
        files_created.append(css_path)

    # Test file
    if not args.no_tests:
        test_path = os.path.join(component_dir, f"{pascal_name}.test.tsx")
        with open(test_path, "w") as f:
            f.write(generate_test(args.name, props))
        files_created.append(test_path)

    # Stories file
    if not args.no_stories:
        stories_path = os.path.join(component_dir, f"{pascal_name}.stories.tsx")
        with open(stories_path, "w") as f:
            f.write(generate_stories(args.name, props))
        files_created.append(stories_path)

    # Barrel export
    if not args.flat:
        index_path = os.path.join(component_dir, "index.ts")
        with open(index_path, "w") as f:
            f.write(generate_barrel_export(args.name))
        files_created.append(index_path)

    # Summary
    print(f"Generated {pascal_name} component:")
    for f_path in files_created:
        print(f"  {f_path}")

    if props:
        print(f"\nProps ({len(props)}):")
        for prop in props:
            opt = " (optional)" if prop.is_optional else " (required)"
            default = f" = {prop.default_value}" if prop.default_value else ""
            print(f"  {prop.name}: {prop.ts_type}{default}{opt}")


if __name__ == "__main__":
    main()
