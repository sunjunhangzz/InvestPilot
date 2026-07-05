"""Stock screening filters applied before recommendation generation.

Filters are ordered from cheapest to most expensive so the pipeline can
short-circuit early.
"""

from __future__ import annotations

from typing import Any

from app.shared.paths import load_config


def apply_filters(
    stocks: list[dict[str, Any]],
    prices: dict[str, list[dict]],
    factors: dict[str, dict[str, float]],
    config: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply all MVP filters and return (passed, rejected).

    Each rejected stock includes a ``reject_reason`` key.
    """

    if config is None:
        config = load_config(overlay_settings=True)

    filters_config = config["filters"]
    passed: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for stock in stocks:
        code = stock["code"]

        # --- 1. board ---
        if stock["board"] != "主板":
            rejected.append({**stock, "reject_reason": "非主板"})
            continue

        # --- 2. ST ---
        if stock["is_st"]:
            rejected.append({**stock, "reject_reason": "ST"})
            continue

        # --- 3. listing days ---
        min_days = filters_config["minListingDays"]
        if not _check_listing_days(stock, min_days):
            rejected.append({**stock, "reject_reason": f"上市不足{min_days}天"})
            continue

        # --- 4. liquidity (dual: absolute floor + turnover rate) ---
        min_amount = filters_config["minAverageAmount20d"]
        min_floor = filters_config.get("minAmountFloor", 30000000)
        min_turnover = filters_config.get("minTurnover20d", 0.003)
        factor = factors.get(code, {})
        avg_amt = factor.get("avg_amount", 0)
        avg_to = factor.get("avg_turnover", 0)

        if avg_amt < min_floor:
            rejected.append({**stock, "reject_reason": f"20日均成交额{avg_amt/1e4:.0f}万 < {min_floor/1e4:.0f}万（僵尸股）"})
            continue
        if avg_to < min_turnover:
            rejected.append({**stock, "reject_reason": f"20日均换手率{avg_to*100:.1f}% < {min_turnover*100:.1f}%（流动性不足）"})
            continue
        if avg_amt < min_amount:
            rejected.append({**stock, "reject_reason": f"20日均成交额{avg_amt/1e8:.1f}亿 < {min_amount/1e8:.0f}亿"})
            continue

        # --- 5. price ---
        min_price = filters_config["minPrice"]
        max_price = filters_config["maxPrice"]
        price = _latest_close(prices.get(code, []))
        if price is None or price < min_price or price > max_price:
            rejected.append(
                {
                    **stock,
                    "reject_reason": f"价格{price}不在{min_price}-{max_price}范围",
                }
            )
            continue

        # --- 6. trend conditions ---
        trend = factor.get("trend", {})
        if not _check_trend(trend):
            rejected.append({**stock, "reject_reason": "趋势条件不满足"})
            continue

        passed.append(stock)

    return passed, rejected


def _check_listing_days(stock: dict[str, Any], min_days: int) -> bool:
    """Check that the stock has been listed for at least *min_days*.

    When list_date is unavailable (NULL), the filter passes — it is better
    to include an unverifiable stock than to silently drop a valid one.
    """

    list_date = stock.get("list_date")
    if list_date is None:
        return True  # unknown → pass

    from datetime import date

    try:
        parsed = date.fromisoformat(str(list_date))
    except (ValueError, TypeError):
        return True  # unparseable → pass

    return (date.today() - parsed).days >= min_days


def _latest_close(prices: list[dict]) -> float | None:
    """Return the closing price of the most recent row, or None."""

    if not prices:
        return None
    return prices[-1].get("close")


def _check_trend(trend: dict[str, Any]) -> bool:
    """Check the four trend conditions required by MVP.

    - close > MA20
    - close > MA60
    - MA20 > MA60
    - 20d return > 0
    - 60d return > 0
    """

    close = trend.get("close", 0)
    ma20 = trend.get("ma20")
    ma60 = trend.get("ma60")
    r20 = trend.get("return_20d")
    r60 = trend.get("return_60d")

    if ma20 is None or ma60 is None:
        return False

    if not (close > ma20):
        return False
    if not (close > ma60):
        return False
    if not (ma20 > ma60):
        return False
    if r20 is not None and r20 <= 0:
        return False
    if r60 is not None and r60 <= 0:
        return False

    return True
