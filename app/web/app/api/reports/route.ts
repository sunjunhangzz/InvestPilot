/**
 * GET /api/reports?runId=xxx
 *
 * Return AI reports joined with recommendations for the report center.
 */
import { NextRequest } from "next/server";
import { ok } from "@/lib/server/api-response";
import { queryAll } from "@/lib/server/db";
import { mapToCamelCase } from "@/lib/server/field-mapper";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  let runId = url.searchParams.get("runId");

  // Default to latest success run.
  if (!runId) {
    const rows = queryAll(
      "SELECT run_id FROM runs WHERE status = 'success' ORDER BY created_at DESC LIMIT 1",
    );
    runId = (rows[0] as { run_id: string } | undefined)?.run_id ?? "";
  }

  if (!runId) return ok([]);

  const rows = queryAll(
    `SELECT r.code, s.name, r.rating, r.total_score, r.reason, r.risk_tags, r.trade_date,
            a.content AS ai_content, a.model_name, a.status AS ai_status
     FROM recommendations r
     JOIN stocks s ON s.code = r.code
     LEFT JOIN ai_reports a ON a.run_id = r.run_id AND a.code = r.code
     WHERE r.run_id = ?
     ORDER BY r.rank`,
    [runId],
  );

  return ok(mapToCamelCase(rows));
}
