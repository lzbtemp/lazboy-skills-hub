---
name: lazboy-data-pipeline
description: "Build data pipelines for La-Z-Boy analytics and reporting. Covers ETL/ELT patterns, data validation, scheduling, error handling, and data quality monitoring using Python, Pandas, and Airflow. Use when building data ingestion or transformation workflows."
version: "1.0.0"
category: Data/AI
tags: [data, ai, python, pipeline, etl]
---

# La-Z-Boy Data Pipeline Skill

Standards for building reliable data pipelines at La-Z-Boy.

**Reference files — load when needed:**
- `references/data-sources.md` — approved data source catalog
- `references/schema-registry.md` — data schema definitions

**Scripts — run when needed:**
- `scripts/validate_data.py` — run data quality checks on a dataset
- `scripts/generate_pipeline.py` — scaffold a new data pipeline

---

## 1. Pipeline Architecture

```
Source → Extract → Validate → Transform → Load → Monitor
```

### Data Sources at La-Z-Boy
| Source | Type | Frequency |
|---|---|---|
| SAP ERP | Product/inventory data | Daily |
| Salesforce | Customer/sales data | Hourly |
| E-commerce DB | Online orders | Real-time |
| Google Analytics | Web traffic | Daily |

## 2. ETL Pattern Template

```python
import pandas as pd
from datetime import datetime
from pathlib import Path

class SkillsDataPipeline:
    def __init__(self, source_config: dict):
        self.config = source_config
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def extract(self) -> pd.DataFrame:
        """Extract data from source system."""
        df = pd.read_sql(self.config["query"], self.config["connection"])
        self.log(f"Extracted {len(df)} rows")
        return df

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data quality."""
        assert not df.empty, "No data extracted"
        assert df["id"].nunique() == len(df), "Duplicate IDs found"
        null_pct = df.isnull().sum() / len(df)
        assert (null_pct < 0.05).all(), f"Null rate exceeds 5%: {null_pct[null_pct >= 0.05]}"
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply business transformations."""
        df["processed_at"] = datetime.now()
        df["category"] = df["category"].str.strip().str.title()
        df = df.drop_duplicates(subset=["id"], keep="last")
        return df

    def load(self, df: pd.DataFrame) -> None:
        """Load into target system."""
        df.to_sql("skills_dim", self.config["target_conn"],
                  if_exists="append", index=False, method="multi")
        self.log(f"Loaded {len(df)} rows")

    def run(self) -> None:
        """Execute full pipeline."""
        df = self.extract()
        df = self.validate(df)
        df = self.transform(df)
        self.load(df)
```

## 3. Data Quality Rules

| Check | Threshold | Action |
|---|---|---|
| Null percentage | < 5% | Warn |
| Duplicate rows | 0% | Block |
| Schema drift | No new columns | Alert |
| Row count change | < 50% variance | Alert |
| Freshness | < 24 hours | Alert |

## 4. Error Handling

- Retry transient failures 3 times with exponential backoff
- Log all failures with run ID, source, and error details
- Send alerts to Slack `#data-alerts` channel
- Never silently drop rows — log and quarantine bad data

## 5. Scheduling (Airflow DAG)

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

dag = DAG(
    "lazboy_skills_pipeline",
    schedule_interval="0 6 * * *",  # Daily at 6 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
    },
)
```
