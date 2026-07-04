# 文档索引

## 阅读顺序

建议按这个顺序阅读：

1. `00-overview/`
2. `01-product/`
3. `02-implementation/`
4. `03-operations/`
5. `04-experiments/`
6. `05-standards/`
7. `06-code-standards/`
8. `app/*/docs/`

## 00-overview

项目总览和使用边界。

```text
00-overview/项目规划.md
00-overview/使用原则.md
```

适合了解项目目标、原则、风险边界。

## 01-product

产品需求、长期蓝图和阶段路线。

```text
01-product/MVP开发需求.md
01-product/产品蓝图.md
01-product/分阶段路线图.md
```

适合确认第一版做什么、长期做什么、每个阶段怎么推进。

## 02-implementation

第一版工程实现方案和数据库设计。

```text
02-implementation/第一版实现方案.md
02-implementation/开发计划.md
02-implementation/开发任务拆分/
02-implementation/架构设计/
02-implementation/数据库设计.md
02-implementation/日志体系.md
```

适合开发前确认工程结构、架构边界、开发顺序、数据表、字段、写入规则和日志体系。

## 03-operations

任务运行、长任务、失败处理和运行状态。

```text
03-operations/任务机制.md
03-operations/本地启动.md
```

适合实现任务执行、状态轮询、错误重试，以及本机启动开发环境时查看。

## 04-experiments

高级能力和实验模块管理。

```text
04-experiments/实验模块管理.md
```

适合多 Agent、优化算法、自动调参等模块进入开发前查看。

## 05-standards

开发规范、命名规范、日志规范、配置和安全规范。

```text
05-standards/00-通用规范.md
05-standards/01-TypeScript和Web规范.md
05-standards/02-Python和Worker规范.md
05-standards/03-数据库规范.md
05-standards/04-日志规范.md
05-standards/05-配置和安全规范.md
05-standards/06-文档维护规范.md
```

适合写代码前确认统一规范。

## 06-code-standards

代码层面的语言和工具规范。

```text
06-code-standards/00-代码规范总则.md
06-code-standards/01-TypeScript-React-Next规范.md
06-code-standards/02-Python规范.md
06-code-standards/03-SQLite和SQL规范.md
06-code-standards/04-日志代码规范.md
06-code-standards/05-测试和质量工具规范.md
06-code-standards/06-安全编码规范.md
06-code-standards/07-Code-Review规范.md
```

适合实际写代码前查看。

## 子项目文档

子项目文档保留在各自目录下。

```text
app/web/docs/
app/worker/docs/
app/shared/docs/
app/api/docs/
```

这些文档是模块局部开发说明，不移动到顶层 docs，避免脱离代码上下文。
