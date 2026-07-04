"""AI report generator — builds structured prompts and writes to ai_reports.

The prompt is a structured summary (NOT raw price history) to keep token
costs low.  AI failure never blocks the recommendation pipeline.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.worker.src.reports.ai_provider import chat, get_ai_config, is_ai_enabled
from app.worker.src.loggers import write_json_log


def build_stock_prompt(stock: dict[str, Any], factors: dict[str, Any] | None, rec: dict[str, Any] | None) -> str:
    """Build a concise structured prompt for one stock.

    Only key indicators are included — no raw daily price tables.
    """

    lines = [
        f"请对以下A股股票做简要的投资研究分析。只做解释和风险提示，不做买卖建议。",
        "",
        f"股票代码：{stock['code']}",
        f"股票名称：{stock['name']}",
        f"所属板块：{stock['board']}",
    ]

    if factors:
        lines.append("")
        lines.append("因子评分：")
        lines.append(f"  趋势：{factors.get('trend_score', '-')}")
        lines.append(f"  动量：{factors.get('momentum_score', '-')}")
        lines.append(f"  流动性：{factors.get('liquidity_score', '-')}")
        lines.append(f"  风险控制：{factors.get('risk_score', '-')}")
        lines.append(f"  总评分：{factors.get('total_score', '-')}")

    if rec:
        lines.append("")
        lines.append(f"推荐评级：{rec.get('rating', '-')}")
        lines.append(f"排名：{rec.get('rank', '-')}")
        if rec.get("reason"):
            lines.append(f"入选理由：{rec['reason']}")
        if rec.get("risk_tags"):
            lines.append(f"风险标签：{rec['risk_tags']}")

    lines.append("")
    lines.append("请从趋势、流动性、风险三个角度简要分析（150字以内）。格式：趋势观点：…；流动性观点：…；风险观点：…；综合结论：…。")

    return "\n".join(lines)


def generate_stock_report(
    stock: dict[str, Any],
    factors: dict[str, Any] | None,
    rec: dict[str, Any] | None,
    run_id: str,
    trade_date: str,
) -> dict[str, Any] | None:
    """Generate an AI report for one stock.  Returns None on failure."""

    if not is_ai_enabled():
        return None

    prompt = build_stock_prompt(stock, factors, rec)
    cfg = get_ai_config()
    content = chat(prompt)

    if content is None:
        write_json_log(
            file_name="ai.log",
            level="WARN",
            module="generate_report",
            run_id=run_id,
            trade_date=trade_date,
            message=f"AI call failed for {stock['code']}",
        )
        return None

    write_json_log(
        file_name="ai.log",
        level="INFO",
        module="generate_report",
        run_id=run_id,
        trade_date=trade_date,
        message=f"AI report generated for {stock['code']}",
        context={"model": cfg["model"], "provider": cfg["provider"]},
    )

    return {
        "run_id": run_id,
        "trade_date": trade_date,
        "code": stock["code"],
        "report_type": "stock",
        "content": content,
        "model_name": cfg["model"],
        "status": "success",
    }


def upsert_ai_reports(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    """UPSERT ai_reports rows."""

    if not rows:
        return 0

    sql = """
        INSERT INTO ai_reports (run_id, trade_date, code, report_type, content, model_name, status)
        VALUES (:run_id, :trade_date, :code, :report_type, :content, :model_name, :status)
        ON CONFLICT(run_id, code, report_type) DO UPDATE SET
            content = excluded.content,
            model_name = excluded.model_name,
            status = excluded.status
    """

    with connection:
        connection.executemany(sql, rows)

    return len(rows)
