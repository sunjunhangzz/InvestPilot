"use client";

import { useEffect, useState, use } from "react";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/AppShell";

const PriceChart = dynamic(() => import("@/components/PriceChart"), { ssr: false });

type StockDetail = {
  code: string; name: string; board: string; isSt: number;
  factors: { trendScore: number; momentumScore: number; liquidityScore: number; riskScore: number; totalScore: number; tradeDate: string } | null;
  recentRecommendations: { tradeDate: string; createdAt: string; rating: string; totalScore: number; reason: string; riskTags: string }[];
  aiReport: { content: string; modelName: string; tradeDate: string } | null;
  fundamental: { pe: number; pb: number; roe: number; revenue: number; revenueYoy: number; netProfit: number; netProfitYoy: number; eps: number; debtRatio: number; industry: string; reportDate: string } | null;
  agentReport: { rating: number; consensus: string; summary: string; modelName: string; tradeDate: string } | null;
};

type Props = { params: Promise<{ code: string }> };

export default function StockPage({ params }: Props) {
  const { code } = use(params);
  const [data, setData] = useState<StockDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [load, setLoad] = useState(true);
  const [debateContent, setDebateContent] = useState<string | null>(null);

  useEffect(() => {
    let c = false;
    async function f() {
      try { const r = await fetch(`/api/stocks/${code}`); const j = await r.json(); if (!j.ok) throw new Error(j.error?.message ?? ""); if (!c) { setData(j.data); setErr(null); } } catch (e) { if (!c) { setErr((e as Error).message); setData(null); } }
      if (!c) setLoad(false);
    }
    f(); return () => { c = true; };
  }, [code]);

  const showDebate = async (c: string) => {
    setDebateContent("加载中…");
    try {
      const r = await fetch("/api/debates?code=" + c);
      const j = await r.json();
      if (j.ok && j.data.length > 0) {
        const latest = j.data[0];
        const rr = await fetch("/api/debates?code=" + c + "&tradeDate=" + latest);
        const jj = await rr.json();
        setDebateContent(jj.ok ? jj.data.content : "无报告");
      } else { setDebateContent("暂无辩论报告"); }
    } catch { setDebateContent("加载失败"); }
  };

  if (load) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">股票详情</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;
  if (err) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">股票详情</h2><div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">{err}<button className="ml-4 underline" onClick={() => window.location.reload()} type="button">重试</button></div></section></AppShell>;
  if (!data) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">股票详情</h2><div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">{code} 暂无数据</div></section></AppShell>;

  const f = data.factors;
  return (
    <AppShell><section className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex items-baseline gap-3"><h2 className="text-xl font-semibold">{data.name}</h2><span className="text-sm text-[var(--muted)]">{data.code} · {data.board}</span>{data.isSt === 1 && <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">ST</span>}</div>
      <div className="mt-6"><PriceChart code={code} /></div>
      {f && <div className="mt-6 grid gap-4 md:grid-cols-5">
        {[{ label: "趋势", v: f.trendScore, tip: "基于MA20/MA60均线排列。>80强劲多头，<50弱势" }, { label: "动量", v: f.momentumScore, tip: "基于20/60日收益率。>80动量充沛" }, { label: "流动性", v: f.liquidityScore, tip: "基于20日均成交额。>80交易活跃" }, { label: "风险", v: f.riskScore, tip: "基于波动率+回撤。越高=风险越低" }, { label: "总分", v: f.totalScore, tip: "趋势35%+动量25%+流动20%+风险20%+基本面20%" }].map((s) => (<div key={s.label} className="rounded-lg border border-[var(--line)] bg-white p-4"><p className="text-sm text-[var(--muted)]">{s.label}</p><p className="mt-2 text-2xl font-semibold">{s.v}</p></div>))}
      </div>}
      {data.recentRecommendations.length > 0 && <div className="mt-6"><h3 className="text-base font-semibold">推荐历史</h3><div className="mt-3 space-y-3">{data.recentRecommendations.map((r, i) => (<div key={i} className="rounded-lg border border-[var(--line)] bg-white p-4"><div className="flex items-center gap-2"><span className="text-sm font-medium">{r.tradeDate}</span><span className="text-xs text-[var(--muted)]">{r.createdAt?.slice(0, 19)?.replace("T", " ") ?? ""}</span><span className="rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">{r.rating}</span><span className="text-sm text-[var(--muted)]">评分 {r.totalScore}</span></div><p className="mt-2 text-sm">{r.reason}</p>{r.riskTags && <p className="mt-1 text-sm text-orange-600">风险：{r.riskTags}</p>}</div>))}</div></div>}
      {data.aiReport && <div className="mt-6"><h3 className="text-base font-semibold">AI 分析</h3><div className="mt-3 rounded-lg border border-[var(--line)] bg-white p-4"><p className="text-sm text-[var(--muted)]">模型：{data.aiReport.modelName} · {data.aiReport.tradeDate}</p><p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{data.aiReport.content}</p></div></div>}
      {data.fundamental && <div className="mt-6"><h3 className="text-base font-semibold">基本面</h3><div className="mt-3 grid gap-3 md:grid-cols-3">{[
        { l: "PE", tip: "市盈率=股价÷每股收益。越低越便宜。&lt;20低估，&gt;50高估", v: data.fundamental.pe?.toFixed(1) }, { l: "PB", tip: "市净率=股价÷每股净资产。&lt;1破净", v: data.fundamental.pb?.toFixed(2) }, { l: "ROE", tip: "净资产收益率。&gt;15%优秀，&lt;5%差", v: data.fundamental.roe?.toFixed(1) + "%", sub: data.fundamental.reportDate ? "报告期:" + data.fundamental.reportDate : "" },
        { l: "营收", v: (data.fundamental.revenue/1e8)?.toFixed(1) + "亿" }, { l: "营收增速", tip: "相比去年同期。&gt;20%高增长，&lt;0下滑", v: data.fundamental.revenueYoy?.toFixed(1) + "%" },
        { l: "净利润", v: (data.fundamental.netProfit/1e8)?.toFixed(1) + "亿" }, { l: "利润增速", tip: "相比去年同期。&gt;20%高增长，&lt;-30%暴跌", v: data.fundamental.netProfitYoy?.toFixed(1) + "%" },
        { l: "行业", v: data.fundamental.industry || "—" }, { l: "EPS", v: data.fundamental.eps?.toFixed(2) }
      ].map(s => (<div key={s.l} className="rounded-lg border border-[var(--line)] bg-white p-3"><p className="text-xs text-[var(--muted)]" title={s.tip || ""}>{s.l} ⓘ</p><p className="mt-1 text-sm font-semibold">{s.v ?? "—"}</p></div>))}</div></div>}
      {data.agentReport && <div className="mt-6"><h3 className="text-base font-semibold">🤖 Agent 委员会</h3><div className="mt-3 rounded-lg border border-[var(--line)] bg-white p-4">
        <div className="flex items-center gap-3"><span className="text-2xl font-bold">{data.agentReport.rating}</span><span className="text-sm text-[var(--muted)]">/ 5 分 · {data.agentReport.consensus === "unanimous" ? "全票通过" : data.agentReport.consensus === "majority" ? "多数同意" : data.agentReport.consensus === "split" ? "分歧" : "否决"} · {data.agentReport.modelName}</span></div>
        <p className="mt-2 text-sm">{data.agentReport.summary}</p>
        <button className="mt-2 text-xs text-[var(--accent)] hover:underline" onClick={() => showDebate(code)}>📄 查看完整辩论报告</button>
        <details className="mt-3"><summary className="cursor-pointer text-xs text-[var(--muted)]">📊 评级说明</summary>
          <div className="mt-2 text-xs text-[var(--muted)] space-y-1">
            <p><b>5分</b> — 强烈推荐（多维度一致看好）</p>
            <p><b>4分</b> — 推荐（整体向好，个别指标稍弱）</p>
            <p><b>3分</b> — 中性（好坏参半，无明显优势）</p>
            <p><b>2分</b> — 谨慎（多处风险，不建议重仓）</p>
            <p><b>1分</b> — 回避（多维度一致看空）</p>
          </div>
        </details>
      </div></div>}
      {!data.aiReport && <div className="mt-6"><h3 className="text-base font-semibold">AI 分析</h3><div className="mt-3 rounded-lg border border-[var(--line)] bg-white p-4 text-sm text-[var(--muted)]">未生成 AI 报告 — 请确认已配置 API Key 并在设置中开启 AI。</div></div>}
    </section>
      {debateContent && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDebateContent(null)}><div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl" onClick={e => e.stopPropagation()}><div className="flex items-center justify-between mb-4"><h3 className="text-lg font-semibold">辩论报告 — {code}</h3><button className="text-sm text-[var(--muted)]" onClick={() => setDebateContent(null)}>✕</button></div><pre className="whitespace-pre-wrap text-sm leading-relaxed">{debateContent}</pre></div></div>}
    </AppShell>
  );
}
