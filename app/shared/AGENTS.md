# AGENTS.md — app/shared

## 适用范围

本文件适用于 `app/shared` 子项目。修改配置或字段约定时必须遵守。

## 必读文档

```text
app/shared/docs/配置说明.md
app/shared/docs/字段约定.md
```

## 职责边界

```text
可以：
  公共配置（config.json）
  字段约定和状态枚举（schema.json）
  路径解析（paths.py / paths.ts）
  因子权重校验（validateFactorWeights）

禁止：
  放业务逻辑
  硬编码绝对路径
  配置值不经过 load_config / getConfigPaths 直接引用
```

## 关键文件

| 文件 | 作用 | 修改约束 |
|---|---|---|
| `config.json` | 运行时参数（推荐数量/因子权重/筛选阈值/AI 配置） | 改完需跑 `calc_factors` 验证 |
| `schema.json` | 状态枚举（run/task/watchlist/report 状态值） | 改前先更新数据库设计文档 |
| `paths.py` | Python 配置读取 + `load_config(overlay_settings)` | 支持 settings 表覆盖 |
| `paths.ts` | TypeScript 配置读取 | 与 paths.py 保持字段一致 |

## 命名约束

- `config.json`：camelCase（`recommendationLimit`、`factorWeights`）
- `schema.json`：camelCase
- Python/.ts 内部：各自语言规范（snake_case / camelCase）

## 配置覆盖规则

`load_config(overlay_settings=True)`：
1. 先读 `config.json` 作为基线
2. 再查 `settings` 表，匹配 key → 覆盖值
3. 支持 JSON 解析（数字/布尔/对象）

Worker 所有脚本必须调用 `load_config(overlay_settings=True)`。
