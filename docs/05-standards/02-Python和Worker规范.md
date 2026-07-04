# 02-Python和Worker规范

## 适用范围

适用于 `app/worker`。

## 职责边界

worker 负责：

- 数据采集
- 数据清洗
- 数据入库
- 因子计算
- 推荐生成
- 观察池维护
- AI 报告生成

worker 不负责：

- 页面展示
- 用户交互
- 权限系统
- 长期服务进程

## 脚本规范

每个脚本必须可以单独运行。

脚本放在：

```text
app/worker/scripts/
```

业务逻辑放在：

```text
app/worker/src/
```

不要把所有逻辑堆在脚本入口里。

## 运行参数

脚本应支持：

```text
--task-id
--run-id
--trade-date
```

没有传入时，可以根据任务类型生成默认值。

## 数据写入

- 写数据库必须使用事务。
- 空数据不能覆盖旧数据。
- 批量任务中单只股票失败不能中断整个批次。
- 失败股票必须记录日志。
- 写入前必须校验关键字段。

## 返回码

- 成功返回 `0`
- 失败返回非 `0`

失败时：

- 写 `system_tasks.failed`
- 写 `error_message` 摘要
- 写详细日志

## Python命名

- 文件名：snake_case
- 函数名：snake_case
- 变量名：snake_case
- 类名：PascalCase
- 常量：UPPER_SNAKE_CASE

## 依赖规范

依赖写入：

```text
app/worker/requirements.txt
```

第一版依赖应保持克制。

不引入大型机器学习框架，除非后续阶段明确需要。

