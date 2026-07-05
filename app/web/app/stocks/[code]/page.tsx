"use client";

import { useEffect, useState, use } from "react";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/AppShell";

const PriceChart = dynamic(() => import("@/components/PriceChart"), { ssr: false });

type StockDetail = {
  code: string; name: string; board: string; isSt: number;
  factors: { trendScore: number; momentumScore: number; liquidityScore: number; riskScore: number; totalScore: number; tradeDate: string } | null;
  recentRecommendations: { tradeDate: string; rating: string; totalScore: number; reason: string; riskTags: string }[];
  aiReport: { content: string; modelName: string; tradeDate: string } | null;
};

type Props = { params: Promise<{ code: string }> };

export default function StockPage({ params }: Props) {
  const { code } = use(params);
  const [data, setData] = useState<StockDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [load, setLoad] = useState(true);

  useEffect(() => {
    let c = false;
    async function f() {
      try { const r = await fetch(`/api/stocks/${code}`); const j = await r.json(); if (!j.ok) throw new Error(j.error?.message ?? ""); if (!c) { setData(j.data); setErr(null); } } catch (e) { if (!c) { setErr((e as Error).message); setData(null); } }
      if (!c) setLoad(false);
    }
    f(); return () => { c = true; };
  }, [code]);

  if (load) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">股票详情</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;
  if (err) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">股票详情</h2><div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">{err}<button className="ml-4 underline" onClick={() => window.location.reload()} type="button">重试</button></div></section></AppShell>;
  if (!data) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">股票详情</h2><div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">{code} 暂无数据</div></section></AppShell>;

  const f = data.factors;
  return (
    <AppShell><section className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex items-baseline gap-3"><h2 className="text-xl font-semibold">{data.name}</h2><span className="text-sm text-[var(--muted)]">{data.code} · {data.board}</span>{data.isSt === 1 && <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">ST</span>}</div>
      <div className="mt-6"><PriceChart code={code} /></div>
      {f && <div className="mt-6 grid gap-4 md:grid-cols-5">
        {[{ label: "趋势", v: f.trendScore }, { label: "动量", v: f.momentumScore }, { label: "流动性", v: f.liquidityScore }, { label: "风险", v: f.riskScore }, { label: "总分", v: f.totalScore }].map((s) => (<div key={s.label} className="rounded-lg border border-[var(--line)] bg-white p-4"><p className="text-sm text-[var(--muted)]">{s.label}</p><p className="mt-2 text-2xl font-semibold">{s.v}</p></div>))}
      </div>}
      {data.recentRecommendations.length > 0 && <div className="mt-6"><h3 className="text-base font-semibold">推荐历史</h3><div className="mt-3 space-y-3">{data.recentRecommendations.map((r, i) => (<div key={i} className="rounded-lg border border-[var(--line)] bg-white p-4"><div className="flex items-center gap-2"><span className="text-sm font-medium">{r.tradeDate}</span><span className="rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">{r.rating}</span><span className="text-sm text-[var(--muted)]">评分 {r.totalScore}</span></div><p className="mt-2 text-sm">{r.reason}</p>{r.riskTags && <p className="mt-1 text-sm text-orange-600">风险：{r.riskTags}</p>}</div>))}</div></div>}
      {data.aiReport && <div className="mt-6"><h3 className="text-base font-semibold">AI 分析</h3><div className="mt-3 rounded-lg border border-[var(--line)] bg-white p-4"><p className="text-sm text-[var(--muted)]">模型：{data.aiReport.modelName} · {data.aiReport.tradeDate}</p><p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{data.aiReport.content}</p></div></div>}
      {!data.aiReport && <div className="mt-6"><h3 className="text-base font-semibold">AI 分析</h3><div className="mt-3 rounded-lg border border-[var(--line)] bg-white p-4 text-sm text-[var(--muted)]">未生成 AI 报告 — 请确认已配置 API Key 并在设置中开启 AI。</div></div>}
    </section></AppShell>
  );
}
