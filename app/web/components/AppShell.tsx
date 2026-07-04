import Link from "next/link";
import { navigationItems } from "@/lib/navigation";

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <main className="min-h-screen">
      <header className="border-b border-[var(--line)] bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-sm text-[var(--muted)]">A股AI投研系统</p>
            <h1 className="text-2xl font-semibold">InvestPilot</h1>
          </div>
          <nav className="hidden gap-2 md:flex">
            {navigationItems.map((item) => (
              <Link
                className="rounded-md px-3 py-2 text-sm text-[var(--muted)] hover:bg-[#eef3f2] hover:text-[var(--accent-strong)]"
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      {children}
    </main>
  );
}
