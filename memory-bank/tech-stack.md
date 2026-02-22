# 虚拟货币量化交易模拟盘系统 - 技术栈文档

## 设计原则

**最简单 + 最健壮 = 只选必需品，每个都是业界验证的稳定方案**

- ✅ 优先使用 Python 标准库
- ✅ 只引入成熟稳定的第三方库
- ✅ 避免过度工程化
- ✅ 保持架构简单清晰

---

## 核心技术栈（最小化）

### 1. 编程语言
```
Python 3.10+
```
**理由**: 
- 量化交易生态最成熟
- 类型提示支持（3.10+ 更完善）
- 异步支持稳定

### 2. 量化交易核心（3个库）
```
ccxt==4.2.0              # 交易所 API 统一接口
backtrader==1.9.78.123   # 专业回测引擎
pandas==2.1.0            # 数据处理
```
**理由**:
- CCXT: 支持 100+ 交易所，API 稳定
- Backtrader: 专业回测框架，文档完善，社区活跃
- Pandas: 数据处理标准库，与 Backtrader 无缝集成

### 3. 数据存储（1个库）
```
SQLite (Python 标准库自带)
```
**理由**:
- 零配置，无需安装数据库服务
- 单文件存储，易于备份
- 足够处理模拟盘数据量
- 支持事务，数据安全

**数据文件结构**:
```
data/
├── database/
│   └── trading.db          # SQLite 数据库（订单、交易记录）
└── historical/
    ├── BTC_USDT_1h.csv     # 历史 K 线数据（CSV 格式）
    └── ETH_USDT_1h.csv
```

### 4. 配置管理（2个库）
```
pyyaml==6.0.1            # YAML 配置文件
python-dotenv==1.0.0     # 环境变量管理
```
**理由**:
- YAML: 人类可读，适合策略参数配置
- dotenv: API 密钥等敏感信息管理

### 5. 日志系统（1个库）
```
loguru==0.7.2
```
**理由**:
- 比标准 logging 简单 10 倍
- 自动日志轮转
- 彩色输出，易于调试
- 异常追踪完善

### 6. CLI 界面（1个库）
```
rich==13.7.0
```
**理由**:
- 美化终端输出
- 进度条、表格、语法高亮
- 零学习成本

### 7. 可视化（1个库）
```
matplotlib==3.8.0
```
**理由**:
- Backtrader 原生支持
- 稳定可靠，文档完善
- 足够绘制资金曲线、K 线图

---

## 完整依赖清单

```txt
# requirements.txt

# 核心交易
ccxt==4.2.0
backtrader==1.9.78.123

# 数据处理
pandas==2.1.0
numpy==1.26.0

# 配置管理
pyyaml==6.0.1
python-dotenv==1.0.0

# 日志与 CLI
loguru==0.7.2
rich==13.7.0

# 可视化
matplotlib==3.8.0

# 开发工具（可选）
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.12.0
```

**总计**: 仅 11 个核心依赖（不含开发工具）

### 开发安全工具（可选，推荐）
```
Varlock CLI              # 环境变量敏感字段校验与脱敏输出
Git hooks (pre-commit)   # 提交前阻断敏感文件与疑似密钥文本
```
**说明**:
- 上述工具属于开发流程防护，不属于应用运行时 Python 依赖；
- 当前仓库通过 `.env.schema`、`scripts/check-secrets.sh`、`.githooks/pre-commit` 接入该能力。

---

## 项目结构（最简化）

```
quantitative-trading-simulator/
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                    # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── account.py          # 账户管理
│   │   ├── order.py            # 订单模型
│   │   ├── matching.py         # 模拟撮合引擎
│   │   └── database.py         # SQLite 封装
│   │
│   ├── data/                    # 数据层
│   │   ├── __init__.py
│   │   ├── market.py           # CCXT 市场数据获取
│   │   └── storage.py          # 历史数据存储
│   │
│   ├── strategies/              # 策略层
│   │   ├── __init__.py
│   │   ├── base.py             # 策略基类
│   │   ├── sma_strategy.py     # 示例：双均线策略
│   │   └── grid_strategy.py    # 示例：网格策略
│   │
│   ├── backtest/                # 回测引擎
│   │   ├── __init__.py
│   │   ├── engine.py           # Backtrader 集成
│   │   └── analyzers.py        # 性能分析
│   │
│   ├── live/                    # 实时模拟交易
│   │   ├── __init__.py
│   │   └── simulator.py        # 实时模拟器
│   │
│   ├── utils/                   # 工具函数
│   │   ├── __init__.py
│   │   ├── logger.py           # 日志配置
│   │   └── config.py           # 配置加载
│   │
│   └── cli.py                   # 命令行入口
│
├── config/
│   ├── config.yaml             # 主配置文件
│   ├── strategies.yaml         # 策略参数配置
│   └── .env.example            # 环境变量模板
│
├── data/
│   ├── database/               # SQLite 数据库
│   └── historical/             # 历史数据
│
├── logs/                        # 日志目录
│
├── tests/                       # 测试
│   ├── test_account.py
│   ├── test_matching.py
│   └── test_strategies.py
│
├── requirements.txt             # 依赖清单
├── .env                         # 环境变量（不提交到 Git）
├── .gitignore
├── README.md
└── main.py                      # 程序入口
```

**总计**: 约 20 个核心文件

---

## 数据库设计（SQLite）

### 表结构

