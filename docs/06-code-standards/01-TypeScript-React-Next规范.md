# 01-TypeScript-React-Next规范

## 适用范围

适用于：

```text
app/web
```

## TypeScript规范

### 类型优先

禁止使用隐式 `any`。

允许极少数显式 `unknown`，但必须在使用前做类型缩小。

优先：

```ts
type TaskStatus = "pending" | "running" | "success" | "failed" | "cancelled";
```

避免：

```ts
let status: string;
```

### 类型命名

类型和接口使用 PascalCase：

```ts
type Recommendation = {
  code: string;
  totalScore: number;
};
```

API 返回类型以 `Response` 结尾：

```ts
type DashboardResponse = {
  latestRunId: string | null;
};
```

### API返回

所有 API 返回统一结构：

```ts
type ApiSuccess<T> = {
  ok: true;
  data: T;
};

type ApiFailure = {
  ok: false;
  error: {
    code: string;
    message: string;
  };
};
```

## React规范

### 组件命名

组件使用 PascalCase：

```tsx
function RecommendationTable() {}
```

文件名和组件名保持一致：

```text
RecommendationTable.tsx
```

### 组件职责

页面组件负责组合。

业务展示组件负责展示。

数据请求逻辑放到 `lib/api/` 或页面 server 逻辑中，不在深层展示组件里到处请求。

### 状态处理

所有页面必须处理：

- loading
- empty
- error
- success

任务按钮必须处理：

- idle
- pending
- running
- success
- failed

## Next.js规范

### 目录结构

遵守 App Router 结构：

```text
app/
  dashboard/
    page.tsx
  recommendations/
    page.tsx
  stocks/[code]/
    page.tsx
  watchlist/
    page.tsx
  settings/
    page.tsx
```

共享代码：

```text
components/
lib/
types/
```

### API Routes

API Routes 只做：

- 任务创建
- 状态查询
- 数据读取
- worker 子进程启动

禁止在 API Routes 里直接做大规模因子计算。

### 字段转换

SQLite/Python 使用 `snake_case`。

前端使用 `camelCase`。

字段转换必须集中在 API 层。

禁止在页面里到处写临时字段转换。

## 格式化和Lint

使用：

- ESLint
- Prettier

提交前必须通过：

```bash
npm run lint
```

## 注释规范

TypeScript / React 代码中的注释用于解释非直观决策。

必须写注释的场景：

- API 字段从 `snake_case` 转 `camelCase` 的集中转换逻辑
- 任务轮询停止条件
- 防重复点击和任务锁逻辑
- 子进程启动和退出码处理
- 对 Next.js API Routes 的本地任务限制说明

不需要写注释的场景：

- JSX 中简单字段展示
- 普通状态变量
- 已由组件名表达清楚的组件用途

组件较复杂时，应在组件顶部用一小段注释说明它负责什么、不负责什么。

修改组件职责、API 字段或任务流时，必须同步更新相关注释。
