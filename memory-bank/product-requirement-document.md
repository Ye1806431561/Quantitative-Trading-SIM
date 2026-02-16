# 虚拟货币量化交易模拟盘系统 - 产品需求文档

## 1. 产品概述

### 1.1 产品定位
基于 Python 和 CCXT 库开发的虚拟货币量化交易模拟盘系统，为量化交易策略提供无风险的回测和实时模拟交易环境。

### 1.2 目标用户
- 量化交易初学者
- 策略开发者
- 需要验证交易策略的投资者

### 1.3 核心价值
- 零资金风险的策略验证
- 真实市场数据模拟
- 完整的交易流程体验
- 策略性能评估与优化

## 2. 功能需求

### 2.1 核心功能模块

#### 2.1.1 账户管理模块
- **虚拟账户初始化**
  - 设置初始资金（如 10,000 USDT）
  - 支持多币种余额管理
  - 账户资产实时计算
  
- **资产查询**
  - 查看当前持仓
  - 查看可用余额
  - 查看冻结资金
  - 总资产估值（按实时价格）

#### 2.1.2 市场数据模块
- **实时行情获取**
  - 通过 CCXT 连接交易所 API
  - 支持多个主流交易所（Binance、OKX、Bybit 等）
  - 获取实时价格、深度、K线数据
  
- **历史数据管理**
  - K线数据下载与存储
  - 支持多时间周期（1m、5m、15m、1h、4h、1d）
  - 本地数据缓存机制

#### 2.1.3 交易执行模块
- **订单类型支持**
  - 市价单（Market Order）
  - 限价单（Limit Order）
  - 止损单（Stop Loss）
  - 止盈单（Take Profit）
  
- **订单管理**
  - 下单
  - 撤单
  - 订单状态查询
  - 订单历史记录
  
- **模拟撮合引擎**
  - 基于实时价格的订单撮合
  - 限价单挂单队列管理
  - 滑点模拟（可配置）
  - 手续费计算（Maker/Taker）

#### 2.1.4 策略引擎模块（双引擎架构）
- **策略抽象层**
  - 定义统一的策略接口规范
  - 策略生命周期管理（初始化、运行、停止）
  - 多策略并行支持
  - 策略适配器：自动转换策略在回测/实时模式下运行
  
- **回测策略实现**
  - 策略继承 `backtrader.Strategy` 基类
  - 实现标准生命周期方法：
    - `__init__()` - 初始化指标和参数
    - `next()` - 每个数据点的策略逻辑
    - `notify_order()` - 订单状态通知
    - `notify_trade()` - 交易完成通知
  - 使用 Backtrader 内置指标库（bt.indicators.SMA, RSI, MACD 等）
  
- **实时交易策略实现**
  - 策略继承自定义 `LiveStrategy` 基类
  - 实现实时数据处理和订单执行
  - 策略适配器将回测策略逻辑映射到实时引擎
  
- **内置策略示例**
  - 简单移动平均线策略（SMA）- 双模式支持
  - 网格交易策略 - 双模式支持
  - 布林带策略 - 双模式支持
  - 自定义策略接口

- **策略参数配置**
  - 参数化策略设计
  - 配置文件支持（JSON/YAML）
  - 参数优化接口（基于 Backtrader Optimizer）

#### 2.1.5 风险控制模块
- **仓位管理**
  - 单笔交易最大金额限制
  - 总仓位比例控制
  - 单币种持仓限制
  
- **风险指标**
  - 最大回撤监控
  - 止损机制
  - 爆仓保护

#### 2.1.6 回测模块（基于 Backtrader）
- **引擎集成**
  - 集成 Backtrader Cerebro 作为回测核心引擎
  - 实现 PandasData 数据馈送接口，将 CCXT 获取的历史 K 线（DataFrame）直接注入 Backtrader
  - 保持事件驱动架构，确保回测的准确性和真实性
  - 支持多品种、多周期同时回测
  
- **回测配置映射**
  - 时间范围选择（start_date, end_date）
  - 初始资金设置 → `cerebro.broker.setcash()`
  - 手续费率配置 → `cerebro.broker.setcommission(commission=0.001, margin=None)`
  - 滑点设置 → 自定义 Sizer 或 Broker
  - 订单类型支持（市价、限价、止损、止盈）
  
- **标准化分析**
  - 集成 Backtrader 内置分析器（Analyzers）：
    - `SharpeRatio` - 夏普比率
    - `DrawDown` - 最大回撤分析
    - `TradeAnalyzer` - 交易统计（胜率、盈亏比等）
    - `Returns` - 收益率分析
    - `TimeReturn` - 时间序列收益
  - 自定义分析器扩展接口
  
- **回测结果输出**
  - 生成详细的回测报告
  - 资金曲线、回撤曲线可视化
  - 交易记录导出（CSV/JSON）

