# Async Python Patterns Reference

Comprehensive guide to asyncio, coroutines, and concurrent I/O patterns in modern Python.

## 1. Event Loop Fundamentals

### Running Async Code

```python
import asyncio

async def main():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

# Entry point -- use asyncio.run() (Python 3.7+)
asyncio.run(main())
```

### Event Loop Internals

```python
# Get the running loop (from within async context)
loop = asyncio.get_running_loop()

# Schedule a callback
loop.call_soon(callback, arg1, arg2)
loop.call_later(5.0, callback)  # After 5 seconds

# Run blocking code in a thread pool
result = await loop.run_in_executor(None, blocking_function, arg)

# Run blocking code with a specific executor
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=4)
result = await loop.run_in_executor(executor, blocking_io)
```

### Important Rules

- Never call `asyncio.run()` from within an async context.
- Never use `time.sleep()` in async code -- always use `await asyncio.sleep()`.
- Never do CPU-bound work directly in a coroutine -- offload to an executor.
- Always `await` coroutines. A coroutine that is called but not awaited does nothing.

## 2. Coroutines and Tasks

### Defining Coroutines

```python
async def fetch_user(user_id: int) -> dict:
    """Coroutine -- declared with async def."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.example.com/users/{user_id}") as resp:
            return await resp.json()
```

### Creating Tasks for Concurrency

```python
async def fetch_all_users(user_ids: list[int]) -> list[dict]:
    """Create tasks to run coroutines concurrently."""
    tasks = [asyncio.create_task(fetch_user(uid)) for uid in user_ids]
    results = await asyncio.gather(*tasks)
    return list(results)
```

### Task Names and Cancellation

```python
async def managed_task():
    task = asyncio.create_task(long_operation(), name="long-op")
    print(f"Started: {task.get_name()}")

    try:
        result = await asyncio.wait_for(task, timeout=30.0)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("Task was cancelled")
```

## 3. asyncio.gather and Concurrency Patterns

### Basic Gather

```python
async def fetch_multiple():
    """Run multiple coroutines concurrently and collect results."""
    user, posts, comments = await asyncio.gather(
        fetch_user(1),
        fetch_posts(1),
        fetch_comments(1),
    )
    return {"user": user, "posts": posts, "comments": comments}
```

### Gather with Error Handling

```python
async def fetch_with_errors():
    """return_exceptions=True prevents one failure from cancelling all."""
    results = await asyncio.gather(
        fetch_user(1),
        fetch_user(2),
        fetch_user(999),  # May fail
        return_exceptions=True,
    )
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Task {i} failed: {result}")
        else:
            print(f"Task {i} succeeded: {result}")
```

### asyncio.wait for Fine-Grained Control

```python
async def wait_example():
    tasks = {asyncio.create_task(fetch(url)) for url in urls}

    # Wait for first completed
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in done:
        print(task.result())

    # Cancel remaining
    for task in pending:
        task.cancel()
```

### TaskGroup (Python 3.11+)

```python
async def fetch_with_taskgroup():
    """Structured concurrency -- all tasks managed together."""
    results = []
    async with asyncio.TaskGroup() as tg:
        for url in urls:
            tg.create_task(fetch(url))
    # If any task raises, all others are cancelled and
    # an ExceptionGroup is raised
```

## 4. Semaphores -- Limiting Concurrency

```python
async def fetch_with_limit(urls: list[str], max_concurrent: int = 10) -> list[str]:
    """Use a semaphore to limit concurrent requests."""
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def bounded_fetch(url: str) -> str:
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    return await resp.text()

    tasks = [asyncio.create_task(bounded_fetch(url)) for url in urls]
    return await asyncio.gather(*tasks)
```

### BoundedSemaphore

```python
# BoundedSemaphore raises ValueError if released more than acquired
sem = asyncio.BoundedSemaphore(5)

async def safe_access():
    async with sem:
        await do_limited_work()
```

## 5. Async Generators

### Defining Async Generators

```python
async def stream_data(url: str):
    """Yield data chunks asynchronously."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            async for chunk in resp.content.iter_chunked(1024):
                yield chunk

# Consuming an async generator
async def process_stream():
    async for chunk in stream_data("https://example.com/large-file"):
        process(chunk)
```

### Async Generator with Cleanup

```python
async def database_cursor(query: str):
    """Async generator with proper cleanup."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with conn.transaction():
            async for record in conn.cursor(query):
                yield record
    finally:
        await conn.close()
```

### Async Comprehensions

```python
# Async list comprehension
results = [item async for item in async_generator() if item.is_valid()]

# Async generator expression
filtered = (item async for item in stream if item.priority > 5)
```

## 6. aiohttp Usage Patterns

### Client Session Best Practices

```python
import aiohttp

async def api_client():
    """Reuse a single session for multiple requests."""
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    async with aiohttp.ClientSession(
        base_url="https://api.example.com",
        timeout=timeout,
        headers={"Authorization": f"Bearer {token}"},
    ) as session:
        # GET request
        async with session.get("/users") as resp:
            resp.raise_for_status()
            users = await resp.json()

        # POST request
        async with session.post("/users", json={"name": "Alice"}) as resp:
            created = await resp.json()

        return users, created
```

