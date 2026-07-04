# 03-shared架构

## 定位

`app/shared` 是 TS 和 Python 共同遵守的配置和约定层。

它不是业务模块，不做计算。

## 文件

```text
app/shared/
  config.json
  schema.json
  README.md
  docs/
```

## config.json

保存运行配置：

- 数据库路径
- 报告路径
- 推荐数量
- 最小跟踪天数
- 最大跟踪天数
- 因子权重
- 过滤阈值
- AI 配置

## schema.json

保存枚举约定：

- runStatus
- runType
- watchlistStatus
- recommendationRating
- reportType

## 命名约定

数据库和 Python 使用：

```text
snake_case
```

TypeScript 和前端使用：

```text
camelCase
```

转换应该集中在 API 层处理，避免页面里到处手动转换。

## 路径原则

不要在代码里硬编码：

- 数据库路径
- 报告路径
- 缓存路径
- 日志路径

统一从 `config.json` 读取。

`config.json` 中的相对路径统一相对项目根目录解析。

项目根目录是：

```text
A股AI投研系统/
```

例如：

```json
{
  "databasePath": "data/a_stock_research.sqlite",
  "reportsPath": "reports",
  "logsPath": "data/logs"
}
```

web 和 worker 必须先定位项目根目录，再解析这些路径。

禁止从当前工作目录直接拼接相对路径，因为 Next.js、Python 脚本和测试的工作目录可能不同。

## 版本演进

后续如果策略参数开始优化，需要增加：

- strategy_version
- factor_weight_version
- prompt_version

第一版先不做版本系统，但配置变更需要谨慎。
