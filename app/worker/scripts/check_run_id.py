"""Smoke test for run_id generation."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.db import database_connection
from app.worker.src.tasks import create_run


def main() -> int:
    """Create sample run rows and print generated run IDs."""

    trade_date = "2026-07-04"

    with database_connection() as connection:
        with connection:
            connection.execute(
                """
                DELETE FROM runs
                WHERE trade_date = ?
                  AND run_type IN ('manual', 'morning')
                """,
                (trade_date,),
            )

        run_ids = [
            create_run(
                run_type="manual",
                trade_date=trade_date,
                connection=connection,
            ),
            create_run(
                run_type="manual",
                trade_date=trade_date,
                connection=connection,
            ),
            create_run(
                run_type="morning",
                trade_date=trade_date,
                connection=connection,
            ),
        ]

    for run_id in run_ids:
        print(run_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
