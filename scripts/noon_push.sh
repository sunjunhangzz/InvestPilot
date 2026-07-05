#!/usr/bin/env bash
# noon_push.sh — 午间推送（12:00）
# send_report.py --type=noon handles incremental price update internally.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source app/worker/.venv/bin/activate

echo "[noon_push] $(date): send noon report"
python app/worker/scripts/send_report.py --type=noon

echo "[noon_push] $(date): done"
