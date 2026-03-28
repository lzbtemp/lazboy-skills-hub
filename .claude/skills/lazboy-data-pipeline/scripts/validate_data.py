#!/usr/bin/env python3
"""Validate data files (CSV, JSON, Parquet) against a JSON Schema.

Usage:
    python validate_data.py --data data.csv --schema schema.json [--output report.json]
    python validate_data.py --data records.json --schema schema.json --format json
    python validate_data.py --data dataset.parquet --schema schema.json

The script checks:
    - Required fields presence
    - Data type conformance
    - Value range constraints (minimum, maximum, minLength, maxLength, pattern)
    - Null/missing value counts per field
    - Duplicate row detection
    - Enum value validation

Output:
    Validation report printed to stdout (and optionally saved as JSON).
    Exit code 0 if all checks pass, 1 if any fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(file_path: Path, file_format: str | None = None) -> list[dict]:
    """Load a data file into a list of dictionaries.

    Supports CSV, JSON (array of objects or newline-delimited), and Parquet.

    Args:
        file_path: Path to the data file.
        file_format: Explicit format override (csv, json, parquet).
            If None, inferred from file extension.

    Returns:
        List of record dictionaries.
    """
    fmt = (file_format or file_path.suffix.lstrip(".")).lower()

    if fmt == "csv":
        return _load_csv(file_path)
    elif fmt in ("json", "jsonl", "ndjson"):
        return _load_json(file_path)
    elif fmt in ("parquet", "pq"):
        return _load_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file format: {fmt}")


def _load_csv(path: Path) -> list[dict]:
    """Load CSV using the csv module (no pandas dependency required)."""
    import csv

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = []
        for row in reader:
            # Convert empty strings to None for null detection
            cleaned = {k: (v if v != "" else None) for k, v in row.items()}
            records.append(cleaned)
    return records


def _load_json(path: Path) -> list[dict]:
    """Load JSON array or newline-delimited JSON."""
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("["):
        return json.loads(text)
    # Newline-delimited JSON
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _load_parquet(path: Path) -> list[dict]:
    """Load Parquet file. Requires pyarrow or fastparquet."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        try:
            import pandas as pd
            df = pd.read_parquet(path)
            return df.where(df.notna(), None).to_dict(orient="records")
        except ImportError:
            raise ImportError(
                "Reading Parquet requires pyarrow or pandas with a Parquet backend. "
                "Install with: pip install pyarrow"
            )
    table = pq.read_table(path)
    return table.to_pydict()  # column-oriented; convert below
    # Actually, convert to list of row dicts:
    df = table.to_pandas()
    return df.where(df.notna(), None).to_dict(orient="records")


def _load_parquet(path: Path) -> list[dict]:
    """Load Parquet file. Requires pyarrow or pandas."""
    try:
        import pandas as pd
        df = pd.read_parquet(path)
        # Replace NaN with None for consistent null handling
        return df.where(df.notna(), None).to_dict(orient="records")
    except ImportError:
        raise ImportError(
            "Reading Parquet requires pandas with pyarrow or fastparquet. "
            "Install with: pip install pandas pyarrow"
        )


# ---------------------------------------------------------------------------
# Schema loading and interpretation
# ---------------------------------------------------------------------------

def load_schema(schema_path: Path) -> dict:
    """Load and validate a JSON Schema file."""
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    if schema.get("type") != "object":
        raise ValueError("Top-level schema type must be 'object'")
    if "properties" not in schema:
        raise ValueError("Schema must define 'properties'")

    return schema


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

JSON_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def check_required_fields(records: list[dict], schema: dict) -> dict:
    """Check that all required fields are present in every record.

    Returns:
        Dict with field-level pass/fail and counts.
    """
    required = set(schema.get("required", []))
    results = {}
    for field in required:
        missing_count = sum(1 for r in records if field not in r)
        results[field] = {
            "check": "required_field_present",
            "status": "PASS" if missing_count == 0 else "FAIL",
            "missing_count": missing_count,
            "total_records": len(records),
        }
    return results


def check_data_types(records: list[dict], schema: dict) -> dict:
    """Check that field values match expected JSON Schema types.

    Handles nullable types specified as ["string", "null"].
    """
    properties = schema.get("properties", {})
    results = {}

    for field, field_schema in properties.items():
        type_spec = field_schema.get("type")
        if type_spec is None:
            continue

        # Handle union types like ["string", "null"]
        nullable = False
        if isinstance(type_spec, list):
            nullable = "null" in type_spec
            types = [t for t in type_spec if t != "null"]
            type_spec = types[0] if types else "string"

        expected_types = JSON_TYPE_MAP.get(type_spec)
        if expected_types is None:
            continue

        invalid_count = 0
        checked = 0
        for record in records:
            value = record.get(field)
            if value is None:
                if not nullable and field in record:
                    invalid_count += 1
                continue
            checked += 1
            # CSV values are strings; attempt type coercion for numeric checks
            if isinstance(value, str) and type_spec in ("integer", "number"):
                try:
                    if type_spec == "integer":
                        int(value)
                    else:
                        float(value)
                    continue
                except (ValueError, TypeError):
                    invalid_count += 1
                    continue
            if not isinstance(value, expected_types):
                invalid_count += 1

        results[field] = {
            "check": "data_type",
            "expected_type": type_spec,
            "nullable": nullable,
            "status": "PASS" if invalid_count == 0 else "FAIL",
            "invalid_count": invalid_count,
            "checked_count": checked,
        }

    return results


