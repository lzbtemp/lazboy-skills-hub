#!/usr/bin/env python3
"""
Database Migration Generator

Generates timestamped SQL migration files with UP and DOWN sections
for common database operations.

Supported actions:
  - create_table: Create a new table with column specifications
  - add_column: Add a column to an existing table
  - add_index: Add an index to an existing table
  - drop_column: Remove a column from an existing table
  - rename_column: Rename a column in an existing table
  - rename_table: Rename a table
  - add_foreign_key: Add a foreign key constraint
  - create_enum: Create a PostgreSQL enum type

Usage:
    python generate_migration.py create_table users "id:serial:pk, name:varchar(255):not_null, email:varchar(255):not_null:unique, created_at:timestamptz:not_null:default_now"
    python generate_migration.py add_column orders "shipping_address:text, discount_pct:numeric(5,2):default_0"
    python generate_migration.py add_index orders "user_id, status" --name idx_orders_user_status
    python generate_migration.py drop_column users "middle_name"
    python generate_migration.py add_column users "role:varchar(50):not_null:default_user" --output ./migrations
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Column type mappings and defaults
# ---------------------------------------------------------------------------

TYPE_MAP = {
    "serial": "SERIAL",
    "bigserial": "BIGSERIAL",
    "smallserial": "SMALLSERIAL",
    "int": "INTEGER",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "text": "TEXT",
    "varchar": "VARCHAR",
    "char": "CHAR",
    "boolean": "BOOLEAN",
    "bool": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMP",
    "timestamptz": "TIMESTAMPTZ",
    "time": "TIME",
    "timetz": "TIMETZ",
    "numeric": "NUMERIC",
    "decimal": "DECIMAL",
    "real": "REAL",
    "float": "FLOAT",
    "double": "DOUBLE PRECISION",
    "json": "JSON",
    "jsonb": "JSONB",
    "uuid": "UUID",
    "bytea": "BYTEA",
    "inet": "INET",
    "cidr": "CIDR",
    "macaddr": "MACADDR",
    "tsvector": "TSVECTOR",
    "tsquery": "TSQUERY",
    "interval": "INTERVAL",
    "money": "MONEY",
    "xml": "XML",
    "point": "POINT",
    "line": "LINE",
    "polygon": "POLYGON",
    "circle": "CIRCLE",
}

# Common default value shortcuts
DEFAULT_SHORTCUTS = {
    "default_now": "DEFAULT NOW()",
    "default_true": "DEFAULT TRUE",
    "default_false": "DEFAULT FALSE",
    "default_0": "DEFAULT 0",
    "default_empty": "DEFAULT ''",
    "default_uuid": "DEFAULT gen_random_uuid()",
}


def parse_column_spec(spec: str) -> dict:
    """Parse a column specification string into a structured dict.

    Format: name:type[:modifier1[:modifier2...]]

    Examples:
        id:serial:pk
        name:varchar(255):not_null
        email:varchar(255):not_null:unique
        created_at:timestamptz:not_null:default_now
        price:numeric(10,2):not_null:default_0
        is_active:boolean:not_null:default_true
    """
    parts = spec.strip().split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid column spec '{spec}'. Expected format: name:type[:modifiers]")

    name = parts[0].strip()
    raw_type = parts[1].strip()
    modifiers = [m.strip().lower() for m in parts[2:]]

    # Handle types with parentheses like varchar(255) or numeric(10,2)
    type_match = re.match(r"(\w+)(\(.+\))?", raw_type)
    if not type_match:
        raise ValueError(f"Invalid type '{raw_type}' in column spec '{spec}'")

    base_type = type_match.group(1).lower()
    type_params = type_match.group(2) or ""

    if base_type not in TYPE_MAP:
        # Allow unknown types (could be custom/enum types)
        sql_type = raw_type.upper()
    else:
        sql_type = TYPE_MAP[base_type] + type_params.upper()

    column = {
        "name": name,
        "type": sql_type,
        "primary_key": False,
        "not_null": False,
        "unique": False,
        "default": None,
        "references": None,
    }

    for mod in modifiers:
        if mod == "pk" or mod == "primary_key":
            column["primary_key"] = True
            column["not_null"] = True
        elif mod == "not_null" or mod == "nn":
            column["not_null"] = True
        elif mod == "unique" or mod == "uq":
            column["unique"] = True
        elif mod == "nullable":
            column["not_null"] = False
        elif mod in DEFAULT_SHORTCUTS:
            column["default"] = DEFAULT_SHORTCUTS[mod]
        elif mod.startswith("default_"):
            value = mod[8:]  # strip "default_"
            column["default"] = f"DEFAULT '{value}'"
        elif mod.startswith("references_"):
            # references_tablename or references_tablename(column)
            column["references"] = mod[11:]

    return column


def parse_columns(column_string: str) -> list:
    """Parse a comma-separated list of column specifications."""
    columns = []
    for spec in column_string.split(","):
        spec = spec.strip()
        if spec:
            columns.append(parse_column_spec(spec))
    return columns


def format_column_definition(col: dict) -> str:
    """Format a single column definition for CREATE TABLE."""
    parts = [f"    {col['name']}", col["type"]]

    if col["not_null"] and not col["primary_key"]:
        parts.append("NOT NULL")
    if col["unique"]:
        parts.append("UNIQUE")
    if col["default"]:
        parts.append(col["default"])

    return " ".join(parts)


def generate_timestamp() -> str:
    """Generate a timestamp string for migration file naming."""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def sanitize_name(name: str) -> str:
    """Sanitize a name for use in SQL identifiers."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()


