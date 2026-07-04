"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/MetricCard";
import type { DashboardMetric } from "@/types/dashboard";

type DashboardData = {
  latestRun: { runId: string; tradeDate: string; status: string } | null;
  recommendations: { total: number; byRating: Record<string, number> };
  watchlist: { total: number; active: number; downgraded: number; exited: number };
  latestTask: { taskId: string; taskName: string; status: string; errorMessage: string | null } | null;
};

type PageState = { loading: true } | { loading: false; data: DashboardData | null; error: string | null };

export default function DashboardPage() {
  const [state, setState] = useState<PageState>({ loading: true });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch("/api/dashboard");
        const json = await res.json();
        if (!json.ok) throw new Error(json.error?.message ?? "unknown");
        if (!cancelled) setState({ loading: false, data: json.data, error: null });
      } catch (err) {
        if (!cancelled) setState({ loading: false, data: null, error: (err as Error).message });
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const triggerPipeline = async (pipeline: string) => {
    try {
      const res = await fetch("/api/tasks/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pipeline }),
      });
      const json = await res.json();
      if (!json.ok) { alert(json.error?.message ?? "启动失败"); return; }
      const taskId = json.data.taskId;
      let attempts = 0;
      const maxAttempts = 3600; // ~2 hours at 2s intervals
      const poll = setInterval(async () => {
        attempts++;
        if (attempts > maxAttempts) { clearInterval(poll); return; }
        try {
          const r = await fetch(`/api/tasks/${taskId}`);
          const j = await r.json();
          if (j.ok && j.data.status !== "pending" && j.data.status !== "running") {
            clearInterval(poll);
            window.location.reload();
          }
        } catch { /* network error — keep polling */ }
      }, 2000);
    } catch { alert("网络错误"); }
  };

  const reload = () => { setState({ loading: true }); window.location.reload(); };

  if (state.loading) {
    return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">首页仪表盘</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;
  }

  if (state.error || !state.data) {
    return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">首页仪表盘</h2><div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">{state.error ?? "暂无数据"}<button className="ml-4 underline" onClick={reload} type="button">重试</button></div></section></AppShell>;
  }

  const { data } = state;
  const items: DashboardMetric[] = [
    { label: "今日候选", value: String(data.recommendations.total), note: data.latestRun ? `A: ${data.recommendations.byRating.A ?? 0}  B: ${data.recommendations.byRating.B ?? 0}` : "暂无推荐" },
    { label: "观察池", value: String(data.watchlist.total), note: `active: ${data.watchlist.active}  downgraded: ${data.watchlist.downgraded}  exited: ${data.watchlist.exited}` },
    { label: "最近任务", value: data.latestTask?.status ?? "未运行", note: data.latestTask ? `${data.latestTask.taskName}${data.latestTask.errorMessage ? ` — ${data.latestTask.errorMessage}` : ""}` : "手动触发后显示状态" },
    { label: "最新交易日", value: data.latestRun?.tradeDate ?? "—", note: data.latestRun ? `run: ${data.latestRun.runId}` : "等待首次筛选" },
  ];

  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div><h2 className="text-xl font-semibold">首页仪表盘</h2><p className="mt-2 text-sm text-[var(--muted)]">数据、筛选、观察池和报告任务汇总展示。</p></div>
          <div className="flex gap-2">
            <button className="h-10 rounded-md bg-[var(--accent)] px-4 text-sm font-medium text-white" onClick={() => triggerPipeline("update-data")} type="button">更新数据</button>
            <button className="h-10 rounded-md border border-[var(--accent)] px-4 text-sm font-medium text-[var(--accent)]" onClick={() => triggerPipeline("run-screening")} type="button">运行筛选</button>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{items.map((item) => (<MetricCard key={item.label} metric={item} />))}</div>
        <div className="mt-6 rounded-lg border border-[var(--line)] bg-white">
          <div className="border-b border-[var(--line)] px-5 py-4"><h3 className="text-base font-semibold">任务链路</h3></div>
          <div className="grid gap-0 md:grid-cols-4">
            {[{ name: "数据获取", done: data.recommendations.total > 0 }, { name: "因子评分", done: data.recommendations.total > 0 }, { name: "推荐生成", done: data.recommendations.total > 0 }, { name: "报告输出", done: false }].map((step) => (
              <div className="border-b border-[var(--line)] p-5 last:border-b-0 md:border-r md:border-b-0 last:md:border-r-0" key={step.name}><p className="text-sm font-medium">{step.name}</p><p className="mt-2 text-sm text-[var(--muted)]">{step.done ? "已完成" : "未运行"}</p></div>
            ))}
          </div>
        </div>
      </section>
    </AppShell>
  );
}