def check_value_ranges(records: list[dict], schema: dict) -> dict:
    """Check minimum, maximum, minLength, maxLength, and pattern constraints."""
    import re

    properties = schema.get("properties", {})
    results = {}

    for field, field_schema in properties.items():
        violations = []

        for i, record in enumerate(records):
            value = record.get(field)
            if value is None:
                continue

            # Numeric range checks
            for constraint, op_name, op_fn in [
                ("minimum", ">=", lambda v, c: _to_num(v) is not None and _to_num(v) >= c),
                ("maximum", "<=", lambda v, c: _to_num(v) is not None and _to_num(v) <= c),
                ("exclusiveMinimum", ">", lambda v, c: _to_num(v) is not None and _to_num(v) > c),
                ("exclusiveMaximum", "<", lambda v, c: _to_num(v) is not None and _to_num(v) < c),
            ]:
                if constraint in field_schema:
                    limit = field_schema[constraint]
                    if not op_fn(value, limit):
                        violations.append({
                            "row": i,
                            "constraint": constraint,
                            "limit": limit,
                            "actual": value,
                        })

            # String length checks
            if isinstance(value, str):
                if "minLength" in field_schema and len(value) < field_schema["minLength"]:
                    violations.append({
                        "row": i,
                        "constraint": "minLength",
                        "limit": field_schema["minLength"],
                        "actual": len(value),
                    })
                if "maxLength" in field_schema and len(value) > field_schema["maxLength"]:
                    violations.append({
                        "row": i,
                        "constraint": "maxLength",
                        "limit": field_schema["maxLength"],
                        "actual": len(value),
                    })

            # Pattern check
            if "pattern" in field_schema and isinstance(value, str):
                if not re.match(field_schema["pattern"], value):
                    violations.append({
                        "row": i,
                        "constraint": "pattern",
                        "pattern": field_schema["pattern"],
                        "actual": value,
                    })

            # Enum check
            if "enum" in field_schema:
                if value not in field_schema["enum"]:
                    violations.append({
                        "row": i,
                        "constraint": "enum",
                        "allowed": field_schema["enum"],
                        "actual": value,
                    })

        if violations:
            results[field] = {
                "check": "value_range",
                "status": "FAIL",
                "violation_count": len(violations),
                "first_violations": violations[:5],  # Limit output
            }
        elif any(
            c in field_schema
            for c in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                       "minLength", "maxLength", "pattern", "enum")
        ):
            results[field] = {
                "check": "value_range",
                "status": "PASS",
                "violation_count": 0,
            }

    return results


