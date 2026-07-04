/**
 * POST /api/tasks/run
 *
 * Trigger a worker pipeline.  The body selects the pipeline:
 *   { "pipeline": "update-data" | "run-screening" | "generate-report" }
 *
 * Returns { ok: true, data: { taskId } } immediately — the worker runs async.
 */
import { NextRequest } from "next/server";
import Database from "better-sqlite3";
import crypto from "node:crypto";
import { ok, fail } from "@/lib/server/api-response";
import { getConfigPaths } from "@shared/paths";
import { findRunningWriteTask, createTaskRecord } from "@/lib/server/task-lock";
import { runWorkers } from "@/lib/server/worker-launcher";
import { writeApiLog } from "@/lib/server/logger";

const PIPELINES: Record<string, string[]> = {
  "update-data": ["update_stocks", "update_prices"],
  "run-screening": ["calc_factors", "run_screening", "update_watchlist"],
  "generate-report": [], // AI report — not yet implemented.
};

function generateTaskId(): string {
  return `web_${crypto.randomUUID()}`;
}

export async function POST(request: NextRequest) {
  let pipeline: string;
  try {
    const body = await request.json();
    pipeline = body.pipeline;
  } catch {
    return fail("INVALID_JSON", "request body must be JSON");
  }

  const scripts = PIPELINES[pipeline];
  if (!scripts) {
    return fail(
      "UNKNOWN_PIPELINE",
      `unknown pipeline: ${pipeline}. Use: ${Object.keys(PIPELINES).join(", ")}`,
    );
  }

  if (scripts.length === 0) {
    return fail("NOT_IMPLEMENTED", `pipeline '${pipeline}' is not yet implemented`);
  }

  // Task lock — only one write pipeline at a time.
  const running = findRunningWriteTask();
  if (running) {
    return fail("TASK_LOCKED", `task '${running}' is already running — wait for it to finish`);
  }

  const taskId = generateTaskId();
  const dbPath = getConfigPaths().databasePath;
  const db = new Database(dbPath);

  try {
    createTaskRecord(db, taskId, pipeline);
  } finally {
    db.close();
  }

  writeApiLog({
    level: "INFO",
    module: "tasks_run",
    message: `start pipeline: ${pipeline}`,
    taskId,
  });

  // Fire-and-forget: don't await the worker — the frontend polls status.
  runWorkers(scripts, taskId)
    .then(({ success }) => {
      const db = new Database(dbPath);
      try {
        db.prepare(
          success
            ? "UPDATE system_tasks SET status='success', finished_at=datetime('now','localtime') WHERE task_id=?"
            : "UPDATE system_tasks SET status='failed', error_message='pipeline script returned non-zero', finished_at=datetime('now','localtime') WHERE task_id=?"
        ).run(taskId);
      } finally {
        db.close();
      }
      writeApiLog({
        level: success ? "INFO" : "ERROR",
        module: "tasks_run",
        message: success ? `pipeline ${pipeline} complete` : `pipeline ${pipeline} failed`,
        taskId,
      });
    })
    .catch((err) => {
      const db = new Database(dbPath);
      try {
        db.prepare(
          "UPDATE system_tasks SET status='failed', error_message=?, finished_at=datetime('now','localtime') WHERE task_id=?"
        ).run(`pipeline crashed: ${String(err)}`, taskId);
      } finally {
        db.close();
      }
      writeApiLog({
        level: "ERROR",
        module: "tasks_run",
        message: `pipeline ${pipeline} crashed: ${String(err)}`,
        taskId,
      });
    });

  return ok({ taskId });
}
