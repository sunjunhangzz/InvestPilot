import { AppShell } from "@/components/AppShell";

type StockPageProps = {
  params: Promise<{
    code: string;
  }>;
};

export default async function StockPage({ params }: StockPageProps) {
  const { code } = await params;

  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-6 py-8">
        <h2 className="text-xl font-semibold">股票详情</h2>
        <div className="mt-6 rounded-lg border border-[var(--line)] bg-white p-6 text-sm text-[var(--muted)]">
          {code} 暂无详情数据
        </div>
      </section>
    </AppShell>
  );
}
