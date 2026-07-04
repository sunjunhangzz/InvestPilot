"""Validate the SQLite schema against the expected first-version structure.

Used by the health-check script and as a pre-condition guard before data pipelines.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


# Expected schema: table name → set of required column names.
# This mirrors docs/02-implementation/数据库设计.md and must be updated when
# the database schema changes.
EXPECTED_SCHEMA: dict[str, set[str]] = {
    "runs": {
        "id",
        "run_id",
        "trade_date",
        "run_type",
        "status",
        "started_at",
        "finished_at",
        "error_message",
        "created_at",
    },
    "system_tasks": {
        "id",
        "task_id",
        "run_id",
        "task_name",
        "status",
        "started_at",
        "finished_at",
        "error_message",
        "created_at",
    },
    "stocks": {
        "code",
        "name",
        "market",
        "board",
        "industry",
        "is_st",
        "is_active",
        "list_date",
        "updated_at",
    },
    "daily_prices": {
        "id",
        "code",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "pct_change",
        "turnover",
        "adjust_type",
        "created_at",
    },
    "factors": {
        "id",
        "run_id",
        "code",
        "trade_date",
        "trend_score",
        "momentum_score",
        "liquidity_score",
        "volatility_score",
        "risk_score",
        "total_score",
        "created_at",
    },
    "recommendations": {
        "id",
        "run_id",
        "trade_date",
        "code",
        "rank",
        "rating",
        "total_score",
        "reason",
        "risk_tags",
        "first_recommended_date",
        "last_recommended_date",
        "tracking_days",
        "created_at",
    },
    "watchlist": {
        "id",
        "code",
        "first_recommended_date",
        "last_recommended_date",
        "status",
        "entry_price",
        "latest_price",
        "tracking_days",
        "min_tracking_days",
        "max_tracking_days",
        "exit_reason",
        "created_at",
        "updated_at",
    },
    "ai_reports": {
        "id",
        "run_id",
        "trade_date",
        "code",
        "report_type",
        "content",
        "model_name",
        "status",
        "error_message",
        "created_at",
    },
    "settings": {
        "key",
        "value",
        "updated_at",
    },
}

# Expected indexes (table, column list).  This is a best-effort check
# because SQLite index names can vary.
EXPECTED_INDEXES: list[tuple[str, tuple[str, ...]]] = [
    ("runs", ("run_id",)),
    ("runs", ("trade_date", "status")),
    ("system_tasks", ("task_id",)),
    ("system_tasks", ("run_id", "task_name")),
    ("stocks", ("code",)),
    ("daily_prices", ("code", "trade_date")),
    ("factors", ("run_id", "total_score")),
    ("recommendations", ("run_id", "rank")),
    ("recommendations", ("trade_date", "rank")),
    ("watchlist", ("status", "tracking_days")),
    ("ai_reports", ("run_id", "code")),
]


@dataclass
class SchemaValidationResult:
    """Result of a schema validation run."""

    valid: bool
    missing_tables: list[str] = field(default_factory=list)
    missing_columns: dict[str, list[str]] = field(default_factory=dict)
    missing_indexes: list[str] = field(default_factory=list)
    unexpected_tables: list[str] = field(default_factory=list)
    extra_columns: dict[str, list[str]] = field(default_factory=dict)
    total_tables: int = 0
    total_indexes: int = 0


def _get_existing_tables(connection: sqlite3.Connection) -> set[str]:
    """Return the set of user table names in the database.

    SQLite internal tables (names starting with 'sqlite_') are excluded
    so they are not flagged as unexpected.
    """

    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    return {
        row["name"]
        for row in rows
        if not row["name"].startswith("sqlite_")
    }


def _get_table_columns(
    connection: sqlite3.Connection, table: str
) -> set[str]:
    """Return the set of column names for a given table."""

    rows = connection.execute(f"PRAGMA table_info('{table}')").fetchall()
    return {row["name"] for row in rows}


def _get_existing_indexes(
    connection: sqlite3.Connection,
) -> list[tuple[str, list[str]]]:
    """Return every user-created index as (table_name, [col1, col2, ...]).

    SQLite automatics (sqlite_autoindex_*) and internal indexes are excluded.
    """

    rows = connection.execute(
        "SELECT name, tbl_name FROM sqlite_master WHERE type = 'index' ORDER BY name"
    ).fetchall()
    indexes: list[tuple[str, list[str]]] = []
    for row in rows:
        name: str = row["name"]
        tbl_name: str = row["tbl_name"]
        # Skip automatic primary-key / unique-constraint indexes.
        if name.startswith("sqlite_autoindex_"):
            continue
        index_info = connection.execute(f"PRAGMA index_info('{name}')").fetchall()
        columns = [col["name"] for col in index_info]
        indexes.append((tbl_name, columns))
    return indexes


def validate_schema(
    connection: sqlite3.Connection,
    expected: dict[str, set[str]] | None = None,
    expected_indexes: list[tuple[str, tuple[str, ...]]] | None = None,
) -> SchemaValidationResult:
    """Check that every expected table and column exists.

    Args:
        connection: An open SQLite connection.
        expected: Optional override for EXPECTED_SCHEMA.
        expected_indexes: Optional override for EXPECTED_INDEXES.

    Returns:
        A SchemaValidationResult with details of any discrepancies.
    """

    expected = expected or EXPECTED_SCHEMA
    expected_indexes = expected_indexes or EXPECTED_INDEXES

    existing_tables = _get_existing_tables(connection)
    result = SchemaValidationResult(
        valid=True,
        total_tables=len(existing_tables),
        total_indexes=0,
    )

    # --- tables: missing ---
    for table in expected:
        if table not in existing_tables:
            result.missing_tables.append(table)
            result.valid = False

    # --- tables: unexpected (not in expected set) ---
    for table in existing_tables:
        if table not in expected:
            result.unexpected_tables.append(table)
            # unexpected tables are informational, not a hard failure
            # in case the user has non-project tables in the same file

    # --- columns: missing and extra ---
    for table in expected:
        if table not in existing_tables:
            continue  # already reported above
        existing_columns = _get_table_columns(connection, table)

        missing_cols = sorted(expected[table] - existing_columns)
        if missing_cols:
            result.missing_columns[table] = missing_cols
            result.valid = False

        extra_cols = sorted(existing_columns - expected[table])
        if extra_cols:
            result.extra_columns[table] = extra_cols

    # --- indexes: best-effort check ---
    existing_indexes = _get_existing_indexes(connection)
    result.total_indexes = len(existing_indexes)

    for table, expected_cols in expected_indexes:
        found = any(
            tbl == table and tuple(cols) == expected_cols
            for tbl, cols in existing_indexes
        )
        if not found:
            index_desc = f"{table}({', '.join(expected_cols)})"
            result.missing_indexes.append(index_desc)
            result.valid = False

    return result


def format_validation_result(result: SchemaValidationResult) -> str:
    """Return a human-readable summary of a schema validation result."""

    lines: list[str] = []
    lines.append(f"Tables found: {result.total_tables}")
    lines.append(f"Indexes found: {result.total_indexes}")

    if result.valid and not result.unexpected_tables and not result.extra_columns:
        lines.append("Schema validation: PASSED")
        return "\n".join(lines)

    status = "PASSED" if result.valid else "FAILED"
    lines.append(f"Schema validation: {status}")

    if result.missing_tables:
        lines.append(
            f"Missing tables: {', '.join(sorted(result.missing_tables))}"
        )

    for table, cols in sorted(result.missing_columns.items()):
        lines.append(f"Table {table}: missing columns {', '.join(cols)}")

    for table, cols in sorted(result.extra_columns.items()):
        lines.append(
            f"Table {table}: extra columns {', '.join(cols)} (not in expected schema)"
        )

    if result.unexpected_tables:
        lines.append(
            f"Unexpected tables: {', '.join(sorted(result.unexpected_tables))}"
        )

    if result.missing_indexes:
        lines.append(
            f"Missing indexes: {', '.join(sorted(result.missing_indexes))}"
        )

    return "\n".join(lines)