# ---------------------------------------------------------------------------
# Migration generators
# ---------------------------------------------------------------------------

def generate_create_table(table: str, columns: list, description: str = "") -> tuple[str, str]:
    """Generate CREATE TABLE migration."""
    table = sanitize_name(table)

    # Build column definitions
    col_defs = []
    pk_columns = []
    fk_constraints = []
    unique_constraints = []

    for col in columns:
        col_defs.append(format_column_definition(col))
        if col["primary_key"]:
            pk_columns.append(col["name"])
        if col["references"]:
            ref_table = col["references"]
            ref_col = "id"
            if "(" in ref_table:
                ref_table, ref_col = ref_table.rstrip(")").split("(")
            fk_constraints.append(
                f"    CONSTRAINT fk_{table}_{col['name']} "
                f"FOREIGN KEY ({col['name']}) REFERENCES {ref_table}({ref_col})"
            )

    # Add primary key constraint
    if pk_columns:
        col_defs.append(f"    CONSTRAINT pk_{table} PRIMARY KEY ({', '.join(pk_columns)})")

    # Add foreign key constraints
    col_defs.extend(fk_constraints)

    columns_sql = ",\n".join(col_defs)

    up = f"""-- Create {table} table
CREATE TABLE IF NOT EXISTS {table} (
{columns_sql}
);

-- Add indexes for foreign keys and commonly queried columns
"""
    # Auto-generate indexes for foreign key columns
    for col in columns:
        if col["references"]:
            up += f"CREATE INDEX IF NOT EXISTS idx_{table}_{col['name']} ON {table} ({col['name']});\n"

    # Auto-generate created_at/updated_at indexes if present
    for col in columns:
        if col["name"] in ("created_at", "updated_at"):
            up += f"CREATE INDEX IF NOT EXISTS idx_{table}_{col['name']} ON {table} ({col['name']});\n"

    down = f"""-- Drop {table} table
DROP TABLE IF EXISTS {table} CASCADE;
"""

    return up.rstrip(), down.rstrip()


