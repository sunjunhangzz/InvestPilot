"""Fetch A-share stock list from AkShare and classify by market, board, and status."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def classify_stock(code: str, name: str) -> dict[str, Any]:
    """Derive market, board, and risk flags from stock code and name.

    A-share code prefix rules (simplified MVP version):

    - 600/601/603/605 → Shanghai main board
    - 000/001/002/003 → Shenzhen main board
    - 300/301         → Shenzhen ChiNext (Growth Enterprise)
    - 688             → Shanghai STAR Market
    - 8xxxxx          → Beijing Stock Exchange
    - 4xxxxx          → NEEQ / Third Board (excluded from active pool)
    - 9xxxxx          → Shanghai B-share (excluded)

    ST / *ST detection is based on the stock name.  Delisted or suspended
    stocks are also tagged via name keywords for later filtering.
    """

    code = str(code).strip()
    name = str(name).strip()

    # --- market ---
    if code.startswith(("60", "68", "9")):
        market = "SH"
    elif code.startswith(("00", "30", "2")):
        market = "SZ"
    elif code.startswith(("8", "4")):
        market = "BJ"
    else:
        market = "OTHER"

    # --- board ---
    if code.startswith(("600", "601", "603", "605")):
        board = "主板"
    elif code.startswith(("000", "001", "002", "003")):
        board = "主板"
    elif code.startswith(("300", "301")):
        board = "创业板"
    elif code.startswith("688"):
        board = "科创板"
    elif code.startswith("8"):
        board = "北交所"
    else:
        board = "其他"

    # --- ST ---
    upper_name = name.upper()
    is_st = 1 if ("ST" in upper_name) else 0

    # --- active ---
    # Stocks whose name suggests delisting or long-term suspension are
    # marked inactive so the screening pipeline skips them.
    is_active = 0 if ("退" in name) else 1

    return {
        "market": market,
        "board": board,
        "is_st": is_st,
        "is_active": is_active,
    }


def fetch_stock_list() -> list[dict[str, Any]]:
    """Return a list of stock dicts from AkShare.

    Each dict contains the fields matching the `stocks` table:
    code, name, market, board, industry, is_st, is_active, list_date.
    """

    # Import here so the module-level path fix runs before akshare tries
    # to import anything that needs the correct sys.path.
    import akshare as ak  # type: ignore[import-untyped]

    raw = ak.stock_info_a_code_name()
    stocks: list[dict[str, Any]] = []

    for _, row in raw.iterrows():
        code = str(row["code"]).strip()
        name = str(row["name"]).strip()

        if not code or not name:
            continue

        # B-shares and NEEQ are out of scope for MVP.
        if code.startswith(("9", "4")):
            continue

        classification = classify_stock(code, name)
        stocks.append(
            {
                "code": code,
                "name": name,
                "market": classification["market"],
                "board": classification["board"],
                "industry": None,
                "is_st": classification["is_st"],
                "is_active": classification["is_active"],
                "list_date": None,
            }
        )

    return stocks


def upsert_stocks(
    stocks: list[dict[str, Any]],
    connection: sqlite3.Connection,
) -> int:
    """Insert or update stock rows in a single transaction.

    Returns the number of rows written.  Uses INSERT … ON CONFLICT so
    repeated runs only refresh data instead of creating duplicates.
    """

    upsert_sql = """
        INSERT INTO stocks (
            code,
            name,
            market,
            board,
            industry,
            is_st,
            is_active,
            list_date,
            updated_at
        )
        VALUES (
            :code,
            :name,
            :market,
            :board,
            :industry,
            :is_st,
            :is_active,
            :list_date,
            datetime('now', 'localtime')
        )
        ON CONFLICT(code) DO UPDATE SET
            name      = excluded.name,
            market    = excluded.market,
            board     = excluded.board,
            industry  = excluded.industry,
            is_st     = excluded.is_st,
            is_active = excluded.is_active,
            list_date = excluded.list_date,
            updated_at = datetime('now', 'localtime')
    """

    with connection:
        connection.executemany(upsert_sql, stocks)

    return len(stocks)
