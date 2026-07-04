# 01-web架构

## 定位

`app/web` 是第一版的用户界面和 API 层。

它承担两个职责：

1. 展示页面
2. 提供 Next.js API Routes

## 页面架构

```text
app/web/
  app/
    dashboard/
    recommendations/
    stocks/[code]/
    watchlist/
    settings/
  components/
    layout/
    tables/
    charts/
    task-status/
  lib/
    api/
    db/
    tasks/
    config/
  types/
```

具体目录会在初始化 Next.js 项目后创建。

## 页面职责

```text
dashboard
  系统状态、最新 run_id、任务状态、推荐数量

recommendations
  最新推荐列表，默认读取最近成功 run_id

stocks/[code]
  股票详情、图表、因子、推荐理由、AI报告

watchlist
  观察池、跟踪天数、状态、退出原因

settings
  推荐数量、AI开关、API Key、路径展示
```

## API Routes

```text
POST /api/tasks/update-data
POST /api/tasks/run-screening
POST /api/tasks/generate-report
GET  /api/tasks/:task_id
GET  /api/runs/latest
GET  /api/dashboard
GET  /api/recommendations/today
GET  /api/stocks/:code
GET  /api/watchlist
GET  /api/settings
POST /api/settings
```

## API职责边界

API Routes 可以：

- 创建任务
- 查询任务状态
- 启动 worker 脚本
- 读取 SQLite
- 返回页面需要的数据

API Routes 不应该：

- 直接实现因子计算
- 直接采集股票数据
- 直接做大量循环计算
- 长时间阻塞等待 Python 任务完成

## 状态管理

第一版不需要复杂全局状态管理。

建议：

- 页面请求 API 获取数据
- 任务执行时使用轮询
- 表单设置本地状态
- 后续如复杂再考虑 Zustand

## 错误处理

所有页面必须处理：

- loading
- empty
- error
- success

所有任务按钮必须处理：

- idle
- pending
- running
- success
- failed

