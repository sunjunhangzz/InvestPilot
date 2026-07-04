"""Fetch daily prices for main-board stocks and write to daily_prices.

Usage:
    python app/worker/scripts/update_prices.py [--task-id <id>] [--codes X,Y] [--retry-failed]
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

from app.worker.src.data_sources.price_source import fetch_daily_prices, upsert_daily_prices
from app.worker.src.db import database_connection
from app.worker.src.tasks import mark_task_failed, mark_task_success
from app.worker.src.loggers import write_json_log
from app.shared.paths import get_config_paths
from app.worker.src.utils.arg_utils import resolve_task_id

LOOKBACK_DAYS = 180


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S_%f")
    return f"update_prices_{ts}"


def _get_main_board_codes(connection) -> list[str]:
    rows = connection.execute(
        "SELECT code FROM stocks WHERE board = '主板' AND is_active = 1 AND is_st = 0 ORDER BY code"
    ).fetchall()
    return [row["code"] for row in rows]


def _get_failed_codes_from_last_run() -> list[str]:
    logs_dir = get_config_paths()["logsPath"]
    log_path = logs_dir / "data_source.log"
    if not log_path.exists():
        return []
    try:
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return []
    last_complete_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        try: record = json.loads(lines[i])
        except json.JSONDecodeError: continue
        if record.get("message") == "batch price fetch complete":
            last_complete_idx = i; break
    if last_complete_idx < 0: return []
    start_idx = -1
    for i in range(last_complete_idx, -1, -1):
        try: record = json.loads(lines[i])
        except json.JSONDecodeError: continue
        if record.get("message") == "start batch price fetch":
            start_idx = i; break
    if start_idx < 0: return []
    failed_codes: list[str] = []
    for i in range(start_idx, last_complete_idx + 1):
        try: record = json.loads(lines[i])
        except json.JSONDecodeError: continue
        ctx = record.get("context")
        if isinstance(ctx, dict) and "code" in ctx:
            if record.get("level") in ("WARN", "ERROR") and ("failed" in record.get("message", "") or "empty" in record.get("message", "")):
                failed_codes.append(ctx["code"])
    return failed_codes


def _parse_args(argv: list[str]) -> tuple[list[str] | None, bool]:
    codes: list[str] | None = None
    retry_failed = False
    for arg in argv[1:]:
        if arg == "--retry-failed": retry_failed = True
        elif arg.startswith("--codes="): codes = arg.split("=", 1)[1].split(",")
    if retry_failed and codes is None:
        codes = _get_failed_codes_from_last_run()
        if not codes:
            print("no failed codes found in last run", file=sys.stderr)
            sys.exit(0)
    return codes, retry_failed


def main(argv: list[str] | None = None) -> int:
    if argv is None: argv = sys.argv
    specific_codes, retry_failed = _parse_args(argv)
    start_date = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    end_date = date.today().isoformat()

    with database_connection() as connection:
        if specific_codes is not None:
            codes = specific_codes
            task_name = "update_prices_retry" if retry_failed else "update_prices_codes"
        else:
            codes = _get_main_board_codes(connection)
            task_name = "update_prices"
        task_id, is_external = resolve_task_id(task_name, connection, _new_task_id)

    write_json_log(file_name="data_source.log", level="INFO", module="update_prices",
                   task_id=task_id, message="start batch price fetch",
                   context={"stock_count": len(codes), "start_date": start_date, "end_date": end_date, "adjust": "qfq", "retry_failed": retry_failed})

    total_rows = 0; success_count = 0; failed_count = 0
    failed_codes: list[str] = []
    start_time = time.monotonic()

    for idx, code in enumerate(codes):
        try:
            rows = fetch_daily_prices(code, start_date, end_date, adjust="qfq")
        except Exception as error:
            failed_count += 1; failed_codes.append(code)
            write_json_log(file_name="data_source.log", level="WARN", module="update_prices",
                           task_id=task_id, message=f"fetch failed for {code}: {error}", context={"code": code})
            continue
        if not rows:
            failed_count += 1
            write_json_log(file_name="data_source.log", level="WARN", module="update_prices",
                           task_id=task_id, message=f"empty data for {code}", context={"code": code})
            continue
        try:
            with database_connection() as connection:
                upsert_daily_prices(rows, connection)
        except Exception as error:
            failed_count += 1; failed_codes.append(code)
            write_json_log(file_name="data_source.log", level="ERROR", module="update_prices",
                           task_id=task_id, message=f"write failed for {code}: {error}", context={"code": code})
            continue
        total_rows += len(rows); success_count += 1
        if (idx + 1) % 100 == 0:
            elapsed = time.monotonic() - start_time
            print(f"  progress: {idx + 1}/{len(codes)} ({elapsed:.0f}s)")
        time.sleep(0.3)  # throttle requests to avoid CPU/network congestion

    elapsed = time.monotonic() - start_time
    with database_connection() as connection:
        if not is_external:
            if success_count > 0:
                mark_task_success(task_id, connection=connection)
            else:
                mark_task_failed(task_id, "all stocks failed — no data written", connection=connection)

    write_json_log(file_name="data_source.log", level="INFO", module="update_prices",
                   task_id=task_id, message="batch price fetch complete",
                   context={"success_count": success_count, "failed_count": failed_count, "total_rows": total_rows, "elapsed_sec": round(elapsed, 1)})

    print(f"total stocks: {len(codes)}")
    print(f"  success: {success_count}  failed: {failed_count}  rows: {total_rows}  elapsed: {elapsed:.0f}s")
    if failed_codes:
        print(f"  failed codes: {', '.join(failed_codes[:10])}...")
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
