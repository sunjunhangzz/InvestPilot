/**
 * GET /api/recommendations
 *
 * Return the latest recommendations, joined with stock names.
 */
import { ok } from "@/lib/server/api-response";
import { queryAll } from "@/lib/server/db";
import { mapToCamelCase } from "@/lib/server/field-mapper";

export async function GET() {
  const rows = queryAll(
    `SELECT r.code, s.name, r.rating, r.rank, r.total_score,
            r.reason, r.risk_tags, r.trade_date,
            f.trend_score, f.momentum_score, f.liquidity_score, f.risk_score,
            (SELECT close FROM daily_prices WHERE code = r.code ORDER BY trade_date DESC LIMIT 1) AS close
     FROM recommendations r
     JOIN stocks s ON s.code = r.code
     LEFT JOIN factors f ON f.run_id = r.run_id AND f.code = r.code
     WHERE r.run_id = (SELECT run_id FROM runs WHERE status = 'success' ORDER BY created_at DESC LIMIT 1)
     ORDER BY r.rank`,
  );

  return ok(mapToCamelCase(rows));
}
