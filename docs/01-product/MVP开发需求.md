# MVP开发需求

## 项目定位

第一版系统定位：

```text
A股主板稳健趋势股 AI 投研助手
```

系统只做投资参考，不做自动交易，不连接券商账户，不自动下单。

第一版目标是先跑通最小可用链路：

```text
数据获取 → 主板股票池 → 基础筛选 → 因子评分 → 推荐列表 → 观察池 → AI解释报告 → 网页展示
```

## MVP边界

第一版只做核心层，保证系统每天能稳定产出结果。

必须实现：

- A股主板股票池
- 日线行情数据
- 基础股票信息
- 趋势因子
- 动量因子
- 流动性因子
- 风险扣分
- 10-50 只候选股票
- 推荐观察池
- 每只推荐股票至少跟踪 5 个交易日
- 基础 AI 解释报告
- 本地网页展示
- 基础任务日志和错误提示

第一版暂不实现：

- 自动交易
- 用户登录
- 多用户权限
- 实时行情
- 微信推送
- 自动定时任务
- 复杂回测
- 财报深度分析
- 公告和重大合同自动解析
- 新闻、情绪、政策自动评分
- 真正多 Agent 并行讨论
- Agent 自我优化
- 策略自动调参
- 贝叶斯优化、遗传算法等复杂优化算法

这些能力保留在产品蓝图和后续路线图中。

## 核心页面

MVP 第一版需要 5 个页面：

1. 首页仪表盘
2. 今日推荐
3. 股票详情
4. 观察池
5. 系统设置

首页仪表盘展示：

- 数据更新时间
- 今日候选股票数量
- A类重点观察数量
- B类普通观察数量
- 观察池股票数量
- 最近一次任务状态

今日推荐展示：

- 股票代码
- 股票名称
- 行业
- 最新收盘价
- 20日涨幅
- 60日涨幅
- 成交额
- 趋势评分
- 动量评分
- 流动性评分
- 风险评分
- 总评分
- AI评级
- 推荐理由
- 风险标签

股票详情展示：

- 股票基础信息
- 近 60 日价格走势（蜡烛图，可切换日K/周K/月K）
- 成交量走势
- 因子评分
- 入选原因
- 风险提示
- AI解释报告

观察池展示：

- 首次推荐日期
- 已跟踪天数
- 当前状态
- 推荐后收益
- 推荐后最大回撤
- 是否跌破趋势线
- 退出原因

系统设置支持：

- 推荐股票数量
- 是否启用 AI 分析
- AI Provider 配置
- API Key 配置
- 手动更新数据
- 手动运行筛选
- 手动生成报告

## 技术栈

第一版技术栈：

```text
前端：Next.js + TypeScript + Tailwind CSS
图表：ECharts
数据脚本：Python + AkShare
数据库：SQLite
AI：DeepSeek API 优先，保留 Provider 抽象
```

## 后端接口

核心接口：

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

第一版任务执行方式：

```text
前端点击按钮 → Next.js API 创建任务并返回 task_id → 后台调用 Python 脚本 → 写入 SQLite → 前端轮询任务状态 → 前端读取结果
```

## Python脚本

第一版脚本：

```text
scripts/init_db.py          初始化数据库
scripts/update_stocks.py   更新股票基础信息
scripts/update_prices.py   更新日线行情
scripts/calc_factors.py    计算基础因子
scripts/run_screening.py   执行主板趋势筛选
scripts/update_watchlist.py 更新观察池状态
scripts/generate_report.py 生成基础AI报告
```

## 数据库表

第一版核心表：

- stocks
- daily_prices
- runs
- factors
- recommendations
- watchlist
- ai_reports
- system_tasks
- settings

本节只描述 MVP 需要哪些核心表和关键字段。

具体字段、索引和写入规则以以下文档为准：

```text
docs/02-implementation/数据库设计.md
```

stocks 表：

```text
code
name
market
board
industry
is_st
is_active
list_date
updated_at
```

daily_prices 表：

```text
id
code
trade_date
open
high
low
close
volume
amount
pct_change
turnover
```

runs 表：

```text
id
run_id
trade_date
run_type
status
started_at
finished_at
error_message
created_at
```

factors 表：

```text
id
run_id
code
trade_date
trend_score
momentum_score
liquidity_score
volatility_score
risk_score
total_score
```

recommendations 表：

```text
id
run_id
trade_date
code
rank
rating
total_score
reason
risk_tags
first_recommended_date
last_recommended_date
tracking_days
created_at
```

watchlist 表：

```text
id
code
first_recommended_date
last_recommended_date
status
entry_price
latest_price
tracking_days
min_tracking_days
max_tracking_days
exit_reason
created_at
updated_at
```

ai_reports 表：

```text
id
run_id
trade_date
code
report_type
content
model_name
created_at
```

system_tasks 表：

```text
id
task_id
run_id
task_name
status
started_at
finished_at
error_message
created_at
```

settings 表：

```text
key
value
updated_at
```

必要索引：

```text
daily_prices(code, trade_date)
factors(trade_date, total_score)
recommendations(trade_date, rank)
watchlist(status, tracking_days)
ai_reports(trade_date, code)
system_tasks(task_name, created_at)
```

## 筛选规则

默认排除：

- 非主板股票
- ST 和退市风险股票
- 停牌股票
- 上市不足 180 天股票
- 近 20 日日均成交额过低股票
- 股价过低股票
- 短期涨幅过高股票

趋势条件：

```text
收盘价 > MA20
收盘价 > MA60
MA20 > MA60
近20日收益率 > 0
近60日收益率 > 0
```

第一版总分：

```text
总分 =
  35% 趋势评分
+ 25% 动量评分
+ 20% 流动性评分
+ 20% 风险控制评分
```

输出分层：

- A类：重点观察，前 10-20 只
- B类：普通观察，后 20-30 只
- C类：暂不展示

## 观察池规则

推荐股票默认进入观察池。

观察池规则：

- 最少跟踪 5 个交易日。
- 未触发风险退出条件时，不因单日评分下降立即移出。
- 连续多个交易日评分下降，可以从 A类降到 B类。
- 退出观察必须记录原因。

观察状态：

```text
active      正在观察
hold        持续观察
downgraded  降级观察
exit        退出观察
blocked     风险阻断
```

退出条件：

- 跌破 MA20 或 MA60。
- 短期涨幅过热且风险收益比下降。
- 流动性明显恶化。
- 出现明确风险事件。
- 已达到最大观察周期且趋势未继续改善。

## AI报告

第一版不做真正多 Agent。

第一版 AI 报告采用单模型结构化提示词，模拟多个视角：

- 趋势观点
- 流动性观点
- 风险观点
- 综合结论

AI 输出只做解释和排雷，不直接决定买卖。

没有 API Key 时，系统仍应能输出基础推荐列表，只是不生成 AI 报告。

## 测试重点

数据测试：

- 无网络时更新失败是否提示
- AkShare 接口异常是否记录日志
- 股票数据缺失是否跳过
- ST 股票是否被排除
- 非主板股票是否被排除

筛选测试：

- MA20、MA60 计算是否正确
- 总评分排序是否正确
- 推荐数量是否控制在 10-50
- 风险扣分是否生效

观察池测试：

- 推荐股票至少跟踪 5 个交易日
- 观察池状态流转正确
- 退出观察需要记录原因

AI测试：

- 没配置 API Key 时是否提示
- API 调用失败时是否不影响基础推荐
- AI 报告为空时是否可重试

前端测试：

- 首页无数据状态
- 推荐列表加载状态
- 股票详情不存在
- 观察池为空
- 设置保存失败
