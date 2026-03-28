# Schema Registry and Schema Management for Data Pipelines

## Overview

Schema management ensures that data producers and consumers agree on the structure, types, and semantics of exchanged data. A well-implemented schema strategy prevents data corruption, simplifies debugging, and enables safe schema evolution in production.

---

## 1. Schema Versioning

### Semantic Versioning for Schemas

Apply semantic versioning to schemas to communicate the nature of changes:

- **Major version (v2.0.0):** Breaking changes. Fields removed, types changed incompatibly, required fields added without defaults.
- **Minor version (v1.1.0):** Backward-compatible additions. New optional fields, new enum values appended.
- **Patch version (v1.0.1):** Documentation or metadata updates. No structural change.

### Version Storage Strategy

```
schemas/
  orders/
    v1/
      order.json        # v1.0.0 schema
      CHANGELOG.md
    v2/
      order.json        # v2.0.0 schema (breaking)
      CHANGELOG.md
    latest -> v2/       # symlink to current version
```

### Schema Version in Data

Embed the schema version in every record to enable consumers to parse correctly:

```json
{
  "_schema": "orders/v2",
  "_schema_version": "2.1.0",
  "order_id": "ORD-12345",
  "total_cents": 4999
}
```

---

## 2. Compatibility Rules

### Backward Compatibility

A new schema is **backward compatible** if data written with the old schema can be read using the new schema.

Rules:
- New fields must have default values.
- Existing fields must not be removed.
- Field types must not change (e.g., `int` to `string`).
- Required fields must not be added without defaults.

```python
# Backward-compatible change: adding an optional field
# v1
{"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}

# v2 (backward compatible)
{
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string", "default": ""}
    },
    "required": ["name"]
}
```

### Forward Compatibility

A new schema is **forward compatible** if data written with the new schema can be read using the old schema.

Rules:
- Consumers must ignore unknown fields.
- No existing field semantics may change.
- Enum values must only be appended, not reordered.

### Full Compatibility

Both backward and forward compatible. This is the safest mode and recommended for critical data paths.

### Compatibility Matrix

| Change Type | Backward | Forward | Full |
|---|---|---|---|
| Add optional field with default | Yes | Yes | Yes |
| Add required field with default | Yes | No | No |
| Add required field without default | No | No | No |
| Remove optional field | No | Yes | No |
| Remove required field | No | No | No |
| Rename field | No | No | No |
| Widen type (int -> long) | Yes | No | No |
| Narrow type (long -> int) | No | Yes | No |
| Add enum value | Yes | No | No |

---

## 3. Schema Evolution Rules

### Safe Evolution Checklist

1. **Never remove a field in the same release it was deprecated.** Mark as deprecated in version N, remove in version N+2.
2. **Never change field semantics.** If `price` meant USD cents and now means USD dollars, create a new field `price_dollars`.
3. **Use union types for gradual migration.** Allow `{"type": ["string", "integer"]}` temporarily.
4. **Version your schemas independently from your code.** A schema change does not require a code release.
5. **Test compatibility automatically in CI.** Validate that new schemas pass compatibility checks against the previous version.

### Migration Pattern

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class SchemaMigration:
    """Represents a single schema migration step."""
    from_version: str
    to_version: str
    description: str
    migrate_fn: callable  # (record: dict) -> dict

    def apply(self, record: dict) -> dict:
        return self.migrate_fn(record)


class SchemaEvolutionManager:
    """Manages schema migrations between versions."""

    def __init__(self):
        self._migrations: list[SchemaMigration] = []

    def register(self, migration: SchemaMigration):
        self._migrations.append(migration)

    def migrate(self, record: dict, from_version: str, to_version: str) -> dict:
        """Apply all necessary migrations to bring a record from one version to another."""
        chain = self._build_chain(from_version, to_version)
        for migration in chain:
            record = migration.apply(record)
        return record

    def _build_chain(self, from_v: str, to_v: str) -> list[SchemaMigration]:
        """Build an ordered chain of migrations between two versions."""
        chain = []
        current = from_v
        while current != to_v:
            migration = next(
                (m for m in self._migrations if m.from_version == current), None
            )
            if migration is None:
                raise ValueError(f"No migration path from {current} to {to_v}")
            chain.append(migration)
            current = migration.to_version
        return chain


