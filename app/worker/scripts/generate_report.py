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
from app.worker.src.tasks import mark_task_failed, mark_task_success, update_task_progress
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
    with database_connection() as fconn:
        fund_map = {}
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
        print("=== Agent 委员会辩论（前5只） ===")
        from app.worker.src.reports.agents import debate_stock, write_debate_report
        from datetime import datetime as dt
        import os, traceback

        # Top-5 only.
        committee_recs = [r for r in rec_rows if r["rank"] <= 5]
        print(f"Evaluating {len(committee_recs)} stocks...")
        if not committee_recs:
            print("  no stocks in top 5")

        # Load industry map.
        with database_connection() as fconn:
            ind_map = {r["code"]: r["industry"] for r in fconn.execute(
                "SELECT code, industry FROM stocks WHERE industry IS NOT NULL").fetchall()}

        # Error trace directory.
        ts = dt.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = os.path.join(PROJECT_ROOT, "docs", "debug", ts)
        os.makedirs(debug_dir, exist_ok=True)

        trade_date_str = str(rec_rows[0]["trade_date"])
        run_id_val = str(rec_rows[0]["run_id"])
        output_dir = os.path.join(PROJECT_ROOT, "reports", "debates", trade_date_str)
        results = []

        for rec in committee_recs:
            code = str(rec["code"]); name = str(rec["name"])
            factors = factors_map.get(code) or {}
            fund = fund_map.get(code)
            industry = rec["industry"] if "industry" in rec.keys() else ind_map.get(code)
            try:
                r = debate_stock(code, name, factors, fund, industry, run_id_val, trade_date_str)
                if not r:
                    print(f"  {code}: ✗ (AI disabled)")
                    continue
                results.append(r)
                write_debate_report(r, output_dir)
                # Store in agent_reports (AI rating stored here, NOT overwriting recommendations).
                try:
                    with database_connection() as wc:
                        wc.execute('''INSERT OR REPLACE INTO agent_reports
                            (run_id,code,trade_date,rating,consensus,debate_history,summary,model_name)
                            VALUES(?,?,?,?,?,?,?,?)''',
                            (run_id_val,code,trade_date_str,r["rating"],r["consensus"],
                             "4-round debate",r["summary"],"deepseek-v4-flash"))
                        wc.commit()
                    update_task_progress(task_id, "committee", len(results)+1, len(committee_recs), code)
                    print(f"  {code}: rating={r['rating']} consensus={r['consensus']} ✓")
                except Exception as dbe:
                    print(f"  {code}: rating={r['rating']} DB write failed: {dbe}")
                    with open(os.path.join(debug_dir, f"{code}_db_error.txt"), "w") as df:
                        df.write(f"agent_reports INSERT failed: {dbe}\n\n{traceback.format_exc()}")
            except Exception as e:
                print(f"  {code}: ✗ {e}")
                with open(os.path.join(debug_dir, f"{code}_error.txt"), "w") as ef:
                    ef.write(f"debate_stock failed: {e}\n\n{traceback.format_exc()}")

        # Summary.
        if results:
            results.sort(key=lambda x: (-x["rating"], -x["votes"].get("agree", 0)))
            ai_a = [r["code"] for r in results[:3] if r["votes"].get("agree", 0) >= 3]
            print(f"AI-A (top 3): {ai_a}")
            with open(os.path.join(debug_dir, "summary.txt"), "w") as sf:
                sf.write(f"AI-A codes: {ai_a}\n")
                for r in results:
                    sf.write(f"{r['code']} rating={r['rating']} consensus={r['consensus']} votes={r['votes']}\n")
        else:
            print("No committee results — all stocks failed or AI disabled")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