def generate_add_column(table: str, columns: list, description: str = "") -> tuple[str, str]:
    """Generate ADD COLUMN migration."""
    table = sanitize_name(table)

    up_parts = [f"-- Add column(s) to {table}"]
    down_parts = [f"-- Remove column(s) from {table}"]

    for col in columns:
        col_def = f"{col['type']}"
        if col["not_null"] and col["default"]:
            col_def += f" NOT NULL {col['default']}"
        elif col["not_null"]:
            # For NOT NULL without default, need a default for existing rows
            col_def += f" NOT NULL"
            up_parts.append(f"-- WARNING: Adding NOT NULL column without default will fail if table has existing rows.")
            up_parts.append(f"-- Consider: ALTER TABLE {table} ADD COLUMN {col['name']} {col['type']}; followed by UPDATE + ALTER SET NOT NULL")
        if col["default"] and not col["not_null"]:
            col_def += f" {col['default']}"
        if col["unique"]:
            col_def += " UNIQUE"

        up_parts.append(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col['name']} {col_def};")

        if col["references"]:
            ref_table = col["references"]
            ref_col = "id"
            if "(" in ref_table:
                ref_table, ref_col = ref_table.rstrip(")").split("(")
            up_parts.append(
                f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_{col['name']} "
                f"FOREIGN KEY ({col['name']}) REFERENCES {ref_table}({ref_col});"
            )
            up_parts.append(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col['name']} ON {table} ({col['name']});")

        down_parts.append(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col['name']};")

    return "\n".join(up_parts), "\n".join(down_parts)


def generate_add_index(table: str, column_string: str, index_name: Optional[str] = None,
                       unique: bool = False, method: str = "btree",
                       where_clause: Optional[str] = None) -> tuple[str, str]:
    """Generate ADD INDEX migration."""
    table = sanitize_name(table)
    columns = [c.strip() for c in column_string.split(",")]
    col_names = "_".join(sanitize_name(c.split()[0]) for c in columns)  # Handle "col DESC"

    if not index_name:
        prefix = "uidx" if unique else "idx"
        index_name = f"{prefix}_{table}_{col_names}"

    unique_kw = "UNIQUE " if unique else ""
    method_clause = f" USING {method}" if method != "btree" else ""
    where_sql = f"\n  WHERE {where_clause}" if where_clause else ""

    col_list = ", ".join(columns)

    up = f"""-- Add {'unique ' if unique else ''}index on {table}({col_list})
CREATE {unique_kw}INDEX CONCURRENTLY IF NOT EXISTS {index_name}
  ON {table}{method_clause} ({col_list}){where_sql};
"""

    down = f"""-- Remove index {index_name}
DROP INDEX CONCURRENTLY IF EXISTS {index_name};
"""

    return up.rstrip(), down.rstrip()


def generate_drop_column(table: str, column_string: str) -> tuple[str, str]:
    """Generate DROP COLUMN migration."""
    table = sanitize_name(table)
    columns = [c.strip() for c in column_string.split(",")]

    up_parts = [f"-- Drop column(s) from {table}"]
    down_parts = [
        f"-- Restore column(s) to {table}",
        f"-- WARNING: Data in dropped columns cannot be automatically restored.",
        f"-- Review and update the column definitions and defaults below.",
    ]

    for col in columns:
        col = sanitize_name(col)
        up_parts.append(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col};")
        down_parts.append(f"-- ALTER TABLE {table} ADD COLUMN {col} TEXT; -- TODO: Set correct type and constraints")

    return "\n".join(up_parts), "\n".join(down_parts)


def generate_rename_column(table: str, column_string: str) -> tuple[str, str]:
    """Generate RENAME COLUMN migration. column_string format: old_name:new_name"""
    table = sanitize_name(table)
    pairs = [c.strip() for c in column_string.split(",")]

    up_parts = [f"-- Rename column(s) in {table}"]
    down_parts = [f"-- Revert column rename(s) in {table}"]

    for pair in pairs:
        parts = pair.split(":")
        if len(parts) != 2:
            raise ValueError(f"Rename format must be 'old_name:new_name', got: '{pair}'")
        old_name = sanitize_name(parts[0])
        new_name = sanitize_name(parts[1])
        up_parts.append(f"ALTER TABLE {table} RENAME COLUMN {old_name} TO {new_name};")
        down_parts.append(f"ALTER TABLE {table} RENAME COLUMN {new_name} TO {old_name};")

    return "\n".join(up_parts), "\n".join(down_parts)


