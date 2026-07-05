/**
 * GET /api/stocks/[code]/prices?days=60&period=daily|weekly|monthly
 *
 * Return OHLC price data for K-line chart rendering.
 */
import { NextRequest } from "next/server";
import { ok, fail } from "@/lib/server/api-response";
import { queryAll } from "@/lib/server/db";

type RawRow = { trade_date: string; open: number; high: number; low: number; close: number; volume: number };
type OutRow = { date: string; open: number; high: number; low: number; close: number; volume: number };

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ code: string }> },
) {
  const { code } = await params;
  const url = new URL(request.url);
  const days = Math.min(parseInt(url.searchParams.get("days") ?? "60", 10) || 60, 365);
  const period = url.searchParams.get("period") ?? "daily";

  const rawRows = queryAll(
    `SELECT trade_date, open, high, low, close, volume
     FROM daily_prices WHERE code = ? ORDER BY trade_date ASC LIMIT ?`,
    [code, days * 7],
  );

  if (rawRows.length === 0) {
    const stockExists = queryAll("SELECT 1 FROM stocks WHERE code = ?", [code]).length > 0;
    if (!stockExists) return fail("NOT_FOUND", `stock '${code}' not found`, 404);
    return ok({ prices: [] });
  }

  const typed = rawRows as unknown as RawRow[];
  let prices: OutRow[];

  if (period === "weekly") {
    prices = aggregate(typed, "week");
  } else if (period === "monthly") {
    prices = aggregate(typed, "month");
  } else {
    prices = typed.slice(-days).map(r => ({ date: r.trade_date, open: r.open, high: r.high, low: r.low, close: r.close, volume: r.volume }));
  }

  return ok({ prices });
}

function aggregate(rows: RawRow[], mode: "week" | "month"): OutRow[] {
  const groups = new Map<string, RawRow[]>();

  for (const r of rows) {
    let key: string;
    if (mode === "week") {
      const d = new Date(r.trade_date + "T00:00:00");
      const day = d.getUTCDay();
      const monday = new Date(d);
      monday.setUTCDate(d.getUTCDate() - (day === 0 ? 6 : day - 1));
      key = monday.toISOString().slice(0, 10);
    } else {
      key = r.trade_date.slice(0, 7);
    }
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(r);
  }

  const result: OutRow[] = [];
  for (const [key, group] of groups) {
    result.push({
      date: key,
      open: group[0].open,
      high: Math.max(...group.map((r) => r.high)),
      low: Math.min(...group.map((r) => r.low)),
      close: group[group.length - 1].close,
      volume: group.reduce((s, r) => s + r.volume, 0),
    });
  }
  return result;
}
