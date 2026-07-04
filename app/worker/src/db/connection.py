"""SQLite connection helpers for worker code."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.shared.paths import get_config_paths


def get_database_path() -> Path:
    """Return the configured SQLite database path."""

    return get_config_paths()["databasePath"]


def ensure_database_directory() -> Path:
    """Ensure the database parent directory exists and return the DB path."""

    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return database_path


def connect_database() -> sqlite3.Connection:
    """Create a SQLite connection with project defaults.

    The busy timeout reduces immediate write-lock failures when later worker
    scripts serialize writes through one process but SQLite still needs time to
    release file locks.
    """

    database_path = ensure_database_directory()
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection and always close it."""

    connection = connect_database()
    try:
        yield connection
    finally:
        connection.close()