def generate_rename_table(table: str, new_name: str) -> tuple[str, str]:
    """Generate RENAME TABLE migration."""
    table = sanitize_name(table)
    new_name = sanitize_name(new_name)

    up = f"""-- Rename table {table} to {new_name}
ALTER TABLE {table} RENAME TO {new_name};
"""
    down = f"""-- Revert: rename table {new_name} back to {table}
ALTER TABLE {new_name} RENAME TO {table};
"""
    return up.rstrip(), down.rstrip()


def generate_add_foreign_key(table: str, column_string: str) -> tuple[str, str]:
    """Generate ADD FOREIGN KEY migration. column_string format: column:ref_table or column:ref_table(ref_col)"""
    table = sanitize_name(table)
    specs = [c.strip() for c in column_string.split(",")]

    up_parts = [f"-- Add foreign key(s) to {table}"]
    down_parts = [f"-- Remove foreign key(s) from {table}"]

    for spec in specs:
        parts = spec.split(":")
        if len(parts) < 2:
            raise ValueError(f"Foreign key format: 'column:ref_table' or 'column:ref_table(ref_col)', got: '{spec}'")

        col = sanitize_name(parts[0])
        ref = parts[1]
        ref_table = ref
        ref_col = "id"
        if "(" in ref:
            ref_table, ref_col = ref.rstrip(")").split("(")

        constraint_name = f"fk_{table}_{col}"

        up_parts.append(
            f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name}\n"
            f"  FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col});"
        )
        up_parts.append(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table} ({col});")

        down_parts.append(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name};")
        down_parts.append(f"DROP INDEX IF EXISTS idx_{table}_{col};")

    return "\n".join(up_parts), "\n".join(down_parts)


def generate_create_enum(enum_name: str, values_string: str) -> tuple[str, str]:
    """Generate CREATE TYPE enum migration."""
    enum_name = sanitize_name(enum_name)
    values = [v.strip().strip("'\"") for v in values_string.split(",")]
    values_sql = ", ".join(f"'{v}'" for v in values)

    up = f"""-- Create enum type {enum_name}
CREATE TYPE {enum_name} AS ENUM ({values_sql});
"""
    down = f"""-- Drop enum type {enum_name}
DROP TYPE IF EXISTS {enum_name};
"""
    return up.rstrip(), down.rstrip()


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------

