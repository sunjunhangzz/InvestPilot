"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";

type Rec = { code: string; name: string; rating: string; rank: number; totalScore: number; reason: string; riskTags: string; tradeDate: string };

export default function RecommendationsPage() {
  const [data, setData] = useState<Rec[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
        <div className="mt-4 overflow-x-auto rounded-lg border border-[var(--line)] bg-white"><table className="w-full text-sm"><thead><tr className="border-b border-[var(--line)] bg-[var(--panel)] text-left text-[var(--muted)]"><th className="px-4 py-3 font-medium">评级</th><th className="px-4 py-3 font-medium">排名</th><th className="px-4 py-3 font-medium">代码</th><th className="px-4 py-3 font-medium">名称</th><th className="px-4 py-3 font-medium">评分</th><th className="px-4 py-3 font-medium">理由</th><th className="px-4 py-3 font-medium">风险</th></tr></thead><tbody>
          {recs.map((r) => (<tr key={r.code} className="border-b border-[var(--line)] hover:bg-[var(--panel)]"><td className="px-4 py-3">{badge(r.rating)}</td><td className="px-4 py-3">{r.rank}</td><td className="px-4 py-3"><Link className="font-medium text-[var(--accent)] hover:underline" href={`/stocks/${r.code}`}>{r.code}</Link></td><td className="px-4 py-3">{r.name}</td><td className="px-4 py-3">{r.totalScore}</td><td className="px-4 py-3 max-w-xs truncate">{r.reason}</td><td className="px-4 py-3 text-[var(--muted)]">{r.riskTags || "—"}</td></tr>))}
        </tbody></table></div>
      </section>
    </AppShell>
  );
}
