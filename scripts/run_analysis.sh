#!/usr/bin/env bash
# run_analysis.sh — 运行因子计算 + 筛选推荐 + 观察池更新（+ 可选 AI 报告）
# 用法:
#   bash scripts/run_analysis.sh           # 基础分析
#   bash scripts/run_analysis.sh --ai      # 含 AI 报告
#   bash scripts/run_analysis.sh --web     # 完成后启动前端

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DO_AI=false
START_WEB=false

for arg in "$@"; do
    case $arg in
        --ai)  DO_AI=true ;;
        --web) START_WEB=true ;;
    esac
done

source app/worker/.venv/bin/activate 2>/dev/null || {
    echo "❌ 虚拟环境未安装，请先运行: bash scripts/setup.sh"
    exit 1
}

echo "============================================"
echo "  分析推荐"
[ "$DO_AI" = true ] && echo "  (含 AI 报告)"
echo "============================================"

echo ""
echo "[1/3] 计算因子评分..."
python app/worker/scripts/calc_factors.py

echo ""
echo "[2/3] 执行策略筛选..."
python app/worker/scripts/run_screening.py

echo ""
echo "[3/3] 更新观察池..."
python app/worker/scripts/update_watchlist.py

if [ "$DO_AI" = true ]; then
    echo ""
    echo "[+] 生成 AI 报告..."
    python app/worker/scripts/generate_report.py
fi

echo ""
echo "============================================"
echo "  分析完成！"
echo "============================================"
python3 -c "
from app.worker.src.db import database_connection
with database_connection() as c:
    c.row_factory = None
    recs = c.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]
    wl = c.execute('SELECT COUNT(*) FROM watchlist').fetchone()[0]
    ai = c.execute('SELECT COUNT(*) FROM ai_reports').fetchone()[0]
    print(f'  推荐: {recs} 只')
    print(f'  观察池: {wl} 只')
    if ai > 0:
        print(f'  AI 报告: {ai} 份')
    print()
    print('  查看结果: cd app/web && npm run dev')
    print('           http://localhost:3000/dashboard')
"

if [ "$START_WEB" = true ]; then
    echo ""
    echo "启动前端..."
    cd app/web && npm run dev
fi
