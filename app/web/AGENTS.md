# AGENTS.md — app/web

## 适用范围

本文件适用于 `app/web` 子项目。开发前必须遵守本文件 + 根目录 `AGENTS.md`。

## 必读文档

```text
app/web/docs/开发指南.md
app/web/docs/API约定.md
app/web/docs/页面设计.md
docs/05-standards/01-TypeScript和Web规范.md
docs/06-code-standards/01-TypeScript-React-Next规范.md
```

## 职责边界

```text
可以做的：
  页面展示、Next.js API Routes、任务创建、任务状态查询
  读取 SQLite（只读，通过 better-sqlite3）
  调用 worker 子进程（白名单）

禁止做的：
  因子计算、数据采集、大规模循环计算
  worker 脚本逻辑、数据库写入（除 system_tasks 标记）
```

## 命名约束

- React 组件：`PascalCase`，文件名一致
- TypeScript 变量/函数：`camelCase`
- API 返回字段：`camelCase`
- 字段转换集中在 `field-mapper.ts`，禁止页面内零散转换

## API 约束

- 统一返回 `{ ok: true, data }` 或 `{ ok: false, error: { code, message } }`
- 长任务立即返回 `taskId`，不可同步等待
- 子进程使用 `worker-launcher.ts` 白名单，参数数组不拼 shell
- 每个页面处理 loading / empty / error 三态

## 数据库约束

- 只读连接（`Database(dbPath, { readonly: true })`）
- 仅 `task-lock.ts` 可写 `system_tasks`（任务状态标记）

## Code Review 要点

- 是否逐项核对了 MVP 需求文档中的字段清单？（页面验收逐项核对）
- 是否有 loading / empty / error 状态？
- snake_case → camelCase 是否统一？
- 是否引入 ECharts SSR 问题？（必须 `dynamic({ ssr: false })`）
