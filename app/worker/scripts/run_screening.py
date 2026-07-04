"""Apply screening filters, rank stocks, and write recommendations.

Usage:
    python app/worker/scripts/run_screening.py

Requires calc_factors to have been run first.
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
from app.worker.src.factors.indicators import avg_amount, ma, return_pct
from app.worker.src.screening.filters import apply_filters
from app.worker.src.tasks import (
    create_task,
    mark_run_running,
    mark_run_success,
    mark_task_failed,
    mark_task_running,
    mark_task_success,
)
from app.worker.src.loggers import write_json_log
from app.worker.src.utils import get_latest_trading_date
from app.shared.paths import load_config


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    return f"run_screening_{ts}"


def _build_reason(factor: dict) -> str:
    """Generate a rule-based recommendation reason (no AI)."""

    parts: list[str] = []
    trend = factor.get("trend_score", 0)
    mom = factor.get("momentum_score", 0)
    liq = factor.get("liquidity_score", 0)

    if trend >= 80:
        parts.append("趋势强劲，均线多头排列")
    elif trend >= 50:
        parts.append("趋势向好")

    if mom >= 80:
        parts.append("近期动量充沛")
    elif mom >= 50:
        parts.append("动量适中")

    if liq >= 80:
        parts.append("流动性充裕")
    elif liq >= 50:
        parts.append("流动性尚可")

    if not parts:
        parts.append("综合评分入围")

    return "；".join(parts)


def _build_risk_tags(factor: dict, prices: list[dict]) -> str:
    """Generate risk tags from factor scores and price data."""

    tags: list[str] = []
    risk = factor.get("risk_score", 100)
    trend = factor.get("trend_score", 0)

    if risk < 30:
        tags.append("风险较高")
    elif risk < 50:
        tags.append("波动偏大")

    if trend < 50:
        tags.append("趋势偏弱")

    # Check if price is near recent high.
    if prices and len(prices) >= 20:
        recent_high = max(r["close"] for r in prices[-20:])
        latest = prices[-1]["close"]
        if latest >= recent_high * 0.95:
            tags.append("接近20日高点")

    return ", ".join(tags) if tags else ""


def _upsert_recommendations(connection, rows: list[dict]) -> int:
    """Insert or replace recommendation rows."""

    sql = """
        INSERT INTO recommendations (
            run_id, trade_date, code, rank, rating, total_score,
            reason, risk_tags, first_recommended_date, last_recommended_date, tracking_days
        )
        VALUES (
            :run_id, :trade_date, :code, :rank, :rating, :total_score,
            :reason, :risk_tags, :first_recommended_date, :last_recommended_date, :tracking_days
        )
        ON CONFLICT(run_id, code) DO UPDATE SET
            rank                  = excluded.rank,
            rating                = excluded.rating,
            total_score           = excluded.total_score,
            reason                = excluded.reason,
            risk_tags             = excluded.risk_tags,
            last_recommended_date = excluded.last_recommended_date,
            tracking_days         = excluded.tracking_days
    """

    with connection:
        connection.executemany(sql, rows)

    return len(rows)


def main() -> int:
    task_id = _new_task_id()
    config = load_config()

    with database_connection() as connection:
        trade_date = get_latest_trading_date(connection)
        if trade_date is None:
            print("no data — run calc_factors first", file=sys.stderr)
            return 1

        # Find the latest factors run_id.
        run_row = connection.execute(
            """
            SELECT run_id FROM factors
            WHERE trade_date = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (trade_date,),
        ).fetchone()

        if run_row is None:
            print("no factors for trade_date — run calc_factors first", file=sys.stderr)
            return 1

        run_id = run_row["run_id"]

        create_task(
            task_id=task_id,
            task_name="run_screening",
            run_id=run_id,
            connection=connection,
        )
        mark_task_running(task_id, connection=connection)
        mark_run_running(run_id, connection=connection)

        # Load data.
        factors_rows = connection.execute(
            """
            SELECT f.*, s.name, s.board, s.is_st, s.list_date
            FROM factors f
            JOIN stocks s ON s.code = f.code
            WHERE f.run_id = ? AND f.trade_date = ?
            """,
            (run_id, trade_date),
        ).fetchall()

        prices_data = connection.execute(
            """
            SELECT dp.code, dp.trade_date, dp.close, dp.amount
            FROM daily_prices dp
            JOIN stocks s ON s.code = dp.code
            WHERE s.board = '主板' AND s.is_active = 1 AND dp.trade_date <= ?
            ORDER BY dp.code, dp.trade_date
            """,
            (trade_date,),
        ).fetchall()

    # --- build lookups ---
    prices: dict[str, list[dict]] = {}
    for row in prices_data:
        code = row["code"]
        if code not in prices:
            prices[code] = []
        prices[code].append({"trade_date": row["trade_date"], "close": row["close"], "amount": row["amount"]})

    stocks_list: list[dict] = []
    factors_map: dict[str, dict] = {}

    for row in factors_rows:
        code = row["code"]
        stock = {
            "code": code,
            "name": row["name"],
            "board": row["board"],
            "is_st": row["is_st"],
            "list_date": row["list_date"],
        }
        stocks_list.append(stock)

        # Enrich factors map with trend details needed by filters.
        price_rows = prices.get(code, [])
        close_val = price_rows[-1]["close"] if price_rows else 0
        factors_map[code] = {
            "trend_score": row["trend_score"],
            "momentum_score": row["momentum_score"],
            "liquidity_score": row["liquidity_score"],
            "risk_score": row["risk_score"],
            "total_score": row["total_score"],
            "avg_amount": avg_amount(price_rows, 20) or 0,
            "trend": {
                "close": close_val,
                "ma20": ma(price_rows, 20),
                "ma60": ma(price_rows, 60),
                "return_20d": return_pct(price_rows, 20),
                "return_60d": return_pct(price_rows, 60),
            },
        }

    write_json_log(
        file_name="screening.log",
        level="INFO",
        module="run_screening",
        task_id=task_id,
        run_id=run_id,
        trade_date=trade_date,
        message="start screening",
        context={"candidates": len(stocks_list)},
    )

    # --- filter ---
    passed, rejected = apply_filters(stocks_list, prices, factors_map, config)

    # --- rank ---
    passed.sort(key=lambda s: factors_map[s["code"]]["total_score"], reverse=True)

    # --- tier ---
    limit = config["recommendationLimit"]
    min_limit = config["minRecommendationLimit"]

    recommendations: list[dict] = []
    for idx, stock in enumerate(passed):
        factor = factors_map[stock["code"]]

        if idx < min_limit:
            rating = "A"
        elif idx < limit:
            rating = "B"
        else:
            rating = "C"

        today_str = trade_date
        rec = {
            "run_id": run_id,
            "trade_date": trade_date,
            "code": stock["code"],
            "rank": idx + 1,
            "rating": rating,
            "total_score": factor["total_score"],
            "reason": _build_reason(factor),
            "risk_tags": _build_risk_tags(factor, prices.get(stock["code"], [])),
            "first_recommended_date": today_str,
            "last_recommended_date": today_str,
            "tracking_days": 1,
        }
        recommendations.append(rec)

    # --- write ---
    try:
        with database_connection() as connection:
            written = _upsert_recommendations(connection, recommendations)
            mark_task_success(task_id, connection=connection)
            mark_run_success(run_id, connection=connection)
    except Exception as error:
        mark_task_failed(task_id, f"write failed: {error}")
        print(f"write failed: {error}", file=sys.stderr)
        return 1

    # --- reject log ---
    reject_reasons: dict[str, int] = {}
    for r in rejected:
        reason = r.get("reject_reason", "未知")
        reject_reasons[reason] = reject_reasons.get(reason, 0) + 1

    write_json_log(
        file_name="screening.log",
        level="INFO",
        module="run_screening",
        task_id=task_id,
        run_id=run_id,
        trade_date=trade_date,
        message="screening complete",
        context={
            "passed": len(passed),
            "recommended": written,
            "rejected": len(rejected),
            "reasons": reject_reasons,
            "tier_a": sum(1 for r in recommendations if r["rating"] == "A"),
            "tier_b": sum(1 for r in recommendations if r["rating"] == "B"),
            "tier_c": sum(1 for r in recommendations if r["rating"] == "C"),
        },
    )

    print(f"trade_date: {trade_date}")
    print(f"run_id: {run_id}")
    print(f"candidates: {len(stocks_list)}")
    print(f"passed: {len(passed)}")
    print(f"rejected: {len(rejected)}")
    print(f"recommended: {written}")
    for reason, count in sorted(reject_reasons.items(), key=lambda x: -x[1]):
        print(f"  reject — {reason}: {count}")
    print(f"tier A: {sum(1 for r in recommendations if r['rating'] == 'A')}")
    print(f"tier B: {sum(1 for r in recommendations if r['rating'] == 'B')}")
    print(f"tier C: {sum(1 for r in recommendations if r['rating'] == 'C')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