```sql
-- 账户表
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    currency TEXT NOT NULL,
    balance REAL NOT NULL,
    available REAL NOT NULL,
    frozen REAL NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 订单表
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    type TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL,
    amount REAL NOT NULL,
    filled REAL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 交易记录表
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    fee REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- 策略运行记录表
CREATE TABLE strategy_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    initial_capital REAL,
    final_capital REAL,
    total_return REAL,
    max_drawdown REAL,
    sharpe_ratio REAL,
    status TEXT NOT NULL
);
```

---

## 配置文件示例

### config.yaml
```yaml
# 系统配置
system:
  log_level: INFO
  log_dir: logs
  data_dir: data

# 交易所配置
exchange:
  name: binance
  testnet: true
  rate_limit: true

# 账户配置
account:
  initial_capital: 10000.0
  base_currency: USDT

# 交易配置
trading:
  commission:
    maker: 0.001  # 0.1%
    taker: 0.001  # 0.1%
  slippage: 0.0005  # 0.05%
  
# 风控配置
risk:
  max_position_size: 0.3  # 单笔最大仓位 30%
  max_total_position: 0.8  # 总仓位上限 80%
  max_drawdown: 0.2  # 最大回撤 20%

# 回测配置
backtest:
  default_timeframe: 1h
  default_period: 90  # 天数
```

### strategies.yaml
```yaml
# 双均线策略
sma_strategy:
  enabled: true
  params:
    fast_period: 10
    slow_period: 30
    position_size: 0.2

# 网格策略
grid_strategy:
  enabled: false
  params:
    grid_num: 10
    price_range: 0.1
    position_size: 0.1
```

### .env.example
```bash
# 交易所 API（模拟盘可选）
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_API_SECRET=your_api_secret_here

# 数据库
DATABASE_PATH=data/database/trading.db

# 日志
LOG_LEVEL=INFO
```

---

## 核心技术决策

### 为什么不用这些？

| 技术 | 不选择的理由 |
|------|------------|
| FastAPI | CLI 程序不需要 Web 框架，Phase 1 过度设计 |
| Streamlit | 先实现核心功能，Web 界面可后续添加 |
| Redis | 模拟盘数据量小，SQLite 足够 |
| Docker | 本地开发工具，无需容器化 |
| PostgreSQL | SQLite 更简单，性能足够 |
| Celery | 无需分布式任务队列 |
| TA-Lib | Backtrader 内置指标足够，避免编译依赖 |

### 为什么选择这些？

| 技术 | 选择理由 |
|------|---------|
| Python 3.10+ | 类型提示完善，异步稳定 |
| CCXT | 行业标准，支持所有主流交易所 |
| Backtrader | 专业回测框架，功能完整 |
| SQLite | 零配置，单文件，事务支持 |
| Loguru | 比 logging 简单 10 倍 |
| Rich | 最佳 CLI 体验 |
| Matplotlib | Backtrader 原生支持 |

---

## 开发流程

### 1. 环境搭建
```bash
# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp config/.env.example .env

# （推荐）启用提交前密钥检查
git config core.hooksPath .githooks
varlock load
```

### 2. 初始化数据库
```bash
python -m src.core.database init
```

### 3. 下载历史数据
```bash
python main.py download --symbol BTC/USDT --timeframe 1h --days 90
```

### 4. 运行回测
```bash
python main.py backtest --strategy sma --symbol BTC/USDT
```

### 5. 启动实时模拟
```bash
python main.py live --strategy sma --symbol BTC/USDT
```

---

## 性能指标

### 预期性能
- 回测速度: 1 年 1 小时 K 线数据 < 5 秒
- 实时延迟: < 1 秒
- 内存占用: < 200MB
- 数据库大小: < 100MB（1 年数据）

### 扩展性
- 支持同时运行 5+ 策略
- 支持 10+ 交易对
- 支持 3 年历史数据回测

---

## 测试策略

### 单元测试覆盖
- 账户管理模块: 100%
- 订单撮合引擎: 100%
- 策略逻辑: 80%+

### 测试命令
```bash
# 运行所有测试
pytest

# 查看覆盖率
pytest --cov=src --cov-report=html
```

---

## 部署建议

### Phase 1（当前）
- 本地运行
- CLI 界面
- SQLite 数据库

### Phase 2（可选升级）
- 添加 Streamlit Web 界面
- 添加 FastAPI 后端 API
- 保持 SQLite（无需升级数据库）

### Phase 3（生产级）
- Docker 容器化
- TimescaleDB 替换 SQLite
- Prometheus + Grafana 监控

---

## 风险控制

### 依赖风险
- 所有依赖都是成熟稳定的库
- 定期更新补丁版本
- 锁定主版本号避免破坏性更新

### 数据风险
- SQLite 事务保证数据一致性
- 定期备份数据库文件
- 历史数据使用 CSV 格式，易于恢复

### 性能风险
- SQLite 性能足够处理模拟盘数据量
- 如需扩展，可无缝迁移到 PostgreSQL
- 代码设计保持数据库抽象层

---

## 总结

### 技术栈特点
✅ **简单**: 仅 11 个核心依赖  
✅ **健壮**: 所有库都是业界验证的稳定方案  
✅ **高效**: 零配置，开箱即用  
✅ **可扩展**: 架构清晰，易于升级  

### 适用场景
- ✅ 个人量化交易学习
- ✅ 策略开发与验证
- ✅ 小规模模拟交易
- ✅ 快速原型开发

### 不适用场景
- ❌ 高频交易（毫秒级延迟）
- ❌ 大规模分布式部署
- ❌ 实盘生产环境（需更多安全措施）

---

**文档版本**: v1.0  
**创建日期**: 2026-02-14  
**技术栈原则**: 最简单 + 最健壮 = 只选必需品
