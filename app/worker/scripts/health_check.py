#!/usr/bin/env python3
"""Health check — verify the environment is ready for the A股AI投研 pipeline.

Usage:
    python app/worker/scripts/health_check.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    failures = 0

    def ok(msg: str) -> None:
        print(f"  ✓ {msg}")

    def fail(msg: str) -> None:
        nonlocal failures
        failures += 1
        print(f"  ✗ {msg}")

    print("=== A股AI投研系统 — 健康检查 ===\n")

    # 1. Python version
    print("[1] Python 版本")
    v = sys.version_info
    if v >= (3, 12):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor}.{v.micro} — 需要 3.12+")

    # 2. Dependencies
    print("\n[2] Python 依赖")
    deps = [
        ("akshare", "数据采集"),
        ("pandas", "数据处理"),
        ("numpy", "数值计算"),
        ("requests", "HTTP 请求"),
        ("dotenv", "环境变量"),
    ]
    for mod, desc in deps:
        try:
            __import__(mod)
            ok(f"{mod} ({desc})")
        except ImportError:
            fail(f"{mod} ({desc}) — 未安装，请运行 pip install -r requirements.txt")

    # 3. Database
    print("\n[3] 数据库")
    from app.worker.src.db import get_database_path, database_connection
    db_path = get_database_path()
    if db_path.exists():
        ok(f"SQLite 存在: {db_path}")
    else:
        fail(f"SQLite 不存在: {db_path} — 请运行 init_db.py")

    # 4. Core tables
    from app.worker.src.db.schema_validator import validate_schema, format_validation_result
    print("\n[4] 数据库 schema")
    try:
        with database_connection() as conn:
            result = validate_schema(conn)
            if result.valid:
                ok(f"{result.total_tables} 表, {result.total_indexes} 索引")
            else:
                for line in format_validation_result(result).split("\n"):
                    if "FAILED" in line or "Missing" in line:
                        fail(line.strip())
    except Exception as e:
        fail(f"无法连接数据库: {e}")

    # 5. Data summary
    print("\n[5] 数据概览")
    try:
        with database_connection() as conn:
            conn.row_factory = None
            tables = {
                "stocks": "股票列表",
                "daily_prices": "日线行情",
                "factors": "因子评分",
                "recommendations": "推荐结果",
                "watchlist": "观察池",
                "system_tasks": "任务记录",
                "ai_reports": "AI 报告",
            }
            for t, label in tables.items():
                count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                if count > 0:
                    ok(f"{label} ({t}): {count} 行")
                else:
                    print(f"  - {label} ({t}): 空")
    except Exception as e:
        fail(f"数据概览失败: {e}")

    # 6. Logs
    print("\n[6] 日志")
    from app.shared.paths import get_config_paths
    logs_dir = get_config_paths()["logsPath"]
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        if log_files:
            ok(f"日志目录存在，{len(log_files)} 个文件: {', '.join(f.name for f in log_files)}")
        else:
            print(f"  - 日志目录存在但无日志文件")
    else:
        fail(f"日志目录不存在: {logs_dir}")

    # 7. Environment
    print("\n[7] 环境变量")
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        ok(".env 存在")
    else:
        print("  - .env 不存在（AI 报告将跳过）")

    from dotenv import load_dotenv
    load_dotenv()
    ai_key = os.getenv("DEEPSEEK_API_KEY")
    if ai_key:
        ok(f"DeepSeek API Key: ***{ai_key[-4:]}")
    else:
        print("  - DeepSeek API Key 未配置（AI 报告将跳过）")

    # --- result ---
    print(f"\n{'='*40}")
    if failures == 0:
        print("  健康检查通过 ✅")
    else:
        print(f"  健康检查未通过 ✗ — {failures} 项失败")
    print("=" * 40)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
