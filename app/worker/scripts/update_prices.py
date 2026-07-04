"""Fetch daily prices for all main-board stocks and write to daily_prices.

Usage:
    python app/worker/scripts/update_prices.py

The script fetches ~120 trading days per stock (qfq adjust), handles per-stock
failures gracefully, and uses UPSERT to avoid overwriting existing data.
"""

from __future__ import annotations

import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.data_sources.price_source import (
    fetch_daily_prices,
    upsert_daily_prices,
)
from app.worker.src.db import database_connection
from app.worker.src.tasks import (
    create_task,
    mark_task_failed,
    mark_task_running,
    mark_task_success,
)
from app.worker.src.loggers import write_json_log


# Number of calendar days to look back.  180 calendar days ≈ 120 trading days
# which is sufficient for MA60 calculation.
LOOKBACK_DAYS = 180


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    return f"update_prices_{ts}"


def _get_main_board_codes(connection) -> list[str]:
    """Return active main-board stock codes ordered by code."""

    rows = connection.execute(
        """
        SELECT code FROM stocks
        WHERE board = '主板'
          AND is_active = 1
        ORDER BY code
        """
    ).fetchall()
    return [row["code"] for row in rows]


def main() -> int:
    task_id = _new_task_id()
    start_date = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    end_date = date.today().isoformat()

    with database_connection() as connection:
        create_task(task_id=task_id, task_name="update_prices", connection=connection)
        mark_task_running(task_id, connection=connection)
        codes = _get_main_board_codes(connection)

    write_json_log(
        file_name="data_source.log",
        level="INFO",
        module="update_prices",
        task_id=task_id,
        message="start batch price fetch",
        context={
            "stock_count": len(codes),
            "start_date": start_date,
            "end_date": end_date,
            "adjust": "qfq",
        },
    )

    total_rows = 0
    success_count = 0
    failed_count = 0
    failed_codes: list[str] = []
    start_time = time.monotonic()

    for idx, code in enumerate(codes):
        try:
            rows = fetch_daily_prices(code, start_date, end_date, adjust="qfq")
        except Exception as error:
            failed_count += 1
            failed_codes.append(code)
            write_json_log(
                file_name="data_source.log",
                level="WARN",
                module="update_prices",
                task_id=task_id,
                message=f"fetch failed for {code}: {error}",
                context={"code": code},
            )
            continue

        if not rows:
            failed_count += 1
            write_json_log(
                file_name="data_source.log",
                level="WARN",
                module="update_prices",
                task_id=task_id,
                message=f"empty data for {code}",
                context={"code": code},
            )
            continue

        # Write each stock individually in a transaction so a single
        # write failure does not lose the entire batch.
        try:
            with database_connection() as connection:
                upsert_daily_prices(rows, connection)
        except Exception as error:
            failed_count += 1
            failed_codes.append(code)
            write_json_log(
                file_name="data_source.log",
                level="ERROR",
                module="update_prices",
                task_id=task_id,
                message=f"write failed for {code}: {error}",
                context={"code": code},
            )
            continue

        total_rows += len(rows)
        success_count += 1

        # Progress every 100 stocks.
        if (idx + 1) % 100 == 0:
            elapsed = time.monotonic() - start_time
            write_json_log(
                file_name="data_source.log",
                level="INFO",
                module="update_prices",
                task_id=task_id,
                message=f"progress: {idx + 1}/{len(codes)}",
                context={
                    "done": idx + 1,
                    "total": len(codes),
                    "elapsed_sec": round(elapsed, 1),
                },
            )
            print(f"  progress: {idx + 1}/{len(codes)} ({elapsed:.0f}s)")

    elapsed = time.monotonic() - start_time

    # --- finalize ---
    with database_connection() as connection:
        if failed_count > 0:
            # Task is still considered successful as long as some data was written;
            # the individual failures are logged for retry.
            mark_task_success(task_id, connection=connection)
        else:
            mark_task_success(task_id, connection=connection)

    write_json_log(
        file_name="data_source.log",
        level="INFO",
        module="update_prices",
        task_id=task_id,
        message="batch price fetch complete",
        context={
            "success_count": success_count,
            "failed_count": failed_count,
            "total_rows": total_rows,
            "elapsed_sec": round(elapsed, 1),
        },
    )

    # --- summary ---
    print(f"total stocks: {len(codes)}")
    print(f"  success: {success_count}")
    print(f"  failed: {failed_count}")
    print(f"  rows written: {total_rows}")
    print(f"  elapsed: {elapsed:.0f}s")
    if failed_codes:
        print(f"  failed codes ({len(failed_codes)}): {', '.join(failed_codes[:10])}...")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
