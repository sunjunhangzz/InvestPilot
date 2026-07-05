/**
 * GET /api/debates?code=000001&tradeDate=2026-07-03
 *
 * Return debate report content for a stock.
 */
import { NextRequest } from "next/server";
import fs from "node:fs";
import path from "node:path";
import { ok, fail } from "@/lib/server/api-response";
import { PROJECT_ROOT } from "@shared/paths";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const tradeDate = url.searchParams.get("tradeDate");

  if (!code || !tradeDate) {
    // List all debates for a code.
    const dir = path.join(PROJECT_ROOT, "reports", "debates");
    if (!fs.existsSync(dir)) return ok([]);

    const results: string[] = [];
    for (const d of fs.readdirSync(dir)) {
      const f = path.join(dir, d, `${code}.md`);
      if (fs.existsSync(f)) results.push(d);
    }
    return ok(results.sort().reverse());
  }

  const filePath = path.join(PROJECT_ROOT, "reports", "debates", tradeDate, `${code}.md`);
  if (!fs.existsSync(filePath)) {
    return fail("NOT_FOUND", "debate report not found", 404);
  }

  const content = fs.readFileSync(filePath, "utf-8");
  return ok({ content });
}
