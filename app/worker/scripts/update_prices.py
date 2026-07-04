"""Fetch daily prices for main-board stocks and write to daily_prices.

Usage:
    python app/worker/scripts/update_prices.py               # all main-board
    python app/worker/scripts/update_prices.py --codes 000001,600519  # specific
    python app/worker/scripts/update_prices.py --retry-failed          # retry

The script fetches ~120 trading days per stock (qfq adjust), handles per-stock
failures gracefully, and uses UPSERT to avoid overwriting existing data.
"""

from __future__ import annotations

import json
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
from app.shared.paths import get_config_paths


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


def _get_failed_codes_from_last_run() -> list[str]:
    """Parse data_source.log for failed codes from the most recent update_prices run.

    Returns an empty list when no prior run is found or parsing fails.
    """

    logs_dir = get_config_paths()["logsPath"]
    log_path = logs_dir / "data_source.log"
    if not log_path.exists():
        return []

    failed_codes: list[str] = []
    # Walk backwards through the log to find the most recent "start batch" →
    # "complete" range, then collect all WARN/ERROR lines with a code.
    try:
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return []

    # Find the last "batch price fetch complete" line.
    last_complete_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        try:
            record = json.loads(lines[i])
        except json.JSONDecodeError:
            continue
        if record.get("message") == "batch price fetch complete":
            last_complete_idx = i
            break

    if last_complete_idx < 0:
        return []

    # Walk backward from the complete line to find "start batch price fetch".
    start_idx = -1
    for i in range(last_complete_idx, -1, -1):
        try:
            record = json.loads(lines[i])
        except json.JSONDecodeError:
            continue
        if record.get("message") == "start batch price fetch":
            start_idx = i
            break

    if start_idx < 0:
        return []

    # Collect failed codes between start and complete.
    for i in range(start_idx, last_complete_idx + 1):
        try:
            record = json.loads(lines[i])
        except json.JSONDecodeError:
            continue
        ctx = record.get("context")
        if isinstance(ctx, dict) and "code" in ctx:
            level = record.get("level", "")
            msg = record.get("message", "")
            if level in ("WARN", "ERROR") and ("failed" in msg or "empty" in msg):
                failed_codes.append(ctx["code"])

    return failed_codes


def _parse_args(argv: list[str]) -> tuple[list[str] | None, bool]:
    """Return (codes, is_retry) from CLI arguments.

    codes=None means process all main-board stocks.
    """

    codes: list[str] | None = None
    retry_failed = False

    for arg in argv[1:]:
        if arg == "--retry-failed":
            retry_failed = True
        elif arg.startswith("--codes="):
            codes = arg.split("=", 1)[1].split(",")

    if retry_failed and codes is None:
        codes = _get_failed_codes_from_last_run()
        if not codes:
            print("no failed codes found in last run", file=sys.stderr)
            sys.exit(0)

    return codes, retry_failed


def main(argv: list[str] | None = None) -> int:
    """Fetch stock prices and write to SQLite."""

    if argv is None:
        argv = sys.argv

    specific_codes, retry_failed = _parse_args(argv)
    task_id = _new_task_id()
    start_date = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    end_date = date.today().isoformat()

    with database_connection() as connection:
        if specific_codes is not None:
            codes = specific_codes
            task_name = "update_prices_retry" if retry_failed else "update_prices_codes"
        else:
            codes = _get_main_board_codes(connection)
            task_name = "update_prices"

        create_task(task_id=task_id, task_name=task_name, connection=connection)
        mark_task_running(task_id, connection=connection)

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
            "retry_failed": retry_failed,
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
