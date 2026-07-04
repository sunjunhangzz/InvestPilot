/**
 * GET /api/watchlist
 *
 * Return all watchlist entries with stock names.
 */
import { ok } from "@/lib/server/api-response";
import { queryAll } from "@/lib/server/db";
import { mapToCamelCase } from "@/lib/server/field-mapper";

export async function GET() {
  const rows = queryAll(
    `SELECT w.code, s.name, w.status, w.entry_price, w.latest_price,
            w.tracking_days, w.first_recommended_date, w.last_recommended_date,
            w.exit_reason
     FROM watchlist w
     JOIN stocks s ON s.code = w.code
     ORDER BY w.first_recommended_date DESC`,
  );

  return ok(mapToCamelCase(rows));
}
