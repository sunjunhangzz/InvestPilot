import { NextResponse } from "next/server";
import { writeApiLog } from "@/lib/server/logger";

export async function POST() {
  writeApiLog({
    level: "INFO",
    module: "health_log",
    message: "api log health check",
    taskId: "health_check_task",
    runId: "health_check_run",
  });

  return NextResponse.json({ ok: true });
}
