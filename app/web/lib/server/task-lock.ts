/**
 * Lightweight task-lock for the local single-user MVP.
 *
 * First-version tasks are NOT a reliable queue:
 * - No persistence across server restarts.
 * - Stale "running" tasks are reset to "failed" on startup.
 * - Failed tasks can be manually re-triggered (each run gets a new task_id).
 * - Old failure records are preserved for debugging.
 *
 * This prevents concurrent SQLite writers that would cause BUSY errors.
 */

import Database from "better-sqlite3";
import { openDatabase } from "./db";
import { getConfigPaths } from "@shared/paths";

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
 * Mark any stale "running" tasks as "failed" — called once at startup.
 *
 * In a local Next.js dev server, restarts lose the child process that was
 * executing the task.  Without cleanup the dashboard would permanently show
 * a task as "running".
 */
export function cleanupStaleTasks(): void {
  const dbPath = getConfigPaths().databasePath;
  const db = new Database(dbPath);
  try {
    const result = db
      .prepare(
        `UPDATE system_tasks
         SET status = 'failed',
             error_message = 'server restarted — task was interrupted',
             finished_at = datetime('now', 'localtime')
         WHERE status = 'running'`,
      )
      .run();
    if (result.changes > 0) {
      console.log(`[task-lock] cleaned up ${result.changes} stale running task(s)`);
    }
  } finally {
    db.close();
  }
}

/**
 * Create a task_id row in system_tasks with pending status.
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