#### 2.1.7 性能分析模块
- **交易统计**
  - 总交易次数
  - 盈利/亏损次数
  - 胜率计算
  - 盈亏比
  
- **收益指标**
  - 总收益率
  - 年化收益率
  - 最大回撤
  - 夏普比率
  - 索提诺比率
  
- **可视化报表**
  - 资金曲线图
  - 回撤曲线图
  - 交易分布图
  - 持仓时间分析

#### 2.1.8 日志与监控模块
- **日志记录**
  - 交易日志
  - 策略运行日志
  - 错误日志
  - 日志分级（DEBUG、INFO、WARNING、ERROR）
  
- **实时监控**
  - 策略运行状态
  - 账户资产变化
  - 异常告警

### 2.2 用户界面

#### 2.2.1 命令行界面（CLI）
- 交互式命令行工具
- 支持常用操作命令
  - `start` - 启动策略
  - `stop` - 停止策略
  - `status` - 查看状态
  - `balance` - 查看余额
  - `orders` - 查看订单
  - `backtest` - 运行回测

#### 2.2.2 Web 界面（可选）
- 基于 Flask/FastAPI 的 Web 服务
- 实时数据展示
- 策略控制面板
- 图表可视化

## 3. 技术需求

### 3.1 技术栈
- **编程语言**: Python 3.8+
- **核心库**: 
  - CCXT - 交易所 API 统一接口
  - Backtrader - 专业的量化回测框架
  - Pandas - 数据处理
  - NumPy - 数值计算
  - Matplotlib/Plotly - 数据可视化
  
- **数据存储**:
  - SQLite - 本地数据库（订单、交易记录）
  - CSV/Parquet - 历史数据存储
  
- **配置管理**:
  - YAML/JSON - 配置文件
  - python-dotenv - 环境变量管理

### 3.2 系统架构（双引擎设计）
```
┌─────────────────────────────────────────────────────┐
│                   用户界面层                          │
│            (CLI / Web Dashboard)                    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                   策略抽象层                          │
│         (统一策略接口 + 策略适配器)                   │
└─────────┬──────────────────────────┬────────────────┘
          │                          │
┌─────────▼─────────┐      ┌─────────▼─────────────┐
│   回测引擎模式     │      │   实时交易模式         │
│  (Backtrader)     │      │  (自研引擎)           │
│                   │      │                       │
│ • Cerebro 引擎    │      │ • 实时数据流          │
│ • 历史数据回放    │      │ • 订单执行            │
│ • 内置分析器      │      │ • 状态监控            │
└─────────┬─────────┘      └─────────┬─────────────┘
          │                          │
          └──────────┬───────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                  业务逻辑层                           │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │
│  │账户  │ │交易  │ │风控  │ │分析  │ │撮合  │    │
│  │管理  │ │执行  │ │模块  │ │模块  │ │引擎  │    │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                   数据层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │市场数据  │  │本地存储  │  │回测数据  │         │
│  │(CCXT)    │  │(SQLite)  │  │(CSV/HDF5)│         │
│  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────┘
```

**架构说明**：
- **策略抽象层**：提供统一的策略编写接口，策略代码可在两种模式下运行
- **双引擎模式**：
  - 回测模式使用 Backtrader 的成熟框架和分析工具
  - 实时模式使用自研引擎处理实时数据流和订单执行
- **策略适配器**：自动将策略逻辑转换为对应引擎的执行格式

### 3.3 数据模型

#### 账户表 (accounts)
```sql
- id: 主键
- currency: 币种
- balance: 总余额
- available: 可用余额
- frozen: 冻结金额
- updated_at: 更新时间
```

#### 订单表 (orders)
```sql
- id: 订单ID
- symbol: 交易对
- type: 订单类型
- side: 买/卖
- price: 价格
- amount: 数量
- filled: 已成交数量
- status: 订单状态
- created_at: 创建时间
- updated_at: 更新时间
```

#### 交易记录表 (trades)
```sql
- id: 交易ID
- order_id: 订单ID
- symbol: 交易对
- side: 买/卖
- price: 成交价格
- amount: 成交数量
- fee: 手续费
- timestamp: 时间戳
```

## 4. 非功能需求

### 4.1 性能要求
- 实时行情延迟 < 1秒
- 订单处理响应时间 < 100ms
- 回测速度：1年数据 < 10秒（1小时K线）
- 支持同时运行 5+ 策略

### 4.2 可靠性要求
- 异常处理机制完善
- 网络断线自动重连
- 数据持久化保证
- 策略崩溃隔离

### 4.3 可扩展性
- 模块化设计
- 插件式策略架构
- 支持自定义指标
- 支持新交易所接入

### 4.4 安全性
- API密钥加密存储（虽然是模拟盘，但保持良好习惯）
- 配置文件权限控制
- 日志脱敏处理

## 5. 项目规划

### 5.1 开发阶段