# Usage
manager = SchemaEvolutionManager()
manager.register(SchemaMigration(
    from_version="1.0.0",
    to_version="1.1.0",
    description="Add email field with default",
    migrate_fn=lambda r: {**r, "email": r.get("email", "")},
))
manager.register(SchemaMigration(
    from_version="1.1.0",
    to_version="2.0.0",
    description="Rename price_cents to total_cents",
    migrate_fn=lambda r: {
        **{k: v for k, v in r.items() if k != "price_cents"},
        "total_cents": r.get("price_cents", r.get("total_cents", 0)),
    },
))
```

---

## 4. Validation with Pydantic

### Pydantic Models as Schemas

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
from typing import Optional

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderItem(BaseModel):
    product_id: str = Field(..., min_length=1, description="Product identifier")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    unit_price_cents: int = Field(..., ge=0, description="Price per unit in cents")

class Order(BaseModel):
    """Schema for order records in the pipeline.

    Version: 2.1.0
    Compatibility: backward-compatible with v2.0.0
    """
    order_id: str = Field(..., pattern=r"^ORD-\d{5,}$")
    customer_id: str = Field(..., min_length=1)
    status: OrderStatus
    items: list[OrderItem] = Field(..., min_length=1)
    total_cents: int = Field(..., ge=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    created_at: datetime
    updated_at: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("total_cents")
    @classmethod
    def validate_total(cls, v, info):
        """Total must not be negative."""
        if v < 0:
            raise ValueError("total_cents must be non-negative")
        return v

    class Config:
        json_schema_extra = {
            "version": "2.1.0",
            "compatibility": "backward",
        }
```

### Batch Validation

```python
from pydantic import ValidationError

def validate_batch(records: list[dict], model: type[BaseModel]) -> dict:
    """Validate a batch of records against a Pydantic model.

    Returns:
        Dict with 'valid' records, 'invalid' records with errors,
        and summary counts.
    """
    valid = []
    invalid = []
    for i, record in enumerate(records):
        try:
            validated = model.model_validate(record)
            valid.append(validated.model_dump())
        except ValidationError as e:
            invalid.append({
                "index": i,
                "record": record,
                "errors": e.errors(),
            })
    return {
        "valid": valid,
        "invalid": invalid,
        "total": len(records),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "error_rate": len(invalid) / len(records) if records else 0,
    }
```

---

## 5. Validation with JSON Schema

### JSON Schema Definition

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/orders/v2.1.0",
  "title": "Order",
  "description": "Schema for order records - v2.1.0",
  "type": "object",
  "required": ["order_id", "customer_id", "status", "items", "total_cents", "created_at"],
  "properties": {
    "order_id": {
      "type": "string",
      "pattern": "^ORD-\\d{5,}$"
    },
    "customer_id": {
      "type": "string",
      "minLength": 1
    },
    "status": {
      "type": "string",
      "enum": ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    },
    "items": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["product_id", "quantity", "unit_price_cents"],
        "properties": {
          "product_id": {"type": "string", "minLength": 1},
          "quantity": {"type": "integer", "minimum": 1},
          "unit_price_cents": {"type": "integer", "minimum": 0}
        }
      }
    },
    "total_cents": {
      "type": "integer",
      "minimum": 0
    },
    "currency": {
      "type": "string",
      "pattern": "^[A-Z]{3}$",
      "default": "USD"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "notes": {
      "type": ["string", "null"],
      "maxLength": 1000
    }
  },
  "additionalProperties": false
}
```

### JSON Schema Validation in Python

```python
import jsonschema
from jsonschema import Draft202012Validator
import json
from pathlib import Path

class SchemaValidator:
    """Validate records against a JSON Schema."""

    def __init__(self, schema_path: str | Path):
        with open(schema_path) as f:
            self.schema = json.load(f)
        Draft202012Validator.check_schema(self.schema)
        self.validator = Draft202012Validator(self.schema)

    def validate_record(self, record: dict) -> list[str]:
        """Validate a single record. Returns list of error messages."""
        errors = []
        for error in sorted(self.validator.iter_errors(record), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in error.path) or "(root)"
            errors.append(f"{path}: {error.message}")
        return errors

    def validate_batch(self, records: list[dict]) -> dict:
        """Validate a batch of records. Returns summary report."""
        results = {"valid": 0, "invalid": 0, "errors": []}
        for i, record in enumerate(records):
            errs = self.validate_record(record)
            if errs:
                results["invalid"] += 1
                results["errors"].append({"index": i, "errors": errs})
            else:
                results["valid"] += 1
        return results
