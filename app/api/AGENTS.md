# AGENTS.md — app/api

## 适用范围

本文件适用于 `app/api` 预留目录。**第一版不开发。**

## 职责边界

```text
当前状态：预留
用途：后续独立后端
状态：禁止开发
说明：第一版所有 API 逻辑在 app/web 的 API Routes 中实现
```

## 必读文档

```text
app/api/docs/后端拆分预案.md
```

## 激活条件

当以下条件之一满足时，可评估激活此子项目：

- Next.js API Routes 成为性能瓶颈
- 需要独立后端服务（定时任务/消息队列/长连接）
- Web 和 Worker 需要独立部署

激活前必须先更新架构设计文档，确认与 web / worker 的边界划分。
