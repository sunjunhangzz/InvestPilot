import { AppShell } from "@/components/AppShell";

export default function RecommendationsPage() {
  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-6 py-8">
        <h2 className="text-xl font-semibold">今日推荐</h2>
        <div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">
          暂无推荐数据
        </div>
      </section>
    </AppShell>
  );
}
