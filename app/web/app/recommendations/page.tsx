"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";

type Rec = {
  code: string; name: string; rating: string; rank: number; totalScore: number;
  trendScore: number; momentumScore: number; liquidityScore: number; riskScore: number;
  close: number | null; agentRating: number | null; agentConsensus: string | null;
  reason: string; riskTags: string; tradeDate: string;
};

export default function RecommendationsPage() {
  const [data, setData] = useState<Rec[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [debateContent, setDebateContent] = useState<string | null>(null);
  const [debateCode, setDebateCode] = useState("");

  useEffect(() => {
    let c = false;
    async function load() {
      try {
        const r = await fetch("/api/recommendations"); const j = await r.json();
        if (!j.ok) throw new Error(j.error?.message ?? "unknown");
        if (!c) { setData(j.data); setError(null); }
      } catch (err) { if (!c) { setError((err as Error).message); setData(null); } }
      if (!c) setLoading(false);
    }
    load();
    return () => { c = true; };
  }, []);

  const showDebate = async (code: string, tradeDate: string) => {
    setDebateCode(code);
    setDebateContent("加载中…");
    try {
      const r = await fetch(`/api/debates?code=${code}&tradeDate=${tradeDate}`);
      const j = await r.json();
      setDebateContent(j.ok ? j.data.content : "暂无辩论报告");
    } catch { setDebateContent("加载失败"); }
  };

  const badge = (r: string) => {
    const m: Record<string, string> = { A: "bg-green-100 text-green-800", B: "bg-blue-100 text-blue-800" };
    return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${m[r] ?? "bg-gray-100 text-gray-600"}`}>{r}</span>;
  };

  if (loading) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">今日推荐</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;
  if (error) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">今日推荐</h2><div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">加载失败：{error}<button className="ml-4 underline" onClick={() => window.location.reload()} type="button">重试</button></div></section></AppShell>;

  const recs = data ?? [];
  if (recs.length === 0) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">今日推荐</h2><div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">暂无推荐数据 — 请先运行「更新数据」再「运行筛选」。</div></section></AppShell>;

  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">今日推荐</h2><p className="mt-2 text-sm text-[var(--muted)]">共 {recs.length} 只 · 交易日 {recs[0]?.tradeDate ?? "—"}</p>
        <div className="mt-4 overflow-x-auto rounded-lg border border-[var(--line)] bg-white"><table className="w-full text-sm"><thead><tr className="border-b border-[var(--line)] bg-[var(--panel)] text-left text-[var(--muted)]"><th className="px-3 py-3 font-medium" title="规则评级：A=前10只重点观察，B=第11-50只普通观察">评级 ⓘ</th><th className="px-3 py-3 font-medium" title="A股6位代码。60开头=上海主板，00/30开头=深圳">代码 ⓘ</th><th className="px-3 py-3 font-medium">名称</th><th className="px-3 py-3 font-medium" title="最近交易日的收盘价（元）">收盘价 ⓘ</th><th className="px-3 py-3 font-medium" title="趋势评分(0-100)：基于MA20/MA60均线排列。>80强劲，<50弱势">趋势 ⓘ</th><th className="px-3 py-3 font-medium" title="动量评分(0-100)：基于20/60日收益率。>80多头充沛">动量 ⓘ</th><th className="px-3 py-3 font-medium" title="流动性评分(0-100)：基于20日均成交额。>80活跃">流动 ⓘ</th><th className="px-3 py-3 font-medium" title="风险评分(0-100)：基于波动率+回撤。越高风险越低">风险 ⓘ</th><th className="px-3 py-3 font-medium" title="Agent委员会投票结果(1-5)。5=强烈推荐，3=中性，1=回避">AI评级 ⓘ</th><th className="px-3 py-3 font-medium" title="4因子加权总分+基本面加分。范围0-100+">总分 ⓘ</th><th className="px-3 py-3 font-medium" title="点击查看5个Agent四轮辩论的完整报告">辩论 ⓘ</th></tr></thead><tbody>
          {recs.map((r) => (<tr key={r.code} className="border-b border-[var(--line)] hover:bg-[var(--panel)]"><td className="px-3 py-3">{badge(r.rating)}</td><td className="px-3 py-3"><Link className="font-medium text-[var(--accent)] hover:underline" href={`/stocks/${r.code}`}>{r.code}</Link></td><td className="px-3 py-3">{r.name}</td><td className="px-3 py-3">{r.close?.toFixed(2) ?? "—"}</td><td className="px-3 py-3">{r.trendScore?.toFixed(0) ?? "—"}</td><td className="px-3 py-3">{r.momentumScore?.toFixed(0) ?? "—"}</td><td className="px-3 py-3">{r.liquidityScore?.toFixed(0) ?? "—"}</td><td className="px-3 py-3">{r.riskScore?.toFixed(0) ?? "—"}</td><td className="px-3 py-3">{r.agentRating != null ? (r.agentRating >= 4 ? "🟢" : r.agentRating >= 3 ? "🟡" : "🔴") + r.agentRating : "—"}</td><td className="px-3 py-3 font-semibold">{r.totalScore}</td><td className="px-3 py-3">{r.agentRating != null ? <button className="text-xs text-[var(--accent)] hover:underline" onClick={() => showDebate(r.code, r.tradeDate)}>📄</button> : "—"}</td></tr>))}
        </tbody></table></div>
      </section>

      {/* Debate modal */}
      {debateContent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDebateContent(null)}>
          <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4"><h3 className="text-lg font-semibold">辩论报告 — {debateCode}</h3><button className="text-sm text-[var(--muted)]" onClick={() => setDebateContent(null)}>✕</button></div>
            <pre className="whitespace-pre-wrap text-sm leading-relaxed">{debateContent}</pre>
          </div>
        </div>
      )}
    </AppShell>
  );
}
