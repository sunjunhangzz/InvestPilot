/**
 * GET /api/backtest?runId=xxx&days=20
 *
 * Return backtest metrics for a given run.
 */
import { NextRequest } from "next/server";
import { ok } from "@/lib/server/api-response";
import { queryAll, queryOne } from "@/lib/server/db";

function avg(arr: number[]): number | null {
  if (arr.length === 0) return null;
  return arr.reduce((s, v) => s + v, 0) / arr.length;
}

function std(arr: number[], mean: number): number {
  if (arr.length < 2) return 0;
  const variance = arr.reduce((s, v) => s + (v - mean) ** 2, 0) / (arr.length - 1);
  return Math.sqrt(variance);
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const runId = url.searchParams.get("runId")
    ?? (queryAll("SELECT run_id FROM runs WHERE status='success' ORDER BY created_at DESC LIMIT 1") as { run_id: string }[])[0]?.run_id
    ?? "";
  const days = parseInt(url.searchParams.get("days") ?? "20", 10);
  if (!runId) return ok({});

  // --- recommendations for this run ---
  const recs = queryAll(
    `SELECT r.code, s.name, s.board, s.industry, r.rating, r.total_score, r.trade_date
     FROM recommendations r JOIN stocks s ON s.code=r.code WHERE r.run_id=? ORDER BY r.rank`,
    [runId],
  ) as Array<Record<string, unknown>>;

  if (recs.length === 0) return ok({});

  const tradeDate = recs[0]["trade_date"] as string;
  const codes = recs.map((r) => r["code"] as string);

  // --- forward prices: check availability ---
  const latestPriceDate = (queryOne(
    "SELECT MAX(trade_date) AS d FROM daily_prices WHERE code IN (" + codes.map(() => "?").join(",") + ")",
    codes,
  ) as { d: string } | null)?.d ?? "";

  const hasForward = latestPriceDate > tradeDate;

  // --- forward returns (only if prices exist) ---
  const forwardReturns: Record<number, number[]> = {};
  const winLoss: { gains: number[]; losses: number[] } = { gains: [], losses: [] };
  const decayData: Array<{ day: number; avgReturn: number | null }> = [];
  const windows = [1, 3, 5, 10, 15, 20];

  for (const w of windows) {
    forwardReturns[w] = [];
  }

  if (hasForward) {
    for (const code of codes) {
      const rows = queryAll(
        `SELECT close FROM daily_prices WHERE code=? AND trade_date > ? ORDER BY trade_date LIMIT ?`,
        [code, tradeDate, days + 1],
      ) as Array<{ close: number }>;

      const entryClose = (queryOne(
        "SELECT close FROM daily_prices WHERE code=? AND trade_date=?",
        [code, tradeDate],
      ) as { close: number } | null)?.close;

      if (!entryClose || rows.length === 0) continue;

      for (const w of windows) {
        if (rows.length >= w) {
          const ret = ((rows[w - 1].close - entryClose) / entryClose) * 100;
          forwardReturns[w].push(ret);
          if (w === windows[windows.length - 1]) {
            if (ret > 0) winLoss.gains.push(ret);
            else winLoss.losses.push(ret);
          }
        }
      }
    }

    for (const w of windows) {
      decayData.push({ day: w, avgReturn: avg(forwardReturns[w]) });
    }
  }

  // --- win rate / profit factor ---
  const winRate = (winLoss.gains.length + winLoss.losses.length) > 0
    ? Math.round((winLoss.gains.length / (winLoss.gains.length + winLoss.losses.length)) * 100)
    : null;

  const avgGain = avg(winLoss.gains);
  const avgLoss = avg(winLoss.losses);
  const profitFactor = avgGain && avgLoss && avgLoss !== 0
    ? Math.round((avgGain / Math.abs(avgLoss)) * 100) / 100
    : null;

  // --- Sharpe ---
  let sharpe: number | null = null;
  if (hasForward && forwardReturns[1] && forwardReturns[1].length > 1) {
    const allDaily = forwardReturns[1].map((r) => r / 100);
    const dailyAvg = avg(allDaily)!;
    const dailyStd = std(allDaily, dailyAvg);
    sharpe = dailyStd > 0 ? Math.round(((dailyAvg - 0.015 / 252) / dailyStd) * Math.sqrt(252) * 100) / 100 : null;
  }

  // --- A/B breakdown ---
  const aReturns = recs.filter((r) => r["rating"] === "A").map((r) => forwardReturns[windows[windows.length - 1]]?.find((_, i) => recs[i]?.code === r["code"])).filter((v): v is number => v !== undefined);
  const bReturns = recs.filter((r) => r["rating"] === "B").map((r) => forwardReturns[windows[windows.length - 1]]?.find((_, i) => recs[i]?.code === r["code"])).filter((v): v is number => v !== undefined);

  // --- industry concentration ---
  const indCounts: Record<string, number> = {};
  for (const r of recs) {
    const ind = (r["industry"] as string) || "未知";
    indCounts[ind] = (indCounts[ind] || 0) + 1;
  }
  const topIndustry = Object.entries(indCounts).sort((a, b) => b[1] - a[1])[0];
  const concentration = topIndustry ? Math.round((topIndustry[1] / recs.length) * 100) : 0;

  // --- turnover vs previous run ---
  let turnoverData: { overlap: number; newCount: number; exitCount: number } | null = null;
  const prevRun = queryOne(
    "SELECT run_id FROM runs WHERE status='success' AND run_id < ? ORDER BY created_at DESC LIMIT 1",
    [runId],
  );
  if (prevRun) {
    const prevCodes = new Set(
      (queryAll("SELECT code FROM recommendations WHERE run_id=?", [(prevRun as { run_id: string }).run_id]) as Array<{ code: string }>).map((r) => r.code),
    );
    const currCodes = new Set(codes);
    const overlap = [...currCodes].filter((c) => prevCodes.has(c)).length;
    turnoverData = {
      overlap: Math.round((overlap / currCodes.size) * 100),
      newCount: currCodes.size - overlap,
      exitCount: prevCodes.size - overlap,
    };
  }

  // --- factor IC ---
  const factorIC: Record<string, number | null> = {};
  const factorNames = ["trend_score", "momentum_score", "liquidity_score", "risk_score"];
  for (const fn of factorNames) {
    const pairs: Array<{ factor: number; ret: number }> = [];
    const factorRows = queryAll(
      `SELECT code, ${fn} FROM factors WHERE run_id=?`,
      [runId],
    ) as Array<Record<string, unknown>>;
    for (const fr of factorRows) {
      const idx = codes.indexOf(fr["code"] as string);
      if (idx >= 0 && forwardReturns[windows[windows.length - 1]]?.[idx] !== undefined) {
        pairs.push({ factor: fr[fn] as number, ret: forwardReturns[windows[windows.length - 1]][idx] });
      }
    }
    if (pairs.length >= 5) {
      const fMean = avg(pairs.map((p) => p.factor))!;
      const rMean = avg(pairs.map((p) => p.ret))!;
      const fStd = std(pairs.map((p) => p.factor), fMean);
      const rStd = std(pairs.map((p) => p.ret), rMean);
      if (fStd > 0 && rStd > 0) {
        const ic = pairs.reduce((s, p) => s + (p.factor - fMean) * (p.ret - rMean), 0) / ((pairs.length - 1) * fStd * rStd);
        factorIC[fn] = Math.round(ic * 100) / 100;
      } else {
        factorIC[fn] = null;
      }
    } else {
      factorIC[fn] = null;
    }
  }

  return ok({
    runId,
    tradeDate,
    recCount: recs.length,
    hasForward,
    forwardReturns: Object.fromEntries(Object.entries(forwardReturns).map(([k, v]) => [k, avg(v)])),
    decayData,
    winRate,
    profitFactor,
    sharpe,
    avgAReturn: avg(aReturns),
    avgBReturn: avg(bReturns),
    industryConcentration: { top: topIndustry?.[0], pct: concentration },
    turnover: turnoverData,
    factorIC,
  });
}
