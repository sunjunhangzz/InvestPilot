# 05-API任务层

## 任务 05.1：创建 Next.js API 基础工具

所属子项目：web

前置依赖：01.2

开发内容：

- 数据库读取工具。
- API 返回格式工具。
- 错误处理工具。
- shared 配置读取工具。
- snake_case 到 camelCase 的字段转换工具。

验收标准：

- API 返回统一格式。
- 错误时有明确 message。
- 前端收到 camelCase 字段。

风险点：

- TS 和 SQLite 字段命名不一致。

## 任务 05.1a：实现 API 任务创建工具

所属子项目：web

前置依赖：05.1

开发内容：

- 创建 task_id。
- 写入 `system_tasks` pending 状态。
- 检查任务锁。
- 启动 Python worker 子进程。
- 处理子进程退出码。

验收标准：

- API 能创建任务记录。
- worker 运行后状态能被更新。
- 子进程失败能记录错误摘要。

风险点：

- API 和 worker 都写任务状态，职责不清会导致状态覆盖。

## 任务 05.2：实现任务创建接口

所属子项目：web

前置依赖：05.1a

开发内容：

- `POST /api/tasks/run` — 统一 pipeline 入口，body: `{ "pipeline": "update-data" | "run-screening" | "generate-report" }`
  - `update-data`：串行调用 `update_stocks.py` → `update_prices.py`
  - `run-screening`：串行调用 `calc_factors.py` → `run_screening.py` → `update_watchlist.py`
  - `generate-report`：预留（07 阶段实现）
- `GET /api/tasks/:taskId` — 查询任务状态
- `GET /api/runs/latest` — 最新成功 run
- `GET /api/recommendations` — 最新推荐列表
- `GET /api/stocks/:code` — 股票详情
- `GET /api/watchlist` — 观察池
- `GET /api/settings` / `POST /api/settings` — 系统设置
- `GET /api/dashboard` — 仪表盘汇总

验收标准：

- 接口立即返回 `task_id`（异步执行）。
- 不等待 Python 长时间执行完成。
- Web 层在 pipeline 结束后统一将 task 标记为 success/failed。
- Worker 脚本在 --task-id 模式下不独立标记任务状态，避免多脚本重复覆盖。

风险点：

- 子进程管理复杂。

## 任务 05.2a：实现任务锁和重复点击防护

所属子项目：web

前置依赖：05.2

开发内容：

- 检查是否已有 running 写任务。
- 有任务运行时拒绝创建新的冲突任务。
- 前端重复点击时返回明确提示。

验收标准：

- 同一时间不会启动两个数据更新任务。
- 数据更新和筛选不会同时写数据库。
- 重复点击不会导致 SQLite 锁冲突。

风险点：

- 本地 Next.js 重启后任务状态可能残留 running。

## 任务 05.2b：实现失败重试机制

所属子项目：web

前置依赖：05.3

开发内容：

- 失败任务允许用户重新触发。
- 重试生成新的 task_id。
- 保留旧失败记录。

验收标准：

- 失败任务能重试。
- 旧错误记录不会丢失。

风险点：

- 重试时覆盖旧任务状态。

## 任务 05.3：实现任务状态查询

所属子项目：web

前置依赖：05.2

开发内容：

- `GET /api/tasks/:task_id`

验收标准：

- 前端能查询任务状态。
- 失败任务返回错误信息。

风险点：

- 任务状态没有及时更新。

## 任务 05.4：实现数据读取接口

所属子项目：web

前置依赖：03.4

开发内容：

- `GET /api/runs/latest`
- `GET /api/dashboard`
- `GET /api/recommendations`
- `GET /api/stocks/:code`
- `GET /api/watchlist`
- `GET /api/settings`
- `POST /api/settings`

验收标准：

- 默认读取最新成功 run_id。
- 没有数据时返回空状态。
- dashboard 能返回推荐数量、观察池数量、最新任务状态。
- settings 能读取和保存第一版配置。

风险点：

- today 命名误导，接口需说明读取最新成功结果。

## 任务 05.5：明确本地轻量任务边界

所属子项目：web

前置依赖：05.2

开发内容：

- 在代码注释或文档中说明第一版任务不是可靠队列。
- 任务中断后允许手动重试。
- 服务重启后需要识别残留 running 任务。

验收标准：

- 重启后不会一直显示任务运行中。
- 用户能重新运行失败或中断任务。

风险点：

- 把本地轻量任务误当成生产级队列。
