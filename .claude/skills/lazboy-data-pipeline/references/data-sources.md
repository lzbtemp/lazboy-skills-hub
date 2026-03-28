# Data Source Integration Patterns

## Overview

This reference covers patterns for connecting to common data sources in Python-based data pipelines. Each section includes connection setup, credential management, retry logic, and production-ready examples.

---

## 1. PostgreSQL

### Connection with SQLAlchemy

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

def create_postgres_engine(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 1800,
) -> "Engine":
    """Create a PostgreSQL engine with connection pooling.

    Args:
        host: Database host.
        port: Database port.
        database: Database name.
        user: Database user.
        password: Database password.
        pool_size: Number of persistent connections in the pool.
        max_overflow: Max connections above pool_size allowed temporarily.
        pool_timeout: Seconds to wait for a connection from the pool.
        pool_recycle: Seconds after which a connection is recycled
            to avoid stale connections behind load balancers.

    Returns:
        SQLAlchemy Engine instance.
    """
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,  # Verify connections before use
        echo=False,
    )
    return engine
```

### Batch Reading with Server-Side Cursors

```python
from sqlalchemy import text

def read_postgres_batched(engine, query: str, batch_size: int = 10_000):
    """Read large tables in batches using server-side cursors.

    Yields batches of rows as lists of dictionaries to avoid
    loading the entire result set into memory.
    """
    with engine.connect().execution_options(
        stream_results=True,
        yield_per=batch_size,
    ) as conn:
        result = conn.execute(text(query))
        columns = result.keys()
        batch = []
        for row in result:
            batch.append(dict(zip(columns, row)))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
```

---

## 2. MySQL

### Connection with SQLAlchemy

```python
def create_mysql_engine(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    charset: str = "utf8mb4",
    pool_size: int = 10,
) -> "Engine":
    """Create a MySQL engine with connection pooling.

    Uses PyMySQL driver. Set charset to utf8mb4 for full Unicode support.
    """
    url = (
        f"mysql+pymysql://{user}:{password}@{host}:{port}"
        f"/{database}?charset={charset}"
    )
    engine = create_engine(
        url,
        pool_size=pool_size,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    return engine
```

### Schema Validation on Ingest

```python
from sqlalchemy import inspect

def validate_table_schema(engine, table_name: str, expected_columns: dict) -> list:
    """Validate that a table matches expected schema before ingestion.

    Args:
        engine: SQLAlchemy engine.
        table_name: Name of the table to inspect.
        expected_columns: Dict of {column_name: expected_type_string}.

    Returns:
        List of validation errors. Empty list means valid.
    """
    inspector = inspect(engine)
    columns = {col["name"]: str(col["type"]) for col in inspector.get_columns(table_name)}
    errors = []
    for col_name, expected_type in expected_columns.items():
        if col_name not in columns:
            errors.append(f"Missing column: {col_name}")
        elif expected_type.upper() not in columns[col_name].upper():
            errors.append(
                f"Column {col_name}: expected type containing "
                f"'{expected_type}', got '{columns[col_name]}'"
            )
    return errors
```

---

## 3. MongoDB

### Connection with Retry Logic

```python
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import time

def create_mongo_client(
    uri: str,
    max_pool_size: int = 50,
    server_selection_timeout_ms: int = 5000,
    connect_timeout_ms: int = 10000,
    retry_writes: bool = True,
) -> MongoClient:
    """Create a MongoDB client with connection pooling and retry.

    Args:
        uri: MongoDB connection URI (e.g., mongodb://user:pass@host:27017/db).
        max_pool_size: Maximum number of connections in the pool.
        server_selection_timeout_ms: Timeout for server selection.
        connect_timeout_ms: Timeout for initial connection.
        retry_writes: Enable retryable writes.

    Returns:
        MongoClient instance.
    """
    client = MongoClient(
        uri,
        maxPoolSize=max_pool_size,
        serverSelectionTimeoutMS=server_selection_timeout_ms,
        connectTimeoutMS=connect_timeout_ms,
        retryWrites=retry_writes,
        retryReads=True,
    )
    # Verify connectivity
    client.admin.command("ping")
    return client


def read_mongo_batched(collection, query: dict, batch_size: int = 5000):
    """Read MongoDB documents in batches.

    Uses cursor batching to control memory usage on large collections.
    """
    cursor = collection.find(query).batch_size(batch_size)
    batch = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])  # Serialize ObjectId
        batch.append(doc)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
```

---

## 4. Amazon S3

### Reading Files with boto3

```python
import boto3
from botocore.config import Config
import io
import pandas as pd

def create_s3_client(
    region: str = "us-east-1",
    max_retries: int = 5,
    connect_timeout: int = 10,
    read_timeout: int = 30,
) -> "S3Client":
    """Create an S3 client with retry configuration.

    Uses exponential backoff with jitter for retries.
    Credentials are resolved from the standard chain:
    environment variables, ~/.aws/credentials, IAM role, etc.
    """
    config = Config(
        region_name=region,
        retries={"max_attempts": max_retries, "mode": "adaptive"},
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )
    return boto3.client("s3", config=config)


