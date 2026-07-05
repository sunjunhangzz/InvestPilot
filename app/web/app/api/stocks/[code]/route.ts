/**
 * GET /api/stocks/[code]
 *
 * Return stock detail: basic info + factors + recommendation history.
 */
import { NextRequest } from "next/server";
import { ok, fail } from "@/lib/server/api-response";
import { queryOne, queryAll } from "@/lib/server/db";
import { mapToCamelCase } from "@/lib/server/field-mapper";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ code: string }> },
) {
  const { code } = await params;

  // Stock info.
  const stock = queryOne(
    `SELECT code, name, market, board, industry, is_st, is_active, list_date
     FROM stocks WHERE code = ?`,
    [code],
  );
  if (!stock) {
    return fail("NOT_FOUND", `stock '${code}' not found`, 404);
  }

  // Latest factors.
  const factors = queryOne(
    `SELECT trend_score, momentum_score, liquidity_score, risk_score, total_score, trade_date
     FROM factors WHERE code = ? ORDER BY created_at DESC LIMIT 1`,
    [code],
  );

  // Recent recommendations.
  const recs = queryAll(
    `SELECT run_id, trade_date, created_at, rating, rank, total_score, reason, risk_tags
     FROM recommendations WHERE code = ? ORDER BY created_at DESC LIMIT 5`,
    [code],
  );

  // Latest AI report.
  const aiReport = queryOne(
    `SELECT content, model_name, status, trade_date
     FROM ai_reports WHERE code = ? AND status = 'success'
     ORDER BY created_at DESC LIMIT 1`,
    [code],
  );

  // Fundamental data.
  const fundamental = queryOne(
    "SELECT * FROM fundamentals WHERE code = ?",
    [code],
  );

  // Agent committee report.
  const agentReport = queryOne(
    "SELECT rating, consensus, summary, model_name, trade_date FROM agent_reports WHERE code = ? ORDER BY created_at DESC LIMIT 1",
    [code],
  );

  return ok(
    mapToCamelCase({
      ...(stock as Record<string, unknown>),
      factors: factors ?? null,
      recentRecommendations: recs,
      aiReport: aiReport ?? null,
      fundamental: fundamental ?? null,
      agentReport: agentReport ?? null,
    }),
  );
}
