"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";

type Task = {
  taskId: string; taskName: string; status: string;
  startedAt: string | null; finishedAt: string | null;
  errorMessage: string | null; createdAt: string;
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [load, setLoad] = useState(true);

  useEffect(() => {
    let c = false;
    async function f() {
      try {
        const r = await fetch("/api/tasks"); const j = await r.json();
        if (!c && j.ok) setTasks(j.data);
      } catch { /* ignore */ }
      if (!c) setLoad(false);
    }
    f(); return () => { c = true; };
  }, []);

  const toggle = (id: string) => {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id); else next.add(id);
    setExpanded(next);
  };

  const filtered = filter === "all" ? tasks : tasks.filter((t) => t.status === filter);

  const statusBadge = (s: string) => {
    const m: Record<string, { t: string; c: string }> = {
      success: { t: "成功", c: "bg-green-100 text-green-800" },
      failed: { t: "失败", c: "bg-red-100 text-red-800" },
      running: { t: "运行中", c: "bg-yellow-100 text-yellow-800" },
      pending: { t: "等待中", c: "bg-gray-100 text-gray-600" },
      cancelled: { t: "已取消", c: "bg-gray-100 text-gray-600" },
    };
    const v = m[s] ?? { t: s, c: "bg-gray-100" };
    return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${v.c}`}>{v.t}</span>;
  };

  const filterClass = (f: string) =>
    `px-3 py-1 text-xs rounded ${filter === f ? "bg-[var(--accent)] text-white" : "bg-gray-100 text-[var(--muted)]"}`;

  if (load) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">任务日志</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;

  return (
    <AppShell><section className="mx-auto max-w-7xl px-6 py-8">
      <h2 className="text-xl font-semibold">任务日志</h2>
      <div className="mt-4 flex gap-1">
        <button className={filterClass("all")} onClick={() => setFilter("all")}>全部</button>
        <button className={filterClass("success")} onClick={() => setFilter("success")}>成功</button>
        <button className={filterClass("failed")} onClick={() => setFilter("failed")}>失败</button>
        <button className={filterClass("running")} onClick={() => setFilter("running")}>运行中</button>
      </div>
      {filtered.length === 0 ? (
        <div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">暂无任务记录</div>
      ) : (
        <div className="mt-4 space-y-2">
          {filtered.map((t) => (
            <div key={t.taskId} className="rounded-lg border border-[var(--line)] bg-white p-3">
              <div className="flex items-center justify-between cursor-pointer" onClick={() => t.errorMessage && toggle(t.taskId)}>
                <div className="flex items-center gap-3">
                  {statusBadge(t.status)}
                  <span className="text-sm font-medium">{t.taskName}</span>
                  <span className="text-xs text-[var(--muted)]">{t.startedAt?.slice(0, 19)?.replace("T", " ") ?? t.createdAt?.slice(0, 19)?.replace("T", " ")}</span>
                  {t.status === "failed" && <span className="text-xs text-red-500 cursor-pointer">{expanded.has(t.taskId) ? "收起 ▲" : "详情 ▼"}</span>}
                </div>
              </div>
              {expanded.has(t.taskId) && t.errorMessage && (
                <div className="mt-2 border-t border-[var(--line)] pt-2 text-sm text-red-600">{t.errorMessage}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </section></AppShell>
  );
}
