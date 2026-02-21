# CLAUDE.md

## 重要提示

**在编写任何代码之前，必须：**

- 📖 完整阅读 `memory-bank/architecture.md`（包含完整数据库结构）
- 📖 完整阅读 `memory-bank/product-requirement-document`
- 📝 每完成一个重大功能或里程碑后，必须更新 `memory-bank/architecture.md`

At the start of any task-oriented session — any interaction where you will
use tools and produce deliverables — invoke the task-observer skill before
beginning work. This ensures skill improvement opportunities are captured
throughout the session.

---

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

虚拟货币量化交易模拟盘系统 (Cryptocurrency Quantitative Trading Simulator) - A Python-based paper trading system for cryptocurrency quantitative strategies using CCXT and Backtrader.

**Core Purpose**: Provide risk-free backtesting and real-time simulation environment for quantitative trading strategies.

## Technology Stack

- **Language**: Python 3.10+
- **Core Libraries**:
  - `ccxt==4.2.0` - Unified exchange API interface
  - `backtrader==1.9.78.123` - Professional backtesting framework
  - `pandas==2.1.0` - Data processing
- **Storage**: SQLite (built-in, zero-config)
- **Config**: PyYAML, python-dotenv
- **Logging**: loguru
- **CLI**: rich
- **Visualization**: matplotlib

**Loguru Configuration**:
```python
# src/utils/logger.py - Proper loguru setup with rotation
from loguru import logger
import sys
from pathlib import Path

def setup_logger(config: dict):
    """Configure loguru with rotation and retention policies"""
    
    # Remove default handler
    logger.remove()
    
    # Console handler (with rich formatting)
    logger.add(
        sys.stderr,
        level=config['logging']['level'],
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File handlers with rotation
    log_dir = Path(config['system']['log_dir'])
    log_dir.mkdir(exist_ok=True)
    
    for log_type, log_config in config['logging']['files'].items():
        logger.add(
            log_config['path'],
            level=log_config['level'],
            rotation=log_config['rotation'],      # "500 MB" or "00:00" (daily)
            retention=log_config['retention'],    # "7 days"
            compression=config['logging'].get('compression', 'zip'),
            format=config['logging']['format'],
            enqueue=True,                         # Thread-safe
            backtrace=True,                       # Full traceback on errors
            diagnose=True                         # Variable values in traceback
        )
    
    logger.info("Logger initialized with rotation and retention policies")
    return logger
```

**Usage in application**:
```python
# main.py
from src.utils.logger import setup_logger
from src.utils.config import load_config

config = load_config('config/config.yaml')
logger = setup_logger(config)

logger.info("Application started")
logger.debug("Debug information")
logger.error("Error occurred")
```

## Project Structure

```
quantitative-trading-simulator/
├── src/
│   ├── core/              # Core business logic
│   │   ├── account.py     # Account management
│   │   ├── order.py       # Order models
│   │   ├── position.py    # Position management & crash recovery
│   │   ├── matching.py    # Simulated matching engine
│   │   └── database.py    # SQLite wrapper
│   ├── data/              # Data layer
│   │   ├── market.py      # CCXT market data fetching
│   │   ├── storage.py     # Candle data storage (SQLite)
│   │   └── feed.py        # Custom Backtrader DataFeed from SQLite
│   ├── strategies/        # Strategy layer
│   │   ├── base.py        # Strategy base class
│   │   ├── sma_strategy.py    # SMA strategy example
│   │   └── grid_strategy.py   # Grid strategy example
│   ├── backtest/          # Backtest engine
│   │   ├── engine.py      # Backtrader integration
│   │   └── analyzers.py   # Performance analysis
│   ├── live/              # Live simulation
│   │   └── simulator.py   # Real-time simulator
│   ├── utils/             # Utilities
│   │   ├── logger.py      # Logging config
│   │   └── config.py      # Config loader
│   └── cli.py             # CLI entry point
├── config/
│   ├── config.yaml        # Main config
│   ├── strategies.yaml    # Strategy parameters
│   └── .env.example       # Environment template
├── data/
│   └── database/          # SQLite database (includes candles)
├── logs/                  # Log directory
├── tests/                 # Tests
│   ├── test_position.py   # Position management tests
│   ├── test_crash_recovery.py  # Crash recovery tests
│   └── ...
├── requirements.txt
└── main.py               # Program entry point
```

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/.env.example .env
```

### Database Operations
```bash
# Initialize database (creates all tables including positions)
python -m src.core.database init

