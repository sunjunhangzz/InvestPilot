"""Fetch fundamental data and write to fundamentals table.

Usage:
    python app/worker/scripts/update_fundamentals.py [--task-id <id>]
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.db import database_connection
from app.worker.src.data_sources.fundamental import (
    _safe_float,
    fetch_deep_financials,
    fetch_financials_batch,
    upsert_fundamentals,
)
from app.worker.src.tasks import mark_task_failed, mark_task_success
from app.worker.src.loggers import write_json_log
from app.worker.src.utils.arg_utils import resolve_task_id


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S_%f")
    return f"update_fundamentals_{ts}"


def main() -> int:
    with database_connection() as conn:
        task_id, is_external = resolve_task_id("update_fundamentals", conn, _new_task_id)

    write_json_log(
        file_name="data_source.log", level="INFO", module="update_fundamentals",
        task_id=task_id, message="start fundamental data fetch",
    )

    # 1. Batch fetch from Efinance.
    try:
        rows = fetch_financials_batch()
    except Exception as e:
        if not is_external:
            mark_task_failed(task_id, f"Efinance fetch failed: {e}")
        print(f"Efinance failed: {e}", file=sys.stderr)
        return 1

    if not rows:
        if not is_external:
            mark_task_failed(task_id, "no fundamental data fetched")
        return 1

    # 2. Enrich PE/PB/ROE/industry for recommended + watchlist stocks only.
    import efinance as ef  # type: ignore[import-untyped]
    codes_map = {r["code"]: r for r in rows}
    enriched = 0
    with database_connection() as conn:
        target_codes = set()
        for t in ["recommendations", "watchlist"]:
            for rc in conn.execute(f"SELECT DISTINCT code FROM {t}").fetchall():
                target_codes.add(rc["code"])
    for code in target_codes:
        if code not in codes_map:
            continue
        try:
            info = ef.stock.get_base_info(code)
            if info is not None:
                r = codes_map[code]
                r["pe"] = __import__("app.worker.src.data_sources.fundamental", fromlist=["_safe_float"])._safe_float(info.get("市盈率(动)"))
                r["pb"] = _safe_float(info.get("市净率"))
                r["roe"] = _safe_float(info.get("ROE"))
                r["market_cap"] = _safe_float(info.get("总市值"))
                r["industry"] = str(info.get("所处行业", "")).strip() or None
                enriched += 1
        except Exception:
            pass
    print(f"enriched {enriched} stocks with PE/PB/ROE/industry")

    # 3. Enrich with Baostock deep data for recommended + watchlist stocks.
    with database_connection() as conn:
        codes = conn.execute(
            "SELECT DISTINCT code FROM recommendations UNION SELECT DISTINCT code FROM watchlist"
        ).fetchall()
        deep_codes = [r["code"] for r in codes]
        deep = fetch_deep_financials(deep_codes)

        for r in rows:
            if r["code"] in deep:
                r["debt_ratio"] = deep[r["code"]].get("debt_ratio")

    # Filter to codes in stocks table.
    with database_connection() as conn:
        stock_codes = {r["code"] for r in conn.execute("SELECT code FROM stocks").fetchall()}
    rows = [r for r in rows if r["code"] in stock_codes]

    # 3. Write.
    try:
        with database_connection() as conn:
            written = upsert_fundamentals(conn, rows)
            if not is_external:
                mark_task_success(task_id, connection=conn)
    except Exception as e:
        if not is_external:
            mark_task_failed(task_id, f"write failed: {e}")
        print(f"Write failed: {e}", file=sys.stderr)
        return 1

    # 4. Backfill stocks.industry.
    industry_count = 0
    try:
        with database_connection() as conn:
            for r in rows:
                if r.get("industry"):
                    conn.execute(
                        "UPDATE stocks SET industry=? WHERE code=? AND industry IS NULL",
                        (r["industry"], r["code"]),
                    )
                    industry_count += 1
    except Exception:
        pass

    write_json_log(
        file_name="data_source.log", level="INFO", module="update_fundamentals",
        task_id=task_id, message="fundamental data written",
        context={"written": written, "industry_filled": industry_count},
    )

    print(f"fundamentals: {written} rows")
    print(f"industry backfill: {industry_count} stocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
