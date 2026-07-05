# 13-第6阶段多Agent委员会

> 2026-07 经 5 轮评估 + 参考 CrewAI / CAMEL / MetaGPT 等业界项目后确定。

## 方案概要

参考 **CAMEL 对话博弈模式**：两个 Agent 多轮辩论 → 主席裁决 → 输出最终评级。不做"各说各话"，做真正的互相质疑和纠错。

## 核心区别

| | 现有 AI 报告 | 新 Agent 委员会 |
|---|---|---|
| 角色 | 单一分析师 | 技术面 + 基本面 + 主席，3 角色独立调用 |
| 交互 | 无 | **多轮对话博弈**——互相质疑/反驳/让步 |
| 输出 | 150 字文字 | 文字 + **评级(1-5)** + **辩论过程** |
| 调用次数 | 1 次/只 | 4-5 次/只（2-3 轮 × 2 + 主席） |
| 对推荐影响 | 无 | **影响前端排序/筛选/强一致标记** |
| 成本 | ~0.003 元/天 | ~0.01 元/天（50 只） |

## Agent 角色定义

### 技术面分析师

```
你是 A 股技术分析师，专注于趋势、动量、流动性和风险指标。

输入数据：收盘价、MA20/MA60、趋势/动量/流动性/风险四因子评分

输出格式：
{
  "rating": <1-5>,
  "argument": "<100 字论据>"
}

评分标准：
5 - 趋势完美，MA 多头排列，低波动，强动量
4 - 趋势向好，一两个指标稍弱
3 - 中性，好坏参半
2 - 趋势转弱，需要警惕
1 - 趋势恶化，建议回避
```

### 基本面分析师

```
你是 A 股基本面分析师，专注于营收增长、利润质量、ROE 和估值。

输入数据：营收增速、净利润增速、ROE、行业

输出格式：
{
  "rating": <1-5>,
  "argument": "<100 字论据>"
}

评分标准：
5 - 高增长+高 ROE，基本面优秀
4 - 稳健增长，一两个指标一般
3 - 中性，有隐忧但可接受
2 - 增长乏力或盈利恶化
1 - 基本面恶化，建议回避
```

### 委员会主席

```
你是投资委员会主席，基于两位分析师的辩论结果做最终裁决。

输入：技术面分析师的多轮观点 + 基本面分析师的多轮观点

输出格式：
{
  "rating": <1-5>,
  "summary": "<150 字综合结论>",
  "consensus": "strong_agree | agree | split | disagreement"
}

strong_agree - 两方评级一致
agree - 分歧 1 分以内
split - 分歧 2 分
disagreement - 分歧 ≥3 分
```

## 辩论流程

```
对于每只推荐股票：

第1轮：
  技术面Agent 分析 → 输出 rating_tech_1 + argument
  基本面Agent 分析 → 输出 rating_fund_1 + argument

第2轮（交叉质疑）：
  技术面Agent 看到基本面Agent 的第1轮意见 → 输出 rating_tech_2 + counter
  基本面Agent 看到技术面Agent 的第1轮意见 → 输出 rating_fund_2 + counter

第3轮（达成共识/僵持）：
  如果 round2 双方评级一致 → 直接给主席
  如果仍有分歧 → 双方各做最后陈述

主席裁决：
  综合所有轮次 → 输出最终 rating + consensus 级别
```

**早停规则**：如果第 1 轮双方便一致（rating 相同），跳过第 2-3 轮，直接给主席。节省 40% 调用量。

## 对推荐的影响

| 规则评级 | AI 评级 | 共识 | 前端展示 |
|---|---|---|---|
| A | 4-5 | strong_agree | 🟢 强一致推荐 |
| A | 1-3 | disagreement | 🟡 规则偏乐观（AI 看空） |
| B | 4-5 | disagreement | 🟡 AI 看多（规则保守） |
| B | 1-3 | agree | ⚪ 一致不推荐 |

在推荐列表中新增「AI 评级」列和「共识」标记。用户可按一致性强弱筛选。

## 任务拆分

### 任务 13.1：Agent 辩论引擎

所属子项目：worker

前置依赖：07（AI 报告已完成）

**开发内容**：

- 创建 `app/worker/src/reports/agents.py`
  - `tech_analyst(code, data)` → 调用 DeepSeek，返回 rating + argument
  - `fund_analyst(code, data)` → 同上
  - `chair_agent(debate_history)` → 主席裁决
  - `debate_stock(code, data)` → 编排多轮辩论，返回最终结果
- 新增表 `agent_reports`：

```sql
CREATE TABLE agent_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  code TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
  consensus TEXT NOT NULL,
  debate_history TEXT NOT NULL,  -- JSON: 每轮的 arguments + ratings
  summary TEXT NOT NULL,
  model_name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  UNIQUE(run_id, code)
);
```

**验收标准**：

- 对推荐列表中的股票逐只生成辩论报告
- 每只输出 rating(1-5) + consensus + 辩论历史
- 早停规则生效（双方一致时跳过后续轮次）

---

### 任务 13.2：Agent 报告 Web 展示

所属子项目：web

前置依赖：13.1

**开发内容**：

- 股票详情页新增「Agent 委员会」区域（与 AI 分析并列）
- 展示：最终评级 + 共识级别 + 辩论摘要
- 可以展开查看完整辩论历史
- 推荐列表新增「AI 评级」列

**验收标准**：

- 有 agent 报告的股票展示评级和共识
- 无 agent 报告的显示「未生成 Agent 分析」
- 推荐列表可看到 AI 评级

---

### 任务 13.3：generate_report.py 集成

所属子项目：worker

前置依赖：13.1

**开发内容**：

- `generate_report.py` 支持 `--mode=committee`
- committee 模式下先跑 Agent 辩论，再跑传统 AI 报告
- Agent 失败不影响传统 AI 报告

**验收标准**：

- `--mode=committee` 正常执行
- Agent 失败时不阻塞后续步骤

## 涉及文件

| 文件 | 说明 |
|---|---|
| `app/worker/src/reports/agents.py` | Agent 辩论引擎 |
| `app/worker/src/db/schema.py` | agent_reports 表 |
| `app/worker/scripts/generate_report.py` | 加 --mode=committee |
| `app/web/app/api/stocks/[code]/route.ts` | Agent 报告 API |
| `app/web/app/stocks/[code]/page.tsx` | Agent 委员会展示 |
| `app/web/app/recommendations/page.tsx` | AI 评级列 |

## 成本估算

每只股票 4-5 次调用（早停后可降至 2-3 次），50 只 × 400 token × DeepSeek 价格 ≈ **0.01 元/天**。
