# 03-SQLite和SQL规范

## 适用范围

适用于：

```text
data/a_stock_research.sqlite
```

## 命名

表名使用复数或清晰集合名：

```text
stocks
daily_prices
recommendations
watchlist
system_tasks
```

字段名使用 snake_case：

```text
trade_date
run_id
task_id
created_at
updated_at
```

## 主键

除自然唯一表外，默认使用：

```text
id INTEGER PRIMARY KEY AUTOINCREMENT
```

业务唯一字段必须加唯一约束或唯一索引。

例如：

```text
run_id
task_id
code + trade_date
```

## 必备字段

业务结果表必须有：

```text
created_at
```

可变状态表必须有：

```text
updated_at
```

推荐相关表必须有：

```text
run_id
trade_date
```

## 写入

必须使用参数化 SQL。

禁止字符串拼接 SQL。

必须使用事务。

空数据不能覆盖旧数据。

## 查询

推荐页默认读取最新成功 `run_id`。

股票详情按需读取，不一次性返回全量数据。

大查询必须有索引支持。

## 迁移

第一版可以用 `init_db.py` 创建表。

任何 schema 变更必须同步更新：

- `数据库设计.md`
- `init_db.py`
- schema 校验脚本
- API 类型

