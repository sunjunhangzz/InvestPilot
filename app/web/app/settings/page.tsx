"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [load, setLoad] = useState(true);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    let c = false;
    async function f() {
      try { const r = await fetch("/api/settings"); const j = await r.json(); if (j.ok && !c) setSettings(j.data); } catch { /* ignore */ }
      if (!c) setLoad(false);
    }
    f(); return () => { c = true; };
  }, []);

  const save = async () => {
    setMsg("");
    try {
      const r = await fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings) });
      const j = await r.json();
      setMsg(j.ok ? "保存成功" : `失败: ${j.error?.message}`);
    } catch { setMsg("网络错误"); }
  };

  if (load) return <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">系统设置</h2><p className="mt-6 text-sm text-[var(--muted)]">加载中…</p></section></AppShell>;

  return (
    <AppShell><section className="mx-auto max-w-7xl px-6 py-8"><h2 className="text-xl font-semibold">系统设置</h2><p className="mt-2 text-sm text-[var(--muted)]">设置保存在本地数据库中。因子权重等参数当前通过 config.json 管理。</p>
      <div className="mt-6 space-y-4 max-w-lg">
        {Object.entries(settings).map(([k, v]) => (<div key={k}><label className="block text-sm font-medium">{k}</label><input className="mt-1 w-full rounded-md border border-[var(--line)] px-3 py-2 text-sm" value={v} onChange={(e) => setSettings({ ...settings, [k]: e.target.value })} /></div>))}
        {Object.keys(settings).length === 0 && <p className="text-sm text-[var(--muted)]">暂无可编辑配置</p>}
        <button className="h-10 rounded-md bg-[var(--accent)] px-4 text-sm font-medium text-white" onClick={save} type="button">保存</button>
        {msg && <p className="text-sm text-[var(--muted)]">{msg}</p>}
      </div>
    </section></AppShell>
  );
}