# Check database integrity
python -m src.core.database check

# Reconcile positions with trades history
python -m src.core.database reconcile

# Backup database
python -m src.core.database backup --output backup_20260215.db
```

### Data Management
```bash
# Download historical data (saves to SQLite)
python main.py download --symbol BTC/USDT --timeframe 1h --days 90

# Import from CSV to SQLite (migration tool)
python main.py import --file data/historical/BTC_USDT_1h.csv

# Export from SQLite to CSV (backup)
python main.py export --symbol BTC/USDT --timeframe 1h --output backup.csv

# Clean old data (retention policy)
python main.py cleanup --days 730  # Keep only last 2 years
```

### Backtesting
```bash
# Run backtest with specific strategy
python main.py backtest --strategy sma --symbol BTC/USDT

# Run backtest with custom parameters
python main.py backtest --strategy sma --symbol BTC/USDT --fast 10 --slow 30
```

### Live Simulation
```bash
# Start real-time simulation
python main.py live --strategy sma --symbol BTC/USDT

# Resume after crash (automatically loads positions from database)
python main.py live --strategy sma --symbol BTC/USDT --resume

# Check current positions
python main.py positions

# View position details
python main.py positions --symbol BTC/USDT --verbose
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_account.py
```

### Code Quality
```bash
# Format code
black src/ tests/

# Run linter (if configured)
pylint src/

# Clean old logs (manual cleanup if needed)
find logs/ -name "*.log" -mtime +7 -delete
find logs/ -name "*.zip" -mtime +30 -delete
```

### Maintenance
```bash
# View recent logs
tail -f logs/app_$(date +%Y-%m-%d).log

# Check log disk usage
du -sh logs/

