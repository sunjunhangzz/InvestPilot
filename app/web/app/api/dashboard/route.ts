/**
 * GET /api/dashboard
 *
 * Returns a summary for the dashboard page:
 * - latest run status
 * - today's recommendation count
 * - watchlist summary
 * - latest task status
 *
 * Also performs a one-time cleanup of stale "running" tasks left behind
 * after a server restart.
 */
import { ok } from "@/lib/server/api-response";
import { queryOne, queryAll } from "@/lib/server/db";
import { cleanupStaleTasks } from "@/lib/server/task-lock";

let cleanedUp = false;

export async function GET() {
  if (!cleanedUp) {
    cleanedUp = true;
    cleanupStaleTasks();
  }

  const latestRun = queryOne(
    `SELECT run_id, trade_date, status, started_at, finished_at
     FROM runs WHERE status = 'success'
     ORDER BY created_at DESC LIMIT 1`,
  );

  let recCount = 0;
  const recAByRating: Record<string, number> = {};
  if (latestRun) {
    const runId = (latestRun as Record<string, unknown>).run_id as string;
    const countRow = queryOne(
      "SELECT COUNT(*) AS cnt FROM recommendations WHERE run_id = ?",
      [runId],
    );
    recCount = (countRow as Record<string, number> | null)?.cnt ?? 0;

    const tierRows = queryAll(
      "SELECT rating, COUNT(*) AS cnt FROM recommendations WHERE run_id = ? GROUP BY rating",
      [runId],
    );
    for (const r of tierRows as Record<string, number>[]) {
      recAByRating[r.rating as string] = r.cnt;
    }
  }

  const wlRow = queryOne(
    `SELECT COUNT(*) AS total,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN status = 'downgraded' THEN 1 ELSE 0 END) AS downgraded,
            SUM(CASE WHEN status = 'exit' THEN 1 ELSE 0 END) AS exited
     FROM watchlist`,
  );
  const wl = (wlRow ?? {}) as Record<string, number>;

  const latestTask = queryOne(
    `SELECT task_id, task_name, status, started_at, finished_at, error_message
     FROM system_tasks ORDER BY created_at DESC LIMIT 1`,
  );

  return ok({
    latestRun: latestRun
      ? {
          runId: (latestRun as Record<string, unknown>).run_id,
          tradeDate: (latestRun as Record<string, unknown>).trade_date,
          status: (latestRun as Record<string, unknown>).status,
        }
      : null,
    recommendations: {
      total: recCount,
      byRating: recAByRating,
    },
    watchlist: {
      total: wl.total ?? 0,
      active: wl.active ?? 0,
      downgraded: wl.downgraded ?? 0,
      exited: wl.exited ?? 0,
    },
    latestTask: latestTask ?? null,
  });
}
