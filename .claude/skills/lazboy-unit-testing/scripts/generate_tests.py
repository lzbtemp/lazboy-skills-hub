#!/usr/bin/env python3
"""
Unit Test Generator

Parses source files to extract exported functions and classes, then generates
test file scaffolds with appropriate test structure.

Usage:
    python generate_tests.py --source src/utils.ts --framework jest
    python generate_tests.py --source app/services.py --framework pytest
    python generate_tests.py --source src/helpers.js --framework jest --output tests/
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FunctionInfo:
    name: str
    params: list[str]
    return_type: Optional[str]
    is_async: bool
    is_exported: bool
    is_method: bool
    class_name: Optional[str]


@dataclass
class ClassInfo:
    name: str
    methods: list[FunctionInfo]
    is_exported: bool


# --- Parsers ---


def parse_javascript(source: str) -> tuple[list[FunctionInfo], list[ClassInfo]]:
    """Parse JavaScript/TypeScript file for exported functions and classes."""
    functions = []
    classes = []

    # Remove multi-line comments
    source_clean = re.sub(r"/\*[\s\S]*?\*/", "", source)
    # Remove single-line comments
    source_clean = re.sub(r"//.*$", "", source_clean, flags=re.MULTILINE)

    # Match exported functions
    # export function name(params): return_type
    # export async function name(params): Promise<return_type>
    # export const name = (params) =>
    # export const name = async (params) =>
    func_patterns = [
        # export function / export async function
        r"export\s+(?P<async>async\s+)?function\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)(?:\s*:\s*(?P<return>[^{]+?))?(?:\s*\{)",
        # export const name = function / arrow
        r"export\s+const\s+(?P<name>\w+)\s*=\s*(?P<async>async\s+)?(?:function\s*)?\((?P<params>[^)]*)\)(?:\s*:\s*(?P<return>[^=>{]+?))?\s*=>",
        # Named export function (non-default)
        r"(?:^|\n)\s*(?P<async>async\s+)?function\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)(?:\s*:\s*(?P<return>[^{]+?))?(?:\s*\{)",
    ]

    for pattern in func_patterns:
        for match in re.finditer(pattern, source_clean):
            name = match.group("name")
            params_str = match.group("params").strip()
            params = [p.strip().split(":")[0].strip().split("=")[0].strip()
                      for p in params_str.split(",") if p.strip()] if params_str else []
            return_type = match.group("return").strip() if match.group("return") else None
            is_async = bool(match.group("async"))
            is_exported = "export" in source_clean[max(0, match.start() - 20):match.start() + 10]

            functions.append(FunctionInfo(
                name=name,
                params=params,
                return_type=return_type,
                is_async=is_async,
                is_exported=is_exported,
                is_method=False,
                class_name=None,
            ))

    # Match exported classes
    class_pattern = r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{"
    for class_match in re.finditer(class_pattern, source_clean):
        class_name = class_match.group(1)
        is_exported = "export" in source_clean[max(0, class_match.start() - 10):class_match.start() + 5]

        # Find methods within the class body (simplified)
        class_start = class_match.end()
        # Find matching closing brace (simplified -- counts braces)
        brace_count = 1
        pos = class_start
        while pos < len(source_clean) and brace_count > 0:
            if source_clean[pos] == "{":
                brace_count += 1
            elif source_clean[pos] == "}":
                brace_count -= 1
            pos += 1
        class_body = source_clean[class_start:pos]

        methods = []
        method_pattern = r"(?P<async>async\s+)?(?P<name>\w+)\s*\((?P<params>[^)]*)\)(?:\s*:\s*(?P<return>[^{]+?))?\s*\{"
        for method_match in re.finditer(method_pattern, class_body):
            method_name = method_match.group("name")
            if method_name in ("constructor", "if", "for", "while", "switch"):
                continue
            params_str = method_match.group("params").strip()
            params = [p.strip().split(":")[0].strip()
                      for p in params_str.split(",") if p.strip()] if params_str else []
            methods.append(FunctionInfo(
                name=method_name,
                params=params,
                return_type=method_match.group("return"),
                is_async=bool(method_match.group("async")),
                is_exported=False,
                is_method=True,
                class_name=class_name,
            ))

        classes.append(ClassInfo(name=class_name, methods=methods, is_exported=is_exported))

    # Check for named exports at the bottom
    export_pattern = r"export\s*\{([^}]+)\}"
    for export_match in re.finditer(export_pattern, source_clean):
        exported_names = {n.strip().split(" as ")[0].strip()
                         for n in export_match.group(1).split(",")}
        for func in functions:
            if func.name in exported_names:
                func.is_exported = True
        for cls in classes:
            if cls.name in exported_names:
                cls.is_exported = True

    # Filter to exported only
    functions = [f for f in functions if f.is_exported]
    classes = [c for c in classes if c.is_exported]

    return functions, classes


def parse_python(source: str) -> tuple[list[FunctionInfo], list[ClassInfo]]:
    """Parse Python file for functions and classes."""
    functions = []
    classes = []

    # Remove docstrings and comments
    source_clean = re.sub(r'"""[\s\S]*?"""', '""""""', source)
    source_clean = re.sub(r"'''[\s\S]*?'''", "''''''", source_clean)
    source_clean = re.sub(r"#.*$", "", source_clean, flags=re.MULTILINE)

    # Top-level functions
    func_pattern = r"^(?P<async>async\s+)?def\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)(?:\s*->\s*(?P<return>[^:]+))?\s*:"
    for match in re.finditer(func_pattern, source_clean, re.MULTILINE):
        name = match.group("name")
        if name.startswith("_"):
            continue  # Skip private functions

        params_str = match.group("params").strip()
        params = []
        if params_str:
            for p in params_str.split(","):
                param_name = p.strip().split(":")[0].split("=")[0].strip()
                if param_name and param_name != "self" and param_name != "cls":
                    params.append(param_name)

        functions.append(FunctionInfo(
            name=name,
            params=params,
            return_type=match.group("return").strip() if match.group("return") else None,
            is_async=bool(match.group("async")),
            is_exported=True,  # In Python, all top-level functions are "exported"
            is_method=False,
            class_name=None,
        ))

    # Classes
    class_pattern = r"^class\s+(\w+)(?:\([^)]*\))?\s*:"
    for class_match in re.finditer(class_pattern, source_clean, re.MULTILINE):
        class_name = class_match.group(1)
        if class_name.startswith("_"):
            continue

        # Find indented methods
        class_start = class_match.end()
        methods = []
        method_pattern = r"^\s{4}(?P<async>async\s+)?def\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)(?:\s*->\s*(?P<return>[^:]+))?\s*:"
        for method_match in re.finditer(method_pattern, source_clean[class_start:], re.MULTILINE):
            method_name = method_match.group("name")
            if method_name.startswith("_") and method_name != "__init__":
                continue

            params_str = method_match.group("params").strip()
            params = []
            if params_str:
                for p in params_str.split(","):
                    param_name = p.strip().split(":")[0].split("=")[0].strip()
                    if param_name and param_name not in ("self", "cls"):
                        params.append(param_name)

            methods.append(FunctionInfo(
                name=method_name,
                params=params,
                return_type=method_match.group("return"),
                is_async=bool(method_match.group("async")),
                is_exported=False,
                is_method=True,
                class_name=class_name,
            ))

        classes.append(ClassInfo(name=class_name, methods=methods, is_exported=True))

    return functions, classes


# --- Generators ---


def generate_jest_tests(
    source_path: str,
    functions: list[FunctionInfo],
    classes: list[ClassInfo],
) -> str:
    """Generate Jest/Vitest test file."""
    source_name = Path(source_path).stem
    import_path = f"../{source_path}" if not source_path.startswith(".") else source_path
    # Remove extension for import
    import_path = re.sub(r"\.(ts|tsx|js|jsx)$", "", import_path)

    lines = []

    # Imports
    all_exports = [f.name for f in functions] + [c.name for c in classes]
    if all_exports:
        imports = ", ".join(all_exports)
        lines.append(f"import {{ {imports} }} from '{import_path}';")
    lines.append("")

    # Function tests
    for func in functions:
        lines.append(f"describe('{func.name}', () => {{")

        # Basic test
        params_str = ", ".join(_get_js_test_value(p) for p in func.params)
        if func.is_async:
            lines.append(f"  it('should return expected result', async () => {{")
            lines.append(f"    // Arrange")
            for param in func.params:
                lines.append(f"    const {param} = {_get_js_test_value(param)};")
            lines.append(f"")
            lines.append(f"    // Act")
            lines.append(f"    const result = await {func.name}({', '.join(func.params)});")
            lines.append(f"")
            lines.append(f"    // Assert")
            lines.append(f"    expect(result).toBeDefined();")
            lines.append(f"    // TODO: Add specific assertions")
            lines.append(f"  }});")
        else:
            lines.append(f"  it('should return expected result', () => {{")
            lines.append(f"    // Arrange")
            for param in func.params:
                lines.append(f"    const {param} = {_get_js_test_value(param)};")
            lines.append(f"")
            lines.append(f"    // Act")
            lines.append(f"    const result = {func.name}({', '.join(func.params)});")
            lines.append(f"")
            lines.append(f"    // Assert")
            lines.append(f"    expect(result).toBeDefined();")
            lines.append(f"    // TODO: Add specific assertions")
            lines.append(f"  }});")

        # Edge case test
        lines.append(f"")
        lines.append(f"  it('should handle edge cases', () => {{")
        lines.append(f"    // TODO: Test with edge case inputs")
        lines.append(f"    // - empty strings, zero, null, undefined")
        lines.append(f"    // - boundary values")
        lines.append(f"    // - invalid inputs")
        lines.append(f"  }});")

        # Error test
        if func.is_async:
            lines.append(f"")
            lines.append(f"  it('should handle errors', async () => {{")
            lines.append(f"    // TODO: Test error scenarios")
            lines.append(f"    // await expect({func.name}(invalidInput)).rejects.toThrow();")
            lines.append(f"  }});")

        lines.append(f"}});")
        lines.append(f"")

    # Class tests
    for cls in classes:
        lines.append(f"describe('{cls.name}', () => {{")
        lines.append(f"  let instance: {cls.name};")
        lines.append(f"")
        lines.append(f"  beforeEach(() => {{")
        lines.append(f"    instance = new {cls.name}();")
        lines.append(f"    // TODO: Provide constructor arguments if needed")
        lines.append(f"  }});")

        for method in cls.methods:
            if method.name == "__init__" or method.name == "constructor":
                continue

            lines.append(f"")
            lines.append(f"  describe('{method.name}', () => {{")

            if method.is_async:
                lines.append(f"    it('should return expected result', async () => {{")
                for param in method.params:
                    lines.append(f"      const {param} = {_get_js_test_value(param)};")
                lines.append(f"      const result = await instance.{method.name}({', '.join(method.params)});")
                lines.append(f"      expect(result).toBeDefined();")
                lines.append(f"      // TODO: Add specific assertions")
                lines.append(f"    }});")
            else:
                lines.append(f"    it('should return expected result', () => {{")
                for param in method.params:
                    lines.append(f"      const {param} = {_get_js_test_value(param)};")
                lines.append(f"      const result = instance.{method.name}({', '.join(method.params)});")
                lines.append(f"      expect(result).toBeDefined();")
                lines.append(f"      // TODO: Add specific assertions")
                lines.append(f"    }});")

            lines.append(f"  }});")

        lines.append(f"}});")
        lines.append(f"")

    return "\n".join(lines)


def generate_pytest_tests(
    source_path: str,
    functions: list[FunctionInfo],
    classes: list[ClassInfo],
) -> str:
    """Generate pytest test file."""
    source_module = Path(source_path).stem
    # Build import path from file path
    import_parts = Path(source_path).with_suffix("").parts
    import_path = ".".join(import_parts)

    lines = []
    lines.append("import pytest")

    # Imports
    func_names = [f.name for f in functions]
    class_names = [c.name for c in classes]
    all_imports = func_names + class_names
    if all_imports:
        lines.append(f"from {import_path} import {', '.join(all_imports)}")

    has_async = any(f.is_async for f in functions) or any(
        m.is_async for c in classes for m in c.methods
    )
    if has_async:
        lines.append("")
        lines.append("pytestmark = pytest.mark.asyncio")

    lines.append("")
    lines.append("")

    # Function tests
    for func in functions:
        # Basic test
        if func.is_async:
            lines.append(f"class Test{_to_pascal(func.name)}:")
            lines.append(f"    async def test_returns_expected_result(self):")
        else:
            lines.append(f"class Test{_to_pascal(func.name)}:")
            lines.append(f"    def test_returns_expected_result(self):")

        lines.append(f"        # Arrange")
        for param in func.params:
            lines.append(f"        {param} = {_get_py_test_value(param)}")
        lines.append(f"")
        lines.append(f"        # Act")
        if func.is_async:
            lines.append(f"        result = await {func.name}({', '.join(func.params)})")
        else:
            lines.append(f"        result = {func.name}({', '.join(func.params)})")
        lines.append(f"")
        lines.append(f"        # Assert")
        lines.append(f"        assert result is not None")
        lines.append(f"        # TODO: Add specific assertions")
        lines.append(f"")

        # Edge case test
        lines.append(f"    def test_handles_edge_cases(self):")
        lines.append(f"        # TODO: Test with edge case inputs")
        lines.append(f"        # - empty strings, zero, None")
        lines.append(f"        # - boundary values")
        lines.append(f"        # - invalid inputs")
        lines.append(f"        pass")
        lines.append(f"")

        # Error test
        lines.append(f"    def test_raises_on_invalid_input(self):")
        lines.append(f"        # TODO: Test error scenarios")
        lines.append(f"        # with pytest.raises(ValueError):")
        lines.append(f"        #     {func.name}(invalid_input)")
        lines.append(f"        pass")
        lines.append(f"")
        lines.append(f"")

    # Class tests
    for cls in classes:
        lines.append(f"class Test{cls.name}:")
        lines.append(f"    @pytest.fixture")
        lines.append(f"    def instance(self):")
        lines.append(f"        # TODO: Provide constructor arguments if needed")
        lines.append(f"        return {cls.name}()")
        lines.append(f"")

        for method in cls.methods:
            if method.name == "__init__":
                continue

            if method.is_async:
                lines.append(f"    async def test_{method.name}(self, instance):")
            else:
                lines.append(f"    def test_{method.name}(self, instance):")

            lines.append(f"        # Arrange")
            for param in method.params:
                lines.append(f"        {param} = {_get_py_test_value(param)}")
            lines.append(f"")
            lines.append(f"        # Act")
            if method.is_async:
                lines.append(f"        result = await instance.{method.name}({', '.join(method.params)})")
            else:
                lines.append(f"        result = instance.{method.name}({', '.join(method.params)})")
            lines.append(f"")
            lines.append(f"        # Assert")
            lines.append(f"        assert result is not None")
            lines.append(f"        # TODO: Add specific assertions")
            lines.append(f"")

        lines.append(f"")

    return "\n".join(lines)


def _to_pascal(name: str) -> str:
    """Convert snake_case or camelCase to PascalCase."""
    # Handle snake_case
    if "_" in name:
        return "".join(word.capitalize() for word in name.split("_"))
    # Handle camelCase
    return name[0].upper() + name[1:]


def _get_js_test_value(param_name: str) -> str:
    """Infer a reasonable test value from parameter name."""
    name_lower = param_name.lower()
    if any(k in name_lower for k in ("id", "uuid")):
        return "'test-123'"
    if any(k in name_lower for k in ("name", "title", "label")):
        return f"'test-{param_name}'"
    if any(k in name_lower for k in ("email",)):
        return "'test@example.com'"
    if any(k in name_lower for k in ("url", "path", "href")):
        return "'https://example.com'"
    if any(k in name_lower for k in ("count", "num", "amount", "total", "size", "length", "index")):
        return "1"
    if any(k in name_lower for k in ("flag", "enabled", "active", "visible", "is_")):
        return "true"
    if any(k in name_lower for k in ("items", "list", "array", "data")):
        return "[]"
    if any(k in name_lower for k in ("options", "config", "params", "settings")):
        return "{}"
    if any(k in name_lower for k in ("callback", "handler", "fn", "on")):
        return "jest.fn()"
    return f"'test-value'"


def _get_py_test_value(param_name: str) -> str:
    """Infer a reasonable test value from parameter name."""
    name_lower = param_name.lower()
    if any(k in name_lower for k in ("id", "uuid")):
        return '"test-123"'
    if any(k in name_lower for k in ("name", "title", "label")):
        return f'"test-{param_name}"'
    if any(k in name_lower for k in ("email",)):
        return '"test@example.com"'
    if any(k in name_lower for k in ("url", "path")):
        return '"https://example.com"'
    if any(k in name_lower for k in ("count", "num", "amount", "total", "size", "length", "index")):
        return "1"
    if any(k in name_lower for k in ("flag", "enabled", "active", "visible")):
        return "True"
    if any(k in name_lower for k in ("items", "list", "data")):
        return "[]"
    if any(k in name_lower for k in ("options", "config", "params", "settings")):
        return "{}"
    return f'"test-value"'


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate unit test scaffolds from source files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source src/utils.ts --framework jest
  %(prog)s --source app/services.py --framework pytest
  %(prog)s --source src/helpers.js --framework jest --output tests/
        """,
    )
    parser.add_argument(
        "--source", "-s", required=True,
        help="Source file to generate tests for",
    )
    parser.add_argument(
        "--framework", "-f", required=True,
        choices=["jest", "vitest", "pytest"],
        help="Test framework to generate for",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: same directory as source)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Error: Source file not found: {args.source}")
        sys.exit(1)

    with open(args.source, "r") as f:
        source = f.read()

    # Detect language
    ext = Path(args.source).suffix.lower()
    if ext in (".py",):
        language = "python"
    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        language = "javascript"
    else:
        print(f"Warning: Unknown file extension {ext}, attempting JavaScript parsing")
        language = "javascript"

    # Parse
    if language == "python":
        functions, classes = parse_python(source)
    else:
        functions, classes = parse_javascript(source)

    if not functions and not classes:
        print(f"No exported functions or classes found in {args.source}")
        sys.exit(0)

    print(f"Found {len(functions)} functions and {len(classes)} classes")

    # Generate
    if args.framework in ("jest", "vitest"):
        test_content = generate_jest_tests(args.source, functions, classes)
        source_stem = Path(args.source).stem
        test_ext = ".test" + Path(args.source).suffix
        test_filename = source_stem + test_ext
    else:
        test_content = generate_pytest_tests(args.source, functions, classes)
        source_stem = Path(args.source).stem
        test_filename = f"test_{source_stem}.py"

    # Output
    if args.output:
        os.makedirs(args.output, exist_ok=True)
        output_path = os.path.join(args.output, test_filename)
    else:
        output_path = os.path.join(os.path.dirname(args.source), test_filename)

    with open(output_path, "w") as f:
        f.write(test_content)

    print(f"Test file generated: {output_path}")
    print(f"  Functions: {', '.join(f.name for f in functions)}")
    print(f"  Classes: {', '.join(c.name for c in classes)}")


if __name__ == "__main__":
    main()
