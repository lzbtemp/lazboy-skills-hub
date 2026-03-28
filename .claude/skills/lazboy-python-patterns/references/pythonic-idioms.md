# Pythonic Idioms Reference

Comprehensive guide to writing idiomatic Python code following modern best practices (Python 3.10+).

## 1. Comprehensions

### List Comprehensions

Use list comprehensions for simple transformations. Avoid nesting beyond two levels.

```python
# Basic filtering and transformation
active_names = [user.name for user in users if user.is_active]

# Flattening nested lists
flat = [item for sublist in nested for item in sublist]

# Conditional expression in comprehension
labels = ["even" if x % 2 == 0 else "odd" for x in range(10)]

# Multiple conditions
results = [x for x in data if x > 0 if x % 2 == 0]
```

### Dict Comprehensions

```python
# Invert a dictionary
inverted = {v: k for k, v in original.items()}

# Build lookup from objects
user_by_id = {u.id: u for u in users}

# Filter a dictionary
filtered = {k: v for k, v in config.items() if v is not None}

# Merge and transform
merged = {k: transform(v) for d in dicts for k, v in d.items()}
```

### Set Comprehensions

```python
# Unique transformed values
unique_domains = {email.split("@")[1] for email in emails}

# Deduplicate with condition
valid_ids = {item.id for item in items if item.is_valid()}
```

### When NOT to Use Comprehensions

```python
# Too complex -- use a loop instead
# Bad: deeply nested with side effects
results = [process(x) for group in data for x in group.items if x.valid and not x.deleted]

# Better: explicit loop
results = []
for group in data:
    for x in group.items:
        if x.valid and not x.deleted:
            results.append(process(x))
```

## 2. Generators

### Generator Functions

```python
def fibonacci(limit: int):
    """Yield Fibonacci numbers up to limit."""
    a, b = 0, 1
    while a < limit:
        yield a
        a, b = b, a + b

# Lazy -- only computes values as needed
for num in fibonacci(1000):
    print(num)
```

### Generator Expressions

```python
# Memory-efficient aggregation over large datasets
total_size = sum(f.stat().st_size for f in Path(".").rglob("*.py"))

# Chaining with any/all
has_admin = any(u.role == "admin" for u in users)
all_valid = all(item.is_valid() for item in items)

# First match
first_match = next((x for x in items if x.name == target), None)
```

### Generator Pipelines

```python
def read_lines(path: str):
    with open(path) as f:
        yield from (line.strip() for line in f)

def filter_comments(lines):
    yield from (line for line in lines if not line.startswith("#"))

def parse_records(lines):
    for line in lines:
        yield line.split(",")

# Compose the pipeline -- no intermediate lists
pipeline = parse_records(filter_comments(read_lines("data.csv")))
for record in pipeline:
    process(record)
```

### yield from

```python
def flatten(nested):
    """Recursively flatten an iterable."""
    for item in nested:
        if isinstance(item, (list, tuple)):
            yield from flatten(item)
        else:
            yield item

list(flatten([1, [2, [3, 4]], 5]))  # [1, 2, 3, 4, 5]
```

## 3. Context Managers

### Built-in Usage

```python
# File handling -- always use with
with open("data.txt", "r") as f:
    content = f.read()

# Multiple resources
with open("input.txt") as src, open("output.txt", "w") as dst:
    dst.write(src.read().upper())

# Locks
import threading
lock = threading.Lock()
with lock:
    shared_resource.update()
```

### Custom Context Managers with contextlib

```python
from contextlib import contextmanager, suppress

@contextmanager
def temporary_env(key: str, value: str):
    """Temporarily set an environment variable."""
    old = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            del os.environ[key]
        else:
            os.environ[key] = old

with temporary_env("DEBUG", "1"):
    run_debug_code()

# suppress -- ignore specific exceptions
with suppress(FileNotFoundError):
    os.remove("temp.txt")
```

### Class-Based Context Manager

```python
class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None

    def __enter__(self):
        self.conn = connect(self.connection_string)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()
        return False  # Do not suppress exceptions
```

## 4. Decorators

### Function Decorators

```python
import functools
import time
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

def timer(func: Callable[P, R]) -> Callable[P, R]:
    """Log execution time of a function."""
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

@timer
def expensive_operation():
    time.sleep(1)
```

### Decorators with Arguments

```python
def retry(max_attempts: int = 3, exceptions: tuple = (Exception,)):
    """Retry a function on failure with exponential backoff."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    wait = 2 ** (attempt - 1)
                    time.sleep(wait)
        return wrapper
    return decorator

@retry(max_attempts=5, exceptions=(ConnectionError, TimeoutError))
def fetch_data(url: str) -> dict:
    ...
```

### Class Decorators

