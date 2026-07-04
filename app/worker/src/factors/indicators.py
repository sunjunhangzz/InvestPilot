"""Technical indicators computed from daily price data.

Every function in this module MUST operate on price data sorted by trade_date
ASCENDING and MUST NOT reference rows beyond the target date — this prevents
future-function leakage into the screening pipeline.
"""

from __future__ import annotations

from typing import Any


def ma(rows: list[dict[str, Any]], window: int) -> float | None:
    """Simple moving average of `close` over the most recent *window* rows.

    Returns None when there are fewer rows than the window.
    """

    if len(rows) < window:
        return None
    closes = [row["close"] for row in rows[-window:]]
    return sum(closes) / len(closes)


def return_pct(rows: list[dict[str, Any]], window: int) -> float | None:
    """Percentage return over the most recent *window* trading days.

    Computed as (close[-1] - close[-window]) / close[-window] * 100.
    Returns None when there are fewer rows than the window or when the
    starting close is zero.
    """

    if len(rows) < window:
        return None
    start_close = rows[-window]["close"]
    end_close = rows[-1]["close"]
    if start_close == 0:
        return None
    return (end_close - start_close) / start_close * 100


def avg_amount(rows: list[dict[str, Any]], window: int) -> float | None:
    """Average daily turnover amount over the most recent *window* rows.

    Returns None when there are fewer rows than the window.
    """

    if len(rows) < window:
        return None
    amounts = [row["amount"] for row in rows[-window:]]
    return sum(amounts) / len(amounts)


def volatility(rows: list[dict[str, Any]], window: int) -> float | None:
    """Annualised volatility (standard deviation of daily returns) over
    the most recent *window* rows.

    Daily returns are computed as close-to-close percentage changes.
    The result is annualised by multiplying the daily stdev by sqrt(252).
    Returns None when there are fewer than (window + 1) rows.
    """

    if len(rows) < window + 1:
        return None

    # Daily log-return proxy: (close[t] - close[t-1]) / close[t-1].
    daily_returns: list[float] = []
    recent = rows[-(window + 1):]  # need window+1 points for window returns
    for i in range(1, len(recent)):
        prev_close = recent[i - 1]["close"]
        curr_close = recent[i]["close"]
        if prev_close == 0:
            return None
        daily_returns.append((curr_close - prev_close) / prev_close)

    if len(daily_returns) < 2:
        return None

    mean = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    daily_std = variance ** 0.5
    # Annualise: multiply by sqrt(252).
    return daily_std * (252 ** 0.5)


def max_drawdown(rows: list[dict[str, Any]], window: int) -> float | None:
    """Maximum drawdown (peak-to-trough decline) over the most recent
    *window* rows, expressed as a negative percentage (e.g. -15.3).

    Returns None when there are fewer rows than the window.
    """

    if len(rows) < window:
        return None

    recent = rows[-window:]
    peak = recent[0]["close"]
    max_dd = 0.0

    for row in recent:
        close = row["close"]
        if close > peak:
            peak = close
        dd = (close - peak) / peak if peak != 0 else 0.0
        if dd < max_dd:
            max_dd = dd

    # Convert to percentage.
    return max_dd * 100