def _to_num(value: Any) -> float | None:
    """Attempt to convert a value to a number."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


def check_null_counts(records: list[dict], schema: dict) -> dict:
    """Count null/missing values per field."""
    properties = schema.get("properties", {})
    results = {}
    total = len(records)

    for field in properties:
        null_count = sum(
            1 for r in records if r.get(field) is None
        )
        missing_count = sum(
            1 for r in records if field not in r
        )
        null_rate = (null_count / total * 100) if total > 0 else 0.0

        results[field] = {
            "check": "null_counts",
            "null_count": null_count,
            "missing_count": missing_count,
            "null_rate_pct": round(null_rate, 2),
            "total_records": total,
        }

    return results


def check_duplicates(
    records: list[dict],
    schema: dict,
    unique_keys: list[str] | None = None,
) -> dict:
    """Detect duplicate rows.

    If unique_keys is provided, checks uniqueness on that combination of fields.
    Otherwise, checks for fully identical rows.
    """
    if unique_keys:
        seen = Counter()
        for record in records:
            key = tuple(record.get(k) for k in unique_keys)
            seen[key] += 1
        dup_count = sum(count - 1 for count in seen.values() if count > 1)
        dup_keys_sample = [
            {k: v for k, v in zip(unique_keys, key)}
            for key, count in seen.items() if count > 1
        ][:5]
        return {
            "check": "duplicates",
            "key_fields": unique_keys,
            "status": "PASS" if dup_count == 0 else "FAIL",
            "duplicate_count": dup_count,
            "duplicate_keys_sample": dup_keys_sample,
            "total_records": len(records),
        }
    else:
        seen = Counter()
        for record in records:
            key = tuple(sorted(record.items()))
            seen[key] += 1
        dup_count = sum(count - 1 for count in seen.values() if count > 1)
        return {
            "check": "duplicates",
            "key_fields": "(all fields)",
            "status": "PASS" if dup_count == 0 else "FAIL",
            "duplicate_count": dup_count,
            "total_records": len(records),
        }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    data_path: str,
    schema_path: str,
    records: list[dict],
    required_results: dict,
    type_results: dict,
    range_results: dict,
    null_results: dict,
    duplicate_result: dict,
) -> dict:
    """Compile all check results into a unified validation report."""
    all_checks = []

    for field, result in required_results.items():
        all_checks.append({"field": field, **result})
    for field, result in type_results.items():
        all_checks.append({"field": field, **result})
    for field, result in range_results.items():
        all_checks.append({"field": field, **result})

    passed = sum(1 for c in all_checks if c.get("status") == "PASS")
    failed = sum(1 for c in all_checks if c.get("status") == "FAIL")

    if duplicate_result.get("status") == "FAIL":
        failed += 1
    elif duplicate_result.get("status") == "PASS":
        passed += 1

    overall = "PASS" if failed == 0 else "FAIL"

    return {
        "validation_report": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data_file": str(data_path),
            "schema_file": str(schema_path),
            "total_records": len(records),
            "overall_status": overall,
            "summary": {
                "checks_passed": passed,
                "checks_failed": failed,
                "total_checks": passed + failed,
            },
            "required_fields": required_results,
            "data_types": type_results,
            "value_ranges": range_results,
            "null_counts": null_results,
            "duplicates": duplicate_result,
        }
    }


def print_report_summary(report: dict) -> None:
    """Print a human-readable summary of the validation report."""
    r = report["validation_report"]
    status_icon = "PASS" if r["overall_status"] == "PASS" else "FAIL"

    print(f"\n{'='*60}")
    print(f"  Data Validation Report")
    print(f"{'='*60}")
    print(f"  Data file:    {r['data_file']}")
    print(f"  Schema file:  {r['schema_file']}")
    print(f"  Records:      {r['total_records']}")
    print(f"  Timestamp:    {r['timestamp']}")
    print(f"  Status:       {status_icon}")
    print(f"{'='*60}")

    summary = r["summary"]
    print(f"\n  Checks: {summary['checks_passed']} passed, "
          f"{summary['checks_failed']} failed, "
          f"{summary['total_checks']} total")

    # Required fields
    if r["required_fields"]:
        print(f"\n  Required Fields:")
        for field, result in r["required_fields"].items():
            status = result["status"]
            detail = f"missing={result['missing_count']}" if status == "FAIL" else ""
            print(f"    {status:4s}  {field}  {detail}")

    # Data types
    if r["data_types"]:
        print(f"\n  Data Types:")
        for field, result in r["data_types"].items():
            status = result["status"]
            detail = f"invalid={result['invalid_count']}" if status == "FAIL" else ""
            print(f"    {status:4s}  {field} (expected: {result['expected_type']})  {detail}")

    # Value ranges
    if r["value_ranges"]:
        print(f"\n  Value Ranges:")
        for field, result in r["value_ranges"].items():
            status = result["status"]
            detail = f"violations={result['violation_count']}" if status == "FAIL" else ""
            print(f"    {status:4s}  {field}  {detail}")

    # Nulls
    if r["null_counts"]:
        print(f"\n  Null Counts:")
        for field, result in r["null_counts"].items():
            rate = result["null_rate_pct"]
            indicator = "!" if rate > 10 else " "
            print(f"    {indicator} {field}: {result['null_count']}/{result['total_records']} "
                  f"({rate}%)")

    # Duplicates
    dup = r["duplicates"]
    print(f"\n  Duplicates: {dup['status']}  "
          f"(found {dup['duplicate_count']} duplicates in {dup['total_records']} records)")

    print(f"\n{'='*60}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Validate a data file against a JSON Schema.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data", "-d",
        required=True,
        help="Path to the data file (CSV, JSON, or Parquet).",
    )
    parser.add_argument(
        "--schema", "-s",
        required=True,
        help="Path to the JSON Schema file.",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["csv", "json", "jsonl", "parquet"],
        default=None,
        help="Explicit data file format (inferred from extension if omitted).",
    )
    parser.add_argument(
        "--unique-keys", "-u",
        nargs="+",
        default=None,
        help="Field names to use for duplicate detection (space-separated).",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Path to write the JSON validation report.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress human-readable output; only write JSON report.",
    )

    args = parser.parse_args()

    data_path = Path(args.data)
    schema_path = Path(args.schema)

    if not data_path.exists():
        print(f"Error: Data file not found: {data_path}", file=sys.stderr)
        sys.exit(2)
    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(2)

    # Load
    schema = load_schema(schema_path)
    records = load_data(data_path, args.format)

    if not records:
        print("Warning: Data file contains no records.", file=sys.stderr)

    # Validate
    required_results = check_required_fields(records, schema)
    type_results = check_data_types(records, schema)
    range_results = check_value_ranges(records, schema)
    null_results = check_null_counts(records, schema)
    duplicate_result = check_duplicates(records, schema, args.unique_keys)

    # Report
    report = generate_report(
        data_path=args.data,
        schema_path=args.schema,
        records=records,
        required_results=required_results,
        type_results=type_results,
        range_results=range_results,
        null_results=null_results,
        duplicate_result=duplicate_result,
    )

    if not args.quiet:
        print_report_summary(report)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(report, indent=2, default=str))
        if not args.quiet:
            print(f"Report written to: {output_path}")

    # Exit code
    overall = report["validation_report"]["overall_status"]
    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
