"""Helpers for writing worker task status to system_tasks."""

from __future__ import annotations

import sqlite3
from typing import Literal

from app.worker.src.db import connect_database


TaskStatus = Literal["pending", "running", "success", "failed", "cancelled"]

VALID_TASK_STATUSES: set[str] = {
    "pending",
    "running",
    "success",
    "failed",
    "cancelled",
}


def validate_task_status(status: str) -> None:
    """Validate a system task status before writing SQLite."""

    if status not in VALID_TASK_STATUSES:
        raise ValueError(f"invalid task status: {status}")


def create_task(
    *,
    task_id: str,
    task_name: str,
    run_id: str | None = None,
    status: TaskStatus = "pending",
    connection: sqlite3.Connection | None = None,
) -> None:
    """Insert a task row.

    API Routes normally create `pending` tasks. This helper also exists in worker
    code so local scripts and tests use the same schema and status validation.
    """

    validate_task_status(status)
    active_connection = connection or connect_database()

    try:
        with active_connection:
            active_connection.execute(
                """
                INSERT INTO system_tasks (
                    task_id,
                    run_id,
                    task_name,
                    status,
                    started_at
                )
                VALUES (
                    :task_id,
                    :run_id,
                    :task_name,
                    :status,
                    CASE WHEN :status = 'running' THEN datetime('now', 'localtime') ELSE NULL END
                )
                """,
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "task_name": task_name,
                    "status": status,
                },
            )
    finally:
        if connection is None:
            active_connection.close()


def update_task_status(
    *,
    task_id: str,
    status: TaskStatus,
    error_message: str | None = None,
    connection: sqlite3.Connection | None = None,
) -> None:
    """Update a task status using the shared lifecycle rules."""

    validate_task_status(status)
    if status == "failed" and not error_message:
        raise ValueError("failed task status requires error_message")

    active_connection = connection or connect_database()

    try:
        with active_connection:
            cursor = active_connection.execute(
                """
                UPDATE system_tasks
                SET
                    status = :status,
                    started_at = CASE
                        WHEN :status = 'running' AND started_at IS NULL
                        THEN datetime('now', 'localtime')
                        ELSE started_at
                    END,
                    finished_at = CASE
                        WHEN :status IN ('success', 'failed', 'cancelled')
                        THEN datetime('now', 'localtime')
                        ELSE finished_at
                    END,
                    error_message = CASE
                        WHEN :status = 'failed' THEN :error_message
                        WHEN :status IN ('success', 'cancelled') THEN NULL
                        ELSE error_message
                    END
                WHERE task_id = :task_id
                """,
                {
                    "task_id": task_id,
                    "status": status,
                    "error_message": error_message,
                },
            )

            if cursor.rowcount != 1:
                raise ValueError(f"task not found: {task_id}")
    finally:
        if connection is None:
            active_connection.close()


def mark_task_running(
    task_id: str,
    connection: sqlite3.Connection | None = None,
) -> None:
    """Mark a task as running."""

    update_task_status(task_id=task_id, status="running", connection=connection)


def mark_task_success(
    task_id: str,
    connection: sqlite3.Connection | None = None,
) -> None:
    """Mark a task as successful."""

    update_task_status(task_id=task_id, status="success", connection=connection)


def mark_task_failed(
    task_id: str,
    error_message: str,
    connection: sqlite3.Connection | None = None,
) -> None:
    """Mark a task as failed with a user-facing error summary."""

    update_task_status(
        task_id=task_id,
        status="failed",
        error_message=error_message,
        connection=connection,
    )


def mark_task_cancelled(
    task_id: str,
    connection: sqlite3.Connection | None = None,
) -> None:
    """Mark a task as cancelled."""

    update_task_status(task_id=task_id, status="cancelled", connection=connection)
