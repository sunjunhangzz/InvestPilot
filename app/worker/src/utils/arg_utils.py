"""Shared CLI argument helpers for worker scripts.

When launched from the Next.js API, scripts receive ``--task-id <id>``.
In standalone mode (no --task-id), each script generates and creates its
own task record and manages its own task lifecycle.

In external (--task-id) mode, the script skips marking success/failed —
the Web layer handles that after the entire pipeline finishes.
"""

from __future__ import annotations

import sys
from typing import Any

from app.worker.src.tasks import create_task, mark_task_running


def resolve_task_id(
    script_name: str,
    connection: Any,
    task_id_generator: callable,
    argv: list[str] | None = None,
) -> tuple[str, bool]:
    """Return (task_id, is_external).

    - is_external=True: caller should NOT mark task success/failed.
    - is_external=False: caller manages its own task lifecycle.

    *argv* defaults to sys.argv so callers that accept their own argv
    (e.g. ``main(argv)``) can pass the parsed list for consistency.
    """

    args = argv if argv is not None else sys.argv
    external_id = None
    for i, arg in enumerate(args):
        if arg == "--task-id" and i + 1 < len(args):
            external_id = args[i + 1]
            break

    if external_id is not None:
        mark_task_running(external_id, connection=connection)
        return external_id, True

    task_id = task_id_generator()
    create_task(task_id=task_id, task_name=script_name, connection=connection)
    mark_task_running(task_id, connection=connection)
    return task_id, False
