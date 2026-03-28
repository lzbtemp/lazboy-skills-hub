# Modern Python Syntax Reference (3.12+)

Read this when writing generics, type aliases, match statements, or when you need to verify whether a syntax pattern is current. All examples target Python 3.12.

---

## Table of Contents
1. [Type Aliases (PEP 695)](#1-type-aliases-pep-695)
2. [Generic Functions and Classes (PEP 695)](#2-generic-functions-and-classes-pep-695)
3. [Union Types](#3-union-types)
4. [Match Statements (Structural Pattern Matching)](#4-match-statements)
5. [Exception Groups](#5-exception-groups)
6. [TypedDict and Protocol](#6-typeddict-and-protocol)
7. [Override and Final](#7-override-and-final)

---

## 1. Type Aliases (PEP 695)

```python
# Python 3.12+ — use `type` keyword
type SKU = str
type ProductMap = dict[SKU, Product]
type Callback[T] = Callable[[T], None]

# Old style — still valid but verbose
from typing import TypeAlias
ProductMap: TypeAlias = dict[str, Product]
```

---

## 2. Generic Functions and Classes (PEP 695)

```python
# Python 3.12+ — clean bracket syntax
def first[T](items: list[T]) -> T:
    return items[0]

class Repository[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

    def add(self, item: T) -> None:
        self._items.append(item)

    def get_all(self) -> list[T]:
        return list(self._items)

# Old style (3.9–3.11) — TypeVar required
from typing import TypeVar
T = TypeVar("T")
def first(items: list[T]) -> T:
    return items[0]
```

---

## 3. Union Types

```python
# Python 3.10+ — use | operator
def find_product(sku: str) -> Product | None:
    ...

def process(value: int | str | None) -> str:
    ...

# Old style
from typing import Optional, Union
def find_product(sku: str) -> Optional[Product]:
    ...
```

---

## 4. Match Statements

Use `match` for branching on structure, not just equality. Particularly useful for command dispatch, state machines, and API response routing.

```python
# Dispatching on a command type
match command:
    case {"action": "create", "sku": sku}:
        await create_product(sku)
    case {"action": "update", "sku": sku, "price": price}:
        await update_price(sku, price)
    case {"action": "delete", "sku": sku}:
        await delete_product(sku)
    case _:
        raise ValidationError(f"Unknown command: {command}")

# Pattern matching on dataclasses
@dataclass
class Ok[T]:
    value: T

@dataclass
class Err:
    message: str

match result:
    case Ok(value=v):
        return v
    case Err(message=msg):
        raise RuntimeError(msg)
```

---

## 5. Exception Groups

Use exception groups when running concurrent tasks that may each fail independently (e.g., with `asyncio.TaskGroup`).

```python
import asyncio

async def fetch_all(skus: list[str]) -> list[Product]:
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_one(sku)) for sku in skus]
    except* httpx.HTTPError as eg:
        # `except*` catches ExceptionGroup containing httpx.HTTPError instances
        failed_skus = [str(e) for e in eg.exceptions]
        raise ExternalServiceError(f"Failed fetching: {failed_skus}") from eg

    return [t.result() for t in tasks]
```

---

## 6. TypedDict and Protocol

### TypedDict — for dict-shaped data you don't control (e.g., JSON from external APIs)

```python
from typing import TypedDict, NotRequired

class ProductPayload(TypedDict):
    sku: str
    name: str
    price: float
    category: NotRequired[str]  # optional key
```

### Protocol — structural typing (duck typing with type safety)

Use `Protocol` when you want to define a contract without requiring inheritance — especially useful for dependency injection and testing.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ProductRepository(Protocol):
    async def find(self, sku: str) -> Product | None: ...
    async def save(self, product: Product) -> None: ...

# Any class implementing these methods satisfies the protocol
class PostgresProductRepo:
    async def find(self, sku: str) -> Product | None:
        ...
    async def save(self, product: Product) -> None:
        ...

# Works without explicit inheritance
repo: ProductRepository = PostgresProductRepo()
```

---

## 7. Override and Final

```python
from typing import override, final

class BaseService:
    def process(self, item: str) -> str:
        return item.strip()

class ProductService(BaseService):
    @override  # type checker errors if parent doesn't have this method
    def process(self, item: str) -> str:
        return super().process(item).upper()

@final  # prevents subclassing
class Config:
    ...
```

`@override` is valuable because it makes refactoring safer — if you rename or remove the parent method, type checkers immediately flag all orphaned `@override` methods.
