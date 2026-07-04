/**
 * Worker script launcher for Next.js API Routes.
 *
 * Spawns Python worker scripts as child processes.  Only scripts on the
 * allowlist may be launched — arbitrary commands from the frontend are
 * rejected.  Task locking is handled by task-lock.ts.
 */

import { spawn } from "node:child_process";
import { PROJECT_ROOT } from "@shared/paths";

const SCRIPT_MAP: Record<string, string> = {
  update_stocks: "app/worker/scripts/update_stocks.py",
  update_prices: "app/worker/scripts/update_prices.py",
  calc_factors: "app/worker/scripts/calc_factors.py",
  run_screening: "app/worker/scripts/run_screening.py",
  update_watchlist: "app/worker/scripts/update_watchlist.py",
};

export type WorkerResult = {
  exitCode: number | null;
  stdout: string;
  stderr: string;
};

export function runWorker(scriptKey: string): Promise<WorkerResult> {
  const relativePath = SCRIPT_MAP[scriptKey];
  if (!relativePath) {
    return Promise.reject(new Error(`unknown worker script: ${scriptKey}`));
  }

  const scriptPath = `${PROJECT_ROOT}/${relativePath}`;
  const venvPython = `${PROJECT_ROOT}/app/worker/.venv/bin/python3`;

  return new Promise((resolve, reject) => {
    const proc = spawn(venvPython, [scriptPath], {
      cwd: PROJECT_ROOT,
      env: { ...process.env },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    proc.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    proc.on("error", (err) => reject(err));
    proc.on("close", (code) => resolve({ exitCode: code, stdout, stderr }));
  });
}

export async function runWorkers(
  scriptKeys: string[],
): Promise<{ success: boolean; results: WorkerResult[] }> {
  const results: WorkerResult[] = [];
  for (const key of scriptKeys) {
    const result = await runWorker(key);
    results.push(result);
    if (result.exitCode !== 0) {
      return { success: false, results };
    }
  }
  return { success: true, results };
}
