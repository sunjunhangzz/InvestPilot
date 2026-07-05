/**
 * GET /api/watchlist
 *
 * Return watchlist entries with computed indicators:
 * - return_pct: (latest - entry) / entry * 100
 * - max_drawdown_pct: peak-to-trough since entry
 * - trend_breach: below MA20 or MA60
 */
import { ok } from "@/lib/server/api-response";
import { queryAll } from "@/lib/server/db";

export async function GET() {
  const rows = queryAll(
    `SELECT w.code, s.name, w.status, w.entry_price, w.latest_price,
            w.tracking_days, w.first_recommended_date, w.last_recommended_date,
            w.exit_reason
     FROM watchlist w
     JOIN stocks s ON s.code = w.code
     ORDER BY w.first_recommended_date DESC`,
  ) as Array<Record<string, unknown>>;

  if (rows.length === 0) return ok([]);

  const codes = rows.map((r) => r["code"] as string);
  const placeholders = codes.map(() => "?").join(",");

  // Batch-load prices since each stock's first_recommended_date.
  const allPrices = queryAll(
    `SELECT dp.code, dp.trade_date, dp.close
     FROM daily_prices dp
     WHERE dp.code IN (${placeholders})
     ORDER BY dp.code, dp.trade_date`,
    codes,
  ) as Array<{ code: string; trade_date: string; close: number }>;

  const priceMap = new Map<string, Array<{ close: number; trade_date: string }>>();
  for (const p of allPrices) {
    if (!priceMap.has(p.code)) priceMap.set(p.code, []);
    priceMap.get(p.code)!.push({ close: p.close, trade_date: p.trade_date });
  }

  const result = rows.map((r) => {
    const code = r["code"] as string;
    const entryPrice = (r["entry_price"] as number) ?? 0;
    const latestPrice = (r["latest_price"] as number) ?? 0;
    const prices = priceMap.get(code) ?? [];

    // Return since entry.
    let returnPct: number | null = null;
    if (entryPrice > 0) {
      returnPct = Math.round(((latestPrice - entryPrice) / entryPrice) * 10000) / 100;
    }

    // Max drawdown since entry.
    let maxDd: number | null = null;
    if (prices.length > 0 && entryPrice > 0) {
      let peak = prices[0].close;
      let worst = 0;
      for (const p of prices) {
        if (p.close > peak) peak = p.close;
        const dd = (p.close - peak) / peak;
        if (dd < worst) worst = dd;
      }
      maxDd = Math.round(worst * 10000) / 100;
    }

    // Trend breach: close below MA20 or MA60.
    let trendBreach = false;
    if (prices.length >= 20) {
      const ma20 = prices.slice(-20).reduce((s, p) => s + p.close, 0) / 20;
      if (latestPrice < ma20) trendBreach = true;
    }
    if (!trendBreach && prices.length >= 60) {
      const ma60 = prices.slice(-60).reduce((s, p) => s + p.close, 0) / 60;
      if (latestPrice < ma60) trendBreach = true;
    }

    return {
      code,
      name: r["name"],
      status: r["status"],
      entryPrice,
      latestPrice,
      trackingDays: r["tracking_days"],
      firstRecommendedDate: r["first_recommended_date"],
      lastRecommendedDate: r["last_recommended_date"],
      exitReason: r["exit_reason"],
      returnPct,
      maxDrawdownPct: maxDd,
      trendBreach: prices.length >= 20 ? trendBreach : null,
    };
  });

  return ok(result);
}
