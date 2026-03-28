# Python Tooling Configuration

La-Z-Boy Python projects use `uv` for package management, `ruff` for linting/formatting, and `pyright` for type checking. This file documents the standard configuration for all three.

---

## Table of Contents
1. [uv — Package Management](#1-uv--package-management)
2. [ruff — Linting and Formatting](#2-ruff--linting-and-formatting)
3. [pyright — Type Checking](#3-pyright--type-checking)
4. [pytest Configuration](#4-pytest-configuration)
5. [Full pyproject.toml](#5-full-pyprojecttoml)

---

## 1. uv — Package Management

`uv` replaces `pip`, `pip-tools`, `virtualenv`, and `poetry` in one tool. It's significantly faster and produces reproducible environments via `uv.lock`.

```bash
# Create a new project
uv init my-service --python 3.12

# Add runtime dependencies
uv add httpx pydantic

# Add dev-only dependencies
uv add --dev pytest pytest-asyncio pytest-cov ruff pyright

# Run a command in the project's virtual environment
uv run pytest
uv run ruff check .
uv run pyright

# Update all dependencies
uv lock --upgrade
```

Commit both `pyproject.toml` and `uv.lock` to version control. The lock file ensures every developer and CI run uses identical dependency versions.

---

## 2. ruff — Linting and Formatting

`ruff` replaces flake8, isort, and black. It's faster than all three combined.

### Enabled rule sets

| Rule prefix | What it checks |
|---|---|
| `E`, `W` | pycodestyle (PEP 8 style) |
| `F` | pyflakes (undefined names, unused imports) |
| `I` | isort (import ordering) |
| `N` | pep8-naming (naming conventions) |
| `UP` | pyupgrade (modernize to target Python version) |
| `B` | flake8-bugbear (common bugs and design issues) |
| `S` | flake8-bandit (security checks) |
| `ANN` | flake8-annotations (missing type annotations) |
| `RUF` | ruff-specific rules |

### Configuration

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "S", "ANN", "RUF"]
ignore = [
    "ANN101",  # missing self type annotation (not useful)
    "ANN102",  # missing cls type annotation (not useful)
    "S101",    # use of assert (OK in tests)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "ANN"]  # allow assert and skip annotations in tests

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Running ruff

```bash
uv run ruff check .          # lint
uv run ruff check . --fix    # lint and auto-fix
uv run ruff format .         # format
```

---

## 3. pyright — Type Checking

```toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
include = ["src"]
exclude = ["tests"]
venvPath = "."
venv = ".venv"
```

Use `"standard"` mode (not `"strict"`) to start. Strict mode can be enabled per-file as the codebase matures:

```python
# pyright: strict
# Add at top of a specific file to enable strict mode there only
```

Run: `uv run pyright`

---

## 4. pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"   # required for async tests without @pytest.mark.asyncio
addopts = [
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
    "-v",
]

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/__init__.py"]

[tool.coverage.report]
show_missing = true
skip_covered = true
```

---

## 5. Full pyproject.toml

This is the standard La-Z-Boy Python project configuration. Copy `assets/pyproject-template.toml` into new projects rather than assembling from scratch.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "lazboy-my-service"
version = "0.1.0"
description = "Brief description of this service"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.4",
    "pyright>=1.1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/lazboy_my_service"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "S", "ANN", "RUF"]
ignore = ["ANN101", "ANN102", "S101"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "ANN"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
include = ["src"]
venvPath = "."
venv = ".venv"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = ["--cov=src", "--cov-report=term-missing", "--cov-fail-under=80", "-v"]

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/__init__.py"]

[tool.coverage.report]
show_missing = true
skip_covered = true
```