def read_s3_csv(s3_client, bucket: str, key: str, **csv_kwargs) -> pd.DataFrame:
    """Read a CSV file from S3 into a DataFrame."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(io.BytesIO(response["Body"].read()), **csv_kwargs)


def read_s3_parquet(s3_client, bucket: str, key: str) -> pd.DataFrame:
    """Read a Parquet file from S3 into a DataFrame."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return pd.read_parquet(io.BytesIO(response["Body"].read()))


def list_s3_objects(s3_client, bucket: str, prefix: str) -> list:
    """List all object keys under a prefix, handling pagination."""
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys
```

### Streaming Large Files

```python
def stream_s3_file_lines(s3_client, bucket: str, key: str, encoding: str = "utf-8"):
    """Stream lines from a large S3 text file without loading it all into memory."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"]
    buffer = ""
    for chunk in body.iter_chunks(chunk_size=1024 * 1024):  # 1 MB chunks
        buffer += chunk.decode(encoding)
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            yield line
    if buffer:
        yield buffer
```

---

## 5. REST APIs

### HTTP Client with Retry and Rate Limiting

```python
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

def create_http_client(
    base_url: str,
    timeout: float = 30.0,
    headers: dict | None = None,
    max_connections: int = 20,
) -> httpx.Client:
    """Create an httpx client with connection pooling.

    Args:
        base_url: Base URL for all requests.
        timeout: Request timeout in seconds.
        headers: Default headers for all requests.
        max_connections: Maximum number of concurrent connections.

    Returns:
        httpx.Client configured for production use.
    """
    transport = httpx.HTTPTransport(
        retries=0,  # We handle retries at a higher level
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_connections // 2,
        ),
    )
    return httpx.Client(
        base_url=base_url,
        timeout=timeout,
        headers=headers or {},
        transport=transport,
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
)
def fetch_api_page(client: httpx.Client, endpoint: str, params: dict) -> dict:
    """Fetch a single page from a paginated API with automatic retries.

    Raises httpx.HTTPStatusError for 4xx/5xx responses after retries.
    """
    response = client.get(endpoint, params=params)
    response.raise_for_status()
    return response.json()


def read_paginated_api(
    client: httpx.Client,
    endpoint: str,
    page_param: str = "page",
    page_size_param: str = "page_size",
    page_size: int = 100,
    results_key: str = "results",
    max_pages: int | None = None,
):
    """Read all pages from a paginated REST API.

    Yields individual records across all pages. Supports both
    offset-based and cursor-based pagination patterns.

    Args:
        client: httpx.Client instance.
        endpoint: API endpoint path.
        page_param: Query parameter name for page number.
        page_size_param: Query parameter name for page size.
        page_size: Number of records per page.
        results_key: Key in the response containing the records list.
        max_pages: Maximum pages to fetch (None for unlimited).
    """
    page = 1
    while True:
        params = {page_param: page, page_size_param: page_size}
        data = fetch_api_page(client, endpoint, params)
        records = data.get(results_key, [])
        if not records:
            break
        yield from records
        if max_pages and page >= max_pages:
            break
        page += 1
```

---

## 6. CSV and Parquet Files

### Local File Reading with Validation

```python
import pandas as pd
from pathlib import Path

def read_csv_validated(
    file_path: str | Path,
    required_columns: list[str] | None = None,
    dtype: dict | None = None,
    chunk_size: int | None = None,
    encoding: str = "utf-8",
) -> pd.DataFrame | "pd.io.parsers.TextFileReader":
    """Read a CSV file with schema validation.

    Args:
        file_path: Path to the CSV file.
        required_columns: List of column names that must be present.
        dtype: Column data types to enforce.
        chunk_size: If set, return an iterator of DataFrames.
        encoding: File encoding.

    Raises:
        ValueError: If required columns are missing.

    Returns:
        DataFrame or chunked reader.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if chunk_size:
        reader = pd.read_csv(path, dtype=dtype, chunksize=chunk_size, encoding=encoding)
        return reader

    df = pd.read_csv(path, dtype=dtype, encoding=encoding)

    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    return df


