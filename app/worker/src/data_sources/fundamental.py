"""Fundamental data fetching via Efinance + Baostock."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def fetch_financials_batch() -> list[dict[str, Any]]:
    """Fetch fundamental data for all A-share stocks via Efinance.

    Returns a list of dicts matching the ``fundamentals`` table columns.
    """

    import efinance as ef  # type: ignore[import-untyped]

    # Use most recent annual report.
    raw = ef.stock.get_all_company_performance("2025-12-31")

    results: list[dict[str, Any]] = []
    for _, row in raw.iterrows():
        code = str(row["股票代码"]).strip()
        if not code:
            continue

        results.append(
            {
                "code": code,
                "pe": None,
                "pb": None,
                "roe": None,
                "market_cap": None,
                "revenue": _safe_float(row.get("营业收入")),
                "revenue_yoy": _safe_float(row.get("营业收入同比增长")),
                "net_profit": _safe_float(row.get("净利润")),
                "net_profit_yoy": _safe_float(row.get("净利润同比增长")),
                "eps": _safe_float(row.get("每股收益")),
                "debt_ratio": None,
                "industry": None,
            }
        )

    return results


def fetch_deep_financials(codes: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch balance-sheet data via Baostock for a batch of codes.

    Returns {code: {debt_ratio, current_ratio, ...}}.
    """

    import baostock as bs  # type: ignore[import-untyped]

    bs.login()
    result: dict[str, dict[str, Any]] = {}

    for code in codes:
        prefix = "sh" if code.startswith(("60", "68")) else "sz"
        symbol = f"{prefix}.{code}"
        try:
            rs = bs.query_balance_data(code=symbol, year=2025, quarter=4)
            df = rs.get_data()
            if len(df) > 0:
                row = df.iloc[0]
                liability = _safe_float(row.get("liabilityToAsset"))
                result[code] = {"debt_ratio": liability / 100 if liability else None}
        except Exception:
            pass

    bs.logout()
    return result


def upsert_fundamentals(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO fundamentals (code, pe, pb, roe, market_cap, revenue, revenue_yoy,
            net_profit, net_profit_yoy, eps, debt_ratio, industry, updated_at)
        VALUES (:code, :pe, :pb, :roe, :market_cap, :revenue, :revenue_yoy,
            :net_profit, :net_profit_yoy, :eps, :debt_ratio, :industry, datetime('now','localtime'))
        ON CONFLICT(code) DO UPDATE SET
            pe=excluded.pe, pb=excluded.pb, roe=excluded.roe, market_cap=excluded.market_cap,
            revenue=excluded.revenue, revenue_yoy=excluded.revenue_yoy,
            net_profit=excluded.net_profit, net_profit_yoy=excluded.net_profit_yoy,
            eps=excluded.eps, debt_ratio=excluded.debt_ratio,
            industry=excluded.industry, updated_at=excluded.updated_at
    """

    with connection:
        connection.executemany(sql, rows)

    return len(rows)


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        v = float(val)
        return None if v != v else v  # NaN check
    except (ValueError, TypeError):
        return None
