#!/usr/bin/env python3
"""Scaffold a data pipeline project structure.

Usage:
    python generate_pipeline.py --name my_pipeline --source db --target s3
    python generate_pipeline.py --name api_ingest --source api --target db
    python generate_pipeline.py --name file_etl --source file --target file --output-dir ./projects

Generates:
    <pipeline_name>/
        config/
            settings.py           # Configuration management
            __init__.py
        extract/
            extractor.py          # Data extraction logic
            __init__.py
        transform/
            transformer.py        # Data transformation logic
            __init__.py
        load/
            loader.py             # Data loading logic
            __init__.py
        tests/
            test_extractor.py
            test_transformer.py
            test_loader.py
            test_pipeline.py
            conftest.py
            __init__.py
        pipeline.py               # Main pipeline runner
        pyproject.toml
        Dockerfile
        docker-compose.yml
        .env.example
        .gitignore
        README.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

SOURCE_TYPES = ("db", "api", "file")
TARGET_TYPES = ("db", "s3", "file")


def _config_settings(name: str, source: str, target: str) -> str:
    """Generate config/settings.py."""
    source_config = {
        "db": dedent("""\
            # Database source settings
            SOURCE_DB_HOST: str = "localhost"
            SOURCE_DB_PORT: int = 5432
            SOURCE_DB_NAME: str = ""
            SOURCE_DB_USER: str = ""
            SOURCE_DB_PASSWORD: str = ""
            SOURCE_DB_SCHEMA: str = "public"
            SOURCE_QUERY: str = ""
            SOURCE_BATCH_SIZE: int = 10000
        """),
        "api": dedent("""\
            # API source settings
            SOURCE_API_BASE_URL: str = ""
            SOURCE_API_KEY: str = ""
            SOURCE_API_ENDPOINT: str = ""
            SOURCE_API_PAGE_SIZE: int = 100
            SOURCE_API_TIMEOUT: int = 30
            SOURCE_API_MAX_RETRIES: int = 3
        """),
        "file": dedent("""\
            # File source settings
            SOURCE_FILE_PATH: str = ""
            SOURCE_FILE_FORMAT: str = "csv"  # csv, json, parquet
            SOURCE_FILE_ENCODING: str = "utf-8"
            SOURCE_FILE_DELIMITER: str = ","
        """),
    }

    target_config = {
        "db": dedent("""\
            # Database target settings
            TARGET_DB_HOST: str = "localhost"
            TARGET_DB_PORT: int = 5432
            TARGET_DB_NAME: str = ""
            TARGET_DB_USER: str = ""
            TARGET_DB_PASSWORD: str = ""
            TARGET_DB_SCHEMA: str = "public"
            TARGET_TABLE: str = ""
            TARGET_WRITE_MODE: str = "append"  # append, replace, upsert
            TARGET_BATCH_SIZE: int = 5000
        """),
        "s3": dedent("""\
            # S3 target settings
            TARGET_S3_BUCKET: str = ""
            TARGET_S3_PREFIX: str = ""
            TARGET_S3_REGION: str = "us-east-1"
            TARGET_S3_FORMAT: str = "parquet"  # parquet, csv, json
            TARGET_S3_PARTITION_BY: list[str] = []
            TARGET_S3_COMPRESSION: str = "snappy"
        """),
        "file": dedent("""\
            # File target settings
            TARGET_FILE_PATH: str = ""
            TARGET_FILE_FORMAT: str = "parquet"  # csv, json, parquet
            TARGET_FILE_ENCODING: str = "utf-8"
            TARGET_FILE_COMPRESSION: str | None = None
        """),
    }

    return dedent(f'''\
        """Pipeline configuration for {name}.

        Settings are loaded from environment variables with an optional .env file.
        Uses pydantic-settings for validation and type coercion.
        """

        from __future__ import annotations

        from pydantic_settings import BaseSettings
        from pydantic import Field


        class PipelineSettings(BaseSettings):
            """Configuration for the {name} pipeline."""

            # General
            PIPELINE_NAME: str = "{name}"
            LOG_LEVEL: str = "INFO"
            DRY_RUN: bool = False

            {_indent(source_config[source], 4)}
            {_indent(target_config[target], 4)}

            model_config = {{"env_file": ".env", "env_file_encoding": "utf-8"}}


        def get_settings() -> PipelineSettings:
            """Load and return pipeline settings."""
            return PipelineSettings()
    ''')


def _extractor(name: str, source: str) -> str:
    """Generate extract/extractor.py."""
    implementations = {
        "db": dedent('''\
            """Data extractor for database source."""

            from __future__ import annotations

            import logging
            from typing import Iterator

            from sqlalchemy import create_engine, text
            from sqlalchemy.engine import Engine

            from config.settings import PipelineSettings

            logger = logging.getLogger(__name__)


            class DatabaseExtractor:
                """Extract data from a relational database in batches."""

                def __init__(self, settings: PipelineSettings):
                    self.settings = settings
                    self._engine: Engine | None = None

                @property
                def engine(self) -> Engine:
                    if self._engine is None:
                        url = (
                            f"postgresql+psycopg2://"
                            f"{self.settings.SOURCE_DB_USER}:{self.settings.SOURCE_DB_PASSWORD}"
                            f"@{self.settings.SOURCE_DB_HOST}:{self.settings.SOURCE_DB_PORT}"
                            f"/{self.settings.SOURCE_DB_NAME}"
                        )
                        self._engine = create_engine(
                            url,
                            pool_size=5,
                            max_overflow=10,
                            pool_pre_ping=True,
                            pool_recycle=1800,
                        )
                    return self._engine

                def extract(self) -> Iterator[list[dict]]:
                    """Yield batches of records from the database.

                    Uses server-side cursors for memory-efficient processing.
                    """
                    query = self.settings.SOURCE_QUERY
                    batch_size = self.settings.SOURCE_BATCH_SIZE
                    logger.info("Starting extraction with batch_size=%d", batch_size)

                    with self.engine.connect().execution_options(
                        stream_results=True
                    ) as conn:
                        result = conn.execute(text(query))
                        columns = list(result.keys())
                        batch = []
                        row_count = 0

                        for row in result:
                            batch.append(dict(zip(columns, row)))
                            if len(batch) >= batch_size:
                                row_count += len(batch)
                                logger.debug("Yielding batch of %d rows (total: %d)", len(batch), row_count)
                                yield batch
                                batch = []

                        if batch:
                            row_count += len(batch)
                            yield batch

                    logger.info("Extraction complete: %d rows", row_count)

                def close(self):
                    """Dispose of the database engine."""
                    if self._engine:
                        self._engine.dispose()
                        self._engine = None
        '''),
        "api": dedent('''\
            """Data extractor for REST API source."""

            from __future__ import annotations

            import logging
            from typing import Iterator

            import httpx
            from tenacity import retry, stop_after_attempt, wait_exponential

            from config.settings import PipelineSettings

            logger = logging.getLogger(__name__)


            class APIExtractor:
                """Extract data from a paginated REST API."""

                def __init__(self, settings: PipelineSettings):
                    self.settings = settings
                    self._client: httpx.Client | None = None

                @property
                def client(self) -> httpx.Client:
                    if self._client is None:
                        headers = {}
                        if self.settings.SOURCE_API_KEY:
                            headers["Authorization"] = f"Bearer {self.settings.SOURCE_API_KEY}"
                        self._client = httpx.Client(
                            base_url=self.settings.SOURCE_API_BASE_URL,
                            headers=headers,
                            timeout=self.settings.SOURCE_API_TIMEOUT,
                        )
                    return self._client

                @retry(
                    stop=stop_after_attempt(3),
                    wait=wait_exponential(multiplier=1, min=1, max=30),
                )
                def _fetch_page(self, page: int) -> dict:
                    """Fetch a single API page with retry logic."""
                    response = self.client.get(
                        self.settings.SOURCE_API_ENDPOINT,
                        params={"page": page, "page_size": self.settings.SOURCE_API_PAGE_SIZE},
                    )
                    response.raise_for_status()
                    return response.json()

                def extract(self) -> Iterator[list[dict]]:
                    """Yield batches of records from the API.

                    Each page is yielded as a separate batch.
                    """
                    page = 1
                    total = 0
                    logger.info("Starting API extraction from %s", self.settings.SOURCE_API_ENDPOINT)

                    while True:
                        data = self._fetch_page(page)
                        records = data.get("results", data.get("data", []))
                        if not records:
                            break
                        total += len(records)
                        logger.debug("Page %d: %d records (total: %d)", page, len(records), total)
                        yield records
                        page += 1

                    logger.info("Extraction complete: %d records from %d pages", total, page - 1)

                def close(self):
                    """Close the HTTP client."""
                    if self._client:
                        self._client.close()
                        self._client = None
        '''),
        "file": dedent('''\
            """Data extractor for file source."""

            from __future__ import annotations

            import csv
            import json
            import logging
            from pathlib import Path
            from typing import Iterator

            from config.settings import PipelineSettings

            logger = logging.getLogger(__name__)


            class FileExtractor:
                """Extract data from local files (CSV, JSON, Parquet)."""

                def __init__(self, settings: PipelineSettings):
                    self.settings = settings

                def extract(self) -> Iterator[list[dict]]:
                    """Yield the file contents as a single batch.

                    For large files, consider chunked reading.
                    """
                    file_path = Path(self.settings.SOURCE_FILE_PATH)
                    fmt = self.settings.SOURCE_FILE_FORMAT.lower()
                    logger.info("Reading %s file: %s", fmt, file_path)

                    if fmt == "csv":
                        yield from self._read_csv(file_path)
                    elif fmt in ("json", "jsonl"):
                        yield from self._read_json(file_path)
                    elif fmt == "parquet":
                        yield from self._read_parquet(file_path)
                    else:
                        raise ValueError(f"Unsupported file format: {fmt}")

                def _read_csv(self, path: Path) -> Iterator[list[dict]]:
                    with open(path, newline="", encoding=self.settings.SOURCE_FILE_ENCODING) as f:
                        reader = csv.DictReader(f, delimiter=self.settings.SOURCE_FILE_DELIMITER)
                        batch = []
                        for row in reader:
                            batch.append(dict(row))
                            if len(batch) >= 10000:
                                yield batch
                                batch = []
                        if batch:
                            yield batch

                def _read_json(self, path: Path) -> Iterator[list[dict]]:
                    text = path.read_text(encoding=self.settings.SOURCE_FILE_ENCODING)
                    if text.strip().startswith("["):
                        yield json.loads(text)
                    else:
                        records = [json.loads(line) for line in text.splitlines() if line.strip()]
                        yield records

                def _read_parquet(self, path: Path) -> Iterator[list[dict]]:
                    import pandas as pd
                    df = pd.read_parquet(path)
                    yield df.to_dict(orient="records")

                def close(self):
                    pass
        '''),
    }
    return implementations[source]


def _transformer(name: str) -> str:
    """Generate transform/transformer.py."""
    return dedent(f'''\
        """Data transformer for {name} pipeline.

        Implement your transformation logic here. This module is called
        between extraction and loading.
        """

        from __future__ import annotations

        import logging
        from datetime import datetime, timezone
        from typing import Any

        from config.settings import PipelineSettings

        logger = logging.getLogger(__name__)


        class DataTransformer:
            """Transform extracted data before loading.

            Customize the transform() method with your business logic:
            - Field renaming and mapping
            - Type casting and normalization
            - Filtering invalid records
            - Enrichment and derived fields
            - Deduplication
            """

            def __init__(self, settings: PipelineSettings):
                self.settings = settings
                self._stats = {{"transformed": 0, "filtered": 0, "errors": 0}}

            def transform(self, batch: list[dict]) -> list[dict]:
                """Transform a batch of records.

                Args:
                    batch: List of raw records from the extractor.

                Returns:
                    List of transformed records ready for loading.
                """
                results = []
                for record in batch:
                    try:
                        transformed = self._transform_record(record)
                        if transformed is not None:
                            results.append(transformed)
                            self._stats["transformed"] += 1
                        else:
                            self._stats["filtered"] += 1
                    except Exception as exc:
                        self._stats["errors"] += 1
                        logger.warning("Transform error on record: %s", exc)

                return results

            def _transform_record(self, record: dict) -> dict | None:
                """Transform a single record.

                Override this method with your transformation logic.
                Return None to filter out the record.

                Args:
                    record: Raw record dictionary.

                Returns:
                    Transformed record or None to skip.
                """
                # --- Example transformations (customize these) ---

                # Normalize column names to snake_case lowercase
                normalized = {{
                    k.strip().lower().replace(" ", "_"): v
                    for k, v in record.items()
                }}

                # Add metadata
                normalized["_pipeline"] = self.settings.PIPELINE_NAME
                normalized["_ingested_at"] = datetime.now(timezone.utc).isoformat()

                return normalized

            @property
            def stats(self) -> dict:
                """Return transformation statistics."""
                return dict(self._stats)
    ''')


def _loader(name: str, target: str) -> str:
    """Generate load/loader.py."""
    implementations = {
        "db": dedent('''\
            """Data loader for database target."""

            from __future__ import annotations

            import logging

            from sqlalchemy import create_engine, text
            from sqlalchemy.engine import Engine

            from config.settings import PipelineSettings

            logger = logging.getLogger(__name__)


            class DatabaseLoader:
                """Load data into a relational database."""

                def __init__(self, settings: PipelineSettings):
                    self.settings = settings
                    self._engine: Engine | None = None
                    self._total_loaded = 0

                @property
                def engine(self) -> Engine:
                    if self._engine is None:
                        url = (
                            f"postgresql+psycopg2://"
                            f"{self.settings.TARGET_DB_USER}:{self.settings.TARGET_DB_PASSWORD}"
                            f"@{self.settings.TARGET_DB_HOST}:{self.settings.TARGET_DB_PORT}"
                            f"/{self.settings.TARGET_DB_NAME}"
                        )
                        self._engine = create_engine(url, pool_size=5, pool_pre_ping=True)
                    return self._engine

                def load(self, batch: list[dict]) -> int:
                    """Load a batch of records into the target table.

                    Uses bulk insert for performance. Returns the number
                    of records loaded.
                    """
                    if not batch:
                        return 0

                    if self.settings.DRY_RUN:
                        logger.info("[DRY RUN] Would load %d records", len(batch))
                        return len(batch)

                    table = self.settings.TARGET_TABLE
                    columns = list(batch[0].keys())
                    placeholders = ", ".join(f":{col}" for col in columns)
                    col_names = ", ".join(columns)

                    insert_sql = text(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})")

                    with self.engine.begin() as conn:
                        conn.execute(insert_sql, batch)

                    self._total_loaded += len(batch)
                    logger.debug("Loaded %d records (total: %d)", len(batch), self._total_loaded)
                    return len(batch)

                @property
                def total_loaded(self) -> int:
                    return self._total_loaded

                def close(self):
                    if self._engine:
                        self._engine.dispose()
                        self._engine = None
        '''),
        "s3": dedent('''\
            """Data loader for S3 target."""

            from __future__ import annotations

            import io
            import logging
            from datetime import datetime, timezone

            import boto3
            from botocore.config import Config

            from config.settings import PipelineSettings

            logger = logging.getLogger(__name__)


            class S3Loader:
                """Load data to Amazon S3 as Parquet, CSV, or JSON."""

                def __init__(self, settings: PipelineSettings):
                    self.settings = settings
                    self._client = None
                    self._part_number = 0
                    self._total_loaded = 0

                @property
                def client(self):
                    if self._client is None:
                        config = Config(
                            region_name=self.settings.TARGET_S3_REGION,
                            retries={"max_attempts": 3, "mode": "adaptive"},
                        )
                        self._client = boto3.client("s3", config=config)
                    return self._client

                def load(self, batch: list[dict]) -> int:
                    """Write a batch of records to S3.

                    Each batch is written as a separate file part.
                    """
                    import pandas as pd

                    if not batch:
                        return 0

                    if self.settings.DRY_RUN:
                        logger.info("[DRY RUN] Would upload %d records to S3", len(batch))
                        return len(batch)

                    df = pd.DataFrame(batch)
                    fmt = self.settings.TARGET_S3_FORMAT.lower()
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    key = (
                        f"{self.settings.TARGET_S3_PREFIX}/{timestamp}"
                        f"/part_{self._part_number:05d}.{fmt}"
                    )

                    buffer = io.BytesIO()
                    if fmt == "parquet":
                        df.to_parquet(buffer, index=False, compression=self.settings.TARGET_S3_COMPRESSION)
                    elif fmt == "csv":
                        df.to_csv(buffer, index=False)
                    elif fmt == "json":
                        buffer.write(df.to_json(orient="records", lines=True).encode())

                    buffer.seek(0)
                    self.client.put_object(
                        Bucket=self.settings.TARGET_S3_BUCKET,
                        Key=key,
                        Body=buffer.getvalue(),
                    )

                    self._part_number += 1
                    self._total_loaded += len(batch)
                    logger.debug("Uploaded %d records to s3://%s/%s", len(batch), self.settings.TARGET_S3_BUCKET, key)
                    return len(batch)

                @property
                def total_loaded(self) -> int:
                    return self._total_loaded

                def close(self):
                    self._client = None
        '''),
        "file": dedent('''\
            """Data loader for file target."""

            from __future__ import annotations

            import csv
            import json
            import logging
            from pathlib import Path

            from config.settings import PipelineSettings

            logger = logging.getLogger(__name__)


            class FileLoader:
                """Load data to local files (CSV, JSON, Parquet)."""

                def __init__(self, settings: PipelineSettings):
                    self.settings = settings
                    self._total_loaded = 0
                    self._initialized = False

                def load(self, batch: list[dict]) -> int:
                    """Append a batch of records to the target file."""
                    if not batch:
                        return 0

                    if self.settings.DRY_RUN:
                        logger.info("[DRY RUN] Would write %d records to file", len(batch))
                        return len(batch)

                    path = Path(self.settings.TARGET_FILE_PATH)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    fmt = self.settings.TARGET_FILE_FORMAT.lower()

                    if fmt == "csv":
                        self._write_csv(path, batch)
                    elif fmt in ("json", "jsonl"):
                        self._write_jsonl(path, batch)
                    elif fmt == "parquet":
                        self._write_parquet(path, batch)

                    self._total_loaded += len(batch)
                    logger.debug("Wrote %d records to %s (total: %d)", len(batch), path, self._total_loaded)
                    return len(batch)

                def _write_csv(self, path: Path, batch: list[dict]):
                    mode = "a" if self._initialized else "w"
                    with open(path, mode, newline="", encoding=self.settings.TARGET_FILE_ENCODING) as f:
                        writer = csv.DictWriter(f, fieldnames=batch[0].keys())
                        if not self._initialized:
                            writer.writeheader()
                            self._initialized = True
                        writer.writerows(batch)

                def _write_jsonl(self, path: Path, batch: list[dict]):
                    with open(path, "a", encoding=self.settings.TARGET_FILE_ENCODING) as f:
                        for record in batch:
                            f.write(json.dumps(record, default=str) + "\\n")
                    self._initialized = True

                def _write_parquet(self, path: Path, batch: list[dict]):
                    import pandas as pd
                    df = pd.DataFrame(batch)
                    if self._initialized and path.exists():
                        existing = pd.read_parquet(path)
                        df = pd.concat([existing, df], ignore_index=True)
                    df.to_parquet(path, index=False)
                    self._initialized = True

                @property
                def total_loaded(self) -> int:
                    return self._total_loaded

                def close(self):
                    pass
        '''),
    }
    return implementations[target]


def _pipeline_runner(name: str, source: str, target: str) -> str:
    """Generate pipeline.py."""
    extractor_class = {
        "db": "DatabaseExtractor",
        "api": "APIExtractor",
        "file": "FileExtractor",
    }[source]
    loader_class = {
        "db": "DatabaseLoader",
        "s3": "S3Loader",
        "file": "FileLoader",
    }[target]

    return dedent(f'''\
        #!/usr/bin/env python3
        """Main runner for the {name} pipeline.

        Usage:
            python pipeline.py
            python pipeline.py --dry-run
            LOG_LEVEL=DEBUG python pipeline.py
        """

        from __future__ import annotations

        import argparse
        import logging
        import sys
        import time
        from datetime import datetime, timezone

        from config.settings import get_settings
        from extract.extractor import {extractor_class}
        from transform.transformer import DataTransformer
        from load.loader import {loader_class}

        logger = logging.getLogger(__name__)


        def run_pipeline(dry_run: bool = False) -> dict:
            """Execute the ETL pipeline.

            Returns:
                Dictionary with pipeline execution statistics.
            """
            settings = get_settings()
            if dry_run:
                settings.DRY_RUN = True

            # Configure logging
            logging.basicConfig(
                level=getattr(logging, settings.LOG_LEVEL),
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            )

            logger.info("Starting pipeline: %s", settings.PIPELINE_NAME)
            start_time = time.time()

            extractor = {extractor_class}(settings)
            transformer = DataTransformer(settings)
            loader = {loader_class}(settings)

            stats = {{
                "pipeline": settings.PIPELINE_NAME,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "batches_processed": 0,
                "records_extracted": 0,
                "records_loaded": 0,
                "status": "running",
            }}

            try:
                for batch in extractor.extract():
                    stats["records_extracted"] += len(batch)

                    transformed = transformer.transform(batch)
                    loaded = loader.load(transformed)

                    stats["records_loaded"] += loaded
                    stats["batches_processed"] += 1

                stats["status"] = "success"

            except Exception as exc:
                logger.exception("Pipeline failed: %s", exc)
                stats["status"] = "failed"
                stats["error"] = str(exc)
                raise

            finally:
                extractor.close()
                loader.close()

                elapsed = time.time() - start_time
                stats["completed_at"] = datetime.now(timezone.utc).isoformat()
                stats["elapsed_seconds"] = round(elapsed, 2)
                stats["transform_stats"] = transformer.stats

                logger.info(
                    "Pipeline %s: %d records extracted, %d loaded in %.2fs",
                    stats["status"],
                    stats["records_extracted"],
                    stats["records_loaded"],
                    elapsed,
                )

            return stats


        def main():
            parser = argparse.ArgumentParser(description="Run the {name} data pipeline.")
            parser.add_argument("--dry-run", action="store_true", help="Run without writing data.")
            args = parser.parse_args()

            try:
                stats = run_pipeline(dry_run=args.dry_run)
                if stats["status"] == "success":
                    sys.exit(0)
                else:
                    sys.exit(1)
            except Exception:
                sys.exit(1)


        if __name__ == "__main__":
            main()
    ''')


def _test_extractor(source: str) -> str:
    """Generate tests/test_extractor.py."""
    extractor_class = {
        "db": "DatabaseExtractor",
        "api": "APIExtractor",
        "file": "FileExtractor",
    }[source]
    return dedent(f'''\
        """Tests for the extractor module."""

        import pytest
        from unittest.mock import MagicMock, patch

        from extract.extractor import {extractor_class}


        @pytest.fixture
        def settings(base_settings):
            """Return settings configured for extraction tests."""
            return base_settings


        class Test{extractor_class}:
            def test_init(self, settings):
                extractor = {extractor_class}(settings)
                assert extractor.settings == settings

            def test_extract_yields_batches(self, settings):
                """Verify that extract() yields lists of dictionaries."""
                # TODO: Implement with appropriate mocking for your source type.
                pass

            def test_close_is_idempotent(self, settings):
                extractor = {extractor_class}(settings)
                extractor.close()
                extractor.close()  # Should not raise
    ''')


def _test_transformer() -> str:
    """Generate tests/test_transformer.py."""
    return dedent('''\
        """Tests for the transformer module."""

        import pytest

        from transform.transformer import DataTransformer


        @pytest.fixture
        def transformer(base_settings):
            return DataTransformer(base_settings)


        class TestDataTransformer:
            def test_transform_normalizes_keys(self, transformer):
                batch = [{"First Name": "Alice", "Last Name": "Smith"}]
                result = transformer.transform(batch)
                assert len(result) == 1
                assert "first_name" in result[0]
                assert "last_name" in result[0]

            def test_transform_adds_metadata(self, transformer):
                batch = [{"id": 1}]
                result = transformer.transform(batch)
                assert "_pipeline" in result[0]
                assert "_ingested_at" in result[0]

            def test_transform_empty_batch(self, transformer):
                result = transformer.transform([])
                assert result == []

            def test_stats_tracking(self, transformer):
                transformer.transform([{"a": 1}, {"b": 2}])
                assert transformer.stats["transformed"] == 2
                assert transformer.stats["errors"] == 0
    ''')


def _test_loader(target: str) -> str:
    """Generate tests/test_loader.py."""
    loader_class = {
        "db": "DatabaseLoader",
        "s3": "S3Loader",
        "file": "FileLoader",
    }[target]
    return dedent(f'''\
        """Tests for the loader module."""

        import pytest
        from unittest.mock import MagicMock, patch

        from load.loader import {loader_class}


        @pytest.fixture
        def loader(base_settings):
            base_settings.DRY_RUN = True
            return {loader_class}(base_settings)


        class Test{loader_class}:
            def test_load_dry_run(self, loader):
                """In dry-run mode, load should report count without writing."""
                batch = [{{"id": 1, "value": "test"}}]
                count = loader.load(batch)
                assert count == 1

            def test_load_empty_batch(self, loader):
                count = loader.load([])
                assert count == 0

            def test_close_is_idempotent(self, loader):
                loader.close()
                loader.close()  # Should not raise
    ''')


def _test_pipeline() -> str:
    """Generate tests/test_pipeline.py."""
    return dedent('''\
        """Integration tests for the full pipeline."""

        import pytest
        from unittest.mock import patch

        from pipeline import run_pipeline


        class TestPipeline:
            def test_dry_run_succeeds(self):
                """Pipeline should complete successfully in dry-run mode."""
                # TODO: Configure test fixtures and mock external dependencies
                pass
    ''')


def _conftest() -> str:
    """Generate tests/conftest.py."""
    return dedent('''\
        """Shared test fixtures."""

        import pytest
        from config.settings import PipelineSettings


        @pytest.fixture
        def base_settings():
            """Return a PipelineSettings instance with test defaults."""
            return PipelineSettings(
                PIPELINE_NAME="test_pipeline",
                LOG_LEVEL="DEBUG",
                DRY_RUN=True,
            )
    ''')


def _pyproject_toml(name: str) -> str:
    """Generate pyproject.toml."""
    return dedent(f'''\
        [build-system]
        requires = ["setuptools>=68.0", "wheel"]
        build-backend = "setuptools.backends._legacy:_Backend"

        [project]
        name = "{name}"
        version = "0.1.0"
        description = "Data pipeline: {name}"
        requires-python = ">=3.11"
        dependencies = [
            "pydantic>=2.0",
            "pydantic-settings>=2.0",
        ]

        [project.optional-dependencies]
        db = ["sqlalchemy>=2.0", "psycopg2-binary>=2.9"]
        api = ["httpx>=0.25", "tenacity>=8.0"]
        s3 = ["boto3>=1.28", "pandas>=2.0", "pyarrow>=14.0"]
        file = ["pandas>=2.0", "pyarrow>=14.0"]
        dev = [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "ruff>=0.1.0",
            "mypy>=1.5",
        ]

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        addopts = "-v --tb=short"

        [tool.ruff]
        line-length = 100
        target-version = "py311"

        [tool.ruff.lint]
        select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]

        [tool.mypy]
        python_version = "3.11"
        strict = true
    ''')


def _dockerfile() -> str:
    """Generate Dockerfile."""
    return dedent('''\
        FROM python:3.12-slim AS base

        WORKDIR /app

        # Install system dependencies
        RUN apt-get update && apt-get install -y --no-install-recommends \\
            build-essential \\
            && rm -rf /var/lib/apt/lists/*

        # Install Python dependencies
        COPY pyproject.toml .
        RUN pip install --no-cache-dir -e ".[db,api,s3,file]"

        # Copy application code
        COPY . .

        # Run as non-root user
        RUN useradd --create-home appuser
        USER appuser

        ENTRYPOINT ["python", "pipeline.py"]
    ''')


def _docker_compose() -> str:
    """Generate docker-compose.yml."""
    return dedent('''\
        services:
          pipeline:
            build: .
            env_file: .env
            depends_on:
              postgres:
                condition: service_healthy
            networks:
              - pipeline-net

          postgres:
            image: postgres:16-alpine
            environment:
              POSTGRES_DB: pipeline_db
              POSTGRES_USER: pipeline
              POSTGRES_PASSWORD: pipeline_secret
            ports:
              - "5432:5432"
            volumes:
              - pgdata:/var/lib/postgresql/data
            healthcheck:
              test: ["CMD-SHELL", "pg_isready -U pipeline"]
              interval: 5s
              timeout: 5s
              retries: 5
            networks:
              - pipeline-net

        volumes:
          pgdata:

        networks:
          pipeline-net:
    ''')


def _env_example(source: str, target: str) -> str:
    """Generate .env.example."""
    lines = [
        "# Pipeline configuration",
        "PIPELINE_NAME=my_pipeline",
        "LOG_LEVEL=INFO",
        "DRY_RUN=false",
        "",
    ]
    if source == "db":
        lines += [
            "# Source database",
            "SOURCE_DB_HOST=localhost",
            "SOURCE_DB_PORT=5432",
            "SOURCE_DB_NAME=source_db",
            "SOURCE_DB_USER=user",
            "SOURCE_DB_PASSWORD=changeme",
            'SOURCE_QUERY=SELECT * FROM my_table WHERE updated_at > :last_run',
            "SOURCE_BATCH_SIZE=10000",
            "",
        ]
    elif source == "api":
        lines += [
            "# Source API",
            "SOURCE_API_BASE_URL=https://api.example.com",
            "SOURCE_API_KEY=your-api-key-here",
            "SOURCE_API_ENDPOINT=/v1/records",
            "SOURCE_API_PAGE_SIZE=100",
            "",
        ]
    elif source == "file":
        lines += [
            "# Source file",
            "SOURCE_FILE_PATH=./data/input.csv",
            "SOURCE_FILE_FORMAT=csv",
            "",
        ]

    if target == "db":
        lines += [
            "# Target database",
            "TARGET_DB_HOST=localhost",
            "TARGET_DB_PORT=5432",
            "TARGET_DB_NAME=target_db",
            "TARGET_DB_USER=user",
            "TARGET_DB_PASSWORD=changeme",
            "TARGET_TABLE=processed_data",
            "TARGET_WRITE_MODE=append",
        ]
    elif target == "s3":
        lines += [
            "# Target S3",
            "TARGET_S3_BUCKET=my-data-bucket",
            "TARGET_S3_PREFIX=pipelines/output",
            "TARGET_S3_REGION=us-east-1",
            "TARGET_S3_FORMAT=parquet",
        ]
    elif target == "file":
        lines += [
            "# Target file",
            "TARGET_FILE_PATH=./data/output.parquet",
            "TARGET_FILE_FORMAT=parquet",
        ]

    return "\n".join(lines) + "\n"


def _gitignore() -> str:
    """Generate .gitignore."""
    return dedent("""\
        # Python
        __pycache__/
        *.py[cod]
        *$py.class
        *.egg-info/
        dist/
        build/
        .eggs/

        # Virtual environments
        .venv/
        venv/
        env/

        # IDE
        .idea/
        .vscode/
        *.swp
        *.swo

        # Environment
        .env
        .env.local

        # Data files (add specific patterns as needed)
        data/output/
        *.parquet
        *.csv.gz

        # Testing
        .pytest_cache/
        htmlcov/
        .coverage

        # OS
        .DS_Store
        Thumbs.db
    """)


def _readme(name: str, source: str, target: str) -> str:
    """Generate README.md."""
    return dedent(f"""\
        # {name}

        Data pipeline: {source} -> transform -> {target}

        ## Quick Start

        ```bash
        # Install dependencies
        pip install -e ".[{source if source != 'file' else 'file'},{target},dev]"

        # Configure
        cp .env.example .env
        # Edit .env with your settings

        # Run
        python pipeline.py

        # Dry run (no writes)
        python pipeline.py --dry-run
        ```

        ## Project Structure

        ```
        {name}/
            config/settings.py      # Configuration (env vars)
            extract/extractor.py    # Data extraction
            transform/transformer.py # Data transformation
            load/loader.py          # Data loading
            tests/                  # Test suite
            pipeline.py             # Main entry point
        ```

        ## Development

        ```bash
        # Install dev dependencies
        pip install -e ".[dev]"

        # Run tests
        pytest

        # Lint
        ruff check .

        # Type check
        mypy .
        ```

        ## Docker

        ```bash
        docker compose up --build
        ```
    """)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _indent(text: str, spaces: int) -> str:
    """Indent all lines of text by the given number of spaces."""
    prefix = " " * spaces
    lines = text.split("\n")
    return "\n".join(prefix + line if line.strip() else line for line in lines)


# ---------------------------------------------------------------------------
# Project generator
# ---------------------------------------------------------------------------

def generate_pipeline(
    name: str,
    source: str,
    target: str,
    output_dir: Path,
) -> Path:
    """Generate a complete data pipeline project structure.

    Args:
        name: Pipeline name (used as directory name and in configs).
        source: Source type (db, api, file).
        target: Target type (db, s3, file).
        output_dir: Parent directory for the generated project.

    Returns:
        Path to the generated project root.
    """
    project_dir = output_dir / name
    if project_dir.exists():
        print(f"Error: Directory already exists: {project_dir}", file=sys.stderr)
        sys.exit(1)

    files = {
        "config/__init__.py": "",
        "config/settings.py": _config_settings(name, source, target),
        "extract/__init__.py": "",
        "extract/extractor.py": _extractor(name, source),
        "transform/__init__.py": "",
        "transform/transformer.py": _transformer(name),
        "load/__init__.py": "",
        "load/loader.py": _loader(name, target),
        "tests/__init__.py": "",
        "tests/conftest.py": _conftest(),
        "tests/test_extractor.py": _test_extractor(source),
        "tests/test_transformer.py": _test_transformer(),
        "tests/test_loader.py": _test_loader(target),
        "tests/test_pipeline.py": _test_pipeline(),
        "pipeline.py": _pipeline_runner(name, source, target),
        "pyproject.toml": _pyproject_toml(name),
        "Dockerfile": _dockerfile(),
        "docker-compose.yml": _docker_compose(),
        ".env.example": _env_example(source, target),
        ".gitignore": _gitignore(),
        "README.md": _readme(name, source, target),
    }

    for relative_path, content in files.items():
        file_path = project_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    print(f"Pipeline project generated at: {project_dir}")
    print(f"  Source: {source}")
    print(f"  Target: {target}")
    print(f"  Files created: {len(files)}")
    print(f"\nNext steps:")
    print(f"  cd {project_dir}")
    print(f"  cp .env.example .env")
    print(f"  pip install -e '.[{source if source != 'file' else 'file'},{target},dev]'")
    print(f"  python pipeline.py --dry-run")

    return project_dir


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a data pipeline project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--name", "-n",
        required=True,
        help="Pipeline name (used as directory name).",
    )
    parser.add_argument(
        "--source", "-s",
        required=True,
        choices=SOURCE_TYPES,
        help="Data source type.",
    )
    parser.add_argument(
        "--target", "-t",
        required=True,
        choices=TARGET_TYPES,
        help="Data target type.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=".",
        help="Parent directory for the generated project (default: current directory).",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()

    if not output_dir.exists():
        print(f"Error: Output directory does not exist: {output_dir}", file=sys.stderr)
        sys.exit(1)

    generate_pipeline(
        name=args.name,
        source=args.source,
        target=args.target,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
