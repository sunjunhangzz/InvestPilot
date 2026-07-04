# 02-worker架构

## 定位

`app/worker` 是 Python 数据和计算层。

它负责所有重计算和外部数据采集。

## 目录结构

```text
app/worker/
  scripts/
    init_db.py
    update_stocks.py
    update_prices.py
    calc_factors.py
    run_screening.py
    update_watchlist.py
    generate_report.py
    health_check.py
    run_pipeline.py
  src/
    config/
    db/
    data_sources/
    factors/
    screening/
    watchlist/
    reports/
    tasks/
    loggers/
    utils/
  tests/
```

`src/` 可以在正式写代码时创建。

说明：日志工具目录使用 `loggers/`，避免和 Python 标准库 `logging` 同名导致导入遮蔽。

## 脚本职责

```text
init_db.py
  创建数据库表和索引

update_stocks.py
  获取股票列表，写入 stocks

update_prices.py
  获取日线行情，写入 daily_prices

calc_factors.py
  计算基础因子，写入 factors

run_screening.py
  生成 recommendations

update_watchlist.py
  维护 watchlist

generate_report.py
  生成 AI 报告，写入 ai_reports

health_check.py
  检查环境、依赖、数据库和表结构

run_pipeline.py
  串行跑完整主流程
```

## worker运行原则

- 每个脚本都可以单独运行。
- 每个脚本都读取 shared 配置。
- 每个脚本都写 system_tasks 状态。
- 每个脚本都写本地日志。
- 每个写入任务都使用事务。
- 空数据不覆盖旧数据。
- 单只股票失败不影响整个批次。
- 失败返回非 0 exit code。
- 详细错误写入 `data/logs/`。

## 数据源边界

第一版只用 AkShare。

采集范围：

- 股票基础列表
- 日线行情

不采集：

- 实时盘口
- 分钟线
- 财报
- 新闻
- 情绪
- 政策

这些属于后续增强层。

## 因子边界

第一版因子：

- 趋势
- 动量
- 流动性
- 风险

第一版不做：

- 多因子机器学习
- 行业中性化
- 财报因子
- 新闻情绪因子
