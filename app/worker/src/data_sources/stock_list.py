"""Fetch A-share stock list from AkShare and classify by market, board, and status."""

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.shared.paths import get_config_paths


@dataclass
class ExclusionStats:
    """Counters for stocks skipped or flagged during classification."""

    total_raw: int = 0
    empty_code_or_name: int = 0
    b_share: int = 0
    neeq: int = 0
    is_st: int = 0
    is_inactive: int = 0
    by_board: dict[str, int] = field(default_factory=dict)
    kept: int = 0

    def summary_lines(self) -> list[str]:
        """Return human-readable summary lines for the exclusion breakdown."""
        lines: list[str] = []
        lines.append(f"  AkShare returned: {self.total_raw}")
        lines.append(f"  written (kept): {self.kept}")
        skipped_total = self.empty_code_or_name + self.b_share + self.neeq
        if skipped_total:
            lines.append(f"  skipped: {skipped_total}")
            if self.empty_code_or_name:
                lines.append(f"    - empty code/name: {self.empty_code_or_name}")
            if self.b_share:
                lines.append(f"    - B-shares (9xxxxx): {self.b_share}")
            if self.neeq:
                lines.append(f"    - NEEQ (4xxxxx): {self.neeq}")
        lines.append(f"  flagged ST: {self.is_st}")
        lines.append(f"  flagged inactive (退市等): {self.is_inactive}")
        lines.append("  by board:")
        for board, count in sorted(self.by_board.items(), key=lambda x: -x[1]):
            lines.append(f"    {board}: {count}")
        # Main board pool is the subset the screening pipeline will actually use.
        main_board = self.by_board.get("主板", 0) - self.is_st - self.is_inactive
        lines.append(f"  主板候选池 (主板 - ST - 退市): {max(main_board, 0)}")
        return lines


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


def save_raw_stock_list(raw_df: Any, source: str = "ak.stock_info_a_code_name") -> Path:
    """Save the raw AkShare DataFrame to data/raw/ for future field-change audits.

    The CSV is the primary artifact; a companion ``_meta.json`` records the
    data source, collection timestamp, and row count so investigations later
    can trace provenance without guessing.
    """

    raw_dir = get_config_paths()["rawDataPath"]
    raw_dir.mkdir(parents=True, exist_ok=True)

    collected_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    timestamp = collected_at.strftime("%Y%m%d_%H%M%S")
    csv_path = raw_dir / f"stocks_raw_{timestamp}.csv"
    meta_path = raw_dir / f"stocks_raw_{timestamp}_meta.json"

    raw_df.to_csv(csv_path, index=False)

    meta = {
        "source": source,
        "collected_at": collected_at.isoformat(timespec="seconds"),
        "row_count": len(raw_df),
        "columns": list(raw_df.columns),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return csv_path


def fetch_stock_list() -> tuple[list[dict[str, Any]], ExclusionStats]:
    """Return stock dicts and exclusion statistics from AkShare.

    Each dict contains the fields matching the `stocks` table:
    code, name, market, board, industry, is_st, is_active, list_date.
    """

    # Import here so the module-level path fix runs before akshare tries
    # to import anything that needs the correct sys.path.
    import akshare as ak  # type: ignore[import-untyped]

    raw = ak.stock_info_a_code_name()

    # Save raw data before processing — if AkShare changes fields later,
    # the CSV + meta files let us diff the old structure.
    save_raw_stock_list(raw)

    stats = ExclusionStats(total_raw=len(raw))
    stocks: list[dict[str, Any]] = []

    for _, row in raw.iterrows():
        code = str(row["code"]).strip()
        name = str(row["name"]).strip()

        if not code or not name:
            stats.empty_code_or_name += 1
            continue

        # B-shares and NEEQ are out of scope for MVP.
        if code.startswith("9"):
            stats.b_share += 1
            continue
        if code.startswith("4"):
            stats.neeq += 1
            continue

        classification = classify_stock(code, name)
        board = classification["board"]
        stats.by_board[board] = stats.by_board.get(board, 0) + 1

        if classification["is_st"]:
            stats.is_st += 1
        if not classification["is_active"]:
            stats.is_inactive += 1

        stocks.append(
            {
                "code": code,
                "name": name,
                "market": classification["market"],
                "board": board,
                "industry": None,
                "is_st": classification["is_st"],
                "is_active": classification["is_active"],
                "list_date": None,
            }
        )

    stats.kept = len(stocks)
    return stocks, stats


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
