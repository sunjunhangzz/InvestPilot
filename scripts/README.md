# scripts/ — 项目操作脚本

## 脚本一览

| 脚本 | 作用 | 需运行次数 |
|---|---|---|
| `setup.sh` | 安装 Python 虚拟环境 + Node 依赖 | **仅首次** |
| `configure.sh` | 创建 `.env` 配置文件 | **仅首次** |
| `update_data.sh` | 更新股票列表和行情数据 | **每次想刷新行情时** |
| `run_analysis.sh` | 计算因子 + 筛选推荐 + 观察池（+AI） | **每次想重新分析时**（可多次跑） |
| `run_pipeline.sh` | 一键跑通上面两个（数据→分析） | **首次或要完整刷新时** |

---

## setup.sh — 安装依赖

```bash
bash scripts/setup.sh
```

**做什么**：
- 创建 `app/worker/.venv` Python 虚拟环境
- 安装 `akshare`、`pandas`、`numpy` 等 Python 包
- 安装 `next`、`react`、`tailwindcss` 等前端包

**重复运行**：✅ 安全，幂等。

---

## configure.sh — 配置环境

```bash
bash scripts/configure.sh
```

**做什么**：从 `.env.example` 复制 `.env`，打印配置项。

**重复运行**：✅ 已有 `.env` 不会被覆盖。

---

## update_data.sh — 更新数据

```bash
bash scripts/update_data.sh           # 全量（~60 分钟）
bash scripts/update_data.sh --test    # 测试（2 只股票，~30 秒）
```

只做两件事：
1. `update_stocks.py` — 拉取 A 股列表
2. `update_prices.py` — 拉取日线行情

**何时使用**：收盘后需要刷新行情时。**只跑一次，之后可以多次跑 `run_analysis.sh` 分析。**

---

## run_analysis.sh — 分析推荐

```bash
bash scripts/run_analysis.sh          # 基础分析
bash scripts/run_analysis.sh --ai     # 含 AI 报告
bash scripts/run_analysis.sh --web    # 分析完自动启动前端
```

只做三件事（+ 可选 AI）：
1. `calc_factors.py` — 计算因子评分
2. `run_screening.py` — 筛选 + A/B 评级
3. `update_watchlist.py` — 更新观察池
4. `generate_report.py` — AI 报告（仅 `--ai`）

**何时使用**：行情已更新，想重新生成推荐。**不碰数据采集，可以反复跑。**

---

## run_pipeline.sh — 一键全流程

```bash
bash scripts/run_pipeline.sh --test     # 测试模式
bash scripts/run_pipeline.sh --ai --web # 全量+AI+前端
```

等价于 `update_data.sh && run_analysis.sh`。包含 `init_db`。

---

## 典型工作流

### 第一次使用

```bash
bash scripts/setup.sh
bash scripts/configure.sh
bash scripts/update_data.sh --test     # 快速验证
bash scripts/run_analysis.sh           # 验证分析
cd app/web && npm run dev              # 查看结果
```

### 每日使用

```bash
bash scripts/update_data.sh            # 更新行情
bash scripts/run_analysis.sh --ai      # 分析 + AI 报告
```

### 同一天反复分析

```bash
bash scripts/run_analysis.sh           # 第一次
# 调整参数或想看最新数据
bash scripts/run_analysis.sh --ai      # 再跑一次，不需要重新采集
```

---

## 定时推送（launchd）

macOS 下安装定时任务：

```bash
# 早盘 08:00
cp scripts/com.investpilot.morning.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.investpilot.morning.plist

# 午间 12:00
cp scripts/com.investpilot.noon.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.investpilot.noon.plist
```

**手动测试**：
```bash
bash scripts/morning_push.sh
bash scripts/noon_push.sh
```

**注意事项**：
- 定时推送需要**电脑保持开机**（睡眠时 launchd 不触发，唤醒后自动补跑）
- 如果电脑关机错过推送时间，可手动运行脚本
- plist 文件中的路径是绝对路径，如果项目位置变了需要修改
