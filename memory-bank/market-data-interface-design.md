# 市场数据接口设计（Step 14）

## 目标
- 为行情读取提供统一接口：交易所选择、限流、错误重试与失败告知。
- 明确运行态数据路径约束，避免偏离 `DC-001 ~ DC-004`。

## 接口总览
- 核心入口：`src/data/market.py::MarketDataFetcher`
- 构建方式：
  - `MarketDataFetcher.from_config(config)`：从运行配置创建客户端。
  - `MarketDataFetcher.from_exchange(exchange, ...)`：测试/注入场景。
- 读取接口：
  - `fetch_ticker(symbol)`
  - `fetch_order_book(symbol, limit=None)`
  - `fetch_ohlcv(symbol, timeframe, since=None, limit=None)`

## 交易所选择策略
- 配置来源：`config.exchange`
  - `name`：交易所名称（如 `binance`、`okx`）。
  - `testnet`：是否开启沙盒模式（若交易所支持）。
  - `rate_limit`：是否启用本地限流等待。
  - `api_key` / `api_secret`：可选鉴权字段。
- 客户端工厂：`create_exchange_client()`（CCXT 适配）。
- 重试与运行态写入目标配置来源：`config.market_data`（由 `src/utils/config_defaults.py` 与 `src/utils/config_validation.py` 约束）。

## 限流策略
- 双层限流：
  - 交易所侧：`enableRateLimit`（CCXT 原生）。
  - 本地侧：`RequestRateLimiter`，使用 `exchange.rateLimit` 控制最小请求间隔。
- 行为：
  - 当请求过快时，自动 `sleep` 到可请求窗口。
  - 限流开关由 `exchange.rate_limit` 控制。

## 错误重试与失败告知策略
- 重试策略：`RetryPolicy`
  - `max_attempts`（默认 3）
  - `initial_delay_seconds`（默认 0.2s）
  - `backoff_multiplier`（默认 2.0）
  - `max_delay_seconds`（默认 2.0s）
- 可重试错误（示例）：
  - 限流类：`RateLimitExceeded`、`DDoSProtection`
  - 瞬时网络类：`NetworkError`、`ExchangeNotAvailable`、`RequestTimeout`
- 不可重试错误（示例）：
  - `AuthenticationError`、`PermissionDenied`、`BadRequest`、`BadSymbol`、`InvalidOrder`
- 失败告知：
  - 重试耗尽或不可重试时，抛出 `MarketDataFetchError`
  - 错误信息包含：接口名、尝试次数、原始错误类型、失败原因（`non-retryable` 或 `retry limit reached`）

## 运行态数据路径约束（强制）
- `market_data.runtime_write_target` 只允许 `sqlite`。
- 当配置为 `csv/parquet` 或其他值时立即拒绝并抛出 `MarketDataConfigError`。
- 结论：
  - 运行态写入目标：**仅 SQLite**
  - `CSV/Parquet`：**仅 import/export/backup 场景可用，不参与运行态写入**

## 验证点（自动化）
- 对应测试：`tests/test_market_data.py`
  - 交易所选择生效（`from_config`）
  - 限流错误可重试并恢复
  - 网络错误重试耗尽后失败告知
  - 鉴权类错误快速失败（不重试）
  - 本地限流在连续请求间生效
  - 非 SQLite 运行态写入目标被拒绝
