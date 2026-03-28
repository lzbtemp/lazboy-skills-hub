#!/usr/bin/env python3
"""Set up Python project tooling: pyproject.toml, pre-commit hooks, and CI workflow.

Generates or updates pyproject.toml with ruff, mypy/pyright, and pytest config.
Optionally creates pre-commit hooks and GitHub Actions CI workflow.

Usage:
    python setup_tooling.py /path/to/project
    python setup_tooling.py . --project-name my-service
    python setup_tooling.py /path/to/project --with-ci --with-precommit
"""

import argparse
import sys
from pathlib import Path
from textwrap import dedent


def detect_project_name(project_dir: Path) -> str:
    """Detect project name from existing config or directory name."""
    # Check existing pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            if line.strip().startswith("name"):
                # Extract name = "value"
                parts = line.split("=", 1)
                if len(parts) == 2:
                    return parts[1].strip().strip('"').strip("'")

    return project_dir.name


def detect_python_version(project_dir: Path) -> str:
    """Detect minimum Python version from project config."""
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8", errors="ignore")
        if "3.12" in content:
            return "3.12"
        if "3.11" in content:
            return "3.11"
    return "3.12"


def generate_pyproject_toml(
    project_name: str,
    python_version: str,
    description: str,
    src_layout: bool = True,
) -> str:
    """Generate a complete pyproject.toml with ruff, pyright, and pytest config."""
    module_name = project_name.replace("-", "_")

    return dedent(f"""\
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [project]
        name = "{project_name}"
        version = "0.1.0"
        description = "{description}"
        readme = "README.md"
        requires-python = ">={python_version}"
        license = "MIT"
        authors = [
            {{ name = "La-Z-Boy Engineering" }},
        ]
        dependencies = []

        [project.optional-dependencies]
        dev = [
            "pytest>=8.0",
            "pytest-asyncio>=0.23",
            "pytest-cov>=5.0",
            "ruff>=0.4",
            "pyright>=1.1",
            "pre-commit>=3.7",
        ]

        # ──────────────────────────────────────
        # Ruff — linter and formatter
        # ──────────────────────────────────────
        [tool.ruff]
        target-version = "py{python_version.replace('.', '')}"
        line-length = 100
        {"src = [\"src\"]" if src_layout else ""}

        [tool.ruff.lint]
        select = [
            "E",      # pycodestyle errors
            "W",      # pycodestyle warnings
            "F",      # pyflakes
            "I",      # isort
            "N",      # pep8-naming
            "UP",     # pyupgrade
            "B",      # flake8-bugbear
            "SIM",    # flake8-simplify
            "TCH",    # flake8-type-checking
            "RUF",    # ruff-specific rules
            "S",      # flake8-bandit (security)
            "PTH",    # flake8-use-pathlib
            "ERA",    # eradicate (commented-out code)
            "T20",    # flake8-print (no print statements)
            "ASYNC",  # flake8-async
        ]
        ignore = [
            "S101",   # assert used (needed in tests)
            "S104",   # binding to all interfaces (needed for containers)
        ]

        [tool.ruff.lint.per-file-ignores]
        "tests/**/*.py" = [
            "S101",   # assert in tests is fine
            "T20",    # print in tests is fine
        ]

        [tool.ruff.lint.isort]
        known-first-party = ["{module_name}"]

        [tool.ruff.format]
        quote-style = "double"
        indent-style = "space"
        docstring-code-format = true

        # ──────────────────────────────────────
        # Pyright — type checker
        # ──────────────────────────────────────
        [tool.pyright]
        pythonVersion = "{python_version}"
        typeCheckingMode = "standard"
        {"venvPath = \".\"\nvenv = \".venv\"" if not src_layout else ""}

        # ──────────────────────────────────────
        # Pytest — test runner
        # ──────────────────────────────────────
        [tool.pytest.ini_options]
        testpaths = ["tests"]
        python_files = ["test_*.py"]
        python_functions = ["test_*"]
        asyncio_mode = "auto"
        addopts = [
            "-ra",            # show summary of all non-passing tests
            "--strict-markers",
            "--strict-config",
            "-v",
            "--tb=short",
        ]
        markers = [
            "slow: marks tests as slow (deselect with '-m \"not slow\"')",
            "integration: marks integration tests",
        ]
        filterwarnings = [
            "error",          # treat warnings as errors
            "ignore::DeprecationWarning:pkg_resources",
        ]

        # ──────────────────────────────────────
        # Coverage
        # ──────────────────────────────────────
        [tool.coverage.run]
        source = ["{"src/" + module_name if src_layout else module_name}"]
        branch = true

        [tool.coverage.report]
        show_missing = true
        skip_empty = true
        fail_under = 80
        exclude_lines = [
            "pragma: no cover",
            "if TYPE_CHECKING:",
            "if __name__ == .__main__.",
            "@overload",
        ]
    """)


