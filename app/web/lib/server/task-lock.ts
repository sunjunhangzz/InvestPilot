/**
 * Lightweight task-lock for the local single-user MVP.
 *
 * Checks system_tasks for any running write task before allowing a new one.
 * This prevents concurrent SQLite writers that would cause BUSY errors.
 */

import Database from "better-sqlite3";
import { openDatabase } from "./db";

/**
 * Return the task_name of any currently-running write task, or null.
 */
export function findRunningWriteTask(): string | null {
  const db = openDatabase();
  try {
    const row = db
      .prepare(
        "SELECT task_name FROM system_tasks WHERE status = 'running' LIMIT 1",
      )
      .get() as { task_name: string } | undefined;
    return row?.task_name ?? null;
  } finally {
    db.close();
  }
}

/**
 * Create a task_id row in system_tasks with pending status.
 *
 * Returns the task_id to pass to the worker script.
 */
export function createTaskRecord(
  db: Database.Database,
  taskId: string,
  taskName: string,
  runId: string | null = null,
): void {
  db.prepare(
    `INSERT INTO system_tasks (task_id, run_id, task_name, status)
     VALUES (?, ?, ?, 'pending')`,
  ).run(taskId, runId, taskName);
}
