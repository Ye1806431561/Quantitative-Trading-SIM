# CLI 使用指南

本文档是 `python main.py` 的命令级操作手册。

## 术语口径（与 README 一致）

- `实时模拟（Live）`：指 `live` 命令驱动的实时策略循环与撮合模拟。
- `性能基准（Benchmark）`：指 `benchmark` 命令执行的回测速度/实时延迟/订单响应基准。
- `回测（Backtest）`：指 `backtest` 命令执行的历史数据策略回放。

## 全局参数

所有命令都支持以下全局参数：

```bash
python main.py [--config config/config.yaml] [--strategies config/strategies.yaml] [--env .env] <command> [...args]
```

## 系统运行命令

### `start` / `stop` / `status`

```bash
python main.py start
python main.py stop
python main.py status
python main.py status --disk
python main.py status --alerts
```

### `balance` / `positions`

```bash
python main.py balance
python main.py positions
```

## 数据相关命令

### `download`

```bash
python main.py download --symbol BTC/USDT --timeframe 1h --days 30
python main.py download --symbol BTC/USDT --timeframe 1h --start-ms 1704067200000 --end-ms 1706745600000
```

### `import` / `export`

```bash
python main.py import --file data/input/candles.csv --symbol BTC/USDT --timeframe 1h
python main.py export --symbol BTC/USDT --timeframe 1h --output data/output/candles.csv --start-ms 1704067200000 --end-ms 1706745600000
```

### `cleanup`

```bash
python main.py cleanup --days 365
```

### `reconcile`

```bash
python main.py reconcile
```

## 订单命令

### `order place`

```bash
python main.py order place --symbol BTC/USDT --side buy --type market --amount 0.01
python main.py order place --symbol BTC/USDT --side buy --type limit --amount 0.01 --price 50000
python main.py order place --symbol BTC/USDT --side sell --type stop_loss --amount 0.01 --trigger-price 45000
python main.py order place --symbol BTC/USDT --side sell --type take_profit --amount 0.01 --trigger-price 60000
```

### `order list` / `order cancel`

```bash
python main.py order list
python main.py order list --symbol BTC/USDT --status open --limit 20
python main.py order cancel --order-id <ORDER_ID>
```

## 回测（Backtest）命令

### 最小用法

```bash
python main.py backtest --strategy sma_strategy --symbol BTC/USDT
```

### 带时间范围、策略参数和导出

```bash
python main.py backtest \
  --strategy sma_strategy \
  --symbol BTC/USDT \
  --timeframe 1h \
  --start-ms 1704067200000 \
  --end-ms 1735689600000 \
  --param fast_period=12 \
  --param slow_period=26 \
  --param position_size=0.2 \
  --output-dir data/reports/backtest \
  --prefix btc_1h
```

## 实时模拟（Live）命令

### 用于验证的有界运行

```bash
python main.py live \
  --strategy sma_strategy \
  --symbol BTC/USDT \
  --timeframe 1m \
  --tick-interval 0.5 \
  --max-iterations 20
```

### 覆盖策略参数运行

```bash
python main.py live \
  --strategy sma_strategy \
  --symbol BTC/USDT \
  --timeframe 1m \
  --max-iterations 50 \
  --param fast_period=8 \
  --param slow_period=21 \
  --param position_size=0.1
```

## 性能基准（Benchmark）命令

```bash
python main.py benchmark
python main.py benchmark --symbol BTC/USDT --strategy sma_strategy --realtime-iterations 300 --order-iterations 500 --seed 42
python main.py benchmark --output-dir data/benchmarks/custom
```

默认报告目录：`<system.data_dir>/benchmarks`。

退出码规则：

- `0`：通过（pass）或告警（warning）
- `1`：失败（fail）

## 策略名约束

CLI 内置策略名：

- `sma_strategy`
- `grid_strategy`
- `bollinger_strategy`

启用状态与默认参数来源：`config/strategies.yaml`。

## 第 41 步验收检查流程

按以下顺序执行（与 `README.md` 保持一致）：

1. 查看系统状态（基线）

```bash
python main.py status --disk
```

2. 下载历史数据

```bash
python main.py download --symbol BTC/USDT --timeframe 1h --days 365
```

3. 执行回测（Backtest）

```bash
python main.py backtest --strategy sma_strategy --symbol BTC/USDT --timeframe 1h --days 365 --output-dir data/reports/step41
```

预期在 `data/reports/step41/` 生成回测摘要、资金曲线序列（JSON/CSV）及图表（`equity_curve`、`drawdown_curve`、`trade_distribution`、`holding_time`）。

4. 执行有界实时模拟（Live）

```bash
python main.py live --strategy sma_strategy --symbol BTC/USDT --timeframe 1m --tick-interval 0.5 --max-iterations 20
```

5. 检查状态与告警

```bash
python main.py status --alerts
python main.py balance
python main.py positions
```

若以上命令均正常执行，且输出符合预期，则第 41 步文档流程可独立跑通。

## 常见问题

- `命令执行失败 symbol must not be empty`
  - 请提供非空的 `--symbol`。

- `CONFIG_MASTER_KEY is required ...`
  - 当配置了 API 凭证，或本地已存在加密 Vault 文件时，必须提供 `CONFIG_MASTER_KEY`。

- `No candle data found in SQLite ...`
  - 回测前请先执行 `download` 或 `import`。

- 实时模拟很快结束
  - 检查 `--max-iterations` 是否设置过小。