def build_migration_content(action: str, up_sql: str, down_sql: str, description: str = "") -> str:
    """Build the full migration file content."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""-- Migration: {description or action}
-- Generated: {timestamp}
-- Action: {action}
--
-- This migration file contains UP (apply) and DOWN (revert) sections.
-- Apply with: psql -f <filename>
-- To revert, run the DOWN section manually or with a migration tool.

-- ============================================================================
-- UP: Apply migration
-- ============================================================================

BEGIN;

{up_sql}

COMMIT;

-- ============================================================================
-- DOWN: Revert migration
-- ============================================================================

-- To revert this migration, run the following in a transaction:
--
-- BEGIN;
--
{chr(10).join('-- ' + line if line.strip() else '--' for line in down_sql.split(chr(10)))}
--
-- COMMIT;
"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate timestamped SQL migration files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Actions and column spec format:
  create_table  <table> <columns>     Create a new table
  add_column    <table> <columns>     Add columns to existing table
  add_index     <table> <columns>     Add an index
  drop_column   <table> <columns>     Drop columns from a table
  rename_column <table> <old:new>     Rename a column
  rename_table  <table> <new_name>    Rename a table
  add_fk        <table> <col:ref>     Add foreign key
  create_enum   <name>  <values>      Create an enum type

Column spec format: name:type[:modifier1[:modifier2...]]
  Types: serial, int, bigint, text, varchar(N), boolean, timestamptz, jsonb, uuid, numeric(P,S), ...
  Modifiers: pk, not_null (nn), unique (uq), nullable, default_now, default_true, default_false,
             default_0, default_uuid, default_<value>, references_<table>

Examples:
  %(prog)s create_table users "id:serial:pk, name:varchar(255):nn, email:varchar(255):nn:uq, created_at:timestamptz:nn:default_now"
  %(prog)s add_column orders "discount:numeric(5,2):default_0, notes:text"
  %(prog)s add_index orders "user_id, status" --name idx_orders_user_status
  %(prog)s add_index products "name" --method gin --gin-trgm
  %(prog)s drop_column users "middle_name, suffix"
  %(prog)s rename_column users "fname:first_name, lname:last_name"
  %(prog)s add_fk orders "user_id:users, product_id:products"
  %(prog)s create_enum order_status "pending, processing, shipped, delivered, cancelled"
        """,
    )

    parser.add_argument(
        "action",
        choices=["create_table", "add_column", "add_index", "drop_column",
                 "rename_column", "rename_table", "add_fk", "create_enum"],
        help="Migration action to perform.",
    )
    parser.add_argument(
        "table",
        help="Table name (or enum name for create_enum).",
    )
    parser.add_argument(
        "columns",
        help="Column specifications (format depends on action).",
    )
    parser.add_argument(
        "--output", "-o",
        default=".",
        help="Output directory for migration file (default: current directory).",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Custom index name (for add_index action).",
    )
    parser.add_argument(
        "--unique",
        action="store_true",
        help="Create a unique index (for add_index action).",
    )
    parser.add_argument(
        "--method",
        default="btree",
        choices=["btree", "hash", "gin", "gist", "brin"],
        help="Index method (for add_index action, default: btree).",
    )
    parser.add_argument(
        "--where",
        default=None,
        dest="where_clause",
        help="Partial index WHERE clause (for add_index action).",
    )
    parser.add_argument(
        "--description", "-d",
        default="",
        help="Human-readable description for the migration.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print migration to stdout instead of writing a file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the generated SQL without writing a file.",
    )

    args = parser.parse_args()

    try:
        action = args.action
        table = args.table
        columns_str = args.columns

        if action == "create_table":
            columns = parse_columns(columns_str)
            up_sql, down_sql = generate_create_table(table, columns)
            desc = args.description or f"Create {table} table"

        elif action == "add_column":
            columns = parse_columns(columns_str)
            up_sql, down_sql = generate_add_column(table, columns)
            col_names = ", ".join(c["name"] for c in columns)
            desc = args.description or f"Add {col_names} to {table}"

        elif action == "add_index":
            up_sql, down_sql = generate_add_index(
                table, columns_str,
                index_name=args.name,
                unique=args.unique,
                method=args.method,
                where_clause=args.where_clause,
            )
            desc = args.description or f"Add index on {table}({columns_str})"

        elif action == "drop_column":
            up_sql, down_sql = generate_drop_column(table, columns_str)
            desc = args.description or f"Drop {columns_str} from {table}"

        elif action == "rename_column":
            up_sql, down_sql = generate_rename_column(table, columns_str)
            desc = args.description or f"Rename columns in {table}"

        elif action == "rename_table":
            up_sql, down_sql = generate_rename_table(table, columns_str)
            desc = args.description or f"Rename {table} to {columns_str}"

        elif action == "add_fk":
            up_sql, down_sql = generate_add_foreign_key(table, columns_str)
            desc = args.description or f"Add foreign key(s) to {table}"

        elif action == "create_enum":
            up_sql, down_sql = generate_create_enum(table, columns_str)
            desc = args.description or f"Create enum type {table}"

        else:
            print(f"Unknown action: {action}", file=sys.stderr)
            sys.exit(2)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    migration_content = build_migration_content(action, up_sql, down_sql, desc)

    if args.stdout or args.dry_run:
        print(migration_content)
        return

    # Write to file
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = generate_timestamp()
    safe_desc = sanitize_name(desc.replace(" ", "_"))[:50]
    filename = f"{timestamp}_{safe_desc}.sql"
    filepath = output_dir / filename

    filepath.write_text(migration_content, encoding="utf-8")
    print(f"Migration generated: {filepath}")
    print(f"Description: {desc}")


if __name__ == "__main__":
    main()
