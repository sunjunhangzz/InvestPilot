# worker 子项目

## 职责

`worker` 是 Python 数据和计算层。

负责：

- 初始化数据库
- 获取 A股主板股票列表
- 获取日线行情
- 写入 SQLite
- 计算基础因子
- 生成推荐结果
- 维护观察池
- 生成基础 AI 报告

## 脚本

```text
scripts/init_db.py
scripts/update_stocks.py
scripts/update_prices.py
scripts/calc_factors.py
scripts/run_screening.py
scripts/generate_report.py
```

## 执行原则

- 所有写入必须使用事务。
- 数据源返回空数据时不能覆盖旧数据。
- 每次推荐必须生成 `run_id`。
- 每个任务必须更新 `system_tasks` 状态。
- AI 失败不能影响推荐结果。

## 数据原则

- 使用前复权日线数据。
- 推荐基于最近可用交易日。
- 缺失行情的股票跳过并记录日志。
- 停牌、ST、低流动性股票默认排除。

## Python环境

建议使用 Python 3.12。

第一版依赖预计：

```text
akshare
pandas
numpy
requests
python-dotenv
```

