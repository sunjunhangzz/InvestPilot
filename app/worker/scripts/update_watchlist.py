"""Update watchlist from latest recommendations and price data.

Usage:
    python app/worker/scripts/update_watchlist.py
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
from app.worker.src.watchlist.manager import (
    compute_entry_updates,
    compute_tracking_updates,
    upsert_watchlist,
)
from app.worker.src.tasks import (
    mark_task_failed,
    mark_task_success,
)
from app.worker.src.loggers import write_json_log
from app.worker.src.utils import get_latest_trading_date
from app.worker.src.utils.arg_utils import resolve_task_id
from app.shared.paths import load_config


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S_%f")
    return f"update_watchlist_{ts}"


def _count_trading_days_from_entry(
    connection, entries: dict[str, dict]
) -> dict[str, int]:
    """Count daily_prices rows from each stock's first_recommended_date.

    For new entries (not yet in watchlist table), first_recommended_date is
    today, so the count will be 1 (today's data point).
    """

    if not entries:
        return {}

    counts: dict[str, int] = {}
    for code, entry in entries.items():
        first_date = entry.get("first_recommended_date", "2000-01-01")
        row = connection.execute(
            """
            SELECT COUNT(*) AS cnt FROM daily_prices
            WHERE code = ? AND trade_date >= ?
            """,
            (code, first_date),
        ).fetchone()
        counts[code] = row["cnt"] if row else 0
    return counts


def main() -> int:
    config = load_config(overlay_settings=True)

    with database_connection() as connection:
        task_id, is_external = resolve_task_id("update_watchlist", connection, _new_task_id)
        trade_date = get_latest_trading_date(connection)
        if trade_date is None:
            print("no data", file=sys.stderr)
            return 1

        run_row = connection.execute(
            "SELECT run_id FROM runs WHERE status = 'success' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if run_row is None:
            if not is_external: mark_task_failed(task_id, "no recommendations found — run run_screening first")
            print("no recommendations", file=sys.stderr)
            return 1
        run_id = run_row["run_id"]

        recs = connection.execute(
            "SELECT code, rating, total_score, rank FROM recommendations WHERE run_id = ?",
            (run_id,),
        ).fetchall()

        existing_rows = connection.execute("SELECT * FROM watchlist").fetchall()
        existing_wl = {row["code"]: dict(row) for row in existing_rows}

        price_rows = connection.execute(
            """
            SELECT code, trade_date, close, amount
            FROM daily_prices WHERE trade_date <= ?
            ORDER BY code, trade_date
            """,
            (trade_date,),
        ).fetchall()

    prices: dict[str, list[dict]] = {}
    for row in price_rows:
        code = row["code"]
        if code not in prices:
            prices[code] = []
        prices[code].append(
            {"trade_date": row["trade_date"], "close": row["close"], "amount": row["amount"]}
        )

    rec_list = [dict(r) for r in recs]

    # --- entry ---
    entry_rows = compute_entry_updates(rec_list, existing_wl, prices, trade_date)

    # Merge existing + new for tracking.
    merged: dict[str, dict] = {r["code"]: dict(r) for r in existing_rows}
    for row in entry_rows:
        merged[row["code"]] = {**merged.get(row["code"], {}), **row}

    with database_connection() as conn:
        trade_day_counts = _count_trading_days_from_entry(conn, merged)

    tracking_rows = compute_tracking_updates(
        list(merged.values()), prices, trade_day_counts, config
    )

    write_json_log(
        file_name="screening.log",
        level="INFO",
        module="update_watchlist",
        task_id=task_id,
        run_id=run_id,
        trade_date=trade_date,
        message="start watchlist update",
        context={"entries": len(tracking_rows)},
    )

    try:
        with database_connection() as connection:
            written = upsert_watchlist(connection, tracking_rows)
            if not is_external: mark_task_success(task_id, connection=connection)
    except Exception as error:
        if not is_external: mark_task_failed(task_id, f"write failed: {error}")
        print(f"write failed: {error}", file=sys.stderr)
        return 1

    status_counts: dict[str, int] = {}
    for row in tracking_rows:
        s = row["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    print(f"trade_date: {trade_date}")
    print(f"watchlist entries: {written}")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    write_json_log(
        file_name="screening.log",
        level="INFO",
        module="update_watchlist",
        task_id=task_id,
        run_id=run_id,
        trade_date=trade_date,
        message="watchlist update complete",
        context={"written": written, "statuses": status_counts},
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
