"""Initialize the local SQLite database."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.db import database_connection, get_database_path
from app.worker.src.db.schema import initialize_schema
from app.worker.src.loggers import log_exception, write_json_log


def main() -> int:
    """Create missing database tables and indexes."""

    try:
        with database_connection() as connection:
            initialize_schema(connection)

        write_json_log(
            file_name="worker.log",
            level="INFO",
            module="init_db",
            message="database schema initialized",
            context={"database_path": str(get_database_path())},
        )
        print(f"database initialized: {get_database_path()}")
        return 0
    except Exception as error:
        log_exception(
            file_name="worker.log",
            module="init_db",
            message="database schema initialization failed",
            error=error,
            context={"database_path": str(get_database_path())},
        )
        print(f"database initialization failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
