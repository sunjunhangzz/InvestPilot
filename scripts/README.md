# scripts/ — 项目操作脚本

## 脚本一览

| 脚本 | 作用 | 需运行次数 |
|---|---|---|
| `setup.sh` | 安装 Python 虚拟环境 + Node 依赖 | **仅首次**（或新增依赖后） |
| `configure.sh` | 创建 `.env` 配置文件 | **仅首次**（或修改配置后） |
| `run_pipeline.sh` | 跑完整数据流水线 | **每次想更新数据/推荐时** |

---

## setup.sh — 安装依赖

```bash
bash scripts/setup.sh
```

**做什么**：
- 创建 `app/worker/.venv` Python 虚拟环境
- 安装 `akshare`、`pandas`、`numpy` 等 Python 包
- 安装 `next`、`react`、`tailwindcss` 等前端包

**何时使用**：
- 首次克隆项目后
- `requirements.txt` 或 `package.json` 有更新时

**重复运行**：✅ 安全，幂等。已安装的包会跳过，不会重复安装。

---

## configure.sh — 配置环境

```bash
bash scripts/configure.sh
```

**做什么**：
- 从 `.env.example` 复制一份 `.env`（如不存在）
- 打印当前 `config.json` 的关键配置项
- 提示如何配置 AI API Key

**何时使用**：
- 首次克隆项目后
- 需要修改 AI 开关、模型选择或 API Key 时（手动编辑 `.env`）

**重复运行**：✅ 安全。已有 `.env` 不会被覆盖。

> 注意：如果启用 AI 报告（`ai.enabled = true`），需要手动编辑 `.env` 填入 `DEEPSEEK_API_KEY`。

---

## run_pipeline.sh — 运行数据流水线

```bash
# 快速测试（2 只股票，~30 秒）
bash scripts/run_pipeline.sh --test

# 全量模式（全部主板股票，行情采集 ~50 分钟）
bash scripts/run_pipeline.sh

# 全量 + AI 报告
bash scripts/run_pipeline.sh --ai

# 全量 + 自动启动前端
bash scripts/run_pipeline.sh --web

# 全量 + AI + 启动前端
bash scripts/run_pipeline.sh --ai --web
```

**做什么**（7 步，依次执行）：

| 步骤 | 脚本 | 说明 |
|---|---|---|
| 1 | `init_db.py` | 创建数据库表（幂等，不会删已有数据） |
| 2 | `update_stocks.py` | 从 AkShare 拉取 A 股列表，写入 `stocks` 表 |
| 3 | `update_prices.py` | 拉取每只股票的日线行情，写入 `daily_prices` |
| 4 | `calc_factors.py` | 计算 MA/收益率/波动率/回撤 + 四因子评分 |
| 5 | `run_screening.py` | 应用筛选规则 + 排序 + A/B 分层 + 推荐理由 |
| 6 | `update_watchlist.py` | 更新观察池（入场/跟踪天数/退出规则） |
| 7 | `generate_report.py` | AI 解释报告（仅 `--ai` 模式下执行） |

**何时使用**：
- 每天收盘后（更新当天的推荐结果）
- 首次初始化项目数据
- 调试时用 `--test` 快速验证全链路是否正常

**重复运行**：✅ 安全，幂等。
- 股票列表：UPSERT，不会重复插入
- 行情数据：UPSERT，同一天不会重复写入
- 因子：每次生成新的 `run_id`，不覆盖历史
- 推荐：同上
- 观察池：更新状态和价格，保留首次推荐日期

---

## 典型工作流

### 第一次使用

```bash
bash scripts/setup.sh        # 安装依赖
bash scripts/configure.sh    # 配置 .env
bash scripts/run_pipeline.sh --test   # 快速验证
# 验证通过后：
bash scripts/run_pipeline.sh          # 全量数据
cd app/web && npm run dev             # 启动前端
```

### 每日使用

```bash
bash scripts/run_pipeline.sh   # 更新数据 + 生成推荐
# 打开浏览器 http://localhost:3000/dashboard 查看
```

### 开发调试

```bash
bash scripts/run_pipeline.sh --test   # 2 只股票 30 秒出结果
cd app/web && npm run dev             # 启动前端看效果
```
