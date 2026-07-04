# shared 子项目

## 职责

`shared` 存放前端、API 和 Python worker 共用的配置和约定。

包括：

- 数据库路径
- 报告目录
- 推荐数量
- 因子权重
- 风险阈值
- AI Provider 配置
- 字段约定

## 文件

```text
config.json
schema.json
```

## 原则

- TS 和 Python 都从这里读取公共配置。
- 不在代码里硬编码数据库路径。
- 字段命名保持一致。
- 策略参数修改要有记录。

