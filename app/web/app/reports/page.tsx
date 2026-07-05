"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";

type Report = {
  code: string; name: string; rating: string; totalScore: number;
  reason: string; riskTags: string; tradeDate: string;
  aiContent: string | null; modelName: string | null; aiStatus: string | null;
};


export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  // run selector reserved for future use
  const [selectedRun, setSelectedRun] = useState("");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [load, setLoad] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let c = false;
    async function f() {
      try {
        const r = await fetch("/api/runs/latest"); const j = await r.json();
        if (j.ok && j.data.runId) {
          if (!c) setSelectedRun(j.data.runId);
        }
      } catch { /* ignore */ }
    }
    f(); return () => { c = true; };
  }, []);

  useEffect(() => {
    let c = false;
    async function f() {
      try {
        const r = await fetch("/api/reports?runId=" + selectedRun); const j = await r.json();
        if (!c) { if (j.ok) setReports(j.data); setErr(null); }
      } catch (e) { if (!c) setErr((e as Error).message); }
      if (!c) setLoad(false);
    }
    if (selectedRun) f();
    return () => { c = true; };
  }, [selectedRun]);

  useEffect(() => {
    let c = false;
    async function f() {
      try {
        const r = await fetch("/api/runs/latest"); const j = await r.json();
        if (!c && j.ok) {
          // Build run list from available data — just use the current one for now.
          // Full run list would need a separate /api/runs endpoint.
        }
      } catch { /* ignore */ }
    }
    f(); return () => { c = true; };
  }, []);

  const toggle = (code: string) => {
    const next = new Set(expanded);
    if (next.has(code)) next.delete(code); else next.add(code);
    setExpanded(next);
  };

  const filtered = reports.filter((r) =>
    !search || r.code.includes(search) || r.name.includes(search)
  );

  if (load) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">报告中心</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;
  if (err) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">报告中心</h2><div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">{err}<button className="ml-4 underline" onClick={() => window.location.reload()} type="button">重试</button></div></section></AppShell>;

  return (
    <AppShell><section className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex items-center justify-between"><h2 className="text-xl font-semibold">报告中心</h2></div>
      <div className="mt-4 flex items-center gap-3">
        <input className="rounded-md border border-[var(--line)] px-3 py-2 text-sm w-64" placeholder="搜索股票代码/名称…" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>
      {filtered.length === 0 ? (
        <div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">{reports.length === 0 ? "暂无推荐报告 — 请先运行筛选。" : "无匹配结果"}</div>
      ) : (
        <div className="mt-4 space-y-3">
          {filtered.map((r) => (
            <div key={r.code} className="rounded-lg border border-[var(--line)] bg-white p-4">
              <div className="flex items-center justify-between cursor-pointer" onClick={() => toggle(r.code)}>
                <div className="flex items-center gap-3">
                  <Link className="font-medium text-[var(--accent)] hover:underline" href={`/stocks/${r.code}`}>{r.code}</Link>
                  <span className="text-sm">{r.name}</span>
                  <span className={`rounded px-2 py-0.5 text-xs font-semibold ${r.rating === "A" ? "bg-green-100 text-green-800" : "bg-blue-100 text-blue-800"}`}>{r.rating}</span>
                  <span className="text-sm text-[var(--muted)]">评分 {r.totalScore}</span>
                  {!r.aiContent && <span className="text-xs text-orange-500">未生成 AI 报告</span>}
                </div>
                <span className="text-xs text-[var(--muted)]">{expanded.has(r.code) ? "收起 ▲" : "展开 ▼"}</span>
              </div>
              {expanded.has(r.code) && r.aiContent && (
                <div className="mt-3 border-t border-[var(--line)] pt-3">
                  <p className="text-xs text-[var(--muted)]">模型：{r.modelName} · {r.tradeDate}</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{r.aiContent}</p>
                </div>
              )}
              {expanded.has(r.code) && !r.aiContent && (
                <div className="mt-3 border-t border-[var(--line)] pt-3 text-sm text-[var(--muted)]">该股票未生成 AI 报告 — 请确认 AI 开关已开启且 API Key 有效。</div>
              )}
            </div>
          ))}
        </div>
      )}
    </section></AppShell>
  );
}
