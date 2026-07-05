# 13-第6阶段多Agent委员会

> 2026-07 经 5 轮评估 + 参考 CrewAI / CAMEL / MetaGPT 等业界项目后确定。

## 方案概要

参考 **CAMEL 对话博弈模式**：两个 Agent 多轮辩论 → 主席裁决 → 输出最终评级。不做"各说各话"，做真正的互相质疑和纠错。

## 核心区别

| | 现有 AI 报告 | 新 Agent 委员会 |
|---|---|---|
| 角色 | 单一分析师 | **5 角色**：技术面/基本面/风险官/估值师/行业对比 + 主席 |
| 交互 | 无 | **多轮对话博弈**——5 人同时发表意见，互相质疑/反驳 |
| 输出 | 150 字文字 | 文字 + **评级(1-5)** + **辩论过程** |
| 调用次数 | 1 次/只 | 10-11 次/只（2 轮 × 5 + 主席） |
| 对推荐影响 | 无 | **影响前端排序/筛选/强一致标记** |
| 成本 | ~0.003 元/天 | ~0.02 元/天（50 只） |

## Agent 角色定义（5 角色，全部在第一轮参与）

### 1. 技术面分析师
```
你是A股技术分析师。基于趋势/动量/波动率/回撤指标评分。
输入：MA20/MA60、趋势/动量/流动性/风险评分、收盘价
输出：{ "rating": <1-5>, "argument": "<80字>" }
```

### 2. 基本面分析师
```
你是A股基本面分析师。基于盈利能力和成长性评分。
输入：营收增速、净利润增速、ROE、行业
输出：{ "rating": <1-5>, "argument": "<80字>" }
```

### 3. 风险官
```
你是风险管理官。天然反对派——只挑问题，不找优点。
输入：波动率、最大回撤、资产负债率、流动性指标
输出：{ "rating": <1-5>, "argument": "<80字>" }
评分逻辑：风险越低分越高（与直觉相反——5=极低风险，1=极高风险）
```

### 4. 估值分析师
```
你是估值分析师。只问"值不值这个价"——不关心趋势多好。
输入：PE（如有）、PB（如有）、行业平均估值（如有）、市值
输出：{ "rating": <1-5>, "argument": "<80字>" }
PE/PB 缺失时输出 rating=3 并标注"估值数据不足"
```

### 5. 行业对比师
```
你是行业对比研究员。不孤立看个股，看它在本行业中的位置。
输入：股票行业、同行业其他推荐股票的平均评分
输出：{ "rating": <1-5>, "argument": "<80字>" }
如果该股票是行业内唯一推荐 → rating=3，标注"无同行对比"
```

### 委员会主席
```
你是投资委员会主席。综合 5 位分析师的辩论结果，做出最终裁决。
5 票制：每票 rating≥3 视为"同意推荐"，<3 视为"反对推荐"。

输出：{ "rating": <1-5>, "summary": "<150字>", "consensus": "unanimous|majority|split|vetoed", "votes": { "agree": <N>, "oppose": <M> } }

unanimous - 5票全同意
majority - 3-4票同意  
split - 3:2 平局（主席裁决）
vetoed - ≥3票反对
```

## 辩论流程（4 轮，含 Tavily 网络搜索）

```
第1轮（独立分析）：
  5 个 Agent 各自基于本地数据独立评分 → 输出 rating + argument
  → 如果 5 票全票一致 → 直接给主席（极罕见，可跳过后续）
  → 否则进入第 2 轮

第2轮（交叉质疑）：
  每个 Agent 看到其他 4 人的第 1 轮意见
  → 可以坚持或修改自己的 rating
  → 必须对与自己意见不一致的 Agent 做出直接回应

第3轮（网络举证）：
  每个 Agent 通过 Tavily Search API 搜索相关公开信息
  → 技术面：搜索 "{股票名称} 技术分析 走势"
  → 基本面：搜索 "{股票名称} 营收 利润 ROE 财报"
  → 风险官：搜索 "{股票名称} 风险 负债 诉讼"
  → 估值师：搜索 "{股票名称} PE PB 估值 目标价"
  → 行业对比：搜索 "{股票名称} 行业 竞争 排名"
  → 引用搜索结果作为证据，重新评估 rating

第4轮（分组辩论）：
  按第3轮结果分成两组：
  → 看多组（rating≥3）：推选代表整合"买入逻辑"
  → 看空组（rating<3）：推选代表整合"风险逻辑"
  → 两组互相辩论，每人做最后陈述

主席裁决：
  综合四轮所有发言 + 投票统计 → 输出最终 rating + consensus
  必须引用辩论中的关键转折点（如"第3轮搜索证据改变了技术面的观点"）
```

**早停规则**：仅第 1 轮 5 票全票一致时跳过后续。否则至少 4 轮完整辩论。

**搜索配额**：Tavily 免费 1000 次/月。每只股票 5 次搜索（5 Agent）× 50 只 = 250 次/天 ≈ 4 天用量/月。日常使用充足。

## 对推荐的影响

| 规则评级 | AI 投票 | 共识 | 前端展示 |
|---|---|---|---|
| A | 5:0 or 4:1 | unanimous/majority | 🟢 强一致推荐 |
| A | 3:2 | split | 🟡 有分歧（规则偏乐观） |
| A | ≤2:3 | vetoed | 🔴 AI 否决推荐 |
| B | ≥4:1 | majority | 🟡 AI 看多（规则保守） |
| B | 3:2 | split | ⚪ 分歧 |
| B | ≤2:3 | vetoed | ⚪ 一致不推荐 |

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

每只股票 ~25 次调用（4 轮 × 5 Agent × 1 次 LLM + 5 次 Tavily 搜索 + 分组代表 + 主席），50 只 ≈ **0.05 元/天**。

4 轮辩论保证充分博弈，实际耗时：50 只 × ~2 秒/轮 × 4 轮 ≈ **6-8 分钟**。


## 数据来源（每轮使用）

| 轮次 | 数据来源 | 说明 |
|---|---|---|
| 第1轮 | 本地 DB（factors/fundamentals/daily_prices） | 结构化运营数据 |
| 第2轮 | 其他 Agent 的第1轮输出 | 观点数据 |
| 第3轮 | **Tavily Search API**（网络公开信息） | 财报/新闻/研报/公告 |
| 第4轮 | 前三轮综合 | 分组辩论 |

## 搜索双引擎（自动切换）

| 引擎 | 优先 | 免费额度 | 切换条件 |
|---|---|---|---|
| Tavily | 主 | 1000/月 | 配额耗尽或 API 异常 |
| SerpAPI | 备 | 100/月 | Tavily 不可用时自动切换 |

实现：search_web(query) 先调 Tavily，失败自动切 SerpAPI。

## 新增依赖

- `tavily-python`：Tavily Search API SDK
- `.env` 新增：`TAVILY_API_KEY`
