import fs from "node:fs";
import path from "node:path";
import { PROJECT_ROOT } from "@shared/paths";
import { AppShell } from "@/components/AppShell";

export default async function DataDictPage() {
  const filePath = path.join(PROJECT_ROOT, "docs", "data-dictionary.md");
  const content = fs.readFileSync(filePath, "utf-8");

  return (
    <AppShell>
      <section className="mx-auto max-w-4xl px-6 py-8">
        <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans">{content}</pre>
      </section>
    </AppShell>
  );
}
