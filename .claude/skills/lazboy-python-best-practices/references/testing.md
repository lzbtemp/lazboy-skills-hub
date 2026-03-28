# Python Testing Patterns

Read this when writing tests for La-Z-Boy Python code. All tests use pytest.

---

## Table of Contents
1. [Project Test Layout](#1-project-test-layout)
2. [Fixtures](#2-fixtures)
3. [Parametrize](#3-parametrize)
4. [Testing Async Code](#4-testing-async-code)
5. [Mocking](#5-mocking)
6. [Testing Pydantic Models](#6-testing-pydantic-models)
7. [Coverage Configuration](#7-coverage-configuration)

---

## 1. Project Test Layout

```
tests/
├── conftest.py          # shared fixtures for the whole test suite
├── unit/
│   ├── test_service.py
│   └── test_models.py
└── integration/
    └── test_api.py
```

Keep unit tests (no I/O, no network) separate from integration tests so CI can run them independently. Unit tests should be fast enough to run on every file save.

---

## 2. Fixtures

Fixtures are reusable setup functions. Use them instead of duplicating setup code across tests.

```python
# conftest.py
import pytest
import pytest_asyncio
import httpx

from lazboy_myservice.config import AppConfig
from lazboy_myservice.service import ProductService

@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        db_url="postgresql://localhost/test",
        api_key="test-key",
        debug=True,
    )

@pytest_asyncio.fixture
async def http_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient() as client:
        yield client

@pytest_asyncio.fixture
async def service(config: AppConfig, http_client: httpx.AsyncClient) -> ProductService:
    return ProductService(config=config, client=http_client)
```

Fixtures compose — `service` above depends on `config` and `http_client`, and pytest resolves the dependency graph automatically.

---

## 3. Parametrize

Use `@pytest.mark.parametrize` to run the same test logic across multiple inputs. This is far cleaner than copy-pasting test functions.

```python
import pytest
from lazboy_myservice.models import ProductRequest

@pytest.mark.parametrize("sku,price,expected_error", [
    ("LZB-001", 999.99, None),           # valid
    ("LZB-002", 0, "price must be positive"),    # zero price
    ("LZB-003", -50.0, "price must be positive"),  # negative price
    ("", 100.0, "sku cannot be empty"),          # empty SKU
])
def test_product_request_validation(sku: str, price: float, expected_error: str | None) -> None:
    if expected_error:
        with pytest.raises(Exception, match=expected_error):
            ProductRequest(sku=sku, price=price, category="seating")
    else:
        model = ProductRequest(sku=sku, price=price, category="seating")
        assert model.price == price
```

---

## 4. Testing Async Code

Install `pytest-asyncio` and configure it for auto mode:

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

```python
import pytest

async def test_fetch_product(service: ProductService) -> None:
    product = await service.fetch("LZB-001")
    assert product.sku == "LZB-001"
    assert product.price > 0

async def test_fetch_missing_product(service: ProductService) -> None:
    product = await service.fetch("DOES-NOT-EXIST")
    assert product is None
```

With `asyncio_mode = "auto"`, async test functions work without any additional decorator.

---

## 5. Mocking

Use `unittest.mock` for mocking. For async code, use `AsyncMock`.

```python
from unittest.mock import AsyncMock, MagicMock, patch

async def test_service_handles_http_error(config: AppConfig) -> None:
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.HTTPError("Connection refused")

    service = ProductService(config=config, client=mock_client)

    with pytest.raises(ExternalServiceError, match="Failed to fetch product"):
        await service.fetch("LZB-001")

    mock_client.get.assert_called_once()

# Patching a module-level dependency
async def test_with_patch() -> None:
    with patch("lazboy_myservice.service.some_function", return_value="mocked") as mock_fn:
        result = await some_code_that_calls_it()
        mock_fn.assert_called_once_with("expected-arg")
```

Prefer injecting dependencies over patching module internals — it makes tests more reliable and avoids brittle import path strings.

---

## 6. Testing Pydantic Models

```python
import pytest
from pydantic import ValidationError as PydanticValidationError

def test_product_request_strips_whitespace() -> None:
    req = ProductRequest(sku="  LZB-001  ", price=999.99, category="seating")
    assert req.sku == "LZB-001"  # stripped by ConfigDict(str_strip_whitespace=True)

def test_product_request_rejects_invalid_price() -> None:
    with pytest.raises(PydanticValidationError) as exc_info:
        ProductRequest(sku="LZB-001", price=-10, category="seating")

    errors = exc_info.value.errors()
    assert any("price" in str(e["loc"]) for e in errors)
```

---

## 7. Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/__init__.py"]

[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = true
```

Run with: `uv run pytest --cov`

Target 80% coverage minimum. Don't chase 100% — testing every `if __name__ == "__main__"` block adds noise without value. Focus coverage on business logic, error handling paths, and data validation.
