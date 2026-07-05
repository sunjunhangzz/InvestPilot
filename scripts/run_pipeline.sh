#!/usr/bin/env bash
# run_pipeline.sh — 一键跑通完整流水线（数据更新 + 分析推荐）
# 等价于: bash scripts/update_data.sh && bash scripts/run_analysis.sh
# 用法:
#   bash scripts/run_pipeline.sh --test     # 测试模式
#   bash scripts/run_pipeline.sh --ai --web # 全量+AI+前端

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TEST_FLAG=""
AI_FLAG=""
WEB_FLAG=""

for arg in "$@"; do
    case $arg in
        --test) TEST_FLAG="--test" ;;
        --ai)   AI_FLAG="--ai" ;;
        --web)  WEB_FLAG="--web" ;;
    esac
done

source app/worker/.venv/bin/activate 2>/dev/null || {
    echo "❌ 虚拟环境未安装，请先运行: bash scripts/setup.sh"
    exit 1
}

# 1. 初始化数据库（幂等，每次跑无害）
python app/worker/scripts/init_db.py

# 2. 更新数据
bash "$ROOT/scripts/update_data.sh" $TEST_FLAG

# 3. 分析推荐
bash "$ROOT/scripts/run_analysis.sh" $AI_FLAG $WEB_FLAG
