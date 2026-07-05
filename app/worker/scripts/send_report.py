"""Send push notifications via 企业微信/ PushPlus / Server酱.

Usage:
    python app/worker/scripts/send_report.py --type=morning|noon [--dry-run]

When --type=noon, the script runs an incremental price update for
recommendation + watchlist stocks (~30 seconds) before sending.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests

from app.worker.src.db import database_connection
from app.worker.src.loggers import write_json_log
from app.worker.src.data_sources.price_source import to_sina_symbol
from app.worker.src.utils.arg_utils import resolve_task_id


def _new_task_id() -> str:
    ts = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S_%f")
    return f"send_report_{ts}"


def _get_setting(key: str, default: str = "") -> str:
    with database_connection() as c:
        row = c.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def _send_wecom(webhook_url: str, content: str) -> bool:
    try:
        resp = requests.post(webhook_url, json={
            "msgtype": "markdown",
            "markdown": {"content": content},
        }, timeout=10)
        return resp.status_code == 200 and resp.json().get("errcode") == 0
    except Exception:
        return False


def _send_pushplus(token: str, title: str, content: str) -> bool:
    try:
        resp = requests.post("http://www.pushplus.plus/send", json={
            "token": token, "title": title, "content": content,
        }, timeout=10)
        return resp.status_code == 200 and resp.json().get("code") == 200
    except Exception:
        return False


def _send_serverchan(sendkey: str, title: str, content: str) -> bool:
    try:
        resp = requests.post(
            f"https://sctapi.ftqq.com/{sendkey}.send",
            data={"title": title, "desp": content}, timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _send(provider: str, token: str, content: str, title: str = "") -> bool:
    if provider == "pushplus":
        return _send_pushplus(token, title, content)
    elif provider == "serverchan":
        return _send_serverchan(token, title, content)
    else:
        # Default: wecom webhook.
        # webhook_url may also be stored under wechat.webhook_url.
        webhook_url = _get_setting("wechat.webhook_url", token)
        return _send_wecom(webhook_url or token, content)


def _build_morning_md() -> str | None:
    """Build Markdown push content for morning report."""
    with database_connection() as c:
        run = c.execute(
            "SELECT run_id, trade_date FROM runs WHERE status='success' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not run:
            return "## 📊 A股AI投研 — 早盘\n\n今日暂无推荐数据，请手动运行筛选。"

        recs = c.execute(
            """SELECT r.code, s.name, r.rating, r.total_score, r.reason,
                      f.trend_score, f.momentum_score, f.liquidity_score, f.risk_score
               FROM recommendations r
               JOIN stocks s ON s.code = r.code
               LEFT JOIN factors f ON f.run_id = r.run_id AND f.code = r.code
               WHERE r.run_id = ?
               ORDER BY r.rank""",
            (run["run_id"],),
        ).fetchall()

        ai = c.execute(
            "SELECT code, content FROM ai_reports WHERE run_id=? AND status='success' ORDER BY code LIMIT 1",
            (run["run_id"],),
        ).fetchone()

        wl = c.execute(
            """SELECT w.code, s.name, w.status, w.tracking_days,
                      w.entry_price, w.latest_price
               FROM watchlist w JOIN stocks s ON s.code = w.code
               ORDER BY w.first_recommended_date DESC"""
        ).fetchall()

    lines = [f"## 📊 A股AI投研 — {run['trade_date']} 早盘"]
    lines.append("")
    lines.append(f"### 今日推荐（{len(recs)} 只）")
    lines.append("")
    lines.append("| 评级 | 代码 | 名称 | 趋势 | 动量 | 流动 | 风险 | 总分 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")

    for r in recs[:20]:  # Top 20 for readability.
        lines.append(
            f"| {r['rating']} | {r['code']} | {r['name']} | "
            f"{r['trend_score'] or '-'} | {r['momentum_score'] or '-'} | "
            f"{r['liquidity_score'] or '-'} | {r['risk_score'] or '-'} | "
            f"{r['total_score']} |"
        )

    if len(recs) > 20:
        lines.append(f"| ... | 等 {len(recs) - 20} 只 | | | | | | |")

    if ai:
        summary = ai["content"][:200]
        lines.append("")
        lines.append(f"> **AI 分析**（{ai['code']}）：{summary}")

    # Watchlist.
    if wl:
        lines.append("")
        lines.append(f"### 观察池（{len(wl)} 只）")
        lines.append("")
        active_count = sum(1 for w in wl if w["status"] == "active")
        downgraded = sum(1 for w in wl if w["status"] == "downgraded")
        lines.append(f"观察中：{active_count} · 降级：{downgraded}")

        # Show breached stocks.
        breached = []
        for w in wl:
            if w["latest_price"] and w["entry_price"]:
                ret = (w["latest_price"] - w["entry_price"]) / w["entry_price"] * 100
                if ret < -5:
                    breached.append(f"{w['code']} {w['name']} {ret:+.1f}%")
        if breached:
            lines.append("")
            lines.append("⚠️ 回撤 > 5%：")
            for b in breached[:5]:
                lines.append(f"- {b}")

    return "\n".join(lines)


def _build_noon_md() -> str | None:
    """Build Markdown push content for noon report with intraday performance."""
    # Incremental price update for recommended + watchlisted stocks.
    codes: list[str] = []
    with database_connection() as c:
        run = c.execute(
            "SELECT run_id FROM runs WHERE status='success' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not run:
            return "## 📊 A股AI投研 — 午间\n\n今日暂无推荐数据。"

        for t in ["recommendations", "watchlist"]:
            rows = c.execute(f"SELECT DISTINCT code FROM {t}").fetchall()
            for r in rows:
                if r["code"] not in codes:
                    codes.append(r["code"])

    # Incremental update.
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    import akshare as ak  # type: ignore[import-untyped]
    updated: dict[str, float] = {}
    for code in codes:
        try:
            raw = ak.stock_zh_a_daily(symbol=to_sina_symbol(code), start_date=today, end_date=today, adjust="qfq")
            if len(raw) > 0:
                row = raw.iloc[-1]
                close = float(row["close"])
                updated[code] = close
                # Quick UPSERT.
                with database_connection() as c2:
                    c2.execute(
                        """INSERT OR REPLACE INTO daily_prices (code, trade_date, open, high, low, close, volume, amount, pct_change, turnover, adjust_type)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'qfq')""",
                        (code, str(row["date"]), float(row["open"]), float(row["high"]), float(row["low"]),
                         close, float(row["volume"]), float(row["amount"]), None, float(row["turnover"])),
                    )
        except Exception:
            pass

    # Build content.
    lines = ["## 📊 A股AI投研 — 午间"]
    lines.append(f"行情更新：{len(updated)} 只")
    lines.append("")

    with database_connection() as c:
        # Recommendations performance.
        recs = c.execute(
            "SELECT r.code, s.name FROM recommendations r JOIN stocks s ON s.code=r.code ORDER BY r.rank"
        ).fetchall()
        if recs:
            # Get previous close for comparison.
            perf: list[tuple[str, str, float | None]] = []
            for r in recs:
                row = c.execute(
                    "SELECT close FROM daily_prices WHERE code=? ORDER BY trade_date DESC LIMIT 2",
                    (r["code"],),
                ).fetchall()
                if len(row) >= 2:
                    chg = (row[0]["close"] - row[1]["close"]) / row[1]["close"] * 100
                    perf.append((r["code"], r["name"], round(chg, 2)))
            if perf:
                perf.sort(key=lambda x: -(x[2] or -999))
                lines.append("### 今日推荐·上午涨跌")
                lines.append("")
                for code, name, chg in perf[:15]:
                    emoji = "🔴" if (chg or 0) > 0 else "🟢" if (chg or 0) < 0 else "⚪"
                    lines.append(f"{emoji} {code} {name} {chg:+.1f}%")

    return "\n".join(lines)


def main() -> int:
    with database_connection() as conn:
        task_id, is_external = resolve_task_id("send_report", conn, _new_task_id)

    report_type = "morning"
    dry_run = False
    for arg in sys.argv[1:]:
        if arg.startswith("--type="):
            report_type = arg.split("=", 1)[1]
        elif arg == "--dry-run":
            dry_run = True

    enabled = _get_setting("wechat.enabled", "false").lower() == "true"
    provider = _get_setting("wechat.provider", "wecom")
    token = _get_setting("wechat.webhook_url", "")

    if not enabled or not token:
        write_json_log(file_name="notification.log", level="INFO", module="send_report",
                       task_id=task_id, message="push disabled or token not set, skipped")
        print("Push disabled or token not set — skipped")
        return 0

    if report_type == "morning":
        content = _build_morning_md()
    else:
        content = _build_noon_md()

    if not content:
        return 0

    if dry_run:
        write_json_log(file_name="notification.log", level="INFO", module="send_report",
                       task_id=task_id, message=f"dry-run: {report_type}", context={"length": len(content)})
        print(f"[dry-run] {report_type} push ({len(content)} chars)")
        print(content[:500])
        return 0

    title = f"A股AI投研 — {'早盘' if report_type == 'morning' else '午间'}"
    success = _send(provider, token, content, title)

    write_json_log(
        file_name="notification.log",
        level="INFO" if success else "ERROR",
        module="send_report",
        task_id=task_id,
        message=f"{report_type} push {'ok' if success else 'failed'}",
        context={"provider": provider, "length": len(content)},
    )

    print(f"{report_type} push: {'✓' if success else '✗'}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
