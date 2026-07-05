"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/AppShell";

const DecayChart = dynamic(() => import("@/components/DecayChart"), { ssr: false });

type BacktestData = {
  runId: string; tradeDate: string; recCount: number; hasForward: boolean;
  forwardReturns: Record<string, number | null>;
  decayData: Array<{ day: number; avgReturn: number | null }>;
  winRate: number | null; profitFactor: number | null; sharpe: number | null;
  avgAReturn: number | null; avgBReturn: number | null;
  industryConcentration: { top: string; pct: number } | null;
  turnover: { overlap: number; newCount: number; exitCount: number } | null;
  factorIC: Record<string, number | null>;
};

export default function BacktestPage() {
  const [data, setData] = useState<BacktestData | null>(null);
  const [load, setLoad] = useState(true);

  useEffect(() => {
    let c = false;
    async function f() {
      try { const r = await fetch("/api/backtest?days=20"); const j = await r.json(); if (!c && j.ok) setData(j.data); } catch { /* */ }
      if (!c) setLoad(false);
    }
    f(); return () => { c = true; };
  }, []);

  if (load) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">复盘中心</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;
  if (!data) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">复盘中心</h2><div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">暂无复盘数据 — 请先运行筛选生成推荐。</div></section></AppShell>;

  const fmtPct = (v: number | null | undefined) => v != null ? `${v > 0 ? "+" : ""}${v.toFixed(1)}%` : "—";
  const fmtNum = (v: number | null | undefined, d = 2) => v != null ? v.toFixed(d) : "—";

  return (
    <AppShell><section className="mx-auto max-w-7xl px-6 py-8">
      <h2 className="text-xl font-semibold">复盘中心</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">交易日 {data.tradeDate} · {data.recCount} 只推荐 · run {data.runId}</p>

      {!data.hasForward && (
        <div className="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
          ⚠️ 前向价格数据不足（最新交易日 = 推荐日）。收益/Sharpe/衰减曲线需数据积累后展示。行业集中度、换手率当前可用。
        </div>
      )}

      {/*收益卡片*/}
      <div className="mt-6 grid gap-3 md:grid-cols-4">
        {[
          { l: "平均收益(20日)", v: fmtPct(data.forwardReturns["20"]) },
          { l: "胜率", v: data.winRate != null ? `${data.winRate}%` : "—" },
          { l: "盈亏比", v: fmtNum(data.profitFactor) },
          { l: "Sharpe", v: fmtNum(data.sharpe) },
        ].map((c) => (<div key={c.l} className="rounded-lg border border-[var(--line)] bg-white p-3"><p className="text-xs text-[var(--muted)]">{c.l}</p><p className="mt-1 text-lg font-semibold">{c.v}</p></div>))}
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {[
          { l: "A类平均收益", v: fmtPct(data.avgAReturn) },
          { l: "B类平均收益", v: fmtPct(data.avgBReturn) },
          { l: "行业集中度", v: data.industryConcentration ? `${data.industryConcentration.top} ${data.industryConcentration.pct}%` : "—" },
        ].map((c) => (<div key={c.l} className="rounded-lg border border-[var(--line)] bg-white p-3"><p className="text-xs text-[var(--muted)]">{c.l}</p><p className="mt-1 text-sm font-semibold">{c.v}</p></div>))}
      </div>

      {/*衰减曲线*/}
      <div className="mt-6">
        <h3 className="text-base font-semibold">收益衰减曲线</h3>
        {data.hasForward && data.decayData.length > 0
          ? <div className="mt-3"><DecayChart data={data.decayData} /></div>
          : <div className="mt-3 rounded-lg border border-[var(--line)] bg-white p-6 text-center text-sm text-[var(--muted)]">数据积累中（需推荐日后 N+1 个交易日价格）</div>}
      </div>

      {/*换手率 + 因子IC*/}
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-[var(--line)] bg-white p-4">
          <h3 className="text-sm font-semibold">换手率</h3>
          {data.turnover
            ? <div className="mt-2 space-y-1 text-sm"><p>重叠度：{data.turnover.overlap}%</p><p>新进：{data.turnover.newCount} 只</p><p>退出：{data.turnover.exitCount} 只</p></div>
            : <p className="mt-2 text-sm text-[var(--muted)]">至少需要 2 个 run 才能比较</p>}
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-white p-4">
          <h3 className="text-sm font-semibold">因子 IC</h3>
          <div className="mt-2 space-y-1 text-sm">
            {Object.entries(data.factorIC).map(([k, v]) => (
              <p key={k}>{k.replace("_score", "")}：{v != null ? v : (data.hasForward ? "样本不足" : "数据积累中")}</p>
            ))}
          </div>
        </div>
      </div>
    </section></AppShell>
  );
}
