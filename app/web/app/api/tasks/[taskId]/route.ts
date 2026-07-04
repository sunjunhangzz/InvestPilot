/**
 * GET /api/tasks/[taskId]
 *
 * Return the status of a single task from system_tasks.
 */
import { NextRequest } from "next/server";
import { ok, fail } from "@/lib/server/api-response";
import { queryOne } from "@/lib/server/db";
import { mapToCamelCase } from "@/lib/server/field-mapper";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> },
) {
  const { taskId } = await params;

  const row = queryOne(
    `SELECT task_id, run_id, task_name, status, started_at, finished_at, error_message, created_at
     FROM system_tasks WHERE task_id = ?`,
    [taskId],
  );

  if (!row) {
    return fail("NOT_FOUND", `task '${taskId}' not found`, 404);
  }

  return ok(mapToCamelCase(row));
}
