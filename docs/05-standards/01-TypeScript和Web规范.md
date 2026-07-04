# 01-TypeScript和Web规范

## 适用范围

适用于 `app/web`。

## 职责边界

web 可以：

- 展示页面
- 创建任务
- 查询任务状态
- 读取 SQLite 数据
- 调用 worker 子进程

web 不应该：

- 直接实现因子计算
- 直接采集数据
- 做大量循环计算
- 等待长任务同步完成

## 命名规范

- React 组件：`PascalCase`
- hooks：`useXxx`
- 普通变量：`camelCase`
- API 返回给前端字段：`camelCase`
- 数据库字段转换集中处理，不在页面里零散转换。

## API返回格式

成功：

```json
{
  "ok": true,
  "data": {}
}
```

失败：

```json
{
  "ok": false,
  "error": {
    "code": "TASK_FAILED",
    "message": "任务执行失败"
  }
}
```

## 页面状态

所有页面必须处理：

- loading
- empty
- error
- success

所有任务按钮必须处理：

- idle
- pending
- running
- success
- failed

## 长任务规范

禁止：

```text
前端请求一直等待 Python 脚本执行完成
```

必须：

```text
API 创建 task_id
前端轮询 task 状态
任务结束后刷新数据
```

## UI原则

- 推荐列表只展示核心字段。
- 复杂信息放到股票详情页。
- 图表第一版只做必要图表。
- 错误提示要能指导用户下一步操作。
- 不做营销式页面，不做复杂大屏。

