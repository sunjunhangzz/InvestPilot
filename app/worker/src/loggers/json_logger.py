"""JSON Lines logger for worker scripts."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from app.shared.paths import get_config_paths


LogLevel = Literal["DEBUG", "INFO", "WARN", "ERROR"]
LogFileName = Literal[
    "worker.log",
    "data_source.log",
    "screening.log",
    "ai.log",
]

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "deepseek_api_key",
    "openai_api_key",
    "password",
    "secret",
    "token",
}


def get_logs_dir() -> Path:
    """Return the shared logs directory and create it if needed."""

    logs_dir = get_config_paths()["logsPath"]
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def mask_sensitive(value: Any) -> Any:
    """Mask sensitive values before writing logs."""

    if isinstance(value, dict):
        return {
            key: "***"
            if key.lower() in SENSITIVE_KEYS
            else mask_sensitive(nested_value)
            for key, nested_value in value.items()
        }

    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]

    return value


def write_json_log(
    *,
    file_name: LogFileName,
    level: LogLevel,
    module: str,
    message: str,
    task_id: str | None = None,
    run_id: str | None = None,
    trade_date: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Append one sanitized JSON log record to a worker log file."""

    record: dict[str, Any] = {
        "time": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "level": level,
        "module": module,
        "message": message,
    }

    if task_id is not None:
        record["task_id"] = task_id
    if run_id is not None:
        record["run_id"] = run_id
    if trade_date is not None:
        record["trade_date"] = trade_date
    if context:
        # Keep secrets out of local files because logs are often shared during debugging.
        record["context"] = mask_sensitive(context)

    log_path = get_logs_dir() / file_name
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        file.write("\n")


def log_exception(
    *,
    file_name: LogFileName,
    module: str,
    message: str,
    error: BaseException,
    task_id: str | None = None,
    run_id: str | None = None,
    trade_date: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Write an ERROR record with exception details for local diagnosis."""

    error_context = {
        **(context or {}),
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    write_json_log(
        file_name=file_name,
        level="ERROR",
        module=module,
        message=message,
        task_id=task_id,
        run_id=run_id,
        trade_date=trade_date,
        context=error_context,
    )


def get_worker_logger(name: str) -> logging.Logger:
    """Return a standard logger name for libraries that require logging.Logger."""

    return logging.getLogger(f"invest_pilot.worker.{name}")
