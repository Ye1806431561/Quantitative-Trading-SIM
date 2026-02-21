"""Real-time simulation main loop (Phase 3 Step 29)."""

from __future__ import annotations

import time
from typing import Any, Mapping

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.execution_cost import ExecutionCostProfile
from src.core.limit_matching import LimitOrderMatchingEngine
from src.core.matching import MatchingEngine
from src.core.order_service import OrderService
from src.core.risk import RiskLimits
from src.core.stop_trigger import StopTriggerEngine
from src.core.trade_service import TradeService
from src.data.realtime_market import RealtimeMarketDataService
from src.data.storage import HistoricalCandleStorage
from src.live.monitor import RuntimeMonitor
from src.live.loop_models import RealtimeLoopConfig, RealtimeLoopError
from src.live.loop_signal_executor import LoopSignalExecutor
from src.live.price_service import PriceService
from src.strategies.base import LiveStrategy, StrategyContext
from src.utils.logger import get_logger


class RealtimeSimulationLoop:
    """Main loop: fetch market data -> run strategy -> execute orders -> match -> update positions."""

    def __init__(
        self,
        database: SQLiteDatabase,
        account_service: AccountService,
        order_service: OrderService,
        trade_service: TradeService,
        market_service: RealtimeMarketDataService,
        price_service: PriceService,
        candle_storage: HistoricalCandleStorage,
        strategy: LiveStrategy,
        config: RealtimeLoopConfig,
        strategy_params: Mapping[str, Any] | None = None,
        cost_profile: ExecutionCostProfile | None = None,
        risk_limits: RiskLimits | None = None,
        monitor: RuntimeMonitor | None = None,
    ) -> None:
        self._db = database
        self._account_service = account_service
        self._order_service = order_service
        self._trade_service = trade_service
        self._market_service = market_service
        self._price_service = price_service
        self._candle_storage = candle_storage
        self._strategy = strategy
        self._config = config
        self._strategy_params = dict(strategy_params or {})
        self._cost_profile = cost_profile or ExecutionCostProfile()
        self._risk_limits = risk_limits
        self._monitor = monitor
        self._strategy_logger = get_logger("strategy")

        # Initialize matching engines
        self._market_matching = MatchingEngine(
            database=database,
            account_service=account_service,
            order_service=order_service,
            trade_service=trade_service,
            market_reader=market_service,
            cost_profile=cost_profile,
            risk_limits=risk_limits,
        )
        self._limit_matching = LimitOrderMatchingEngine(
            database=database,
            account_service=account_service,
            order_service=order_service,
            trade_service=trade_service,
            market_reader=market_service,
            cost_profile=cost_profile,
            risk_limits=risk_limits,
        )
        self._stop_trigger = StopTriggerEngine(
            database=database,
            account_service=account_service,
            order_service=order_service,
            trade_service=trade_service,
            market_reader=market_service,
            cost_profile=cost_profile,
            risk_limits=risk_limits,
        )

        # Signal executor handles order execution and strategy notifications
        self._signal_executor = LoopSignalExecutor(
            symbol=config.symbol,
            strategy=strategy,
            order_service=order_service,
            trade_service=trade_service,
            market_matching=self._market_matching,
            limit_matching=self._limit_matching,
            stop_trigger=self._stop_trigger,
        )

        self._running = False
        self._iteration_count = 0

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any],
        database: SQLiteDatabase,
        strategy: LiveStrategy,
        symbol: str,
        timeframe: str,
        tick_interval_seconds: float = 1.0,
        max_iterations: int | None = None,
        strategy_params: Mapping[str, Any] | None = None,
    ) -> "RealtimeSimulationLoop":
        """Factory method to construct loop from system config."""
        account_service = AccountService.from_config(database, config)
        order_service = OrderService(database, account_service)
        trade_service = TradeService(database, order_service)
        market_service = RealtimeMarketDataService.from_config(config)
        price_service = PriceService(database, account_service, market_service)
        candle_storage = HistoricalCandleStorage(database, market_service.get_klines)

        cost_profile = ExecutionCostProfile(
            maker_fee_rate=config.get("trading", {}).get("commission", {}).get("maker", 0.001),
            taker_fee_rate=config.get("trading", {}).get("commission", {}).get("taker", 0.001),
            slippage_rate=config.get("trading", {}).get("slippage", 0.0005),
        )

        risk_config = config.get("risk", {})
        risk_limits = RiskLimits(
            max_position_size=risk_config.get("max_position_size", 0.3),
            max_total_position=risk_config.get("max_total_position", 0.8),
            max_drawdown=risk_config.get("max_drawdown", 0.2),
        )

        loop_config = RealtimeLoopConfig(
            symbol=symbol,
            timeframe=timeframe,
            tick_interval_seconds=tick_interval_seconds,
            max_iterations=max_iterations,
        )

        return cls(
            database=database,
            account_service=account_service,
            order_service=order_service,
            trade_service=trade_service,
            market_service=market_service,
            price_service=price_service,
            candle_storage=candle_storage,
            strategy=strategy,
            config=loop_config,
            strategy_params=strategy_params,
            cost_profile=cost_profile,
            risk_limits=risk_limits,
            monitor=RuntimeMonitor.from_config(config),
        )

    def start(self) -> None:
        """Initialize strategy and start the main loop."""
        if self._running:
            raise RealtimeLoopError("loop is already running")

        context = StrategyContext(
            strategy_id=f"{self._strategy.name}_{self._config.symbol}_{int(time.time())}",
            symbol=self._config.symbol,
            timeframe=self._config.timeframe,
            parameters=self._strategy_params,
        )
        self._strategy.initialize(context)
        if self._monitor is not None:
            self._monitor.mark_started(
                strategy_name=self._strategy.name,
                symbol=self._config.symbol,
                timeframe=self._config.timeframe,
            )
        self._running = True

        try:
            self._run_loop()
        finally:
            self._running = False
            self._strategy.stop(reason="loop terminated")
            if self._monitor is not None:
                self._monitor.mark_stopped(reason="loop terminated")

    def _run_loop(self) -> None:
        """Execute the main simulation loop."""
        while self._running:
            if self._config.max_iterations is not None and self._iteration_count >= self._config.max_iterations:
                break
            self._iteration_count += 1

            try:
                # Step 1: Fetch latest market data
                snapshot = self._market_service.get_latest_price(self._config.symbol)
                timestamp_ms = snapshot.fetched_at_ms
                latest_price = snapshot.data.get("last_price")
                if self._monitor is not None:
                    self._monitor.mark_iteration(
                        iteration_count=self._iteration_count,
                        timestamp_ms=timestamp_ms,
                    )

                if latest_price is None or not snapshot.ok:
                    self._strategy_logger.warning(
                        "market snapshot unavailable symbol={} error={} fallback={} timeout={}",
                        self._config.symbol,
                        snapshot.error,
                        snapshot.fallback,
                        snapshot.timed_out,
                    )
                    if self._monitor is not None:
                        self._monitor.record_network_issue(
                            message=snapshot.error or "market snapshot unavailable",
                            reconnect_attempted=True,
                        )
                    time.sleep(self._config.tick_interval_seconds)
                    continue

                # Step 2: Persist latest candle to SQLite (runtime write path)
                self._persist_latest_candle(timestamp_ms, latest_price)

                # Step 3: Update positions with latest price
                try:
                    valuation = self._price_service.valuate_portfolio()
                    if self._monitor is not None:
                        self._monitor.record_account_change(
                            base_currency=self._account_service.base_currency,
                            total_assets=valuation.total_assets,
                            base_cash=valuation.base_cash,
                            positions_value=valuation.positions_value,
                        )
                except Exception as exc:
                    self._strategy_logger.warning("portfolio valuation failed: {}", exc)
                    if self._monitor is not None:
                        self._monitor.record_alert(
                            level="warning",
                            category="valuation",
                            message=f"portfolio valuation failed: {exc}",
                        )

                # Step 4: Process pending limit orders and stop triggers
                orders_matched = 0
                limit_result = self._limit_matching.process_limit_order_queue(self._config.symbol)
                orders_matched += len(limit_result.matched)
                stop_result = self._stop_trigger.process_trigger_orders(self._config.symbol)
                orders_matched += len(stop_result.matched)

                # Step 5-6: Run strategy with market data
                market_data = {
                    "symbol": self._config.symbol,
                    "timestamp": timestamp_ms,
                    "latest_price": latest_price,
                    "bid": snapshot.data.get("bid"),
                    "ask": snapshot.data.get("ask"),
                }
                try:
                    strategy_signal = self._strategy.run(market_data)
                except Exception as exc:
                    self._strategy_logger.error(
                        "strategy run error strategy={} symbol={} error={}",
                        self._strategy.name,
                        self._config.symbol,
                        exc,
                    )
                    if self._monitor is not None:
                        self._monitor.record_strategy_error(stage="run", error=exc)
                    strategy_signal = None

                # Step 7: Execute strategy signal
                if strategy_signal:
                    try:
                        self._signal_executor.execute_signal(strategy_signal)
                    except Exception as exc:
                        self._strategy_logger.error("signal execution failed: {}", exc)
                        if self._monitor is not None:
                            self._monitor.record_alert(
                                level="error",
                                category="signal_execution",
                                message=f"signal execution failed: {exc}",
                            )

                # Step 8: Notify strategy of order/trade updates
                try:
                    self._signal_executor.notify_strategy_updates()
                except Exception as exc:
                    self._strategy_logger.error("strategy notification failed: {}", exc)
                    if self._monitor is not None:
                        self._monitor.record_alert(
                            level="error",
                            category="strategy_notification",
                            message=f"strategy notification failed: {exc}",
                        )

            except Exception as exc:
                self._strategy_logger.error("realtime loop iteration {} failed: {}", self._iteration_count, exc)
                if self._monitor is not None:
                    self._monitor.record_alert(
                        level="error",
                        category="loop_iteration",
                        message=f"iteration {self._iteration_count} failed: {exc}",
                    )

            time.sleep(self._config.tick_interval_seconds)

    def _persist_latest_candle(self, timestamp_ms: int, price: float) -> None:
        """Persist latest price as a candle to SQLite (runtime write path)."""
        try:
            interval_ms = _timeframe_to_interval_ms(self._config.timeframe)
            bucket_ts = timestamp_ms - (timestamp_ms % interval_ms)
            with self._db.transaction() as tx:
                tx.execute(
                    """
                    INSERT INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT(symbol, timeframe, timestamp) DO UPDATE SET
                        high = MAX(candles.high, excluded.high),
                        low = MIN(candles.low, excluded.low),
                        close = excluded.close,
                        volume = candles.volume + excluded.volume;
                    """,
                    (
                        self._config.symbol,
                        self._config.timeframe,
                        bucket_ts,
                        price,
                        price,
                        price,
                        price,
                    ),
                )
        except Exception as exc:
            self._strategy_logger.warning("persist latest candle failed: {}", exc)

    def stop(self) -> None:
        """Stop the simulation loop."""
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if loop is currently running."""
        return self._running

    @property
    def iteration_count(self) -> int:
        """Get current iteration count."""
        return self._iteration_count


def _timeframe_to_interval_ms(timeframe: str) -> int:
    value = timeframe.strip().lower()
    if len(value) < 2:
        raise ValueError(f"invalid timeframe: {timeframe}")

    unit = value[-1]
    amount = int(value[:-1])
    if amount <= 0:
        raise ValueError(f"invalid timeframe amount: {timeframe}")

    if unit == "m":
        return amount * 60 * 1000
    if unit == "h":
        return amount * 60 * 60 * 1000
    if unit == "d":
        return amount * 24 * 60 * 60 * 1000
    raise ValueError(f"unsupported timeframe unit: {timeframe}")