```python
def singleton(cls):
    """Ensure only one instance of a class exists."""
    instances = {}
    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class Config:
    def __init__(self):
        self.settings = load_settings()
```

## 5. Dataclasses vs NamedTuples

### Dataclasses

```python
from dataclasses import dataclass, field, asdict
from datetime import datetime

@dataclass
class User:
    name: str
    email: str
    roles: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.email = self.email.lower().strip()

# Frozen (immutable) dataclass
@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

# Serialization
user = User("Alice", "alice@example.com")
user_dict = asdict(user)
```

### NamedTuples

```python
from typing import NamedTuple

class Coordinate(NamedTuple):
    lat: float
    lon: float
    label: str = ""

# Lightweight, immutable, iterable, hashable
coord = Coordinate(40.7128, -74.0060, "NYC")
lat, lon, label = coord  # Unpacking works
```

### Decision Guide

| Feature | dataclass | NamedTuple |
|---------|-----------|------------|
| Mutable | Yes (default) | No |
| Hashable | Only if frozen | Yes |
| Iterable | No | Yes |
| Inheritance | Full | Limited |
| Memory | Normal (slots=True helps) | Very compact |
| Use case | Domain objects | Simple records, dict keys |

## 6. Type Hints Best Practices

### Modern Syntax (3.10+)

```python
# Union with pipe operator
def process(value: str | int | None) -> str:
    ...

# Built-in generics -- no typing imports needed
def transform(items: list[str]) -> dict[str, int]:
    ...

# Type aliases with type statement (3.12+)
type JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None
type Handler = Callable[[Request], Response]
```

### Protocols for Structural Typing

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Renderable(Protocol):
    def render(self) -> str: ...

class HtmlWidget:
    def render(self) -> str:
        return "<div>widget</div>"

def display(item: Renderable) -> None:
    print(item.render())

# HtmlWidget satisfies Renderable without inheriting from it
display(HtmlWidget())  # Works
```

### TypeVar and Generics

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()
```

## 7. Walrus Operator (:=)

```python
# Assignment expression -- assign and test in one step
if (n := len(data)) > 10:
    print(f"Processing {n} items")

# Filter with expensive computation
results = [y for x in data if (y := expensive(x)) is not None]

# Read loop
while chunk := f.read(8192):
    process(chunk)

# Regex matching
import re
if m := re.match(r"(\d+)-(\d+)", text):
    start, end = int(m.group(1)), int(m.group(2))
```

## 8. Structural Pattern Matching (3.10+)

```python
# Basic match
match command.split():
    case ["quit"]:
        sys.exit(0)
    case ["go", direction]:
        move(direction)
    case ["get", item] if item in inventory:
        pick_up(item)
    case _:
        print("Unknown command")

# Matching objects
match event:
    case Click(position=(x, y)) if x > 100:
        handle_right_click(x, y)
    case KeyPress(key_name="q"):
        quit()
    case Scroll(position=pos, offset=(_, y)):
        scroll_window(pos, y)

# Matching dictionaries
match response:
    case {"status": 200, "data": data}:
        process(data)
    case {"status": 404}:
        raise NotFoundError()
    case {"status": status} if status >= 500:
        raise ServerError(status)

# Guard clauses and OR patterns
match value:
    case int() | float() if value > 0:
        print("Positive number")
    case str() as s if s.strip():
        print(f"Non-empty string: {s}")
    case [*items] if len(items) > 0:
        print(f"Non-empty sequence: {items}")
```

## 9. Essential Built-in Patterns

```python
# enumerate -- always prefer over manual indexing
for i, item in enumerate(items, start=1):
    print(f"{i}. {item}")

# zip -- parallel iteration
for name, score in zip(names, scores, strict=True):
    print(f"{name}: {score}")

# unpacking
first, *middle, last = [1, 2, 3, 4, 5]

# dict merge (3.9+)
combined = defaults | overrides

# f-string debugging (3.8+)
print(f"{variable=}")  # prints: variable=42

# pathlib for file operations
from pathlib import Path
config_path = Path.home() / ".config" / "app" / "settings.json"
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(config))
```

## 10. Anti-Pattern Quick Reference

| Anti-Pattern | Pythonic Alternative |
|---|---|
| `for i in range(len(lst))` | `for i, item in enumerate(lst)` |
| `if x == True` | `if x` |
| `if x == None` | `if x is None` |
| `type(x) == int` | `isinstance(x, int)` |
| `dict.has_key(k)` | `k in dict` |
| `"" + s1 + s2` in loop | `"".join(parts)` |
| `try: ... except:` | `except SpecificError:` |
| `def f(x, lst=[])` | `def f(x, lst=None)` |
| Manual file open/close | `with open(...) as f:` |
| `if len(lst) == 0` | `if not lst` |
