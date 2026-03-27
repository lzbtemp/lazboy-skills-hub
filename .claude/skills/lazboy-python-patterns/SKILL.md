---
name: lazboy-python-patterns
description: >
  Pythonic idioms, PEP 8 standards, type hints, and best practices for building robust
  Python applications. Use this skill when writing new Python code, reviewing Python code,
  refactoring existing Python code, or designing Python packages and modules. Triggers on
  any Python development, type annotation questions, or project structure decisions.
version: "1.0.0"
category: Backend
tags: [python, type-hints, pep8, patterns, testing, async]
---

# Python Development Patterns

Pythonic idioms and modern best practices for robust Python applications.

## 1. Core Principles

- **Readability counts** — clarity over cleverness
- **Explicit is better than implicit** — no hidden side effects
- **EAFP** — Easier to Ask Forgiveness than Permission (use exceptions, not checks)

```python
# ✅ EAFP — Pythonic
try:
    value = data["key"]
except KeyError:
    value = default_value

# ❌ LBYL — less Pythonic
if "key" in data:
    value = data["key"]
else:
    value = default_value
```

## 2. Type Hints

Use modern syntax (Python 3.10+):

```python
# ✅ Modern syntax
def process_items(items: list[str], config: dict[str, int] | None = None) -> bool:
    ...

# ❌ Legacy imports
from typing import List, Dict, Optional
def process_items(items: List[str], config: Optional[Dict[str, int]] = None) -> bool:
    ...
```

### Type Aliases and Protocols

```python
type UserId = str
type Coordinates = tuple[float, float]

from typing import Protocol

class Repository(Protocol):
    def find_by_id(self, id: str) -> dict | None: ...
    def save(self, entity: dict) -> dict: ...
```

## 3. Error Handling

```python
# ✅ Specific exceptions with chaining
class ServiceError(Exception):
    """Base exception for service errors."""

class NotFoundError(ServiceError):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} not found: {id}")
        self.resource = resource
        self.id = id

class ValidationError(ServiceError):
    def __init__(self, field: str, message: str):
        super().__init__(f"Validation error on {field}: {message}")

# ✅ Always chain exceptions
try:
    result = external_api.fetch(url)
except ConnectionError as err:
    raise ServiceError(f"API unavailable: {url}") from err
```

## 4. Context Managers

```python
from contextlib import contextmanager

@contextmanager
def database_transaction(conn):
    """Manage database transaction with automatic rollback on error."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

# Usage
with database_transaction(conn) as tx:
    tx.execute("INSERT INTO users ...")
```

## 5. Comprehensions and Generators

```python
# ✅ List comprehension for simple transformations
names = [user.name for user in users if user.is_active]

# ✅ Dict comprehension
user_map = {u.id: u for u in users}

# ✅ Generator for large datasets — lazy evaluation
def read_large_file(path: str):
    with open(path) as f:
        for line in f:
            yield line.strip()

# ✅ Generator expression — memory efficient
total = sum(order.amount for order in orders if order.status == "completed")
```

## 6. Dataclasses and Records

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)  # Immutable
class Product:
    id: str
    name: str
    price: float
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.price < 0:
            raise ValueError(f"Price must be non-negative: {self.price}")
```

### When to Use What

| Type | Use Case |
|------|----------|
| `dataclass(frozen=True)` | Immutable data records |
| `dataclass` | Mutable data with validation |
| `NamedTuple` | Lightweight immutable tuples |
| `Pydantic BaseModel` | API request/response validation |

## 7. Decorators

```python
import functools
import time

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as err:
                    if attempt == max_attempts:
                        raise
                    wait = delay * (2 ** (attempt - 1))
                    time.sleep(wait)
        return wrapper
    return decorator

@retry(max_attempts=3, delay=0.5)
def fetch_data(url: str) -> dict:
    ...
```

## 8. Concurrency

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio

# ✅ ThreadPoolExecutor for I/O-bound tasks
def fetch_all_urls(urls: list[str]) -> list[str]:
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_url, urls))
    return results

# ✅ ProcessPoolExecutor for CPU-bound tasks
def process_images(paths: list[str]) -> list[bytes]:
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(resize_image, paths))
    return results

# ✅ Async/await for concurrent I/O
async def fetch_all(urls: list[str]) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        return await asyncio.gather(*tasks)
```

## 9. Package Organization

```
src/
├── mypackage/
│   ├── __init__.py         # __all__ exports
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   └── services/
│       ├── __init__.py
│       └── user_service.py
├── tests/
│   ├── conftest.py
│   ├── test_routes.py
│   └── test_user_service.py
└── pyproject.toml
```

### Import Order

```python
# 1. Standard library
import os
from datetime import datetime

# 2. Third-party
import httpx
from pydantic import BaseModel

# 3. Local
from mypackage.core.config import settings
from mypackage.models.user import User
```

## 10. Tooling

| Tool | Purpose |
|------|---------|
| `ruff` | Linting and formatting (replaces black, isort, flake8) |
| `mypy` or `pyright` | Type checking |
| `pytest` | Testing with fixtures and parametrize |
| `uv` | Fast dependency management |
| `bandit` | Security linting |

### pyproject.toml Configuration

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]

[tool.mypy]
strict = true
warn_return_any = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=src"
```

## 11. Anti-Patterns to Avoid

```python
# ❌ Mutable default argument
def add_item(item, items=[]):  # Shared across calls!
    items.append(item)

# ✅ Use None sentinel
def add_item(item, items: list | None = None):
    if items is None:
        items = []
    items.append(item)

# ❌ Bare except
try:
    do_something()
except:  # Catches SystemExit, KeyboardInterrupt!
    pass

# ✅ Catch specific exceptions
try:
    do_something()
except ValueError as err:
    logger.warning("Invalid value: %s", err)

# ❌ type() for checking
if type(x) == int:

# ✅ isinstance()
if isinstance(x, int):

# ❌ Comparing to None with ==
if x == None:

# ✅ Use identity check
if x is None:
```

## 12. Quick Reference

| Idiom | Purpose |
|-------|---------|
| EAFP | Exception-based control flow |
| Context managers | Resource cleanup |
| List comprehensions | Simple transformations |
| Generators | Lazy evaluation |
| `dataclass(frozen=True)` | Immutable data containers |
| `__slots__` | Memory optimization |
| f-strings | String formatting |
| `pathlib.Path` | Cross-platform file paths |
| `enumerate()` | Index-element iteration |
| `zip()` | Parallel iteration |
