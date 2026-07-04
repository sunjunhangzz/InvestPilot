import { AppShell } from "@/components/AppShell";

export default function WatchlistPage() {
  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-6 py-8">
        <h2 className="text-xl font-semibold">观察池</h2>
        <div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">
          暂无观察股票
        </div>
      </section>
    </AppShell>
  );
}
