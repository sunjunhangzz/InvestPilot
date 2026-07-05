#!/usr/bin/env bash
# morning_push.sh — 早盘推送（08:00）
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source app/worker/.venv/bin/activate

echo "[morning_push] $(date): run analysis"
bash scripts/run_analysis.sh

echo "[morning_push] $(date): send report"
python app/worker/scripts/send_report.py --type=morning

echo "[morning_push] $(date): done"
