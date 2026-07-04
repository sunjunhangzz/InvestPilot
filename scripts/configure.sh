#!/usr/bin/env bash
# configure.sh — 初始化配置文件
# 用法: bash scripts/configure.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== A股AI投研系统 — 配置 ==="

cd "$ROOT"

# .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "已创建 .env（从 .env.example 复制）"
    echo ""
    echo "如需启用 AI 报告，请编辑 .env 填入 DeepSeek API Key："
    echo "  DEEPSEEK_API_KEY=sk-xxxxxxxx"
    echo ""
    echo "默认配置下 AI 报告为关闭状态（ai.enabled = false），"
    echo "基础筛选和推荐功能不受影响。"
else
    echo ".env 已存在，跳过"
fi

# 验证
echo ""
echo "配置检查："
python3 -c "
import json
from pathlib import Path
config = json.loads(Path('app/shared/config.json').read_text())
print(f'  数据库路径: {config[\"databasePath\"]}')
print(f'  推荐数量: {config[\"recommendationLimit\"]}')
print(f'  AI 开关: {config[\"ai\"][\"enabled\"]}')
print(f'  AI 模型: {config[\"ai\"][\"model\"]}')
" 2>/dev/null || echo "  (Python 未配置，请先运行 bash scripts/setup.sh)"

echo ""
echo "============================================"
echo "  配置完成！"
echo "  下一步: bash scripts/run_pipeline.sh  # 运行全流程"
echo "============================================"