def generate_precommit_config(python_version: str) -> str:
    """Generate .pre-commit-config.yaml."""
    return dedent(f"""\
        # Pre-commit hooks for Python project
        # Install: pre-commit install
        # Run all: pre-commit run --all-files

        repos:
          # Ruff — fast linter and formatter
          - repo: https://github.com/astral-sh/ruff-pre-commit
            rev: v0.4.4
            hooks:
              - id: ruff
                args: [--fix, --exit-non-zero-on-fix]
              - id: ruff-format

          # Pyright — type checker
          - repo: https://github.com/RobertCraiworthy/pyright-python
            rev: v1.1.360
            hooks:
              - id: pyright
                additional_dependencies: []

          # General file hygiene
          - repo: https://github.com/pre-commit/pre-commit-hooks
            rev: v4.6.0
            hooks:
              - id: check-yaml
              - id: check-toml
              - id: end-of-file-fixer
              - id: trailing-whitespace
              - id: check-merge-conflict
              - id: check-added-large-files
                args: [--maxkb=500]
              - id: no-commit-to-branch
                args: [--branch, main, --branch, master]
              - id: check-json
              - id: detect-private-key

          # Security scanning
          - repo: https://github.com/Yelp/detect-secrets
            rev: v1.5.0
            hooks:
              - id: detect-secrets
                args: [--baseline, .secrets.baseline]
    """)


def generate_github_ci_workflow(project_name: str, python_version: str) -> str:
    """Generate GitHub Actions CI workflow."""
    return dedent(f"""\
        # CI workflow for {project_name}
        # Runs linting, type checking, and tests on every push and PR

        name: CI

        on:
          push:
            branches: [main]
          pull_request:
            branches: [main]

        permissions:
          contents: read

        jobs:
          lint:
            name: Lint & Format
            runs-on: ubuntu-latest
            steps:
              - uses: actions/checkout@v4

              - name: Install uv
                uses: astral-sh/setup-uv@v3

              - name: Set up Python
                run: uv python install {python_version}

              - name: Install dependencies
                run: uv sync --dev

              - name: Ruff check
                run: uv run ruff check .

              - name: Ruff format check
                run: uv run ruff format --check .

          typecheck:
            name: Type Check
            runs-on: ubuntu-latest
            steps:
              - uses: actions/checkout@v4

              - name: Install uv
                uses: astral-sh/setup-uv@v3

              - name: Set up Python
                run: uv python install {python_version}

              - name: Install dependencies
                run: uv sync --dev

              - name: Pyright
                run: uv run pyright

          test:
            name: Test
            runs-on: ubuntu-latest
            strategy:
              matrix:
                python-version: ["{python_version}"]
            steps:
              - uses: actions/checkout@v4

              - name: Install uv
                uses: astral-sh/setup-uv@v3

              - name: Set up Python ${{{{ matrix.python-version }}}}
                run: uv python install ${{{{ matrix.python-version }}}}

              - name: Install dependencies
                run: uv sync --dev

              - name: Run tests with coverage
                run: uv run pytest --cov --cov-report=xml --cov-report=term-missing

              - name: Upload coverage
                if: github.event_name == 'push' && github.ref == 'refs/heads/main'
                uses: actions/upload-artifact@v4
                with:
                  name: coverage-report
                  path: coverage.xml
    """)


def generate_conftest(project_name: str) -> str:
    """Generate tests/conftest.py with common fixtures."""
    module_name = project_name.replace("-", "_")
    return dedent(f"""\
        \"\"\"Shared test fixtures for {project_name}.\"\"\"

        import asyncio
        from collections.abc import AsyncGenerator, Generator

        import pytest


        @pytest.fixture(scope="session")
        def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
            \"\"\"Create a session-scoped event loop for async tests.\"\"\"
            loop = asyncio.new_event_loop()
            yield loop
            loop.close()


        @pytest.fixture
        def sample_data() -> dict[str, str]:
            \"\"\"Provide sample test data.\"\"\"
            return {{
                "name": "Test Item",
                "description": "A test item for unit tests",
            }}
    """)


