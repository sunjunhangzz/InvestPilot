/**
 * GET /api/runs/latest
 *
 * Return the most recent successful run.
 */
import { ok } from "@/lib/server/api-response";
import { queryOne } from "@/lib/server/db";
import { mapToCamelCase } from "@/lib/server/field-mapper";

export async function GET() {
  const run = queryOne(
    `SELECT run_id, trade_date, run_type, status, started_at, finished_at
     FROM runs WHERE status = 'success' ORDER BY created_at DESC LIMIT 1`,
  );
  return ok(mapToCamelCase(run ?? {}));
}
