"""SQLite schema creation for the first version database."""

from __future__ import annotations

import sqlite3


TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL UNIQUE,
        trade_date TEXT NOT NULL,
        run_type TEXT NOT NULL CHECK (run_type IN ('manual', 'morning', 'afternoon', 'scheduled')),
        status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
        started_at TEXT,
        finished_at TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS system_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL UNIQUE,
        run_id TEXT,
        task_name TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
        started_at TEXT,
        finished_at TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stocks (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        market TEXT NOT NULL,
        board TEXT NOT NULL,
        industry TEXT,
        is_st INTEGER NOT NULL DEFAULT 0 CHECK (is_st IN (0, 1)),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
        list_date TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        amount REAL,
        pct_change REAL,
        turnover REAL,
        adjust_type TEXT NOT NULL DEFAULT 'qfq',
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (code, trade_date, adjust_type),
        FOREIGN KEY (code) REFERENCES stocks(code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS factors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        trend_score REAL,
        momentum_score REAL,
        liquidity_score REAL,
        volatility_score REAL,
        risk_score REAL,
        total_score REAL,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (run_id, code, trade_date),
        FOREIGN KEY (run_id) REFERENCES runs(run_id),
        FOREIGN KEY (code) REFERENCES stocks(code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        code TEXT NOT NULL,
        rank INTEGER NOT NULL,
        rating TEXT NOT NULL CHECK (rating IN ('A', 'B', 'C')),
        total_score REAL,
        reason TEXT,
        risk_tags TEXT,
        first_recommended_date TEXT,
        last_recommended_date TEXT,
        tracking_days INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (run_id, code),
        FOREIGN KEY (run_id) REFERENCES runs(run_id),
        FOREIGN KEY (code) REFERENCES stocks(code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        first_recommended_date TEXT NOT NULL,
        last_recommended_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('active', 'hold', 'downgraded', 'exit', 'blocked')),
        entry_price REAL,
        latest_price REAL,
        tracking_days INTEGER NOT NULL DEFAULT 0,
        min_tracking_days INTEGER NOT NULL DEFAULT 5,
        max_tracking_days INTEGER NOT NULL DEFAULT 20,
        exit_reason TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (code) REFERENCES stocks(code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        code TEXT,
        report_type TEXT NOT NULL CHECK (report_type IN ('basic', 'stock', 'daily')),
        content TEXT,
        model_name TEXT,
        status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
        error_message TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (run_id, code, report_type),
        FOREIGN KEY (run_id) REFERENCES runs(run_id),
        FOREIGN KEY (code) REFERENCES stocks(code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
]


INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_runs_trade_date_status ON runs(trade_date, status)",
    "CREATE INDEX IF NOT EXISTS idx_system_tasks_task_id ON system_tasks(task_id)",
    "CREATE INDEX IF NOT EXISTS idx_system_tasks_run_id_task_name ON system_tasks(run_id, task_name)",
    "CREATE INDEX IF NOT EXISTS idx_stocks_code ON stocks(code)",
    "CREATE INDEX IF NOT EXISTS idx_daily_prices_code_trade_date ON daily_prices(code, trade_date)",
    "CREATE INDEX IF NOT EXISTS idx_factors_run_id_total_score ON factors(run_id, total_score)",
    "CREATE INDEX IF NOT EXISTS idx_recommendations_run_id_rank ON recommendations(run_id, rank)",
    "CREATE INDEX IF NOT EXISTS idx_recommendations_trade_date_rank ON recommendations(trade_date, rank)",
    "CREATE INDEX IF NOT EXISTS idx_watchlist_status_tracking_days ON watchlist(status, tracking_days)",
    "CREATE INDEX IF NOT EXISTS idx_ai_reports_run_id_code ON ai_reports(run_id, code)",
]

FUNDAMENTALS_TABLE = """
    CREATE TABLE IF NOT EXISTS fundamentals (
        code TEXT PRIMARY KEY,
        pe REAL,
        pb REAL,
        roe REAL,
        market_cap REAL,
        revenue REAL,
        revenue_yoy REAL,
        net_profit REAL,
        net_profit_yoy REAL,
        eps REAL,
        debt_ratio REAL,
        industry TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (code) REFERENCES stocks(code)
    )
"""


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create all first-version tables and indexes without deleting existing data."""

    # All schema statements are idempotent; this transaction only creates missing
    # objects and never drops or truncates user data.
    with connection:
        for statement in TABLE_STATEMENTS:
            connection.execute(statement)

        connection.execute(FUNDAMENTALS_TABLE)

        for statement in INDEX_STATEMENTS:
            connection.execute(statement)
