#!/usr/bin/env bash
# update_data.sh — 更新股票列表和行情数据
# 用法:
#   bash scripts/update_data.sh           # 全量模式（~60 分钟）
#   bash scripts/update_data.sh --test    # 测试模式（2 只股票，~30 秒）

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="full"
CODES_ARG=""

for arg in "$@"; do
    case $arg in
        --test) MODE="test"; CODES_ARG="--codes=000001,600519" ;;
    esac
done

source app/worker/.venv/bin/activate 2>/dev/null || {
    echo "❌ 虚拟环境未安装，请先运行: bash scripts/setup.sh"
    exit 1
}

echo "============================================"
if [ "$MODE" = "test" ]; then
    echo "  更新数据 — 测试模式 (2 只股票)"
else
    echo "  更新数据 — 全量模式"
fi
echo "============================================"

echo ""
echo "[1/2] 更新股票列表..."
python app/worker/scripts/update_stocks.py

echo ""
echo "[2/2] 更新行情数据..."
if [ "$MODE" = "test" ]; then
    python app/worker/scripts/update_prices.py --codes=000001,600519
else
    python app/worker/scripts/update_prices.py
fi

echo ""
echo "============================================"
echo "  数据更新完成！"
echo "  下一步: bash scripts/run_analysis.sh   # 分析推荐"
echo "============================================"
