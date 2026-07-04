# web API约定

## 原则

前端不直接调用 Python。

前端只调用 Next.js API Routes，由 API Routes 创建任务、读取数据库或调用 worker。

## 核心接口

```text
GET  /api/dashboard
POST /api/tasks/run (body: {"pipeline": "update-data"})
POST /api/tasks/run (body: {"pipeline": "run-screening"})
POST /api/tasks/run (body: {"pipeline": "generate-report"})
GET  /api/tasks/:task_id
GET  /api/runs/latest
GET /api/recommendations
GET  /api/stocks/:code
GET  /api/watchlist
POST /api/watchlist/:code/update-status
GET  /api/settings
POST /api/settings
```

## 长任务接口

长任务接口不等待 Python 执行完成。

正确流程：

```text
前端点击按钮
  ↓
POST /api/tasks/run (body: {"pipeline": "update-data"})
  ↓
API 创建 task_id 并立即返回
  ↓
后台执行 worker
  ↓
前端轮询 GET /api/tasks/:task_id
```

## 返回格式

成功：

```json
{
  "ok": true,
  "data": {}
}
```

失败：

```json
{
  "ok": false,
  "error": {
    "code": "TASK_FAILED",
    "message": "任务执行失败"
  }
}
```

长任务创建：

```json
{
  "ok": true,
  "data": {
    "taskId": "task_20260704_001",
    "status": "pending"
  }
}
```

## 注意事项

- API 不直接返回大量历史行情，详情页按需获取。
- API 需要返回最近一次成功的 `run_id`。
- `/api/recommendations` 默认读取最近一次成功 `run_id`，不是简单按自然日读取。
- 如果没有成功运行结果，前端显示空状态。
- AI 报告失败时，推荐列表仍然正常展示。
