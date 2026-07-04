# AGENTS.md

## 适用范围

本文件适用于整个 `A股AI投研系统` 项目。

后续开发、修改、排错、重构、测试时，必须先遵守本文件，再参考 `docs/` 下的详细规范。

## 项目边界

本项目是 A股主板稳健趋势股 AI 投研助手。

第一版只做投资研究辅助，不做自动交易，不连接券商账户，不自动下单。

禁止把 AI 输出作为直接买卖指令。AI 只做解释、排雷和辅助分析。

## 必读文档

开发前必须优先阅读：

```text
docs/README.md
docs/01-product/MVP开发需求.md
docs/02-implementation/开发计划.md
docs/02-implementation/架构设计/README.md
docs/02-implementation/开发任务拆分/README.md
docs/05-standards/README.md
docs/06-code-standards/README.md
```

如果修改具体子项目，还必须阅读对应目录：

```text
app/web/docs/
app/worker/docs/
app/shared/docs/
app/api/docs/
```

## 开发顺序

第一版按主链路顺序推进：

```text
shared配置 → 数据库 → worker数据层 → worker筛选层 → 观察池 → API任务层 → 前端展示 → AI报告 → 联调
```

不要跳过数据层直接做页面，不要在基础推荐没跑通前实现多 Agent、微信推送、自动调参等后续能力。

## 架构边界

```text
app/web
  页面、Next.js API Routes、任务创建、任务状态查询、读取 SQLite

app/worker
  Python 数据采集、因子计算、推荐生成、观察池维护、AI报告

app/shared
  公共配置、字段约定、状态枚举、路径约定

app/api
  后续独立后端预留，第一版不开发
```

禁止在 `web` 中实现因子计算。

禁止在 `worker` 中实现页面逻辑。

禁止绕过 `shared` 硬编码数据库路径、报告路径、因子权重和状态枚举。

## 代码规范

必须遵守：

```text
docs/05-standards/
docs/06-code-standards/
```

核心约束：

- Python 文件、函数、变量使用 `snake_case`
- SQLite 表和字段使用 `snake_case`
- TypeScript 变量和函数使用 `camelCase`
- React 组件使用 `PascalCase`
- 所有任务必须有 `task_id`
- 所有推荐运行必须有 `run_id`
- 所有交易数据必须有 `trade_date`
- SQL 必须参数化
- 长任务必须异步执行并可追踪

## 注释规范

注释必须及时写入，并和代码同步更新。

必须写注释的场景：

- 策略筛选规则
- 因子计算边界
- 避免未来函数的特殊处理
- AkShare 字段兼容
- SQLite 事务和写锁规避
- AI 输入压缩或裁剪
- 任务轮询停止条件
- 任务锁和防重复点击
- 日志脱敏逻辑

禁止保留过期注释，禁止用注释解释坏命名，禁止注释掉大段废弃代码。

## 日志规范

必须遵守：

```text
docs/02-implementation/日志体系.md
docs/06-code-standards/04-日志代码规范.md
```

任务失败必须写入 `system_tasks`。

详细错误必须写入：

```text
data/logs/
```

日志禁止写入：

- API Key
- 密码
- `.env` 完整内容
- 任何敏感密钥

## 数据库规范

必须遵守：

```text
docs/02-implementation/数据库设计.md
docs/06-code-standards/03-SQLite和SQL规范.md
```

写入 SQLite 必须使用事务。

同一时间只允许一个 worker 写数据库。

数据源返回空数据时不能覆盖旧数据。

每次推荐必须新建 `run_id`。

默认展示最近一次 `success` 状态的 `run_id`。

## 任务规范

必须遵守：

```text
docs/03-operations/任务机制.md
docs/02-implementation/架构设计/04-数据流和任务流.md
```

API Routes 负责：

- 创建 `task_id`
- 写入 `pending`
- 启动 worker 子进程

worker 负责：

- 写入 `running`
- 写入 `success` 或 `failed`
- 写入错误摘要和详细日志

如果 worker 异常退出且没有更新状态，API 需要根据子进程退出码把任务标记为 `failed`。

## 安全规范

API Key 只能放在 `.env`。

禁止提交：

```text
.env
data/*.sqlite
data/cache/
data/raw/
data/logs/
reports/
.venv/
node_modules/
```

API Routes 调 worker 时，只允许调用白名单脚本，参数必须校验，不允许前端传任意 shell 命令。

## 文档同步

如果改动涉及以下内容，必须先更新文档，再改代码：

- 表结构
- API 接口
- 任务流程
- 因子逻辑
- 推荐规则
- 日志格式
- 配置字段
- 安全边界

文档和代码冲突时，先确认需求，再更新文档，最后修改代码。

## 验证要求

每个任务完成后，必须按对应任务拆分文档里的验收标准检查。

优先形成这些命令：

```bash
python scripts/health_check.py
python scripts/run_pipeline.py
npm run lint
npm run dev
```

如果暂时不能运行测试或验证，必须在最终说明中明确原因。

## Code Review 要求

每次代码修改完成后，必须进行自我 Code Review。

必须遵守：

```text
docs/06-code-standards/07-Code-Review规范.md
```

Code Review 必须检查：

- 是否满足当前任务需求
- 是否违反架构边界
- 是否缺少 `run_id`、`task_id`、`trade_date`
- 是否存在未来函数
- 是否有事务和 SQLite 写锁风险
- 是否有日志和错误处理
- 是否有 API Key、`.env`、敏感信息泄露风险
- 是否同步更新文档和注释
- 是否运行了必要验证

每次最终回复必须包含 Code Review 摘要。
