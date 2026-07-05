/**
 * POST /api/tasks/run
 *
 * Trigger a worker pipeline.  The body selects the pipeline:
 *   { "pipeline": "update-data" | "run-screening" | "generate-report" }
 *
 * When AI is enabled (via settings), "run-screening" automatically appends
 * generate_report to the pipeline.
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
  "generate-report": [],
};

function getPipelineScripts(pipeline: string): string[] {
  const scripts = [...(PIPELINES[pipeline] ?? [])];
  if (pipeline === "run-screening" && isAiEnabled()) {
    scripts.push("generate_report");
  }
  return scripts;
}

function isAiEnabled(): boolean {
  try {
    const dbPath = getConfigPaths().databasePath;
    const db = new Database(dbPath, { readonly: true });
    const row = db.prepare("SELECT value FROM settings WHERE key = 'ai.enabled'").get() as { value: string } | undefined;
    db.close();
    if (row) {
      try { return JSON.parse(row.value) as boolean; } catch { return row.value === "true"; }
    }
  } catch { /* fall through */ }
  return false;
}

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

  const scripts = getPipelineScripts(pipeline);
  if (scripts.length === 0) {
    return fail("NOT_IMPLEMENTED", `pipeline '${pipeline}' is not yet implemented`);
  }

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

  runWorkers(scripts, taskId)
    .then(({ success }) => {
      const db2 = new Database(dbPath);
      try {
        db2.prepare(
          success
            ? "UPDATE system_tasks SET status='success', finished_at=datetime('now','localtime') WHERE task_id=?"
            : "UPDATE system_tasks SET status='failed', error_message='pipeline script returned non-zero', finished_at=datetime('now','localtime') WHERE task_id=?"
        ).run(taskId);
      } finally { db2.close(); }
      writeApiLog({ level: success ? "INFO" : "ERROR", module: "tasks_run", message: success ? `pipeline ${pipeline} complete` : `pipeline ${pipeline} failed`, taskId });
    })
    .catch((err) => {
      const db3 = new Database(dbPath);
      try {
        db3.prepare("UPDATE system_tasks SET status='failed', error_message=?, finished_at=datetime('now','localtime') WHERE task_id=?").run(`pipeline crashed: ${String(err)}`, taskId);
      } finally { db3.close(); }
      writeApiLog({ level: "ERROR", module: "tasks_run", message: `pipeline ${pipeline} crashed: ${String(err)}`, taskId });
    });

  return ok({ taskId });
}
