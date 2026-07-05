/**
 * GET /api/tasks
 *
 * Return system task history for the task log page.
 */
import { ok } from "@/lib/server/api-response";
import { queryAll } from "@/lib/server/db";
import { mapToCamelCase } from "@/lib/server/field-mapper";

export async function GET() {
  const rows = queryAll(
    `SELECT task_id, task_name, status, started_at, finished_at, error_message, created_at
     FROM system_tasks
     ORDER BY created_at DESC
     LIMIT 200`,
  );
  return ok(mapToCamelCase(rows));
}
