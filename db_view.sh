#!/bin/bash
# SQLite 数据库浏览器 - 一键启动
# 用法: ./db_view.sh

DB_PATH="$(cd "$(dirname "$0")" && pwd)/data/a_stock_research.sqlite"
PORT=8080
SQLITE_WEB="/Users/sjh/Library/Python/3.12/bin/sqlite_web"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库文件不存在: $DB_PATH"
    exit 1
fi

if lsof -i :$PORT &>/dev/null; then
    echo "⚠️  端口 $PORT 已被占用，先停止旧进程..."
    kill $(lsof -ti :$PORT) 2>/dev/null
    sleep 1
fi

echo "🚀 启动数据库浏览器..."
nohup "$SQLITE_WEB" -H 127.0.0.1 -p $PORT "$DB_PATH" > /tmp/sqlite_web.log 2>&1 &
echo "✅ 已启动: http://127.0.0.1:$PORT"
open "http://127.0.0.1:$PORT"
