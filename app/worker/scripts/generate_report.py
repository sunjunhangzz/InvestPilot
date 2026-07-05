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
    mode = "single"
    # When called from Web (--task-id present), default to committee mode.
    if any(a.startswith("--task-id") for a in sys.argv):
        mode = "committee"
    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            mode = arg.split("=", 1)[1]

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

    # Load fundamentals for committee mode.
    fund_map: dict[str, dict] = {}
    with database_connection() as fconn:
        for fr in fconn.execute("SELECT * FROM fundamentals").fetchall():
            fund_map[fr["code"]] = dict(fr)

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

    # --- Agent committee (--mode=committee) ---
    if mode == "committee" and is_ai_enabled():
        print()
        print("=== Agent 委员会辩论 ===")
        from app.worker.src.reports.agents import debate_stock, write_debate_report
        import os

        # Only top-10 by rank for committee.
        committee_recs = [r for r in rec_rows if r["rank"] <= 10]
        print(f"Evaluating {len(committee_recs)} stocks...")

        committee_results = []
        output_dir = os.path.join(PROJECT_ROOT, "reports", "debates", str(rec_rows[0]["trade_date"]))
        for rec in committee_recs:
            code = rec["code"]
            stock = {"code": code, "name": rec["name"], "board": rec["board"]}
            factors = factors_map.get(code)
            fund = fund_map.get(code) if 'fund_map' in dir() else None
            industry = (rec.get("industry") or
                        (fund.get("industry") if fund else None) or
                        (c.execute("SELECT industry FROM stocks WHERE code=?", (code,)).fetchone() or {}).get("industry"))

            try:
                result = debate_stock(code, rec["name"], factors or {}, fund, industry,
                                      rec["run_id"], rec["trade_date"])
                if result:
                    committee_results.append(result)
                    write_debate_report(result, output_dir)
                    print(f"  {code}: rating={result['rating']} consensus={result['consensus']}")
                else:
                    print(f"  {code}: ✗ (AI disabled)")
            except Exception as e:
                print(f"  {code}: ✗ {e}")

        if committee_results:
            # Determine AI-A stocks (top 5 by rating, minimum 3 votes).
            committee_results.sort(key=lambda x: (-x["rating"], -x["votes"].get("agree", 0)))
            ai_a_codes = set()
            for r in committee_results[:5]:
                if r["votes"].get("agree", 0) >= 3:
                    ai_a_codes.add(r["code"])

            # Update recommendations with AI ratings.
            with database_connection() as conn:
                for r in committee_results:
                    ai_grade = "AI-A" if r["code"] in ai_a_codes else "B"
                    conn.execute(
                        "UPDATE recommendations SET rating=? WHERE run_id=? AND code=?", 
                        (ai_grade, r.get("run_id", rec_rows[0]["run_id"]), r["code"]),
                    )
                conn.commit()
            print(f"AI-A: {len(ai_a_codes)} stocks")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
