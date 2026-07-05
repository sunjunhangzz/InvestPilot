"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";

export default function SettingsPage() {
  const [recLimit, setRecLimit] = useState(50);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [load, setLoad] = useState(true);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    let c = false;
    async function f() {
      try {
        const r = await fetch("/api/settings"); const j = await r.json();
        if (j.ok && !c) {
          if (j.data["recommendationLimit"]) setRecLimit(Number(j.data["recommendationLimit"]));
          if (j.data["ai.enabled"] !== undefined) setAiEnabled(j.data["ai.enabled"] === "true" || j.data["ai.enabled"] === true);
        }
      } catch { /* ignore */ }
      if (!c) setLoad(false);
    }
    f(); return () => { c = true; };
  }, []);

  const save = async () => {
    setMsg("");
    try {
      const r = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          "recommendationLimit": String(recLimit),
          "ai.enabled": String(aiEnabled),
        }),
      });
      const j = await r.json();
      setMsg(j.ok ? "保存成功 — 下次运行筛选时生效" : `失败: ${j.error?.message}`);
    } catch { setMsg("网络错误"); }
  };

  if (load) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">系统设置</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;

  return (
    <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">系统设置</h2><p className="mt-2 text-sm text-[var(--muted)]">以下参数保存后，下次运行筛选时生效。</p>
      <div className="mt-6 space-y-6 max-w-lg">
        <div>
          <label className="block text-sm font-medium">推荐数量 (10-50)</label>
          <input className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2 text-sm" type="number" min={10} max={50} value={recLimit} onChange={(e) => setRecLimit(Number(e.target.value))} />
          <p className="mt-1 text-xs text-[var(--muted)]">控制最终推荐列表输出的股票数量。</p>
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm font-medium">
            <input type="checkbox" checked={aiEnabled} onChange={(e) => setAiEnabled(e.target.checked)} className="h-4 w-4" />
            启用 AI 报告
          </label>
          <p className="mt-1 text-xs text-[var(--muted)]">开启后，运行筛选时自动生成 AI 分析报告（需配置 API Key）。关闭时只做规则筛选。</p>
        </div>
        <button className="h-10 rounded-md bg-[var(--accent)] px-4 text-sm font-medium text-white" onClick={save} type="button">保存</button>
        {msg && <p className="text-sm text-[var(--muted)]">{msg}</p>}
      </div>
    </section></AppShell>
  );
}
