import type { DashboardMetric } from "@/types/dashboard";

export function MetricCard({ metric }: Readonly<{ metric: DashboardMetric }>) {
  return (
    <article className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4">
      <p className="text-sm text-[var(--muted)]">{metric.label}</p>
      <p className="mt-3 text-2xl font-semibold">{metric.value}</p>
      <p className="mt-2 text-sm text-[var(--muted)]">{metric.note}</p>
    </article>
  );
}