### Retry with Backoff

```python
async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    max_retries: int = 3,
) -> dict:
    """Fetch with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            async with session.get(url) as resp:
                if resp.status == 429:  # Rate limited
                    retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Max retries exceeded")
```

### Streaming Uploads

```python
async def upload_file(session: aiohttp.ClientSession, path: str):
    """Stream a large file upload."""
    async with aiofiles.open(path, "rb") as f:
        data = aiohttp.FormData()
        data.add_field("file", f, filename=Path(path).name)
        async with session.post("/upload", data=data) as resp:
            return await resp.json()
```

## 7. Async Context Managers

### Custom Async Context Manager

```python
class AsyncDatabasePool:
    def __init__(self, dsn: str, min_size: int = 5, max_size: int = 20):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.pool = None

    async def __aenter__(self):
        self.pool = await asyncpg.create_pool(
            self.dsn, min_size=self.min_size, max_size=self.max_size
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.pool:
            await self.pool.close()
        return False

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

# Usage
async def main():
    async with AsyncDatabasePool("postgresql://localhost/db") as db:
        users = await db.execute("SELECT * FROM users WHERE active = $1", True)
```

### contextlib for Async

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_resource(name: str):
    """Async context manager using decorator."""
    resource = await acquire_resource(name)
    try:
        yield resource
    finally:
        await release_resource(resource)

async def use_resource():
    async with managed_resource("my-resource") as res:
        await res.process()
```

## 8. Error Handling in Async Code

### Exception Groups (Python 3.11+)

```python
async def handle_exception_groups():
    """TaskGroup raises ExceptionGroup on failure."""
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(might_fail_1())
            tg.create_task(might_fail_2())
    except* ValueError as eg:
        for exc in eg.exceptions:
            print(f"ValueError: {exc}")
    except* TypeError as eg:
        for exc in eg.exceptions:
            print(f"TypeError: {exc}")
```

### Cancellation Handling

```python
async def cancellable_work():
    """Properly handle cancellation."""
    try:
        while True:
            data = await fetch_next_batch()
            await process_batch(data)
    except asyncio.CancelledError:
        # Perform cleanup before re-raising
        await save_progress()
        raise  # Always re-raise CancelledError
```

### Graceful Shutdown

```python
async def shutdown(loop, signal=None):
    """Clean up tasks on shutdown."""
    if signal:
        print(f"Received exit signal {signal.name}")

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            print(f"Error during shutdown: {result}")

    loop.stop()
```

## 9. Common Async Patterns

### Producer-Consumer with Queue

```python
async def producer(queue: asyncio.Queue, items: list):
    for item in items:
        await queue.put(item)
    await queue.put(None)  # Sentinel

async def consumer(queue: asyncio.Queue):
    while True:
        item = await queue.get()
        if item is None:
            break
        await process(item)
        queue.task_done()

async def pipeline():
    queue = asyncio.Queue(maxsize=100)
    await asyncio.gather(
        producer(queue, data),
        consumer(queue),
    )
```

### Periodic Tasks

```python
async def periodic(interval: float, func, *args):
    """Run a function periodically."""
    while True:
        await func(*args)
        await asyncio.sleep(interval)

async def main():
    task = asyncio.create_task(periodic(60, check_health))
    try:
        await run_server()
    finally:
        task.cancel()
```

### Event Coordination

```python
async def coordinated_work():
    event = asyncio.Event()

    async def waiter():
        print("Waiting for signal...")
        await event.wait()
        print("Signal received!")

    async def signaler():
        await asyncio.sleep(2)
        event.set()

    await asyncio.gather(waiter(), signaler())
```

## 10. Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_user():
    user = await fetch_user(1)
    assert user["name"] == "Alice"

@pytest.mark.asyncio
async def test_concurrent_fetches():
    results = await asyncio.gather(
        fetch_user(1),
        fetch_user(2),
    )
    assert len(results) == 2

# Mocking async functions
from unittest.mock import AsyncMock

async def test_with_mock():
    mock_client = AsyncMock()
    mock_client.fetch.return_value = {"id": 1, "name": "Test"}
    result = await mock_client.fetch("/users/1")
    assert result["name"] == "Test"
```

## 11. Performance Tips

| Tip | Why |
|-----|-----|
| Reuse `ClientSession` | Avoids TCP connection overhead per request |
| Use semaphores | Prevents overwhelming servers or file descriptors |
| Prefer `TaskGroup` over `gather` | Better error propagation and structured concurrency |
| Use `asyncio.to_thread()` for blocking I/O | Offloads blocking calls without custom executor |
| Batch database queries | Reduces round trips -- use `executemany` or bulk inserts |
| Profile with `asyncio.get_event_loop().slow_callback_duration` | Detects blocking calls in the event loop |
