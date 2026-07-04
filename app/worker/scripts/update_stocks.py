"""Fetch the A-share stock list from AkShare and write it to the stocks table.

Usage:
    python app/worker/scripts/update_stocks.py

The script is idempotent: repeated runs refresh stock metadata instead of
creating duplicate rows.  B-shares (9xxxxx) and NEEQ (4xxxxx) are excluded.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.data_sources.stock_list import fetch_stock_list, upsert_stocks
from app.worker.src.db import database_connection
from app.worker.src.tasks import (
    create_task,
    mark_task_failed,
    mark_task_running,
    mark_task_success,
)
from app.worker.src.loggers import write_json_log


def _new_task_id() -> str:
    """Generate a unique task ID for this run."""
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    return f"update_stocks_{ts}"


def main() -> int:
    """Fetch stock list and write to SQLite."""

    task_id = _new_task_id()

    with database_connection() as connection:
        create_task(
            task_id=task_id,
            task_name="update_stocks",
            connection=connection,
        )
        mark_task_running(task_id, connection=connection)

    write_json_log(
        file_name="data_source.log",
        level="INFO",
        module="update_stocks",
        task_id=task_id,
        message="start fetch stock list",
    )

    # --- fetch ---
    try:
        stocks, stats = fetch_stock_list()
    except Exception as error:
        write_json_log(
            file_name="data_source.log",
            level="ERROR",
            module="update_stocks",
            task_id=task_id,
            message=f"fetch failed: {error}",
        )
        mark_task_failed(task_id, f"failed to fetch stock list: {error}")
        print(f"fetch failed: {error}", file=sys.stderr)
        return 1

    if not stocks:
        mark_task_failed(task_id, "stock list is empty — no data written")
        print("stock list is empty — no data written", file=sys.stderr)
        return 1

    # --- write ---
    try:
        with database_connection() as connection:
            written = upsert_stocks(stocks, connection)
            mark_task_success(task_id, connection=connection)
    except Exception as error:
        write_json_log(
            file_name="data_source.log",
            level="ERROR",
            module="update_stocks",
            task_id=task_id,
            message=f"write failed: {error}",
        )
        mark_task_failed(task_id, f"failed to write stocks: {error}")
        print(f"write failed: {error}", file=sys.stderr)
        return 1

    write_json_log(
        file_name="data_source.log",
        level="INFO",
        module="update_stocks",
        task_id=task_id,
        message="stock list written",
        context={
            "stock_count": written,
            "main_board_candidates": max(stats.by_board.get("主板", 0) - stats.is_st - stats.is_inactive, 0),
        },
    )

    # --- summary ---
    print(f"written: {written} stocks (UPSERT)")
    for line in stats.summary_lines():
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