```

---

## 6. Data Contracts

### What Is a Data Contract?

A data contract is a formal agreement between a data producer and consumer that specifies:

- **Schema:** Field names, types, and constraints.
- **Semantics:** What each field means (business definitions).
- **SLAs:** Freshness guarantees, availability, quality thresholds.
- **Ownership:** Who owns the data, who to contact for issues.
- **Versioning:** How the schema evolves over time.

### Data Contract Template

```yaml
# data-contract.yml
apiVersion: v1
kind: DataContract
metadata:
  name: orders-stream
  version: "2.1.0"
  owner: order-service-team
  contact: orders-team@company.com
  description: Real-time order events from the order service.

schema:
  type: json-schema
  ref: schemas/orders/v2/order.json

quality:
  freshness:
    max_delay_minutes: 5
    measurement: event_time_vs_processing_time
  completeness:
    required_fields_null_rate_max: 0.01  # <1% nulls in required fields
  uniqueness:
    unique_keys: ["order_id"]
    dedup_window_hours: 24
  validity:
    custom_checks:
      - name: total_matches_items
        description: "total_cents == sum(item.quantity * item.unit_price_cents)"
        severity: warning

sla:
  availability: 99.9
  latency_p99_ms: 200
  support_hours: "24x7"

compatibility:
  mode: backward
  validation: ci  # Validated in CI pipeline

consumers:
  - name: analytics-warehouse
    contact: data-eng@company.com
    usage: "Aggregated in daily revenue reports"
  - name: shipping-service
    contact: shipping@company.com
    usage: "Triggers shipment workflows"
```

### Enforcing Contracts in CI

```python
"""CI check: validate that a schema change is compatible with the contract."""

import yaml
import json
from pathlib import Path

def check_contract_compliance(
    contract_path: str,
    new_schema_path: str,
    old_schema_path: str,
) -> list[str]:
    """Verify a new schema complies with the data contract.

    Returns list of violations. Empty means compliant.
    """
    with open(contract_path) as f:
        contract = yaml.safe_load(f)

    with open(new_schema_path) as f:
        new_schema = json.load(f)

    with open(old_schema_path) as f:
        old_schema = json.load(f)

    violations = []
    compat_mode = contract.get("compatibility", {}).get("mode", "backward")

    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))
    old_props = set(old_schema.get("properties", {}).keys())
    new_props = set(new_schema.get("properties", {}).keys())

    if compat_mode in ("backward", "full"):
        # New schema must read old data
        removed_props = old_props - new_props
        if removed_props:
            violations.append(f"Backward: removed properties {removed_props}")

        new_required_fields = new_required - old_required
        for field in new_required_fields:
            if field not in old_props:
                new_field_schema = new_schema["properties"].get(field, {})
                if "default" not in new_field_schema:
                    violations.append(
                        f"Backward: new required field '{field}' has no default"
                    )

    if compat_mode in ("forward", "full"):
        # Old schema must read new data
        if new_schema.get("additionalProperties") is False:
            pass  # Fine, strict mode
        added_required = new_required - old_required
        if added_required:
            violations.append(
                f"Forward: new required fields {added_required} break old consumers"
            )

    return violations
```

---

## 7. Schema Registry Patterns

### Centralized Registry Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Producer A  │────>│  Schema Registry  │<────│  Consumer X  │
│  Producer B  │────>│  (REST API)       │<────│  Consumer Y  │
└─────────────┘     └──────────────────┘     └─────────────┘
                            │
                      ┌─────┴─────┐
                      │ PostgreSQL │
                      │ (storage)  │
                      └───────────┘
```

### Registry API Design

```python
"""Minimal schema registry implementation."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import hashlib
import json

app = FastAPI(title="Schema Registry")

# In production, back this with a database
_schemas: dict[str, dict] = {}  # subject -> {version -> schema_record}


class SchemaRecord(BaseModel):
    subject: str
    version: int
    schema_json: dict
    fingerprint: str
    created_at: datetime
    compatibility: str = "backward"


@app.post("/subjects/{subject}/versions")
def register_schema(subject: str, schema_json: dict, compatibility: str = "backward"):
    """Register a new schema version for a subject.

    Validates compatibility with the previous version before accepting.
    """
    if subject not in _schemas:
        _schemas[subject] = {}

    versions = _schemas[subject]
    new_version = max(versions.keys(), default=0) + 1

    fingerprint = hashlib.sha256(
        json.dumps(schema_json, sort_keys=True).encode()
    ).hexdigest()

    # Check for duplicate
    for v, record in versions.items():
        if record["fingerprint"] == fingerprint:
            return {"subject": subject, "version": v, "status": "already_registered"}

    # Compatibility check against previous version
    if versions:
        prev = versions[max(versions.keys())]
        # In production, use a proper compatibility checker here
        # violations = check_compatibility(prev["schema_json"], schema_json, compatibility)

    record = {
        "subject": subject,
        "version": new_version,
        "schema_json": schema_json,
        "fingerprint": fingerprint,
        "created_at": datetime.utcnow().isoformat(),
        "compatibility": compatibility,
    }
    versions[new_version] = record
    return {"subject": subject, "version": new_version, "fingerprint": fingerprint}


@app.get("/subjects/{subject}/versions/{version}")
def get_schema(subject: str, version: int):
    """Retrieve a specific schema version."""
    if subject not in _schemas or version not in _schemas[subject]:
        raise HTTPException(status_code=404, detail="Schema not found")
    return _schemas[subject][version]


@app.get("/subjects/{subject}/versions/latest")
def get_latest_schema(subject: str):
    """Retrieve the latest schema version."""
    if subject not in _schemas or not _schemas[subject]:
        raise HTTPException(status_code=404, detail="Subject not found")
    latest_version = max(_schemas[subject].keys())
    return _schemas[subject][latest_version]
```

