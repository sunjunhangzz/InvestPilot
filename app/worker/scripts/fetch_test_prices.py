"""Test daily price fetch for 1-3 main board stocks before full batch.

Usage:
    python app/worker/scripts/fetch_test_prices.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.data_sources.price_source import (
    fetch_daily_prices,
    save_raw_prices,
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


# Pick one Shenzhen and one Shanghai main-board stock for smoke testing.
TEST_CODES = ["000001", "600519"]


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    return f"fetch_test_prices_{ts}"


def main() -> int:
    task_id = _new_task_id()

    with database_connection() as connection:
        create_task(task_id=task_id, task_name="fetch_test_prices", connection=connection)
        mark_task_running(task_id, connection=connection)

    # Pull ~120 trading days so we can verify MA60 coverage later.
    start_date = "20260101"
    end_date = "20260704"

    write_json_log(
        file_name="data_source.log",
        level="INFO",
        module="fetch_test_prices",
        task_id=task_id,
        message="start test price fetch",
        context={"codes": TEST_CODES, "start": start_date, "end": end_date},
    )

    all_rows: list[dict] = []
    for code in TEST_CODES:
        try:
            # We also need the raw DataFrame for save_raw_prices.
            import akshare as ak  # type: ignore[import-untyped]
            from app.worker.src.data_sources.price_source import to_sina_symbol

            raw_df = ak.stock_zh_a_daily(
                symbol=to_sina_symbol(code),
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            save_raw_prices(code, raw_df)
        except Exception as error:
            write_json_log(
                file_name="data_source.log",
                level="ERROR",
                module="fetch_test_prices",
                task_id=task_id,
                message=f"raw save failed for {code}: {error}",
            )

        try:
            rows = fetch_daily_prices(code, start_date, end_date, adjust="qfq")
            all_rows.extend(rows)
            print(f"  {code}: {len(rows)} trading days")
        except Exception as error:
            write_json_log(
                file_name="data_source.log",
                level="ERROR",
                module="fetch_test_prices",
                task_id=task_id,
                message=f"fetch failed for {code}: {error}",
            )
            print(f"  {code}: FAILED — {error}")

    if not all_rows:
        mark_task_failed(task_id, "no price data fetched")
        print("no price data fetched", file=sys.stderr)
        return 1

    # --- write ---
    try:
        with database_connection() as connection:
            written = upsert_daily_prices(all_rows, connection)
            mark_task_success(task_id, connection=connection)
    except Exception as error:
        mark_task_failed(task_id, f"write failed: {error}")
        print(f"write failed: {error}", file=sys.stderr)
        return 1

    write_json_log(
        file_name="data_source.log",
        level="INFO",
        module="fetch_test_prices",
        task_id=task_id,
        message="test price fetch complete",
        context={"written": written, "codes": TEST_CODES},
    )

    # --- verify ---
    print(f"written: {written} rows (UPSERT)")
    with database_connection() as connection:
        for code in TEST_CODES:
            row = connection.execute(
                """
                SELECT COUNT(*) AS cnt,
                       MIN(trade_date) AS first_date,
                       MAX(trade_date) AS last_date
                FROM daily_prices
                WHERE code = ?
                """,
                (code,),
            ).fetchone()
            print(f"  {code}: {row['cnt']} rows, {row['first_date']} ~ {row['last_date']}")

        # Show one sample row.
        sample = connection.execute(
            "SELECT * FROM daily_prices WHERE code = ? ORDER BY trade_date DESC LIMIT 1",
            (TEST_CODES[0],),
        ).fetchone()
        print(f"  sample: {dict(sample)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
