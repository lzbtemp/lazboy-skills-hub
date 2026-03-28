---
name: lazboy-python-best-practices
description: "La-Z-Boy Python coding standards for writing modern, type-safe, maintainable Python. Apply this skill whenever writing, reviewing, or refactoring Python code for La-Z-Boy — even if the user doesn't say 'best practices'. Trigger on: Python function, class, module, script, API endpoint, data model, async code, pytest, error handling, type hints, pyproject.toml, uv, ruff, or any request to write or improve Python code. This skill ensures La-Z-Boy Python code is consistent, readable, and production-ready across all teams."
version: "1.0.0"
category: Backend
tags: [python, best-practices, type-hints, testing, tooling]
---

# La-Z-Boy Python Best Practices

Write modern Python 3.12+ that is type-safe, readable, and maintainable. These standards apply to all Python at La-Z-Boy — APIs, data pipelines, scripts, and tooling.

**Reference files — load when needed:**
- `references/modern-syntax.md` — Python 3.12+ syntax patterns (generics, type aliases, match)
- `references/testing.md` — pytest patterns: fixtures, parametrize, mocking, coverage
- `references/tooling.md` — pyproject.toml setup, ruff, pyright, uv configuration
- `assets/pyproject-template.toml` — standard La-Z-Boy pyproject.toml to copy into new projects
- `assets/exceptions.py` — exception hierarchy template for new services

---

## 1. Python Version & Type Safety

La-Z-Boy targets **Python 3.12+**. Always use modern syntax — agents trained on older code tend to generate outdated patterns.

### Use native type syntax

```python
# Correct — Python 3.12+
def process_items(items: list[str]) -> dict[str, int]:
    ...

def find(value: str | None = None) -> str | None:
    ...

# Wrong — pre-3.9 style
from typing import List, Dict, Optional, Union
def process_items(items: List[str]) -> Dict[str, int]:
    ...
```

### Annotate everything — functions, class attributes, module-level vars

Type annotations are documentation that the type checker enforces. Unannotated code creates maintenance debt because future developers (and agents) can't understand the contract.

```python
# Service class — annotate every attribute
class ProductService:
    _cache: dict[str, Product]
    _client: httpx.AsyncClient

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._cache = {}
        self._client = client
```

### Use `pyright` for type checking (not mypy)

pyright is faster and stricter. Configure it in `pyproject.toml`:

```toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
```

---

## 2. Data Modeling

Choose the right data container based on what it represents:

| Use case | Tool | Why |
|---|---|---|
| Config / settings | Frozen `@dataclass` | Immutable, startup-time validation |
| API request/response | `pydantic.BaseModel` | Validation, serialization, OpenAPI docs |
| Internal value objects | `@dataclass` | Simple, no deps |
| Named tuples (read-only) | `typing.NamedTuple` | Lightweight, unpacks nicely |
| External data boundary | `pydantic.BaseModel` | Parse and validate at the edge |

### Frozen dataclass for config

Config should be immutable and validated at startup — not a dict that can be mutated mid-run.

```python
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class AppConfig:
    db_url: str
    api_key: str
    debug: bool = False

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            db_url=os.environ["DATABASE_URL"],
            api_key=os.environ["API_KEY"],
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )
```

### Pydantic v2 at API boundaries

```python
from pydantic import BaseModel, field_validator, ConfigDict

class ProductRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str
    price: float
    category: str

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price must be positive")
        return v
```

---

## 3. Error Handling

### Build a typed exception hierarchy

Rather than raising bare `Exception` or `ValueError`, define a hierarchy that makes error types explicit. This lets callers handle errors precisely and makes logging more useful.

```python
# assets/exceptions.py — copy this pattern into each service
class LazBoyError(Exception):
    """Base for all La-Z-Boy application errors."""

class ValidationError(LazBoyError):
    """Input failed business rule validation."""

class NotFoundError(LazBoyError):
    """Requested resource does not exist."""

class ExternalServiceError(LazBoyError):
    """Downstream API or service call failed."""
```

### Always chain exceptions

Chaining preserves the original traceback, which is critical for debugging in production.

```python
# Correct — preserves context
try:
    result = await client.get(url)
except httpx.HTTPError as err:
    raise ExternalServiceError(f"Failed to fetch product {sku}") from err

# Wrong — swallows original traceback
try:
    result = await client.get(url)
except httpx.HTTPError:
    raise ExternalServiceError(f"Failed to fetch product {sku}")
```

