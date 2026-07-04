import fs from "node:fs";
import path from "node:path";
import { getConfigPaths } from "@shared/paths";

type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR";

type ApiLogInput = {
  level: LogLevel;
  module: string;
  message: string;
  taskId?: string;
  runId?: string;
  tradeDate?: string;
  context?: Record<string, unknown>;
};

const sensitiveKeys = new Set([
  "api_key",
  "apikey",
  "authorization",
  "cookie",
  "deepseek_api_key",
  "openai_api_key",
  "password",
  "secret",
  "token",
]);

function maskSensitive(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => maskSensitive(item));
  }

  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => [
        key,
        sensitiveKeys.has(key.toLowerCase()) ? "***" : maskSensitive(nestedValue),
      ]),
    );
  }

  return value;
}

function getShanghaiIsoTime(): string {
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());

  return `${parts.replace(" ", "T")}+08:00`;
}

export function writeApiLog(input: ApiLogInput): void {
  const logPaths = getConfigPaths();
  fs.mkdirSync(logPaths.logsPath, { recursive: true });

  const record: Record<string, unknown> = {
    time: getShanghaiIsoTime(),
    level: input.level,
    module: input.module,
    message: input.message,
  };

  if (input.taskId) {
    record.task_id = input.taskId;
  }
  if (input.runId) {
    record.run_id = input.runId;
  }
  if (input.tradeDate) {
    record.trade_date = input.tradeDate;
  }
  if (input.context) {
    // API logs can be copied into issues, so secrets are masked before writing.
    record.context = maskSensitive(input.context);
  }

  fs.appendFileSync(
    path.join(logPaths.logsPath, "api.log"),
    `${JSON.stringify(record)}\n`,
    "utf8",
  );
}