def read_parquet_validated(
    file_path: str | Path,
    required_columns: list[str] | None = None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Read a Parquet file with optional column selection and validation.

    Args:
        file_path: Path to the Parquet file.
        required_columns: Columns that must exist.
        columns: Subset of columns to read (for performance).

    Returns:
        DataFrame.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_parquet(path, columns=columns)

    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    return df
```

---

## 7. Credential Management

### Environment-Based Configuration

```python
import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class DatabaseCredentials:
    """Immutable credentials loaded from environment variables.

    Never log or serialize this object. The __repr__ method is
    overridden to prevent accidental credential exposure.
    """
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_mode: str = "require"

    def __repr__(self) -> str:
        return f"DatabaseCredentials(host={self.host}, database={self.database}, user=***)"

    @classmethod
    def from_env(cls, prefix: str = "DB") -> "DatabaseCredentials":
        """Load credentials from environment variables.

        Expects: {PREFIX}_HOST, {PREFIX}_PORT, {PREFIX}_NAME,
        {PREFIX}_USER, {PREFIX}_PASSWORD.
        """
        def _get(key: str) -> str:
            value = os.environ.get(f"{prefix}_{key}")
            if value is None:
                raise EnvironmentError(f"Missing environment variable: {prefix}_{key}")
            return value

        return cls(
            host=_get("HOST"),
            port=int(_get("PORT")),
            database=_get("NAME"),
            user=_get("USER"),
            password=_get("PASSWORD"),
            ssl_mode=os.environ.get(f"{prefix}_SSL_MODE", "require"),
        )
```

### AWS Secrets Manager Integration

```python
import json
import boto3
from functools import lru_cache

@lru_cache(maxsize=16)
def get_secret(secret_name: str, region: str = "us-east-1") -> dict:
    """Retrieve a secret from AWS Secrets Manager.

    Results are cached for the lifetime of the process.
    For long-running services, use a TTL cache instead.

    Args:
        secret_name: Name or ARN of the secret.
        region: AWS region.

    Returns:
        Parsed JSON secret as a dictionary.
    """
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])
```

---

## 8. Generic Retry Logic

### Configurable Retry Decorator

```python
import time
import logging
from functools import wraps
from typing import Callable, Type

logger = logging.getLogger(__name__)

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay between retries.
        backoff_factor: Multiplier applied to delay after each retry.
        retryable_exceptions: Tuple of exception types that trigger a retry.

    Returns:
        Decorated function.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts:
                        logger.error(
                            "Function %s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise
                    logger.warning(
                        "Function %s attempt %d/%d failed: %s. Retrying in %.1fs.",
                        func.__name__, attempt, max_attempts, exc, delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
        return wrapper
    return decorator
```

---

## 9. Batch vs Streaming Reads

### Decision Matrix

| Factor | Batch | Streaming |
|---|---|---|
| Data size < 1 GB | Preferred | Acceptable |
| Data size > 1 GB | Possible with chunking | Preferred |
| Latency tolerance | Minutes | Seconds |
| Memory constraints | Needs enough for batch | Constant memory |
| Processing complexity | Full dataset operations | Record-by-record |
| Error recovery | Restart entire batch | Resume from offset |

### Streaming Pattern Example

```python
from typing import Iterator, Callable

def streaming_pipeline(
    source: Iterator[dict],
    transform: Callable[[dict], dict | None],
    sink: Callable[[list[dict]], None],
    flush_size: int = 1000,
    flush_interval_seconds: float = 30.0,
) -> dict:
    """Generic streaming pipeline with micro-batched writes.

    Reads records one at a time, applies a transform, and flushes
    to the sink in batches for efficiency.

    Args:
        source: Iterator yielding records.
        transform: Function to transform a record. Return None to skip.
        sink: Function accepting a batch of records to write.
        flush_size: Number of records per flush.
        flush_interval_seconds: Max seconds between flushes.

    Returns:
        Dict with counts: total_read, total_written, total_skipped.
    """
    import time

    buffer = []
    last_flush = time.time()
    stats = {"total_read": 0, "total_written": 0, "total_skipped": 0}

    def flush():
        nonlocal buffer, last_flush
        if buffer:
            sink(buffer)
            stats["total_written"] += len(buffer)
            buffer = []
        last_flush = time.time()

    for record in source:
        stats["total_read"] += 1
        result = transform(record)
        if result is None:
            stats["total_skipped"] += 1
            continue
        buffer.append(result)
        if len(buffer) >= flush_size or (time.time() - last_flush) >= flush_interval_seconds:
            flush()

    flush()  # Final flush
    return stats
```

---

## 10. Putting It All Together

### Complete Pipeline Example

```python
"""Example: Read from PostgreSQL, transform, and write to S3 as Parquet."""

import pandas as pd
import io
from datetime import datetime

def run_pg_to_s3_pipeline(
    pg_engine,
    s3_client,
    query: str,
    bucket: str,
    prefix: str,
    batch_size: int = 50_000,
):
    """Extract from PostgreSQL, transform, and load to S3 as Parquet.

    Processes data in batches to handle large tables within
    bounded memory.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    total_rows = 0
    part = 0

    for batch in read_postgres_batched(pg_engine, query, batch_size=batch_size):
        df = pd.DataFrame(batch)

        # --- Transform ---
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df = df.dropna(subset=["id"])  # Drop rows with no primary key
        df["_ingested_at"] = datetime.utcnow().isoformat()

        # --- Load ---
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow")
        buffer.seek(0)

        key = f"{prefix}/{timestamp}/part_{part:05d}.parquet"
        s3_client.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())

        total_rows += len(df)
        part += 1

    return {"total_rows": total_rows, "parts": part, "s3_prefix": f"{prefix}/{timestamp}/"}
```
