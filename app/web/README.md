# web 子项目

## 职责

`web` 是第一版的前端网站，同时承载 Next.js API Routes。

负责：

- 首页仪表盘
- 今日推荐页面
- 股票详情页面
- 观察池页面
- 系统设置页面
- API Routes
- 调用 Python worker
- 读取 SQLite 数据

## 页面

```text
/dashboard
/recommendations
/stocks/[code]
/watchlist
/settings
```

## API

```text
POST /api/tasks/update-data
POST /api/tasks/run-screening
POST /api/tasks/generate-report
GET  /api/tasks/:task_id
GET  /api/dashboard
GET  /api/recommendations/today
GET  /api/stocks/:code
GET  /api/watchlist
GET  /api/settings
POST /api/settings
```

## 前端约束

- 长任务必须显示 loading 状态。
- 任务创建后通过 `task_id` 轮询状态。
- 推荐列表只展示核心字段。
- 股票详情展示完整信息。
- 空数据、错误、API Key 缺失都要有明确提示。

## 不做

第一版不做：

- 用户登录
- 权限系统
- 移动端深度适配
- 复杂大屏
- 独立 NestJS 后端

