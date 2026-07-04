#!/usr/bin/env bash
# run_pipeline.sh — 运行完整数据流水线（初始化 → 采集 → 因子 → 推荐 → 观察池）
# 用法:
#   bash scripts/run_pipeline.sh           # 全量模式（行情采集 ~50 分钟）
#   bash scripts/run_pipeline.sh --test    # 测试模式（仅 2 只股票，~30 秒）
#   bash scripts/run_pipeline.sh --ai      # 全量 + AI 报告
#   bash scripts/run_pipeline.sh --web     # 全量结束后自动启动前端

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="full"
START_WEB=false
DO_AI=false
CODES_ARG=""

for arg in "$@"; do
    case $arg in
        --test) MODE="test"; CODES_ARG="--codes=000001,600519" ;;
        --ai)   DO_AI=true ;;
        --web)  START_WEB=true ;;
    esac
done

# --- 激活虚拟环境 ---
source app/worker/.venv/bin/activate 2>/dev/null || {
    echo "❌ 虚拟环境未安装，请先运行: bash scripts/setup.sh"
    exit 1
}

echo "============================================"
if [ "$MODE" = "test" ]; then
    echo "  A股AI投研系统 — 测试模式 (2 只股票)"
else
    echo "  A股AI投研系统 — 全量模式 (全部主板股票)"
fi
echo "============================================"

# 1. 数据库
echo ""
echo "[1/7] 初始化数据库..."
python app/worker/scripts/init_db.py
python app/worker/scripts/check_schema.py

# 2. 股票列表
echo ""
echo "[2/7] 采集股票列表..."
python app/worker/scripts/update_stocks.py

# 3. 行情
echo ""
echo "[3/7] 采集行情数据..."
if [ "$MODE" = "test" ]; then
    echo "  (测试模式：仅 000001, 600519)"
    python app/worker/scripts/update_prices.py --codes=000001,600519
else
    echo "  (全量模式：约需 50 分钟，请耐心等待)"
    python app/worker/scripts/update_prices.py
fi

# 4. 因子
echo ""
echo "[4/7] 计算因子评分..."
python app/worker/scripts/calc_factors.py

# 5. 筛选
echo ""
echo "[5/7] 执行策略筛选..."
python app/worker/scripts/run_screening.py

# 6. 观察池
echo ""
echo "[6/7] 更新观察池..."
python app/worker/scripts/update_watchlist.py

# 7. AI 报告（可选）
if [ "$DO_AI" = true ]; then
    echo ""
    echo "[7/7] 生成 AI 报告..."
    python app/worker/scripts/generate_report.py
else
    echo ""
    echo "[7/7] AI 报告：跳过 (需要时加 --ai)"
fi

# --- 摘要 ---
echo ""
echo "============================================"
echo "  流水线完成！"
echo "============================================"
python3 -c "
from app.worker.src.db import database_connection
with database_connection() as c:
    c.row_factory = None
    stocks = c.execute('SELECT COUNT(*) FROM stocks').fetchone()[0]
    prices = c.execute('SELECT COUNT(DISTINCT code) FROM daily_prices').fetchone()[0]
    recs = c.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]
    wl = c.execute('SELECT COUNT(*) FROM watchlist').fetchone()[0]
    print(f'  股票: {stocks} 只')
    print(f'  行情覆盖: {prices} 只')
    print(f'  推荐: {recs} 只')
    print(f'  观察池: {wl} 只')
"

# --- 启动前端 ---
if [ "$START_WEB" = true ]; then
    echo ""
    echo "启动前端: http://localhost:3000/dashboard"
    cd app/web && npm run dev
fi
