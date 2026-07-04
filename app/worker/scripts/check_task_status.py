"""Smoke test for system_tasks status helpers."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.db import database_connection
from app.worker.src.tasks import (
    create_task,
    mark_task_failed,
    mark_task_failed_with_exception,
    mark_task_running,
    mark_task_success,
)


def main() -> int:
    """Create and update sample task rows for local verification."""

    success_task_id = "task_status_check_success"
    failed_task_id = "task_status_check_failed"
    exception_task_id = "task_status_check_exception"

    with database_connection() as connection:
        with connection:
            connection.execute(
                "DELETE FROM system_tasks WHERE task_id IN (?, ?, ?)",
                (success_task_id, failed_task_id, exception_task_id),
            )

        create_task(
            task_id=success_task_id,
            task_name="status_check",
            run_id="run_status_check",
            connection=connection,
        )
        mark_task_running(success_task_id, connection=connection)
        mark_task_success(success_task_id, connection=connection)

        create_task(
            task_id=failed_task_id,
            task_name="status_check",
            run_id="run_status_check",
            connection=connection,
        )
        mark_task_running(failed_task_id, connection=connection)
        mark_task_failed(
            failed_task_id,
            "status check failed summary " * 30,
            connection=connection,
        )

        create_task(
            task_id=exception_task_id,
            task_name="status_check",
            run_id="run_status_check",
            connection=connection,
        )
        mark_task_running(exception_task_id, connection=connection)
        try:
            raise RuntimeError("simulated detailed exception")
        except RuntimeError as error:
            mark_task_failed_with_exception(
                task_id=exception_task_id,
                module="check_task_status",
                error=error,
                error_summary="exception status check failed",
                run_id="run_status_check",
                context={"debug_detail": "local stack is written to worker.log"},
                connection=connection,
            )

        rows = connection.execute(
            """
            SELECT task_id, status, error_message
            FROM system_tasks
            WHERE task_id IN (?, ?, ?)
            ORDER BY task_id
            """,
            (exception_task_id, failed_task_id, success_task_id),
        ).fetchall()

    for row in rows:
        print(dict(row))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
