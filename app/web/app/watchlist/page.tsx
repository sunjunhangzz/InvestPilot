"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";

type Wl = { code: string; name: string; status: string; entryPrice: number | null; latestPrice: number | null; trackingDays: number; firstRecommendedDate: string; exitReason: string | null };

export default function WatchlistPage() {
  const [data, setData] = useState<Wl[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [load, setLoad] = useState(true);

  useEffect(() => {
    let c = false;
    async function f() {
      try { const r = await fetch("/api/watchlist"); const j = await r.json(); if (!j.ok) throw new Error(j.error?.message ?? ""); if (!c) { setData(j.data); setErr(null); } } catch (e) { if (!c) { setErr((e as Error).message); setData(null); } }
      if (!c) setLoad(false);
    }
    f(); return () => { c = true; };
  }, []);

  const sl = (s: string) => {
    const m: Record<string, { t: string; c: string }> = { active: { t: "观察中", c: "bg-green-100 text-green-800" }, downgraded: { t: "降级", c: "bg-yellow-100 text-yellow-800" }, exit: { t: "退出", c: "bg-gray-100 text-gray-600" }, blocked: { t: "阻断", c: "bg-red-100 text-red-800" } };
    const v = m[s] ?? { t: s, c: "bg-gray-100" };
    return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${v.c}`}>{v.t}</span>;
  };

  if (load) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">观察池</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;
  if (err) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">观察池</h2><div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">{err}<button className="ml-4 underline" onClick={() => window.location.reload()} type="button">重试</button></div></section></AppShell>;

  const items = data ?? [];
  return (
    <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">观察池</h2>
      {items.length === 0 ? <div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">暂无观察股票</div> :
        <div className="mt-4 overflow-x-auto rounded-lg border border-[var(--line)] bg-white"><table className="w-full text-sm"><thead><tr className="border-b border-[var(--line)] bg-[var(--panel)] text-left text-[var(--muted)]"><th className="px-4 py-3 font-medium">状态</th><th className="px-4 py-3 font-medium">代码</th><th className="px-4 py-3 font-medium">名称</th><th className="px-4 py-3 font-medium">入场价</th><th className="px-4 py-3 font-medium">最新价</th><th className="px-4 py-3 font-medium">跟踪天数</th><th className="px-4 py-3 font-medium">首次推荐</th><th className="px-4 py-3 font-medium">退出原因</th></tr></thead><tbody>
          {items.map((w) => (<tr key={w.code} className="border-b border-[var(--line)] hover:bg-[var(--panel)]"><td className="px-4 py-3">{sl(w.status)}</td><td className="px-4 py-3"><Link className="font-medium text-[var(--accent)] hover:underline" href={`/stocks/${w.code}`}>{w.code}</Link></td><td className="px-4 py-3">{w.name}</td><td className="px-4 py-3">{w.entryPrice?.toFixed(2) ?? "—"}</td><td className="px-4 py-3">{w.latestPrice?.toFixed(2) ?? "—"}</td><td className="px-4 py-3">{w.trackingDays}</td><td className="px-4 py-3">{w.firstRecommendedDate}</td><td className="px-4 py-3 text-[var(--muted)]">{w.exitReason || "—"}</td></tr>))}
        </tbody></table></div>}
    </section></AppShell>
  );
}
