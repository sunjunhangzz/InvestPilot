/**
 * GET /api/settings
 * POST /api/settings
 *
 * Read and update first-version settings from the settings table.
 */
import { NextRequest } from "next/server";
import Database from "better-sqlite3";
import { ok, fail } from "@/lib/server/api-response";
import { queryAll } from "@/lib/server/db";
import { getConfigPaths } from "@shared/paths";

export async function GET() {
  const rows = queryAll("SELECT key, value, updated_at FROM settings ORDER BY key");
  const result: Record<string, string> = {};
  for (const r of rows as { key: string; value: string }[]) {
    result[r.key] = r.value;
  }
  return ok(result);
}

export async function POST(request: NextRequest) {
  let body: Record<string, string>;
  try {
    body = await request.json();
  } catch {
    return fail("INVALID_JSON", "request body must be JSON");
  }

  const dbPath = getConfigPaths().databasePath;
  const db = new Database(dbPath);
  try {
    const upsert = db.prepare(
      `INSERT INTO settings (key, value, updated_at)
       VALUES (?, ?, datetime('now', 'localtime'))
       ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at`,
    );
    db.transaction(() => {
      for (const [key, value] of Object.entries(body)) {
        upsert.run(key, String(value));
      }
    })();
    return ok({ saved: Object.keys(body).length });
  } finally {
    db.close();
  }
}