def write_file(filepath: Path, content: str, dry_run: bool = False, overwrite: bool = False) -> bool:
    """Write content to file. Returns True if written."""
    if filepath.exists() and not overwrite:
        print(f"  SKIP (exists): {filepath}")
        return False

    if dry_run:
        print(f"  [DRY RUN] Would write: {filepath}")
        return False

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    status = "UPDATED" if filepath.exists() else "CREATED"
    print(f"  {status}: {filepath}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up Python project tooling: pyproject.toml with ruff/pyright/pytest, pre-commit hooks, CI workflow.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s . --project-name my-service
  %(prog)s /path/to/project --with-ci --with-precommit
  %(prog)s . --overwrite --dry-run
        """,
    )
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to the Python project directory",
    )
    parser.add_argument(
        "--project-name",
        default=None,
        help="Project name (default: auto-detected from pyproject.toml or directory name)",
    )
    parser.add_argument(
        "--description",
        default="A La-Z-Boy Python service",
        help="Project description for pyproject.toml",
    )
    parser.add_argument(
        "--python-version",
        default=None,
        help="Minimum Python version (default: auto-detected or 3.12)",
    )
    parser.add_argument(
        "--no-src-layout",
        action="store_true",
        help="Use flat layout instead of src/ layout",
    )
    parser.add_argument(
        "--with-precommit",
        action="store_true",
        default=True,
        help="Generate .pre-commit-config.yaml (default: true)",
    )
    parser.add_argument(
        "--no-precommit",
        action="store_true",
        help="Skip .pre-commit-config.yaml generation",
    )
    parser.add_argument(
        "--with-ci",
        action="store_true",
        default=True,
        help="Generate GitHub Actions CI workflow (default: true)",
    )
    parser.add_argument(
        "--no-ci",
        action="store_true",
        help="Skip CI workflow generation",
    )
    parser.add_argument(
        "--with-conftest",
        action="store_true",
        default=True,
        help="Generate tests/conftest.py (default: true)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )

    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    project_name = args.project_name or detect_project_name(project_dir)
    python_version = args.python_version or detect_python_version(project_dir)
    src_layout = not args.no_src_layout

    print(f"Setting up Python tooling for: {project_name}")
    print(f"  Python version: {python_version}")
    print(f"  Layout: {'src/' if src_layout else 'flat'}")
    print()

    files_written = 0

    # pyproject.toml
    if write_file(
        project_dir / "pyproject.toml",
        generate_pyproject_toml(project_name, python_version, args.description, src_layout),
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    ):
        files_written += 1

    # .pre-commit-config.yaml
    if not args.no_precommit:
        if write_file(
            project_dir / ".pre-commit-config.yaml",
            generate_precommit_config(python_version),
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        ):
            files_written += 1

    # GitHub Actions CI
    if not args.no_ci:
        if write_file(
            project_dir / ".github" / "workflows" / "ci.yml",
            generate_github_ci_workflow(project_name, python_version),
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        ):
            files_written += 1

    # tests/conftest.py
    if args.with_conftest:
        if write_file(
            project_dir / "tests" / "conftest.py",
            generate_conftest(project_name),
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        ):
            files_written += 1

    # Create directory structure if src layout
    if src_layout and not args.dry_run:
        module_name = project_name.replace("-", "_")
        src_pkg = project_dir / "src" / module_name
        src_pkg.mkdir(parents=True, exist_ok=True)
        init_file = src_pkg / "__init__.py"
        if not init_file.exists():
            init_file.write_text(f'"""Top-level package for {project_name}."""\n', encoding="utf-8")
            print(f"  CREATED: {init_file}")
            files_written += 1

    # Summary
    print(f"\n{'Would create' if args.dry_run else 'Created/updated'} {files_written} files.")

    if not args.dry_run:
        print(f"\nNext steps:")
        print(f"  1. cd {project_dir}")
        print(f"  2. uv sync --dev")
        if not args.no_precommit:
            print(f"  3. uv run pre-commit install")
        print(f"  4. uv run ruff check .")
        print(f"  5. uv run pytest")


if __name__ == "__main__":
    main()
