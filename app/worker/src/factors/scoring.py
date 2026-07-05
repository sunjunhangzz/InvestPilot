"""Factor scoring functions that convert raw indicators into 0–100 scores.

Each scoring function accepts indicator values and returns a normalised score.
The MVP uses simple percentile-like scaling; later versions may introduce
cross-sectional ranking across the entire stock universe.
"""

from __future__ import annotations

import math

from app.shared.paths import load_config


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def trend_score(
    close: float,
    ma20: float | None,
    ma60: float | None,
) -> float:
    """Score trend strength based on moving-average alignment.

    - close > MA20 → bonus
    - close > MA60 → bonus
    - MA20 > MA60 → golden-cross bonus
    """

    if ma20 is None or ma60 is None:
        return 0.0

    score = 50.0  # neutral baseline

    if close > ma20:
        score += 20
    if close > ma60:
        score += 15
    if ma20 > ma60:
        score += 15

    return _clamp(score)


def momentum_score(
    return_20d: float | None,
    return_60d: float | None,
) -> float:
    """Score recent price momentum.

    Positive returns earn points; the magnitude is capped to avoid
    rewarding extreme short-term spikes.
    """

    if return_20d is None and return_60d is None:
        return 0.0

    r20 = return_20d or 0.0
    r60 = return_60d or 0.0

    # Map return to 0–50 sub-score (capped at ±20%).
    def _sub(r: float) -> float:
        return _clamp(50 + r * 2.5, 0, 100) / 2

    return _clamp(_sub(r20) + _sub(r60))


def liquidity_score(avg_amount_20d: float | None) -> float:
    """Score trading liquidity based on 20-day average turnover amount.

    Uses a log scale to differentiate within reasonable ranges without
    letting mega-caps dominate.
    """

    if avg_amount_20d is None or avg_amount_20d <= 0:
        return 0.0

    # log10 scale: 10^7 (10M) → 0, 10^9 (1B) → 100.
    log_val = math.log10(avg_amount_20d)
    return _clamp((log_val - 7.0) / 2.0 * 100)


def risk_score(
    volatility_20d: float | None,
    max_drawdown_20d: float | None,
) -> float:
    """Score risk control — higher volatility / drawdown → lower score.

    max_drawdown_20d is negative (e.g. -15.3); the absolute value is used.
    """

    if volatility_20d is None and max_drawdown_20d is None:
        return 50.0  # neutral when data is missing

    score = 100.0

    # Volatility penalty: 0% vol → full, 50%+ vol → 0.
    if volatility_20d is not None:
        vol_penalty = min(volatility_20d / 0.5, 1.0) * 50
        score -= vol_penalty

    # Drawdown penalty: 0% → full, -30% → 0 for this sub-score.
    if max_drawdown_20d is not None:
        dd_abs = abs(max_drawdown_20d) / 100.0  # convert e.g. -15.3 → 0.153
        dd_penalty = min(dd_abs / 0.3, 1.0) * 50
        score -= dd_penalty

    return _clamp(score)


def total_score(
    trend: float,
    momentum: float,
    liquidity: float,
    risk: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Weighted sum of the four factor scores.

    Weights default to the values in shared/config.json and must sum to 1.
    """

    if weights is None:
        config = load_config(overlay_settings=True)
        weights = config["factorWeights"]

    return round(
        trend * weights["trend"]
        + momentum * weights["momentum"]
        + liquidity * weights["liquidity"]
        + risk * weights["risk"],
        2,
    )


def fundamental_score(f: dict | None) -> float:
    """Score fundamental quality (0-100). Returns 50 if no data."""
    if f is None:
        return 50.0
    score = 50.0
    roe = f.get("roe")
    if roe is not None:
        if roe > 15: score += 10
        elif roe < 5: score -= 5
    rev_yoy = f.get("revenue_yoy")
    if rev_yoy is not None:
        if rev_yoy > 20: score += 10
        elif rev_yoy < 0: score -= 5
    profit_yoy = f.get("net_profit_yoy")
    if profit_yoy is not None:
        if profit_yoy > 20: score += 10
        elif profit_yoy < -30: score -= 10
    pe = f.get("pe")
    if pe is not None and pe > 0:
        if pe < 20: score += 5
        elif pe > 100: score -= 5
    debt = f.get("debt_ratio")
    if debt is not None:
        if debt < 60: score += 5
        elif debt > 80: score -= 5
    return max(0.0, min(100.0, score))