---

## 4. Project Structure

Use the **src layout** for all La-Z-Boy Python packages. It prevents accidental imports from the project root and makes packaging behavior consistent between development and production.

```
my-service/
├── pyproject.toml
├── src/
│   └── lazboy_myservice/
│       ├── __init__.py
│       ├── models.py
│       ├── service.py
│       ├── exceptions.py
│       └── config.py
└── tests/
    ├── conftest.py
    └── test_service.py
```

### Module organization

Order within a module: docstring → `__all__` → stdlib imports → third-party imports → local imports → constants → types → classes → functions.

```python
"""Module docstring — one sentence describing purpose."""

__all__ = ["ProductService", "ProductRequest"]

import asyncio
from dataclasses import dataclass

import httpx
from pydantic import BaseModel

from lazboy_myservice.exceptions import ExternalServiceError

MAX_RETRIES = 3
```

Defining `__all__` makes the public API explicit — other developers and agents know exactly what's intended to be imported.

---

## 5. Async Patterns

Use async for I/O-bound work (API calls, DB queries). Use `ProcessPoolExecutor` for CPU-bound work — not `asyncio`.

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

# I/O-bound: use asyncio + TaskGroup (Python 3.11+)
async def fetch_products(skus: list[str]) -> list[Product]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_one(sku)) for sku in skus]
    return [t.result() for t in tasks]

# CPU-bound: use ProcessPoolExecutor
def process_images_sync(paths: list[str]) -> list[str]:
    with ProcessPoolExecutor() as pool:
        return list(pool.map(resize_image, paths))
```

Prefer `asyncio.TaskGroup` over `asyncio.gather` — it propagates exceptions immediately and cancels sibling tasks, preventing silent failures.

---

## 6. Logging

Use structured logging so logs are machine-parseable in production (Datadog, CloudWatch, etc.).

```python
import logging
import json

# Configure once at app startup
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)

logger = logging.getLogger(__name__)

# Log with context as extra fields
logger.info("Product fetched", extra={"sku": sku, "duration_ms": elapsed})
logger.error("Fetch failed", extra={"sku": sku, "error": str(err)}, exc_info=True)
```

Never use `print()` in production code. Logs are always preferable — they carry level, timestamp, and source context.

---

## 7. Tooling

Use **uv** for environment and dependency management. Use **ruff** for linting and formatting.

```bash
# Create a new project
uv init my-service
uv add httpx pydantic
uv add --dev pytest pytest-asyncio ruff pyright

# Run tools
uv run ruff check .
uv run ruff format .
uv run pyright
uv run pytest
```

Copy `assets/pyproject-template.toml` into new projects — it has ruff, pyright, and pytest pre-configured to La-Z-Boy standards.

> Read `references/tooling.md` for the full pyproject.toml config and ruff rule set.

---

## 8. What NOT to Do

- **Don't use pre-3.9 type imports** (`List`, `Dict`, `Optional`, `Union` from `typing`) — use native syntax (`list`, `dict`, `X | None`)
- **Don't swallow exception context** — always `raise X from err`, never bare `raise X` after a `try`
- **Don't use bare `except Exception`** — catch specific types; if you must catch broadly, log the full traceback
- **Don't use `print()` for debugging or logging** — use `logging` or remove before merging
- **Don't mutate config at runtime** — use frozen dataclasses; mutable config is a source of subtle bugs
- **Don't use `asyncio.gather`** — prefer `asyncio.TaskGroup` which cancels siblings on failure instead of silently swallowing errors
- **Don't mix sync and async without care** — calling a sync function inside async code that does I/O blocks the event loop; use `asyncio.to_thread()` for sync wrappers

---

## 9. Resources

| Resource | When to use |
|---|---|
| `references/modern-syntax.md` | Writing generics, type aliases, match statements, PEP 695 patterns |
| `references/testing.md` | Setting up pytest, writing fixtures, parametrize, mocking async |
| `references/tooling.md` | Configuring pyproject.toml, ruff rules, pyright strictness |
| `assets/pyproject-template.toml` | Starting a new La-Z-Boy Python project |
| `assets/exceptions.py` | Defining a new service's exception hierarchy |
