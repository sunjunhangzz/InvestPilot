"""Check the local SQLite schema against the expected first-version structure.

Usage:
    python app/worker/scripts/check_schema.py
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.db import database_connection
from app.worker.src.db.schema_validator import (
    format_validation_result,
    validate_schema,
)


def main() -> int:
    """Run schema validation and print the result."""

    with database_connection() as connection:
        result = validate_schema(connection)

    print(format_validation_result(result))

    if result.valid:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