---

## 8. Handling Schema Migration in Production

### Zero-Downtime Migration Strategy

1. **Deploy new consumer code** that can read both old and new schema (dual-read).
2. **Register the new schema** in the registry.
3. **Deploy new producer code** that writes the new schema.
4. **Monitor** that all data now arrives in the new format.
5. **Remove old schema support** from consumer code after a deprecation period.

### Migration Execution Checklist

```markdown
## Schema Migration Checklist

- [ ] New schema registered in registry and compatibility validated
- [ ] Data contract updated with new version
- [ ] Consumer code updated to handle both old and new schema
- [ ] Consumer deployed and verified in staging
- [ ] Producer code updated to emit new schema
- [ ] Producer deployed and verified in staging
- [ ] Monitor error rates and data quality metrics for 48h
- [ ] Backfill historical data if needed
- [ ] Remove old schema handling from consumers
- [ ] Archive old schema version (do not delete)
```

### Backfill Script Pattern

```python
"""Backfill records from old schema to new schema."""

import logging
from typing import Iterator

logger = logging.getLogger(__name__)

def backfill_records(
    source: Iterator[dict],
    evolution_manager: "SchemaEvolutionManager",
    sink: callable,
    from_version: str,
    to_version: str,
    batch_size: int = 1000,
    dry_run: bool = False,
) -> dict:
    """Backfill records by migrating them from one schema version to another.

    Args:
        source: Iterator of records in the old format.
        evolution_manager: Schema evolution manager with registered migrations.
        sink: Function that writes a batch of migrated records.
        from_version: Source schema version.
        to_version: Target schema version.
        batch_size: Records per write batch.
        dry_run: If True, validate but do not write.

    Returns:
        Summary statistics.
    """
    stats = {"processed": 0, "migrated": 0, "failed": 0, "skipped": 0}
    batch = []

    for record in source:
        stats["processed"] += 1
        try:
            version = record.get("_schema_version", from_version)
            if version == to_version:
                stats["skipped"] += 1
                continue

            migrated = evolution_manager.migrate(record, version, to_version)
            migrated["_schema_version"] = to_version
            batch.append(migrated)
            stats["migrated"] += 1

            if len(batch) >= batch_size:
                if not dry_run:
                    sink(batch)
                batch = []

        except Exception as e:
            stats["failed"] += 1
            logger.error("Failed to migrate record %s: %s", record.get("id"), e)

    if batch and not dry_run:
        sink(batch)

    logger.info("Backfill complete: %s", stats)
    return stats
```

---

## 9. Best Practices Summary

1. **Always version schemas.** Use semantic versioning and store schemas alongside code.
2. **Default to backward compatibility.** It is the most common and safest mode.
3. **Validate in CI.** Every schema change should be checked for compatibility before merge.
4. **Use data contracts.** Formalize agreements between producers and consumers.
5. **Embed schema version in records.** Enables consumers to parse correctly and migrate on read.
6. **Never delete a schema version.** Archive it. Historical data may still reference it.
7. **Monitor data quality continuously.** Schema validation is necessary but not sufficient. Track null rates, cardinality, and distribution shifts.
8. **Test with realistic data.** Unit tests with contrived records miss edge cases. Use production-sampled data in integration tests.
9. **Plan for rollback.** If a new schema causes issues, consumers should be able to fall back to the previous version without data loss.
10. **Document field semantics.** A field named `price` is ambiguous. Document the unit, currency, and whether it includes tax.
