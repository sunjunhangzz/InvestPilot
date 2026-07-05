"""Fetch daily price data via AkShare (sina source) and write to daily_prices."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.shared.paths import get_config_paths


# AkShare stock_zh_a_daily uses sina-style symbols: sz + code for SZ, sh + code for SH.
# 8xxxxx (BJ) is not well tested; MVP only pulls SH/SZ main board.
def to_sina_symbol(code: str) -> str:
    """Convert a stock code to the sina-compatible symbol used by AkShare."""
    if code.startswith(("60", "68", "9")):
        return f"sh{code}"
    if code.startswith(("00", "30", "2")):
        return f"sz{code}"
    if code.startswith("8"):
        return f"bj{code}"
    return code


def fetch_daily_prices(
    code: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq",
) -> list[dict[str, Any]]:
    """Return daily price rows for a single stock via Baostock."""

    import baostock as bs  # type: ignore[import-untyped]
    import pandas as pd  # type: ignore[import-untyped]
    pd.DataFrame.append = pd.DataFrame._append  # pandas 2.x compat

    prefix = "sh" if code.startswith(("60", "68")) else "sz"
    symbol = f"{prefix}.{code}"
    adj_flag = "2" if adjust == "qfq" else "1" if adjust == "hfq" else "3"

    bs.login()
    try:
        rs = bs.query_history_k_data_plus(
            symbol, "date,open,high,low,close,volume,amount,turn",
            start_date=start_date, end_date=end_date,
            frequency="d", adjustflag=adj_flag,
        )
        raw = rs.get_data()
    finally:
        bs.logout()

    rows: list[dict[str, Any]] = []
    for _, row in raw.iterrows():
        volume = float(row["volume"]) if row["volume"] else 0
        if volume <= 0:
            continue

        rows.append(
            {
                "code": code,
                "trade_date": str(row["date"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": volume,
                "amount": float(row["amount"]) if row["amount"] else 0,
                "pct_change": None,
                "turnover": float(row["turn"]) if row["turn"] else 0,
                "adjust_type": adjust,
            }
        )

    return rows


def save_raw_prices(
    code: str,
    raw_df: Any,
    source: str = "ak.stock_zh_a_daily",
) -> Path:
    """Save raw AkShare response for a single stock to data/raw/."""

    raw_dir = get_config_paths()["rawDataPath"]
    raw_dir.mkdir(parents=True, exist_ok=True)

    collected_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    timestamp = collected_at.strftime("%Y%m%d_%H%M%S")
    csv_path = raw_dir / f"prices_{code}_{timestamp}.csv"
    meta_path = raw_dir / f"prices_{code}_{timestamp}_meta.json"

    raw_df.to_csv(csv_path, index=False)

    meta = {
        "source": source,
        "code": code,
        "collected_at": collected_at.isoformat(timespec="seconds"),
        "row_count": len(raw_df),
        "columns": list(raw_df.columns),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return csv_path


def upsert_daily_prices(
    rows: list[dict[str, Any]],
    connection: sqlite3.Connection,
) -> int:
    """Insert or ignore daily price rows in a single transaction.

    Uses the (code, trade_date, adjust_type) unique constraint so repeated
    runs do not produce duplicates.  Returns the number of rows written.
    """

    upsert_sql = """
        INSERT INTO daily_prices (
            code, trade_date, open, high, low, close,
            volume, amount, pct_change, turnover, adjust_type
        )
        VALUES (
            :code, :trade_date, :open, :high, :low, :close,
            :volume, :amount, :pct_change, :turnover, :adjust_type
        )
        ON CONFLICT(code, trade_date, adjust_type) DO UPDATE SET
            open        = excluded.open,
            high        = excluded.high,
            low         = excluded.low,
            close       = excluded.close,
            volume      = excluded.volume,
            amount      = excluded.amount,
            pct_change  = excluded.pct_change,
            turnover    = excluded.turnover
    """

    with connection:
        connection.executemany(upsert_sql, rows)

    return len(rows)
