# AGENTS.md — app/worker

## 适用范围

本文件适用于 `app/worker` 子项目。开发前必须遵守本文件 + 根目录 `AGENTS.md`。

## 必读文档

```text
app/worker/docs/开发指南.md
app/worker/docs/数据采集.md
app/worker/docs/因子与筛选.md
app/worker/docs/观察池规则.md
docs/05-standards/02-Python和Worker规范.md
docs/06-code-standards/02-Python规范.md
docs/02-implementation/数据库设计.md
docs/02-implementation/日志体系.md
```

## 职责边界

```text
可以做的：
  数据采集（AkShare）、数据清洗、数据入库
  因子计算、推荐生成、观察池维护
  AI 报告生成（DeepSeek API）
  写 SQLite（事务包裹）

禁止做的：
  页面展示、用户交互、权限系统
  长期服务进程、Web 框架
```

## 命名约束

- 文件/函数/变量：`snake_case`
- 类：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`

## 三要素（不可遗漏）

- 所有任务：`task_id`
- 所有推荐：`run_id`
- 所有交易数据：`trade_date`

## SQL 约束

- 全部参数化（禁止 f-string / % 拼接）
- 写入必须 `with connection:` 包裹事务
- 空数据不覆盖旧数据（UPSERT ON CONFLICT）
- 单只股票失败不中断整个批次

## 任务模式

- `--task-id` 模式（Web 调用）：resolve_task_id 解析，脚本不标记 success/failed
- 独立模式（命令行调用）：脚本管理完整任务生命周期

## 日志约束

- `system_tasks` 保存任务摘要（`error_message` ≤ 300 字符）
- `data/logs/*.log` 保存 JSON Lines 详细日志
- 禁写 API Key / 密码 / 敏感信息

## Code Review 要点

- 是否存在未来函数？（`rows[-window:]` 切片，`WHERE trade_date <= :date`）
- 是否遗漏 run_id / task_id / trade_date？
- SQL 是否参数化？
- AI 失败是否阻断推荐？（必须不影响）
