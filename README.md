# A股AI投研系统

## 项目定位

这是一个面向个人投资者的 A股主板趋势股投研辅助系统。

系统目标是在 A股主板股票中筛选出 10-50 只稳健型趋势候选股票，生成投资参考报告，辅助人工判断。

系统偏好稳健收益，不追求高频交易、极端短线、题材连板和高风险博弈。

本系统不做自动交易，不连接券商账户，不直接下单。

## 核心思想

系统主旨为：

```text
短、快、准
```

- 短：关注 1-4 周观察和持仓周期，不做长期价值投资系统。
- 快：每天收盘后快速完成数据更新、筛选和报告生成，不做盘中高频追涨。
- 准：第一版通过主板股票池、趋势确认、风险过滤和基础因子降低误判；后续再引入多维度数据和 AI 多 Agent 评审。

系统风格：

```text
稳健收益优先，趋势确认优先，风险过滤优先。
```

## 长期系统设计

长期整体采用三级漏斗模式：

```text
A股主板股票池
  ↓
一级漏斗：主板趋势策略筛选，保留约 20%
  ↓
二级漏斗：稳健 Alpha 多因子筛选，再保留约 20%
  ↓
三级漏斗：AI 专家委员会评审
  ↓
每日输出 10-50 只稳健趋势投资参考股票
```

## 技术路线

第一版 MVP 采用：

```text
前端网站：Next.js + TypeScript
数据采集：Python + AkShare
数据库：SQLite，后续可升级 DuckDB / PostgreSQL
AI 模型：DeepSeek API，后续可切换通义千问、智谱 GLM、Kimi、OpenAI
报告格式：Markdown / HTML
```

第一版只实现基础 AI 解释报告，不实现真正多 Agent 专家委员会。多 Agent、策略优化和 Agent 自我复盘属于后续实验层能力。

## 目录结构

```text
A股AI投研系统/
  app/          项目代码目录
    web/        Next.js网站和API Routes
    worker/     Python数据采集和因子计算
    shared/     公共配置和字段约定
    api/        后续独立后端预留目录
  data/         本地数据库、缓存数据、行情数据
  reports/      每日生成的AI投研报告
  docs/         项目文档、策略说明、使用说明
  backups/      重要配置和数据备份
  README.md     项目总说明
```

## 文档说明

```text
docs/README.md                         文档总索引
docs/00-overview/项目规划.md            项目阶段规划
docs/00-overview/使用原则.md            投资和系统使用边界
docs/01-product/MVP开发需求.md          第一版必须开发的最小可用系统
docs/01-product/产品蓝图.md             长期完整系统设计
docs/01-product/分阶段路线图.md         分阶段交付计划
docs/02-implementation/第一版实现方案.md 第一版工程结构和实现原则
docs/02-implementation/架构设计/       全栈架构、数据流、任务流和扩展边界
docs/02-implementation/开发计划.md       第一版开发顺序、里程碑和验收标准
docs/02-implementation/开发任务拆分/     可执行任务包
docs/02-implementation/数据库设计.md     SQLite表结构和写入规则
docs/02-implementation/日志体系.md       任务日志、本地日志和日志收集规则
docs/03-operations/任务机制.md           长任务、run_id、task_id和失败处理
docs/03-operations/本地启动.md           本机开发环境启动步骤
docs/04-experiments/实验模块管理.md      多Agent、优化算法等高级模块的影子运行规则
docs/05-standards/                      开发规范、命名规范、日志规范、配置和安全规范
docs/06-code-standards/                 代码层语言规范、测试规范和安全编码规范
docs/06-code-standards/07-Code-Review规范.md 每次代码修改后的强制 review 规范
```

## 本地启动

启动步骤见：

```text
docs/03-operations/本地启动.md
```

## MVP 第一阶段目标

第一阶段先实现一个本地可运行版本：

1. 获取 A股基础行情数据。
2. 本地保存股票基础数据和日线数据。
3. 建立 A股主板股票池，剔除 ST、退市风险、停牌、流动性过低和财务异常股票。
4. 实现一级主板趋势策略筛选。
5. 实现二级稳健因子打分。
6. 输出候选股票列表。
7. 接入 AI 生成简版投研报告。
8. 在网页中查看每日候选股和报告。

## 风险边界

本系统只用于投资研究和个人决策辅助。

系统输出不构成投资建议，不保证收益。任何买卖决策都需要人工判断，并自行承担风险。
