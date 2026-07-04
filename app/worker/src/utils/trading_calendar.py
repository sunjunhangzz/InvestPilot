"""Trading-date helpers derived from the daily_prices table.

The MVP does not use an external trading calendar.  Instead, the latest
available trading date is inferred from the data that has already been
collected.  This is sufficient for a system that runs daily after market
close — weekends and holidays simply have no rows in daily_prices.
"""

from __future__ import annotations

import sqlite3

from app.worker.src.db import connect_database


def get_latest_trading_date(
    connection: sqlite3.Connection | None = None,
) -> str | None:
    """Return the most recent trade_date in daily_prices, or None if empty.

    All factor calculation and screening pipelines should use this as their
    reference date so that non-trading-day runs do not break.
    """

    active_connection = connection or connect_database()

    try:
        row = active_connection.execute(
            "SELECT MAX(trade_date) AS latest FROM daily_prices"
        ).fetchone()
        if row is None:
            return None
        value = row["latest"]
        # sqlite3.Row access; row may also be a tuple.
        return str(value) if value is not None else None
    finally:
        if connection is None:
            active_connection.close()
