"""Watchlist maintenance logic — entry, tracking, and exit rules."""

from __future__ import annotations

from typing import Any

from app.worker.src.factors.indicators import avg_amount, ma


def compute_entry_updates(
    recommendations: list[dict[str, Any]],
    existing_watchlist: dict[str, dict[str, Any]],
    prices: dict[str, list[dict]],
    trade_date: str,
) -> list[dict[str, Any]]:
    """Return UPSERT rows for watchlist based on A/B recommendations.

    - New stocks are inserted with active status.
    - Existing stocks have last_recommended_date and latest_price refreshed.
    - first_recommended_date is never overwritten.
    """

    rows: list[dict[str, Any]] = []
    today_prices = _latest_prices(prices)

    for rec in recommendations:
        if rec["rating"] == "C":
            continue  # Only A/B enter the watchlist.

        code = rec["code"]
        existing = existing_watchlist.get(code)
        latest_price = today_prices.get(code)

        if existing is not None:
            rows.append(
                {
                    "code": code,
                    "first_recommended_date": existing["first_recommended_date"],
                    "last_recommended_date": trade_date,
                    "status": _refresh_status(existing["status"]),
                    "entry_price": existing["entry_price"],
                    "latest_price": latest_price,
                    "tracking_days": existing["tracking_days"],
                    "min_tracking_days": existing["min_tracking_days"],
                    "max_tracking_days": existing["max_tracking_days"],
                    "exit_reason": existing.get("exit_reason"),
                }
            )
        else:
            rows.append(
                {
                    "code": code,
                    "first_recommended_date": trade_date,
                    "last_recommended_date": trade_date,
                    "status": "active",
                    "entry_price": latest_price,
                    "latest_price": latest_price,
                    "tracking_days": 1,
                    "min_tracking_days": 5,
                    "max_tracking_days": 20,
                    "exit_reason": None,
                }
            )

    return rows


def compute_tracking_updates(
    watchlist: list[dict[str, Any]],
    prices: dict[str, list[dict]],
    trade_date_counts: dict[str, int],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Update tracking_days, latest_price, and apply exit/downgrade rules.

    Returns the rows to UPSERT into watchlist.
    """

    today_prices = _latest_prices(prices)
    updated: list[dict[str, Any]] = []

    for entry in watchlist:
        code = entry["code"]
        stock_prices = prices.get(code, [])
        latest_price = today_prices.get(code, entry.get("latest_price"))

        # Count trading days since first_recommended_date.
        tracking_days = trade_date_counts.get(code, 0)

        new_status = entry["status"]
        exit_reason = entry.get("exit_reason")

        # Only evaluate exit rules for active/hold/downgraded stocks.
        if new_status in ("active", "hold", "downgraded"):
            new_status, exit_reason = _evaluate_exit(
                entry, stock_prices, tracking_days, config
            )

        updated.append(
            {
                "code": code,
                "first_recommended_date": entry["first_recommended_date"],
                "last_recommended_date": entry["last_recommended_date"],
                "status": new_status,
                "entry_price": entry["entry_price"],
                "latest_price": latest_price,
                "tracking_days": tracking_days,
                "min_tracking_days": entry.get("min_tracking_days", 5),
                "max_tracking_days": entry.get("max_tracking_days", 20),
                "exit_reason": exit_reason,
            }
        )

    return updated


def _latest_prices(prices: dict[str, list[dict]]) -> dict[str, float | None]:
    """Return {code: latest_close} for every code in prices."""

    result: dict[str, float | None] = {}
    for code, rows in prices.items():
        result[code] = rows[-1]["close"] if rows else None
    return result


def _refresh_status(current: str) -> str:
    """Reactivate a stock when it reappears in recommendations.

    Only "blocked" (risk-triggered) stays terminal — exited and downgraded
    stocks get a fresh "active" status when recommended again.
    """

    if current == "blocked":
        return current
    return "active"


def _evaluate_exit(
    entry: dict[str, Any],
    stock_prices: list[dict],
    tracking_days: int,
    config: dict[str, Any],
) -> tuple[str, str | None]:
    """Check exit and downgrade conditions. Returns (new_status, reason).

    Rules (in priority order):
    1. Below MA20 or MA60 → downgraded
    2. Liquidity collapse (avg_amount < 50% of threshold) → blocked
    3. Max tracking days exceeded → exit
    4. Min tracking days not yet reached → stay active (no forced exit)
    """

    min_tracking = entry.get("min_tracking_days", 5)
    max_tracking = entry.get("max_tracking_days", 20)

    if not stock_prices:
        return entry["status"], entry.get("exit_reason")

    close = stock_prices[-1]["close"]
    ma20_val = ma(stock_prices, 20)
    ma60_val = ma(stock_prices, 60)

    # 1. Below MA lines → downgrade.
    if ma20_val is not None and ma60_val is not None:
        if close < ma20_val or close < ma60_val:
            if tracking_days >= min_tracking:
                return "downgraded", "跌破关键均线（MA20/MA60）"

    # 2. Liquidity collapse.
    min_amount = config["filters"]["minAverageAmount20d"]
    amt = avg_amount(stock_prices, 20)
    if amt is not None and amt < min_amount * 0.5:
        return "blocked", "流动性严重恶化"

    # 3. Max tracking exceeded.
    if tracking_days > max_tracking:
        return "exit", f"超过最大跟踪周期（{max_tracking}个交易日）"

    return entry["status"], entry.get("exit_reason")


def upsert_watchlist(connection, rows: list[dict[str, Any]]) -> int:
    """UPSERT watchlist rows."""

    sql = """
        INSERT INTO watchlist (
            code, first_recommended_date, last_recommended_date,
            status, entry_price, latest_price,
            tracking_days, min_tracking_days, max_tracking_days, exit_reason
        )
        VALUES (
            :code, :first_recommended_date, :last_recommended_date,
            :status, :entry_price, :latest_price,
            :tracking_days, :min_tracking_days, :max_tracking_days, :exit_reason
        )
        ON CONFLICT(code) DO UPDATE SET
            first_recommended_date = excluded.first_recommended_date,
            last_recommended_date  = excluded.last_recommended_date,
            status                 = excluded.status,
            entry_price            = excluded.entry_price,
            latest_price           = excluded.latest_price,
            tracking_days          = excluded.tracking_days,
            min_tracking_days      = excluded.min_tracking_days,
            max_tracking_days      = excluded.max_tracking_days,
            exit_reason            = excluded.exit_reason,
            updated_at             = datetime('now', 'localtime')
    """

    with connection:
        connection.executemany(sql, rows)

    return len(rows)