#### Phase 1: 基础框架（2周）
- [ ] 项目结构搭建
- [ ] CCXT 集成与市场数据获取
- [ ] 虚拟账户管理
- [ ] 基础订单执行

#### Phase 2: 核心功能（3周）
- [ ] 模拟撮合引擎
- [ ] 策略引擎框架
- [ ] 回测引擎
- [ ] 数据存储与管理

#### Phase 3: 策略与分析（2周）
- [ ] 内置策略实现
- [ ] 性能分析模块
- [ ] 可视化报表
- [ ] 风险控制模块

#### Phase 4: 优化与完善（1周）
- [ ] CLI 界面优化
- [ ] 文档编写
- [ ] 单元测试
- [ ] 性能优化

### 5.2 里程碑
- **M1**: 完成基础交易功能（Week 2）
- **M2**: 完成回测引擎（Week 5）
- **M3**: 完成策略示例（Week 7）
- **M4**: 发布 v1.0（Week 8）

## 6. 使用场景示例

### 6.1 场景一：策略回测（Backtrader 引擎）
```python
# 用户加载历史数据，配置策略参数，运行回测
from backtrader import Cerebro
from strategies import SMAStrategy

cerebro = Cerebro()
cerebro.addstrategy(SMAStrategy, fast=10, slow=30)

# 加载 CCXT 历史数据
data = CCXTData(
    exchange='binance',
    symbol='BTC/USDT',
    timeframe='1h',
    fromdate=datetime(2024, 1, 1),
    todate=datetime(2024, 12, 31)
)
cerebro.adddata(data)

# 配置回测参数
cerebro.broker.setcash(10000.0)
cerebro.broker.setcommission(commission=0.001)

# 添加分析器
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

# 运行回测
results = cerebro.run()
cerebro.plot()

# 查看分析结果
print(f"夏普比率: {results[0].analyzers.sharpe.get_analysis()}")
print(f"最大回撤: {results[0].analyzers.drawdown.get_analysis()}")
```

### 6.2 场景二：实时模拟交易（自研引擎）
```python
# 用户启动实时模拟交易（使用相同的策略逻辑）
from strategies import SMAStrategy
from live_engine import LiveSimulator

simulator = LiveSimulator(
    exchange='binance',
    strategy=SMAStrategy(fast=10, slow=30),  # 同样的策略类
    symbol='BTC/USDT',
    initial_capital=10000
)

# 策略适配器自动将 Backtrader 策略转换为实时模式
simulator.start()

# 实时监控
simulator.get_status()  # 查看运行状态
simulator.get_positions()  # 查看持仓
simulator.stop()  # 停止策略
```

### 6.3 场景三：策略优化（Backtrader Optimizer）
```python
# 用户对策略参数进行网格搜索优化
from backtrader import Cerebro

cerebro = Cerebro()

# 使用 optstrategy 进行参数优化
cerebro.optstrategy(
    SMAStrategy,
    fast=range(5, 20),
    slow=range(20, 50)
)

# 加载数据
data = CCXTData(exchange='binance', symbol='BTC/USDT', ...)
cerebro.adddata(data)

cerebro.broker.setcash(10000.0)
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

# 运行优化
results = cerebro.run()

# 找出最佳参数组合
best_sharpe = -999
best_params = None
for result in results:
    sharpe = result[0].analyzers.sharpe.get_analysis()['sharperatio']
    if sharpe and sharpe > best_sharpe:
        best_sharpe = sharpe
        best_params = result[0].params

print(f"最佳参数: fast={best_params.fast}, slow={best_params.slow}")
print(f"最佳夏普比率: {best_sharpe}")
```

## 7. 风险与限制

### 7.1 技术风险
- CCXT API 限流问题
- 网络连接稳定性
- 数据质量依赖交易所

### 7.2 功能限制
- 模拟盘与实盘存在差异（滑点、深度）
- 不支持合约交易（初期）
- 不支持高频交易策略

### 7.3 免责声明
- 本系统仅供学习和研究使用
- 模拟盘结果不代表实盘表现
- 实盘交易需谨慎，风险自负

## 8. 后续迭代方向

### v2.0 规划
- Web 可视化界面
- 合约交易支持
- 多账户管理
- 策略市场（分享与下载策略）
- 实盘对接（谨慎）

### v3.0 规划
- 机器学习策略支持
- 社区功能
- 云端部署
- 移动端监控

## 9. 附录

### 9.1 参考资料
- CCXT 官方文档: https://docs.ccxt.com/
- 量化交易策略参考
- Python 最佳实践

### 9.2 术语表
- **CCXT**: CryptoCurrency eXchange Trading Library
- **回测**: 使用历史数据验证策略
- **滑点**: 预期价格与实际成交价格的差异
- **夏普比率**: 风险调整后收益指标
- **最大回撤**: 资金曲线最大跌幅

---

**文档版本**: v1.0  
**创建日期**: 2026-02-14  
**最后更新**: 2026-02-14  
**负责人**: [待填写]
