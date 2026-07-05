"""Multi-Agent debate committee — CAMEL-style collaborative evaluation.

5 agents debate in 4 rounds, then the chair votes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.worker.src.reports.ai_provider import chat as llm, is_ai_enabled, get_ai_config
from app.worker.src.reports.search_web import search_web
from app.worker.src.loggers import write_json_log

PROJECT_ROOT = Path(__file__).resolve().parents[3]

AGENTS = {
    "tech": {
        "name": "技术面分析师",
        "system": "你是A股技术面分析师。分析趋势/动量/波动率/回撤。输出JSON：{\"rating\":1-5,\"argument\":\"<80字>\"}。5=趋势完美，3=中性，1=趋势恶化。只输出JSON。",
    },
    "fund": {
        "name": "基本面分析师",
        "system": "你是A股基本面分析师。分析营收/利润增速/ROE。输出JSON：{\"rating\":1-5,\"argument\":\"<80字>\"}。5=高增长+高ROE，3=中性，1=基本面恶化。只输出JSON。",
    },
    "risk": {
        "name": "风险官",
        "system": "你是风险管理官。天然反对派——只挑问题不找优点。分析波动率/回撤/负债率。输出JSON：{\"rating\":1-5,\"argument\":\"<80字>\"}。5=极低风险，1=极高风险。只输出JSON。",
    },
    "value": {
        "name": "估值分析师",
        "system": "你是估值分析师。只看估值不问趋势。分析PE/PB/市值。PE/PB缺失时输出{\"rating\":3,\"argument\":\"估值数据不足\"}。输出JSON。",
    },
    "sector": {
        "name": "行业对比师",
        "system": "你是行业对比研究员。比较股票与其行业的相对表现。行业未知时输出{\"rating\":3,\"argument\":\"无同行对比数据\"}。输出JSON。",
    },
}


def _build_stock_context(code: str, name: str, factors: dict[str, Any], fund: dict[str, Any] | None, industry: str | None) -> str:
    ctx = f"股票：{code} {name}"
    if industry:
        ctx += f"\n行业：{industry}"
    if factors:
        ctx += f"\n趋势={factors.get('trend_score','-')} 动量={factors.get('momentum_score','-')} 流动性={factors.get('liquidity_score','-')} 风险={factors.get('risk_score','-')}"
    if fund:
        if fund.get("revenue_yoy") is not None:
            ctx += f"\n营收增速={fund['revenue_yoy']:.1f}%"
        if fund.get("net_profit_yoy") is not None:
            ctx += f"\n利润增速={fund['net_profit_yoy']:.1f}%"
        if fund.get("roe") is not None:
            ctx += f"\nROE={fund['roe']:.1f}%"
        if fund.get("debt_ratio") is not None:
            ctx += f"\n资产负债率={fund['debt_ratio']*100:.0f}%" if fund['debt_ratio'] < 1 else f"\n资产负债率={fund['debt_ratio']:.1f}%"
    return ctx


def _parse_json(text: str) -> dict[str, Any]:
    try:
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1].split("```")[0].replace("json", "").strip()
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return {"rating": 3, "argument": text[:80]}


def _agent_call(agent_key: str, context: str, others: str = "") -> dict[str, Any]:
    agent = AGENTS[agent_key]
    prompt = f"{context}\n\n" if not others else f"{context}\n\n其他Agent的意见：\n{others}\n\n请回应（坚持或修改你的rating）：\n"
    result = llm(prompt, system=agent["system"])
    if result is None:
        return {"rating": 3, "argument": "Agent 调用失败"}
    return _parse_json(result)


def _search_context(code: str, name: str, industry: str | None) -> dict[str, dict]:
    queries = {
        "tech": f"{name} {code} 技术分析 走势",
        "fund": f"{name} {code} 营收 利润 ROE 财报",
        "risk": f"{name} {code} 风险 负债 波动",
        "value": f"{name} {code} PE PB 估值 目标价",
        "sector": f"{name} {code} 行业 {industry or ''} 竞争 排名",
    }
    results: dict[str, dict] = {}
    for key, q in queries.items():
        results[key] = {"query": q, "hits": search_web(q)}
    return results


def debate_stock(
    code: str, name: str, factors: dict[str, Any], fund: dict[str, Any] | None,
    industry: str | None, run_id: str, trade_date: str,
) -> dict[str, Any] | None:
    """Run 4-round debate for one stock. Returns None if AI disabled."""

    if not is_ai_enabled():
        return None

    ctx = _build_stock_context(code, name, factors, fund, industry)
    history: list[dict[str, Any]] = []

    # Round 1: Independent analysis.
    round1: dict[str, dict[str, Any]] = {}
    for key in AGENTS:
        result = _agent_call(key, ctx)
        round1[key] = result
        write_json_log(file_name="ai.log", level="INFO", module="agent_committee",
                       run_id=run_id, trade_date=trade_date,
                       message=f"R1 {key} for {code}", context={"rating": result["rating"]})
    history.append({"round": 1, "results": round1})

    # Check early stop.
    ratings = [r["rating"] for r in round1.values()]
    if len(set(ratings)) == 1:
        pass  # Unanimous — still do round 2 for rigor.

    # Round 2: Cross-examination.
    round1_summary = "\n".join(
        f"{AGENTS[k]['name']}（评级{r['rating']}）：{r['argument']}" for k, r in round1.items()
    )
    round2: dict[str, dict[str, Any]] = {}
    for key in AGENTS:
        others = "\n".join(
            f"{AGENTS[k]['name']}（评级{r['rating']}）：{r['argument']}" for k, r in round1.items() if k != key
        )
        result = _agent_call(key, ctx, others)
        round2[key] = result
        write_json_log(file_name="ai.log", level="INFO", module="agent_committee",
                       run_id=run_id, trade_date=trade_date,
                       message=f"R2 {key} for {code}", context={"rating": result["rating"]})
    history.append({"round": 2, "results": round2})

    # Round 3: Web evidence.
    search_results = _search_context(code, name, industry)
    round3: dict[str, dict[str, Any]] = {}
    search_log: dict[str, dict] = {}
    for key in AGENTS:
        sr = search_results.get(key, {"query": "", "hits": []})
        search_log[key] = {"query": sr["query"], "hits": sr["hits"]}
        web_evidence = ""
        if sr["hits"]:
            web_evidence = "网络搜索证据：\n" + "\n".join(
                f"- {h['title']}: {h['snippet']}" for h in sr["hits"][:2]
            )
        prompt = f"{ctx}\n{web_evidence}\n\n其他Agent第2轮意见：\n{round1_summary}"
        result = llm(prompt, system=AGENTS[key]["system"])
        if result:
            round3[key] = _parse_json(result)
    history.append({"round": 3, "results": round3, "search": search_log})

    # Round 4: Group debate.
    pro_group = [k for k, r in round3.items() if r.get("rating", 3) >= 3]
    con_group = [k for k, r in round3.items() if r.get("rating", 3) < 3]
    round4: dict[str, dict[str, Any]] = {}
    if pro_group and con_group:
        pro_summary = "看多组：\n" + "\n".join(f"{AGENTS[k]['name']}: {round3[k]['argument']}" for k in pro_group)
        con_summary = "看空组：\n" + "\n".join(f"{AGENTS[k]['name']}: {round3[k]['argument']}" for k in con_group)
        debate_prompt = f"{ctx}\n\n两方意见：\n{pro_summary}\n\n{con_summary}\n\n请做最后陈述。只输出JSON。"
        for key in AGENTS:
            result = llm(debate_prompt, system=AGENTS[key]["system"])
            if result:
                round4[key] = _parse_json(result)
        history.append({"round": 4, "results": round4, "groups": {"pro": pro_group, "con": con_group}})
    else:
        round4 = round3
        history.append({"round": 4, "results": round4, "note": "all same side, skip group debate"})

    # Chair.
    final_round = round4 or round3
    chair_prompt = f"综合4轮辩论，请给出最终评级和投票统计。\n\n股票：{code} {name}\n\n"
    for k, r in final_round.items():
        chair_prompt += f"{AGENTS[k]['name']}：评级{r['rating']} — {r['argument']}\n"
    chair_prompt += "\n输出JSON：{\"rating\":1-5,\"summary\":\"<150字>\",\"consensus\":\"unanimous|majority|split|vetoed\",\"votes\":{\"agree\":N,\"oppose\":M}}"

    cfg = get_ai_config()
    chair_result = llm(chair_prompt, system="你是投资委员会主席，综合所有Agent意见做出最终裁决。只输出JSON。")
    if chair_result:
        chair = _parse_json(chair_result)
    else:
        all_r = [r["rating"] for r in final_round.values()]
        agrees = sum(1 for r in all_r if r >= 3)
        chair = {
            "rating": round(sum(all_r) / len(all_r)),
            "summary": "主席调用失败，取平均评级",
            "consensus": "unanimous" if agrees == 5 else "majority" if agrees >= 3 else "vetoed",
            "votes": {"agree": agrees, "oppose": 5 - agrees},
        }

    return {
        "code": code,
        "name": name,
        "rating": chair["rating"],
        "consensus": chair["consensus"],
        "summary": chair["summary"],
        "votes": chair.get("votes", {}),
        "history": history,
        "final_ratings": {AGENTS[k]["name"]: r["rating"] for k, r in final_round.items()},
    }


def write_debate_report(debate: dict[str, Any], output_dir: str) -> str:
    """Generate Markdown debate report. Returns file path."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{debate['code']}.md")

    lines = [
        f"# Agent 委员会辩论报告 — {debate['code']} {debate['name']}",
        f"> 最终评级 **{debate['rating']}** | 共识 **{debate['consensus']}** | 同意 {debate['votes'].get('agree',0)}:{debate['votes'].get('oppose',0)}",
        "",
        f"## 主席总结",
        debate["summary"],
        "",
        "## 各Agent最终评级",
    ]
    for name, rating in debate["final_ratings"].items():
        lines.append(f"- {name}：**{rating}**")
    lines.append("")

    for round_data in debate["history"]:
        rn = round_data["round"]
        lines.append(f"## 第{rn}轮")
        if "search" in round_data:
            lines.append("")
            for agent_key, sd in round_data["search"].items():
                lines.append(f"**{AGENTS[agent_key]['name']}** 搜索：`{sd.get('query','')}`")
                for h in sd.get('hits', []):
                    lines.append(f"  - [{h['title']}]({h['url']})")
                    lines.append(f"    {h['snippet']}")
                lines.append("")
        if "groups" in round_data:
            lines.append(f"看多组：{', '.join(round_data['groups']['pro'])}")
            lines.append(f"看空组：{', '.join(round_data['groups']['con'])}")
            lines.append("")
        for key, r in round_data["results"].items():
            lines.append(f"**{AGENTS[key]['name']}**（评级{r['rating']}）：{r['argument']}")
            lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path
