"""Smoke test for run_id generation and run status transitions."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.db import database_connection
from app.worker.src.tasks import (
    create_run,
    mark_run_failed,
    mark_run_failed_with_exception,
    mark_run_running,
    mark_run_success,
)


def main() -> int:
    """Create sample runs and exercise the full status lifecycle."""

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

        # --- run_id generation ---
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

        # --- status transitions ---
        success_run = create_run(
            run_type="manual",
            trade_date=trade_date,
            connection=connection,
        )
        mark_run_running(success_run, connection=connection)
        mark_run_success(success_run, connection=connection)

        failed_run = create_run(
            run_type="manual",
            trade_date=trade_date,
            connection=connection,
        )
        mark_run_running(failed_run, connection=connection)
        mark_run_failed(failed_run, "run status check failed", connection=connection)

        exception_run = create_run(
            run_type="manual",
            trade_date=trade_date,
            connection=connection,
        )
        mark_run_running(exception_run, connection=connection)
        try:
            raise RuntimeError("simulated run-level exception")
        except RuntimeError as error:
            mark_run_failed_with_exception(
                run_id=exception_run,
                module="check_run_id",
                error=error,
                error_summary="exception run status check failed",
                trade_date=trade_date,
                context={"debug_detail": "run-level stack in worker.log"},
                connection=connection,
            )

        # --- verify ---
        rows = connection.execute(
            """
            SELECT run_id, status, error_message,
                   started_at IS NOT NULL AS has_started,
                   finished_at IS NOT NULL AS has_finished
            FROM runs
            WHERE run_id IN (?, ?, ?)
            ORDER BY run_id
            """,
            (success_run, failed_run, exception_run),
        ).fetchall()

    for row in rows:
        print(dict(row))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
