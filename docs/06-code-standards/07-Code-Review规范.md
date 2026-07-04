# 07-Code Review规范

## 目标

每次代码修改完成后，必须进行 Code Review。

本项目的 Code Review 目标：

- 发现缺陷
- 保证架构边界
- 保证数据正确
- 保证任务可追踪
- 保证日志可定位
- 保证安全边界
- 保证文档同步

## 参考来源

本规范参考：

- Google Engineering Practices: Code Review
- GitHub Pull Request Reviews
- OWASP Code Review Guide

参考链接：

- https://google.github.io/eng-practices/review/reviewer/
- https://google.github.io/eng-practices/review/developer/
- https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews
- https://owasp.org/www-project-code-review-guide/

## 强制要求

每次修改代码后，必须执行一次自我 Code Review。

如果修改涉及以下内容，必须重点 review：

- 数据库 schema
- 数据采集
- 因子计算
- 推荐逻辑
- 观察池状态
- API Routes
- 任务状态流转
- 日志
- AI 调用
- 配置和密钥
- 安全边界

## Review顺序

建议按这个顺序 review：

```text
1. 需求是否满足
2. 架构边界是否正确
3. 数据正确性
4. 错误处理和日志
5. 安全性
6. 可维护性
7. 测试和验证
8. 文档和注释
```

## 通用检查清单

### 需求

- 是否只实现当前任务需要的功能？
- 是否提前实现了后续阶段能力？
- 是否偏离 MVP 边界？
- 是否符合任务拆分文档的验收标准？

### 架构

- web 是否只负责页面、API Routes 和任务触发？
- worker 是否只负责数据、计算和报告？
- shared 是否仍然只保存配置和约定？
- 是否绕过 shared 硬编码路径或状态？
- 是否把后续增强层或实验层能力放进了第一版主链路？

### 数据

- 是否正确使用 `run_id`？
- 是否正确使用 `task_id`？
- 是否正确使用 `trade_date`？
- 是否存在未来函数？
- 空数据是否会覆盖旧数据？
- 重复运行是否会破坏历史结果？
- 非交易日是否使用最近交易日？

### 数据库

- SQL 是否参数化？
- 写入是否使用事务？
- 是否可能造成 SQLite 写锁？
- 索引是否支持主要查询？
- schema 变更是否同步更新文档和校验？

### API

- 长任务是否立即返回 `task_id`？
- 是否避免等待 Python 长时间同步完成？
- 是否有任务锁防重复点击？
- 子进程退出码是否被处理？
- API 返回格式是否统一？
- snake_case 到 camelCase 是否集中转换？

### 日志

- 任务失败是否写入 `system_tasks`？
- 详细错误是否写入 `data/logs/`？
- 日志是否包含 `task_id`、`run_id`、`module`？
- 是否避免把 API Key 或 `.env` 写入日志？
- 错误摘要是否足够让前端展示？

### AI

- AI 失败是否不影响基础推荐？
- AI 输入是否是结构化摘要？
- 是否避免传入全量行情或敏感信息？
- 是否记录模型名称和调用状态？
- token 使用是否受控？

### 安全

- API Key 是否只在 `.env`？
- 是否有密钥进入代码、文档、日志、报告？
- API Routes 是否只允许调用白名单 worker 脚本？
- 是否存在拼接 shell 命令？
- SQL 是否避免注入风险？

### 可维护性

- 函数是否过长？
- 命名是否清晰？
- 是否有重复逻辑可以适度抽取？
- 是否产生不必要抽象？
- 注释是否解释了必要业务规则？
- 是否有过期注释？

### 测试和验证

- 是否运行了可用的验证命令？
- 如果不能运行，是否说明原因？
- 是否覆盖异常场景？
- 是否检查无 API Key 场景？
- 是否检查数据为空场景？

### 文档

- 表结构变更是否更新 `数据库设计.md`？
- API 变更是否更新 API 文档？
- 任务流程变更是否更新 `任务机制.md`？
- 规范变化是否更新 standards？
- 注释是否和代码同步？

## Review输出格式

每次完成代码修改后，最终回复中必须包含 Code Review 摘要。

格式：

```text
Code Review:
- 架构边界：通过 / 有问题
- 数据一致性：通过 / 有问题
- 错误处理和日志：通过 / 有问题
- 安全：通过 / 有问题
- 验证：已运行 xxx / 未运行，原因 xxx
```

如果发现问题，必须优先列出问题：

```text
发现的问题：
1. 文件:行号 - 问题说明
2. 文件:行号 - 问题说明
```

## 禁止事项

禁止在发现以下问题时直接宣称完成：

- 任务失败但没有日志
- 数据库写入没有事务
- 缺少 `run_id`
- 缺少 `task_id`
- API Key 可能泄露
- AI 失败会阻塞推荐
- 文档与代码明显不一致

## 与自动化工具关系

Code Review 不能替代测试。

测试也不能替代 Code Review。

两者都需要：

- lint 检查风格和部分错误
- test 检查行为
- review 检查架构、边界、可维护性和安全性

