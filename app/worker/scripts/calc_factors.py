"""Calculate factor scores for all main-board stocks and write to factors table.

Usage:
    python app/worker/scripts/calc_factors.py

Requires stocks and daily_prices to be populated first.
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
from app.worker.src.factors.indicators import (
    avg_amount,
    ma,
    max_drawdown,
    return_pct,
    volatility,
)
from app.worker.src.factors.scoring import (
    fundamental_score,
    liquidity_score,
    momentum_score,
    risk_score,
    total_score,
    trend_score,
)
from app.worker.src.tasks import (
    create_run,
    mark_run_running,
    mark_run_success,
    mark_task_failed,
    mark_task_success,
)
from app.worker.src.loggers import write_json_log
from app.worker.src.utils import get_latest_trading_date
from app.worker.src.utils.arg_utils import resolve_task_id


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S_%f")
    return f"calc_factors_{ts}"


def _load_prices(connection, trade_date: str) -> dict[str, list[dict]]:
    """Return {code: [price_rows sorted by date]} for main-board stocks.

    Only rows on or before *trade_date* are included to avoid future leakage.
    """

    rows = connection.execute(
        """
        SELECT dp.code, dp.trade_date, dp.close, dp.amount
        FROM daily_prices dp
        JOIN stocks s ON s.code = dp.code
        WHERE s.board = '主板'
          AND s.is_active = 1
          AND dp.trade_date <= :trade_date
        ORDER BY dp.code, dp.trade_date
        """,
        {"trade_date": trade_date},
    ).fetchall()

    prices: dict[str, list[dict]] = {}
    for row in rows:
        code = row["code"]
        if code not in prices:
            prices[code] = []
        prices[code].append(
            {"trade_date": row["trade_date"], "close": row["close"], "amount": row["amount"]}
        )

    return prices


def _upsert_factors(connection, rows: list[dict]) -> int:
    """Insert or replace factor rows in a single transaction."""

    sql = """
        INSERT INTO factors (
            run_id, code, trade_date,
            trend_score, momentum_score, liquidity_score, risk_score, total_score
        )
        VALUES (
            :run_id, :code, :trade_date,
            :trend_score, :momentum_score, :liquidity_score, :risk_score, :total_score
        )
        ON CONFLICT(run_id, code, trade_date) DO UPDATE SET
            trend_score     = excluded.trend_score,
            momentum_score  = excluded.momentum_score,
            liquidity_score = excluded.liquidity_score,
            risk_score      = excluded.risk_score,
            total_score     = excluded.total_score
    """

    with connection:
        connection.executemany(sql, rows)

    return len(rows)


def main() -> int:
    with database_connection() as connection:
        trade_date = get_latest_trading_date(connection)
        if trade_date is None:
            print("no price data — run update_prices first", file=sys.stderr)
            return 1

        task_id, is_external = resolve_task_id("calc_factors", connection, _new_task_id)

        run_id = create_run(
            run_type="manual",
            trade_date=trade_date,
            status="running",
            connection=connection,
        )
        mark_run_running(run_id, connection=connection)

        prices = _load_prices(connection, trade_date)

    write_json_log(
        file_name="screening.log",
        level="INFO",
        module="calc_factors",
        task_id=task_id,
        run_id=run_id,
        trade_date=trade_date,
        message="start factor calculation",
        context={"stock_count": len(prices)},
    )

    factor_rows: list[dict] = []
    skipped_no_data = 0
    skipped_no_ma60 = 0

    # Load fundamentals for bonus scoring.
    fund_map: dict[str, dict] = {}
    with connection:
        for r in connection.execute("SELECT * FROM fundamentals").fetchall():
            fund_map[r["code"]] = dict(r)

    for code, rows in sorted(prices.items()):
        # Must have at least 60 rows for MA60.
        if len(rows) < 60:
            skipped_no_ma60 += 1
            continue

        close = rows[-1]["close"]
        ma20 = ma(rows, 20)
        ma60 = ma(rows, 60)
        r20 = return_pct(rows, 20)
        r60 = return_pct(rows, 60)
        amt = avg_amount(rows, 20)
        vol = volatility(rows, 20)
        mdd = max_drawdown(rows, 20)

        # Skip stocks where core indicators failed.
        if ma20 is None or ma60 is None or amt is None:
            skipped_no_data += 1
            continue

        t_score = trend_score(close, ma20, ma60)
        m_score = momentum_score(r20, r60)
        l_score = liquidity_score(amt)
        r_score = risk_score(vol, mdd)
        fs = fundamental_score(fund_map.get(code))
        ttl = total_score(t_score, m_score, l_score, r_score) + fs * 0.2

        factor_rows.append(
            {
                "run_id": run_id,
                "code": code,
                "trade_date": trade_date,
                "trend_score": round(t_score, 2),
                "momentum_score": round(m_score, 2),
                "liquidity_score": round(l_score, 2),
                "risk_score": round(r_score, 2),
                "fundamental_score": round(fs, 2),
            "total_score": round(ttl, 2),
            }
        )

    # --- write ---
    try:
        with database_connection() as connection:
            written = _upsert_factors(connection, factor_rows)
            if not is_external: mark_task_success(task_id, connection=connection)
            if not is_external: mark_run_success(run_id, connection=connection)
    except Exception as error:
        if not is_external: mark_task_failed(task_id, f"factor write failed: {error}")
        print(f"write failed: {error}", file=sys.stderr)
        return 1

    write_json_log(
        file_name="screening.log",
        level="INFO",
        module="calc_factors",
        task_id=task_id,
        run_id=run_id,
        trade_date=trade_date,
        message="factor calculation complete",
        context={
            "written": written,
            "skipped_no_ma60": skipped_no_ma60,
            "skipped_no_data": skipped_no_data,
        },
    )

    print(f"trade_date: {trade_date}")
    print(f"run_id: {run_id}")
    print(f"stocks with prices: {len(prices)}")
    print(f"factors written: {written}")
    print(f"skipped (no MA60): {skipped_no_ma60}")
    print(f"skipped (no data): {skipped_no_data}")

    # Show score distribution.
    if factor_rows:
        scores = sorted(r["total_score"] for r in factor_rows)
        print(f"total_score range: {scores[0]:.1f} ~ {scores[-1]:.1f}")
        print(f"total_score median: {scores[len(scores)//2]:.1f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
