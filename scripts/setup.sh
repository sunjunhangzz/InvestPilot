#!/usr/bin/env bash
# setup.sh — 安装所有依赖（Python 虚拟环境 + Node 包）
# 用法: bash scripts/setup.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== A股AI投研系统 — 安装依赖 ==="
echo "项目根目录: $ROOT"

# --- Python worker ---
echo ""
echo "[1/2] 安装 Python worker 依赖..."
cd "$ROOT/app/worker"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  虚拟环境已创建"
fi

source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "  Python 依赖安装完成"

# --- Web frontend ---
echo ""
echo "[2/2] 安装前端依赖..."
cd "$ROOT/app/web"
npm install --silent
echo "  前端依赖安装完成"

echo ""
echo "============================================"
echo "  安装完成！"
echo "  下一步: bash scripts/configure.sh    # 配置环境"
echo "============================================"
