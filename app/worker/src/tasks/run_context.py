"""Run ID generation and runs table helpers."""

from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from app.worker.src.db import connect_database


RunType = Literal["manual", "morning", "afternoon", "scheduled"]
RunStatus = Literal["pending", "running", "success", "failed", "cancelled"]

VALID_RUN_TYPES: set[str] = {"manual", "morning", "afternoon", "scheduled"}
VALID_RUN_STATUSES: set[str] = {
    "pending",
    "running",
    "success",
    "failed",
    "cancelled",
}


def get_today_trade_date() -> str:
    """Return today's date in China timezone as YYYY-MM-DD.

    Later data tasks may replace this with the latest available trading day on
    weekends or holidays. The run ID utility only needs a stable date string.
    """

    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def normalize_trade_date(trade_date: str | date | None = None) -> str:
    """Normalize trade_date to YYYY-MM-DD."""

    if trade_date is None:
        return get_today_trade_date()

    if isinstance(trade_date, date):
        return trade_date.isoformat()

    try:
        return date.fromisoformat(trade_date).isoformat()
    except ValueError as error:
        raise ValueError(f"invalid trade_date: {trade_date}") from error


def validate_run_type(run_type: str) -> None:
    """Validate run_type before writing runs."""

    if run_type not in VALID_RUN_TYPES:
        raise ValueError(f"invalid run_type: {run_type}")


def validate_run_status(status: str) -> None:
    """Validate run status before writing runs."""

    if status not in VALID_RUN_STATUSES:
        raise ValueError(f"invalid run status: {status}")


def format_run_id(
    *,
    trade_date: str | date,
    run_type: RunType,
    sequence: int,
) -> str:
    """Format a run ID as YYYYMMDD-run_type-001."""

    validate_run_type(run_type)
    normalized_date = normalize_trade_date(trade_date).replace("-", "")
    if sequence < 1:
        raise ValueError("run_id sequence must be positive")

    return f"{normalized_date}-{run_type}-{sequence:03d}"


def get_next_run_sequence(
    *,
    connection: sqlite3.Connection,
    trade_date: str | date,
    run_type: RunType,
) -> int:
    """Return the next sequence for a trade date and run type."""

    validate_run_type(run_type)
    normalized_date = normalize_trade_date(trade_date)
    run_id_prefix = f"{normalized_date.replace('-', '')}-{run_type}-"

    rows = connection.execute(
        """
        SELECT run_id
        FROM runs
        WHERE trade_date = :trade_date
          AND run_type = :run_type
          AND run_id LIKE :run_id_pattern
        """,
        {
            "trade_date": normalized_date,
            "run_type": run_type,
            "run_id_pattern": f"{run_id_prefix}%",
        },
    ).fetchall()

    max_sequence = 0
    pattern = re.compile(rf"^{re.escape(run_id_prefix)}(\d{{3}})$")
    for row in rows:
        match = pattern.match(row["run_id"])
        if match:
            max_sequence = max(max_sequence, int(match.group(1)))

    return max_sequence + 1


def create_run(
    *,
    run_type: RunType = "manual",
    trade_date: str | date | None = None,
    status: RunStatus = "pending",
    connection: sqlite3.Connection | None = None,
) -> str:
    """Create a runs row and return a unique run_id."""

    validate_run_type(run_type)
    validate_run_status(status)
    normalized_date = normalize_trade_date(trade_date)
    active_connection = connection or connect_database()

    try:
        with active_connection:
            sequence = get_next_run_sequence(
                connection=active_connection,
                trade_date=normalized_date,
                run_type=run_type,
            )
            run_id = format_run_id(
                trade_date=normalized_date,
                run_type=run_type,
                sequence=sequence,
            )
            active_connection.execute(
                """
                INSERT INTO runs (
                    run_id,
                    trade_date,
                    run_type,
                    status,
                    started_at
                )
                VALUES (
                    :run_id,
                    :trade_date,
                    :run_type,
                    :status,
                    CASE WHEN :status = 'running' THEN datetime('now', 'localtime') ELSE NULL END
                )
                """,
                {
                    "run_id": run_id,
                    "trade_date": normalized_date,
                    "run_type": run_type,
                    "status": status,
                },
            )
            return run_id
    finally:
        if connection is None:
            active_connection.close()
