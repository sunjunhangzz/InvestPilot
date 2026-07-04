"""Generate AI reports for recommended stocks.

Usage:
    python app/worker/scripts/generate_report.py [--task-id <id>]

Requires DEEPSEEK_API_KEY in .env and ai.enabled = true in config.json.
Without API key or when ai.enabled = false, this script exits cleanly.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.db import database_connection
from app.worker.src.tasks import mark_task_failed, mark_task_success
from app.worker.src.loggers import write_json_log
from app.worker.src.reports.ai_provider import is_ai_enabled
from app.worker.src.reports.generator import (
    generate_stock_report,
    upsert_ai_reports,
)
from app.worker.src.utils.arg_utils import resolve_task_id


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S_%f")
    return f"generate_report_{ts}"


def main() -> int:
    with database_connection() as connection:
        task_id, is_external = resolve_task_id("generate_report", connection, _new_task_id)

    write_json_log(
        file_name="ai.log", level="INFO", module="generate_report",
        task_id=task_id, message="start AI report generation",
    )

    if not is_ai_enabled():
        print("AI is disabled or API key not set — skipping")
        with database_connection() as c:
            if not is_external:
                mark_task_success(task_id, connection=c)
        return 0

    # Load latest recommendations.
    with database_connection() as connection:
        rec_rows = connection.execute(
            """
            SELECT r.code, r.rating, r.rank, r.total_score, r.reason, r.risk_tags, r.run_id, r.trade_date,
                   s.name, s.board
            FROM recommendations r
            JOIN stocks s ON s.code = r.code
            WHERE r.run_id = (SELECT run_id FROM runs WHERE status = 'success' ORDER BY created_at DESC LIMIT 1)
            ORDER BY r.rank
            """
        ).fetchall()

        if not rec_rows:
            print("no recommendations — skipping")
            if not is_external:
                mark_task_success(task_id, connection=connection)
            return 0

        # Load factors for the same run.
        factor_rows = connection.execute(
            "SELECT * FROM factors WHERE run_id = ?",
            (rec_rows[0]["run_id"],),
        ).fetchall()
        factors_map = {r["code"]: dict(r) for r in factor_rows}

    reports: list[dict] = []
    success = 0
    failed = 0

    for rec in rec_rows:
        code = rec["code"]
        stock = {"code": code, "name": rec["name"], "board": rec["board"]}
        factors = factors_map.get(code)
        rec_dict = {
            "rating": rec["rating"], "rank": rec["rank"],
            "total_score": rec["total_score"], "reason": rec["reason"],
            "risk_tags": rec["risk_tags"],
        }

        report = generate_stock_report(
            stock, factors, rec_dict,
            run_id=rec["run_id"], trade_date=rec["trade_date"],
        )
        if report:
            reports.append(report)
            success += 1
            print(f"  {code}: ✓")
        else:
            failed += 1
            print(f"  {code}: ✗")

    # Write reports.
    if reports:
        with database_connection() as connection:
            upsert_ai_reports(connection, reports)
            if not is_external:
                mark_task_success(task_id, connection=connection)

    write_json_log(
        file_name="ai.log", level="INFO", module="generate_report",
        task_id=task_id, message="AI report generation complete",
        context={"success": success, "failed": failed},
    )

    print(f"reports: {success} ok, {failed} failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