# Compress old logs manually (if not using auto-compression)
gzip logs/*.log

# Archive logs before cleanup
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

## Architecture Principles

### 🚨 CRITICAL: Modular Architecture - NO MONOLITHS

**MANDATORY RULES:**

1. **File Size Limits**:
   - ❌ **NEVER** create files > 300 lines of code
   - ❌ **NEVER** put multiple unrelated classes in one file
   - ✅ **ALWAYS** split large modules into smaller, focused files
   - ✅ **ALWAYS** use subdirectories to organize related modules

2. **Single Responsibility Principle**:
   - ❌ **FORBIDDEN**: `utils.py` with 50+ functions
   - ❌ **FORBIDDEN**: `models.py` with all data models
   - ❌ **FORBIDDEN**: `strategy.py` with multiple strategy implementations
   - ✅ **REQUIRED**: One class/concept per file
   - ✅ **REQUIRED**: Clear file naming that reflects its single purpose

3. **Module Organization**:
   ```
   ✅ GOOD:
   src/strategies/
   ├── __init__.py
   ├── base.py              # Base strategy class only
   ├── sma_strategy.py      # SMA strategy only
   ├── grid_strategy.py     # Grid strategy only
   └── bollinger_strategy.py # Bollinger strategy only

   ❌ BAD:
   src/strategies/
   ├── __init__.py
   └── strategies.py        # All strategies in one 1000-line file
   ```

4. **Refactoring Triggers**:
   - If a file exceeds 250 lines → **MUST** split immediately
   - If a class has > 10 methods → ensure splitting into multiple classes
   - If you need to scroll > 3 screens → File is too large

5. **Import Structure**:
   ```python
   ✅ GOOD:
   from src.core.account import Account
   from src.core.order import Order, OrderStatus
   from src.core.matching import MatchingEngine

   ❌ BAD:
   from src.core import Account, Order, OrderStatus, MatchingEngine, Trade, Position
   # (all from one giant core.py file)
   ```

6. **Subdirectory Usage**:
   - Use subdirectories liberally to group related modules
   - Each subdirectory must have `__init__.py`
   - Example: `src/strategies/indicators/` for custom indicators

### Dual-Engine Design
The system uses two separate engines:

1. **Backtest Mode** (Backtrader-based):
   - Uses Backtrader's Cerebro engine
   - Historical data replay
   - Built-in analyzers (SharpeRatio, DrawDown, TradeAnalyzer)
   - Strategy inherits from `backtrader.Strategy`

2. **Live Mode** (Custom engine):
   - Real-time data streaming
   - Order execution simulation
   - Status monitoring
   - Strategy inherits from custom `LiveStrategy`

### Strategy Abstraction Layer
- Unified strategy interface for both modes
- Strategy adapter automatically converts between engines
- Same strategy logic can run in backtest or live mode

### Data Flow
```
CCXT API → Market Data → SQLite (candles table) → Strategy Engine → Order Execution → Account Management → Database
                              ↓
                    Backtrader DataFeed (query from SQLite)
                              ↓
                    Live Simulator (real-time append to SQLite)
```

**Key Implementation Points**:

1. **Custom Backtrader DataFeed**:
   ```python
   # src/data/feed.py
   class SQLiteDataFeed(bt.DataBase):
       """Custom DataFeed that reads from SQLite candles table"""
       
       def __init__(self, symbol, timeframe, start_date, end_date):
           self.symbol = symbol
           self.timeframe = timeframe
           # Query candles from SQLite
           self.candles = db.query_candles(symbol, timeframe, start_date, end_date)
   ```

2. **Real-time Candle Appending**:
   ```python
   # Live mode: New candles automatically saved
   async def on_new_candle(candle):
       db.insert_candle(symbol, timeframe, candle)  # Async insert
       strategy.process_candle(candle)
   ```

3. **Data Consistency**:
   - UNIQUE constraint prevents duplicate candles
   - Both backtest and live use same query interface
   - Historical data and real-time data in same table

## Database Schema

### accounts table
- `id`: Primary key
- `currency`: Currency code
- `balance`: Total balance
- `available`: Available balance
- `frozen`: Frozen amount
- `updated_at`: Last update timestamp

### orders table
- `id`: Order ID (TEXT primary key)
- `symbol`: Trading pair
- `type`: Order type (market/limit/stop)
- `side`: Buy/sell
- `price`: Order price
- `amount`: Order amount
- `filled`: Filled amount
- `status`: Order status
- `created_at`, `updated_at`: Timestamps

### trades table
- `id`: Trade ID
- `order_id`: Foreign key to orders
- `symbol`: Trading pair
- `side`: Buy/sell
- `price`: Execution price
- `amount`: Execution amount
- `fee`: Trading fee
- `timestamp`: Execution time

### positions table (Current Holdings)
**Purpose**: Track current positions for crash recovery and state persistence

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,       -- Trading pair (one position per symbol)
    amount REAL NOT NULL,              -- Current holding amount (can be 0)
    entry_price REAL NOT NULL,         -- Average entry price
    current_price REAL,                -- Last known market price
    unrealized_pnl REAL,               -- Unrealized profit/loss
    realized_pnl REAL DEFAULT 0,       -- Realized profit/loss (from closed trades)
    opened_at TIMESTAMP,               -- First entry timestamp
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK(amount >= 0)                 -- Prevent negative positions (spot trading)
);

-- Index for quick symbol lookup
CREATE INDEX idx_positions_symbol ON positions(symbol);
```

**Key Features**:
- ✅ **Crash Recovery**: System can restore positions after restart
- ✅ **State Persistence**: No need to recalculate from trades history
- ✅ **Performance**: Direct position lookup without aggregating trades
- ✅ **Data Integrity**: UNIQUE constraint ensures one position per symbol

**Position Lifecycle**:
```python
# 1. Open position (first buy)
db.upsert_position(
    symbol='BTC/USDT',
    amount=0.5,
    entry_price=50000.0
)

# 2. Add to position (average down/up)
current_pos = db.get_position('BTC/USDT')
new_avg_price = (current_pos.amount * current_pos.entry_price + new_amount * new_price) / (current_pos.amount + new_amount)
db.update_position(
    symbol='BTC/USDT',
    amount=current_pos.amount + new_amount,
    entry_price=new_avg_price
)

# 3. Reduce position (partial sell)
db.update_position(
    symbol='BTC/USDT',
    amount=current_pos.amount - sell_amount,
    realized_pnl=current_pos.realized_pnl + (sell_price - entry_price) * sell_amount
)

# 4. Close position (full sell)
db.update_position(
    symbol='BTC/USDT',
    amount=0,
    realized_pnl=total_pnl
)
# Or delete the record: db.delete_position('BTC/USDT')
```

**Crash Recovery Process**:
```python
# On system startup
def recover_state():
    # 1. Load all open positions from database
    positions = db.get_all_positions(amount__gt=0)
    
    # 2. Restore account state
    for pos in positions:
        account.restore_position(pos)
    
    # 3. Verify consistency with trades table (optional)
    for pos in positions:
        calculated_amount = db.calculate_position_from_trades(pos.symbol)
        if abs(calculated_amount - pos.amount) > 0.0001:
            logger.warning(f"Position mismatch for {pos.symbol}: DB={pos.amount}, Calculated={calculated_amount}")
            # Trigger reconciliation
    
    # 4. Resume strategy execution
    logger.info(f"Recovered {len(positions)} open positions")
```

**Data Consistency Rules**:
- Update `positions` table atomically with `trades` table (use transactions)
- Periodically reconcile positions with trades history
- Log all position changes for audit trail

### candles table (K-line data)
**Purpose**: Unified storage for both historical and real-time candle data

```sql
CREATE TABLE candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,              -- e.g., 'BTC/USDT'
    timeframe TEXT NOT NULL,           -- e.g., '1h', '4h', '1d'
    timestamp INTEGER NOT NULL,        -- Unix timestamp (milliseconds)
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, timestamp)  -- Prevent duplicates
);

-- Critical indexes for query performance
CREATE INDEX idx_candles_symbol_time ON candles(symbol, timeframe, timestamp);
CREATE INDEX idx_candles_timestamp ON candles(timestamp);
```

**Benefits**:
- ✅ Unified data source for backtest and live trading
- ✅ Real-time candles automatically persisted
- ✅ Easy time-range queries
- ✅ Automatic deduplication via UNIQUE constraint

**Usage Pattern**:
```python
# Backtest: Query historical data
candles = db.query_candles(
    symbol='BTC/USDT',
    timeframe='1h',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 12, 31)
)

# Live: Append new candles
db.insert_candle(
    symbol='BTC/USDT',
    timeframe='1h',
    timestamp=current_timestamp,
    ohlcv=[open, high, low, close, volume]
)
```

**Performance Considerations**:
- Use batch inserts for historical data import
- Implement data retention policy (e.g., keep 2 years max)
- Consider partitioning by year for very large datasets
- Cache recent candles in memory for live trading

### strategy_runs table
- Tracks strategy execution history
- Performance metrics (return, drawdown, Sharpe ratio)
- Start/end times and status

## Configuration Files

### config.yaml
Main system configuration:
- System settings (log level, directories, log rotation)
- Exchange settings (name, testnet, rate limit)
- Account settings (initial capital, base currency)
- Trading settings (commission, slippage)
- Risk settings (position limits, max drawdown)
- Backtest settings (timeframe, period)

**Example config.yaml with log rotation**:
```yaml
# System Configuration
system:
  log_level: INFO
  log_dir: logs
  data_dir: data

# Logging Configuration
logging:
  level: INFO
  rotation: "00:00"          # Rotate daily at midnight
  retention: "7 days"        # Keep logs for 7 days
  compression: "zip"         # Compress old logs
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
  
  # Separate log files by type
  files:
    main:
      path: "logs/app_{time:YYYY-MM-DD}.log"
      rotation: "500 MB"     # Also rotate when file reaches 500MB
      retention: "7 days"
      level: INFO
    
    strategy:
      path: "logs/strategy_{time:YYYY-MM-DD}.log"
      rotation: "100 MB"
      retention: "14 days"   # Keep strategy logs longer
      level: DEBUG
    
    trade:
      path: "logs/trade_{time:YYYY-MM-DD}.log"
      rotation: "50 MB"
      retention: "30 days"   # Keep trade logs for 1 month
      level: INFO
    
    error:
      path: "logs/error_{time:YYYY-MM-DD}.log"
      rotation: "100 MB"
      retention: "30 days"   # Keep error logs longer
      level: ERROR

# Exchange Configuration
exchange:
  name: binance
  testnet: true
  rate_limit: true

# Account Configuration
account:
  initial_capital: 10000.0
  base_currency: USDT

# Trading Configuration
trading:
  commission:
    maker: 0.001
    taker: 0.001
  slippage: 0.0005

# Risk Configuration
risk:
  max_position_size: 0.3
  max_total_position: 0.8
  max_drawdown: 0.2

# Backtest Configuration
backtest:
  default_timeframe: 1h
  default_period: 90
```

### strategies.yaml
Strategy-specific parameters:
- Enable/disable strategies
- Strategy parameters (periods, position sizes)
- Multiple strategy configurations

### .env
Sensitive information:
- Exchange API keys (optional for paper trading)
- Database path
- Log level

## Strategy Development

### Backtest Strategy Template
```python
import backtrader as bt

class MyStrategy(bt.Strategy):
    params = (
        ('period', 20),
        ('position_size', 0.2),
    )

    def __init__(self):
        # Initialize indicators
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)

    def next(self):
        # Strategy logic for each data point
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy(size=self.params.position_size)
        else:
            if self.data.close[0] < self.sma[0]:
                self.close()

    def notify_order(self, order):
        # Handle order status changes
        pass

    def notify_trade(self, trade):
        # Handle trade completion
        pass
```

### Live Strategy Template
Strategy adapter will automatically convert backtest strategies to live mode.

## Key Design Decisions

### Why SQLite?
- Zero configuration, no database server needed
- Single-file storage, easy backup
- Sufficient for paper trading data volume (with proper indexing)
- Transaction support for data integrity
- **Unified storage for candles, orders, trades, and accounts**

**Performance Notes**:
- With indexes, SQLite can handle millions of candle records efficiently
- For 10 trading pairs × 3 timeframes × 2 years ≈ 500K records (manageable)
- Query time for 1 year of 1h candles: < 100ms
- If scaling beyond 5M records, consider TimescaleDB migration

### Why Backtrader?
- Professional backtesting framework
- Comprehensive built-in indicators
- Active community and documentation
- Native matplotlib integration

### Why CCXT?
- Supports 100+ exchanges
- Stable API
- Industry standard for crypto trading

### Preferred Practices
- **CLI-first approach**: Focus on robust command-line interface implementation for Phase 1.
- **Local SQLite storage**: Use SQLite which is fully sufficient for the current data volume.
- **Local environment focus**: Optimize for local development and execution.
- **Native indicators**: Prioritize Backtrader's built-in indicators to minimize secondary dependencies like TA-Lib.

## Performance Expectations

- Backtest speed: 1 year of 1h candles < 5 seconds
- Real-time latency: < 1 second
- Memory usage: < 200MB
- Database size: < 100MB (1 year data)
- Concurrent strategies: 5+
- Trading pairs: 10+

## Risk Controls

### Position Management
- Max single trade size: 30% of capital
- Max total position: 80% of capital
- Per-symbol position limits

### Risk Metrics
- Max drawdown monitoring
- Stop-loss mechanisms
- Liquidation protection

## Common Issues

### CCXT Rate Limiting
- Enable `rate_limit: true` in config
- Use data caching for historical data
- Implement exponential backoff for retries

### Data Quality
- Validate data completeness before backtesting
- Handle missing candles gracefully
- Check for data gaps in historical downloads
- Use `UNIQUE` constraint to prevent duplicate candles in SQLite

### SQLite Performance Optimization
- **Always use indexes**: `CREATE INDEX idx_candles_symbol_time ON candles(symbol, timeframe, timestamp)`
- **Batch inserts**: Use transactions for bulk historical data import
  ```python
  with db.transaction():
      for candle in candles:
          db.insert_candle(candle)
  ```
- **Query optimization**: Always filter by `symbol` and `timeframe` first
- **Data retention**: Implement cleanup policy to remove old candles (e.g., > 2 years)
- **Vacuum frequency**: Run `VACUUM` after large deletions or once a week to reclaim space and maintain performance.

### Crash Recovery & Data Consistency
- **Atomic Updates**: Always update `positions` and `trades` in same transaction
  ```python
  with db.transaction():
      db.insert_trade(trade)
      db.update_position(symbol, new_amount, new_entry_price)
  ```
- **Startup Recovery**: Load positions from database on system restart
- **Reconciliation**: Periodically verify positions match trades history
  ```python
  # Daily reconciliation job
  for symbol in active_symbols:
      db_position = db.get_position(symbol)
      calculated_position = db.calculate_from_trades(symbol)
      if abs(db_position - calculated_position) > 0.0001:
          logger.error(f"Position mismatch: {symbol}")
          # Trigger alert or auto-fix
  ```
- **Audit Trail**: Log all position changes with timestamps
- **Backup Strategy**: Regular database backups before trading sessions

### Strategy Debugging
- Use loguru for detailed logging
- Enable DEBUG level for strategy development
- Check `notify_order()` and `notify_trade()` callbacks

### Backtrader DataFeed Integration
- Ensure SQLite query returns data in chronological order
- Convert query results to Pandas DataFrame before feeding to Backtrader
- Handle timezone conversions properly (UTC recommended)

## Code Organization Rules

### File Naming Conventions

- Strategy files: `{strategy_name}_strategy.py`
- Test files: `test_{module_name}.py`
- Config files: lowercase with underscores
- Data files: `{SYMBOL}_{TIMEFRAME}.csv`

### 🚨 Code Review Standards: Modular Design

#### ❌ FORBIDDEN: Monolithic Files
```python
# ❌ BAD: src/core.py (1500 lines)
class Account:
    # 200 lines
    pass

class Order:
    # 150 lines
    pass

class Trade:
    # 100 lines
    pass

class MatchingEngine:
    # 300 lines
    pass

class RiskManager:
    # 250 lines
    pass

# ... more classes
```

#### ✅ REQUIRED: Modular Files
```python
# ✅ GOOD: src/core/account.py (80 lines)
class Account:
    """Account management only"""
    pass

# ✅ GOOD: src/core/order.py (120 lines)
class Order:
    """Order model only"""
    pass

class OrderStatus(Enum):
    """Order status enum"""
    pass

# ✅ GOOD: src/core/matching.py (200 lines)
class MatchingEngine:
    """Order matching logic only"""
    pass
```

### Module Split Guidelines

#### When to Split a File

1. **File exceeds 300 lines** → Split immediately
2. **Multiple unrelated classes** → One file per class
3. **God class with 15+ methods** → Extract related methods into helper classes
4. **Mixing concerns** → Separate by responsibility

#### How to Split

```python
# Before: src/strategies/strategy.py (800 lines)
# ❌ BAD: Everything in one file

# After: Modular structure
# ✅ GOOD:
src/strategies/
├── __init__.py
├── base.py                    # 100 lines - Base strategy class
├── sma_strategy.py            # 150 lines - SMA implementation
├── grid_strategy.py           # 180 lines - Grid implementation
├── bollinger_strategy.py      # 160 lines - Bollinger implementation
└── indicators/                # Custom indicators subdirectory
    ├── __init__.py
    ├── momentum.py            # 80 lines
    └── volatility.py          # 90 lines
```

### Import Best Practices

```python
# ✅ GOOD: Explicit imports from modular files
from src.core.account import Account
from src.core.order import Order, OrderStatus, OrderType
from src.core.matching import MatchingEngine
from src.data.market import MarketDataFetcher
from src.data.storage import HistoricalDataStorage

# ❌ BAD: Importing from monolithic file
from src.core import (
    Account, Order, OrderStatus, OrderType, 
    MatchingEngine, Trade, Position, RiskManager,
    # ... 20 more classes
)
```

### Directory Structure Enforcement

```
✅ GOOD: Deep, organized hierarchy
src/
├── core/
│   ├── __init__.py
│   ├── account.py          # 80 lines
│   ├── order.py            # 120 lines
│   ├── trade.py            # 60 lines
│   ├── matching.py         # 200 lines
│   └── database.py         # 150 lines
├── strategies/
│   ├── __init__.py
│   ├── base.py             # 100 lines
│   ├── sma_strategy.py     # 150 lines
│   ├── grid_strategy.py    # 180 lines
│   └── indicators/
│       ├── __init__.py
│       ├── momentum.py     # 80 lines
│       └── volatility.py   # 90 lines

❌ BAD: Flat, monolithic structure
src/
├── __init__.py
├── core.py                 # 1500 lines - TOO BIG!
├── strategies.py           # 1200 lines - TOO BIG!
├── data.py                 # 800 lines - TOO BIG!
└── utils.py                # 600 lines - TOO BIG!
```

## Important Notes

- This is a **paper trading system** - results do not guarantee real trading performance
- Always test strategies thoroughly before considering real trading
- Keep API keys secure even for testnet/paper trading
- Perform weekly backups of the SQLite database file.
- Monitor log files for errors and warnings
- Use version control for strategy code
- **Monitor disk usage**: Logs and database can grow large over time
- **Set up log rotation**: Prevent disk space issues from uncontrolled log growth

## Disk Space Management

### Expected Storage Requirements

```
Component                    Size (Typical)       Retention
─────────────────────────────────────────────────────────────
SQLite Database              50-200 MB            Permanent
├─ candles (1 year)          ~30 MB               2 years
├─ orders/trades             ~10 MB               Permanent
└─ positions                 <1 MB                Permanent

Logs (per day)               10-100 MB            7-30 days
├─ app.log                   ~20 MB/day           7 days
├─ strategy.log              ~30 MB/day           14 days
├─ trade.log                 ~5 MB/day            30 days
└─ error.log                 ~1 MB/day            30 days

Total (steady state)         ~500 MB - 2 GB
```

### Automated Cleanup Strategy

1. **Loguru Auto-Rotation**: Configured in `config.yaml`
   - Daily rotation at midnight
   - Size-based rotation (500 MB threshold)
   - Automatic compression (zip)
   - Automatic deletion after retention period

2. **Database Cleanup**: Scheduled jobs
   ```python
   # Weekly cleanup job
   python -m src.core.database cleanup --candles --days 730  # Keep 2 years
   python -m src.core.database vacuum  # Reclaim space
   ```

3. **Manual Monitoring**:
   ```bash
   # Check disk usage
   python main.py status --disk
   
   # Output:
   # Database: 156 MB
   # Logs: 234 MB (7 days)
   # Total: 390 MB
   ```

## Code Quality Checklist

Before committing code, verify:

- [ ] ✅ No file exceeds 300 lines
- [ ] ✅ Each file has a single, clear responsibility
- [ ] ✅ No "god classes" with 15+ methods
- [ ] ✅ No `utils.py` or `helpers.py` dumping grounds
- [ ] ✅ Proper subdirectory organization
- [ ] ✅ Clear, descriptive file names
- [ ] ✅ All imports are explicit and organized
- [ ] ✅ Tests cover each module independently
- [ ] ✅ Documentation reflects modular structure

### Database Operations Checklist

- [ ] ✅ All position updates wrapped in transactions
- [ ] ✅ Positions and trades updated atomically
- [ ] ✅ Crash recovery tested (kill process and restart)
- [ ] ✅ Reconciliation job scheduled (daily/weekly)
- [ ] ✅ Database backup before live trading
- [ ] ✅ Audit logs for all position changes
- [ ] ✅ Indexes created for performance-critical queries

### Logging & Monitoring Checklist

- [ ] ✅ Log rotation configured in `config.yaml`
- [ ] ✅ Retention policies set (7-30 days)
- [ ] ✅ Compression enabled for old logs
- [ ] ✅ Separate log files by type (app, strategy, trade, error)
- [ ] ✅ Disk space monitoring enabled
- [ ] ✅ Log levels appropriate (DEBUG for dev, INFO for prod)
- [ ] ✅ Sensitive data (API keys, passwords) not logged

## Future Roadmap

### v2.0
- Web visualization interface
- Futures/derivatives support
- Multi-account management
- Strategy marketplace

### v3.0
- Machine learning strategy support
- Cloud deployment
- Mobile monitoring
