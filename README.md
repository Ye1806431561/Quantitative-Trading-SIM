# 虚拟货币量化交易模拟盘（Quantitative Trading Simulator）

一个基于 Python 的加密货币模拟交易系统，支持：

- 历史数据下载与本地 SQLite 存储
- 回测（Backtest）与结果导出
- 实时模拟（Live）与监控告警
- 性能基准（Benchmark）

## 功能概览

- 数据层：`download / import / export / cleanup`
- 交易核心：账户、订单、撮合、风控
- 回测：策略执行 + 分析指标 + 报告/图表导出
- 实时模拟：策略循环、下单执行、状态与告警
- 性能基准：回测速度、实时延迟、订单响应

## 术语口径

为避免歧义，本文档与 `docs/usage-guide.md` 统一使用以下术语：

- `实时模拟（Live）`：指 `live` 命令驱动的实时策略循环与撮合模拟。
- `性能基准（Benchmark）`：指 `benchmark` 命令执行的回测速度/实时延迟/订单响应基准。
- `回测（Backtest）`：指 `backtest` 命令执行的历史数据策略回放。

## 环境要求

- Python `3.10+`
- macOS/Linux 终端环境（示例命令基于 `zsh`）
- 若执行 `download` 或连接交易所行情，需要可用网络

## 安装与初始化

1. 创建并激活虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 准备环境变量文件

```bash
cp config/.env.example .env
```

4. （可选）配置交易所凭证

- 如果在 `.env` 中设置了 `EXCHANGE_API_KEY` / `EXCHANGE_API_SECRET`，必须同时设置 `CONFIG_MASTER_KEY`。
- CLI 启动时会将凭证加密写入本地 Vault；缺少主密钥会直接失败（fail-fast）。

5. （推荐）启用 Varlock 与提交前密钥检查

```bash
# 1) 校验本地环境变量（敏感值会自动脱敏）
varlock load

# 2) 启用仓库内 pre-commit 钩子（提交前自动执行密钥检查）
git config core.hooksPath .githooks
```

说明：
- `.env.schema` 定义了环境变量类型与敏感级别；
- `scripts/check-secrets.sh` 会阻止提交 `.env`、`data/secure/`、数据库文件及疑似密钥文本。

## 第 41 步验收检查流程（下载 → 回测 → 实时模拟）

以下命令均在仓库根目录执行。

### 1）查看系统状态（基线）

```bash
python main.py status --disk
```

### 2）下载历史 K 线到 SQLite

```bash
python main.py download --symbol BTC/USDT --timeframe 1h --days 365
```

### 2.1）主网历史数据下载（隔离数据库）

当你需要较长窗口（例如 `15m` 的 `365` 天）时，建议使用主网配置并隔离数据库，避免测试网短历史窗口影响回测样本。

```bash
DATABASE_PATH=data/database/trading_mainnet.db \
python main.py --config config/config.mainnet.yaml download \
  --symbol BTC/USDT \
  --timeframe 15m \
  --days 365
```

随后使用同一数据库执行回测：

```bash
DATABASE_PATH=data/database/trading_mainnet.db \
python main.py --config config/config.mainnet.yaml backtest \
  --strategy sma_strategy \
  --symbol BTC/USDT \
  --timeframe 15m \
  --days 365 \
  --param position_size=0.001 \
  --output-dir data/reports/mainnet_15m
```

### 3）执行一次回测（Backtest）并导出报告

```bash
python main.py backtest \
  --strategy sma_strategy \
  --symbol BTC/USDT \
  --timeframe 1h \
  --days 365 \
  --output-dir data/reports/step41
```

预期在 `data/reports/step41/` 生成：

- 回测摘要：JSON + CSV
- 资金曲线序列：JSON + CSV
- 图表：`equity_curve`、`drawdown_curve`、`trade_distribution`、`holding_time`

### 4）执行有界实时模拟（Live）

```bash
python main.py live \
  --strategy sma_strategy \
  --symbol BTC/USDT \
  --timeframe 1m \
  --tick-interval 0.5 \
  --max-iterations 20
```

随后检查运行状态与告警：

```bash
python main.py status --alerts
python main.py balance
python main.py positions
```

若以上命令均正常执行，且输出符合预期，则第 41 步文档流程可独立跑通。

## 第 40 步性能基准命令

```bash
python main.py benchmark \
  --symbol BTC/USDT \
  --strategy sma_strategy \
  --realtime-iterations 300 \
  --order-iterations 500 \
  --seed 42
```

- 默认报告目录：`<system.data_dir>/benchmarks`
- 退出码策略：
  - `0`：通过（pass）或告警（warning）
  - `1`：失败（fail）

## CLI 使用指南

完整参数说明、命令示例、验收流程和常见问题，请查看：

- `docs/usage-guide.md`

## 测试命令

全量测试：

```bash
PYTHONPATH=. ./.venv/bin/pytest -q
```

仅运行基准相关测试：

```bash
PYTHONPATH=. ./.venv/bin/pytest -q \
  tests/test_benchmark_executors.py \
  tests/test_benchmark_reporter.py \
  tests/test_benchmark_runner.py \
  tests/test_cli_benchmark.py
```

## 日志说明

日志配置来源：`config/config.yaml`

- 控制台输出受 `logging.level` 控制
- 文件流按类型拆分：`main`、`strategy`、`trade`、`error`
- 支持轮转、保留、压缩
- 敏感字段（如 `api_key`、`api_secret`、`token`、`password`、`secret`）会脱敏
