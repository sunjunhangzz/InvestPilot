import { AppShell } from "@/components/AppShell";
import { MetricCard } from "@/components/MetricCard";
import type { DashboardMetric, TaskStep } from "@/types/dashboard";

const summaryItems: DashboardMetric[] = [
  { label: "今日候选", value: "0", note: "等待首次筛选" },
  { label: "观察池", value: "0", note: "至少跟踪 5 个交易日" },
  { label: "最近任务", value: "未运行", note: "手动触发后显示状态" },
  { label: "AI 分析", value: "关闭", note: "规则筛选可独立运行" },
];

const taskSteps: TaskStep[] = [
  { name: "数据获取", status: "未运行" },
  { name: "因子评分", status: "未运行" },
  { name: "推荐生成", status: "未运行" },
  { name: "报告输出", status: "未运行" },
];

export default function DashboardPage() {
  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-xl font-semibold">首页仪表盘</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
              数据、筛选、观察池和报告任务将在这里汇总展示。
            </p>
          </div>
          <button
            className="h-10 rounded-md bg-[var(--accent)] px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-[#9aa8a5]"
            disabled
            type="button"
          >
            手动更新数据
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {summaryItems.map((item) => (
            <MetricCard key={item.label} metric={item} />
          ))}
        </div>

        <div className="mt-6 rounded-lg border border-[var(--line)] bg-white">
          <div className="border-b border-[var(--line)] px-5 py-4">
            <h3 className="text-base font-semibold">任务链路</h3>
          </div>
          <div className="grid gap-0 md:grid-cols-4">
            {taskSteps.map((step) => (
              <div
                className="border-b border-[var(--line)] p-5 last:border-b-0 md:border-r md:border-b-0 last:md:border-r-0"
                key={step.name}
              >
                <p className="text-sm font-medium">{step.name}</p>
                <p className="mt-2 text-sm text-[var(--muted)]">{step.status}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </AppShell>
  );
}
