"""Backtrader backtest engine integration (step 26-27, refactored)."""

from __future__ import annotations

from typing import Any, Mapping

import backtrader as bt

from src.backtest.analyzers import AnalyzerMount
from src.backtest.result_builder import AnalyzerResultBuilder
from src.backtest.result_models import (
    BacktestRunRequest,
    BacktestRunResult,
    TradeRecord,
)
from src.core.database import SQLiteDatabase
from src.data.feed import BacktestDataSlice, SQLiteFeedError, SQLitePandasFeedFactory
from src.strategies.param_resolver import StrategyParamResolver
from src.strategies.registry import StrategyRegistry


class BacktestEngineError(RuntimeError):
    """Raised when backtest engine configuration or execution is invalid."""


class BacktestEngine:
    """Run Backtrader backtests using SQLite candles and PandasData feed."""

    def __init__(
        self,
        database: SQLiteDatabase,
        *,
        initial_capital: float,
        commission_rate: float,
        slippage_rate: float,
        data_read_source: str = "sqlite",
        strategies_config: Mapping[str, Any] | None = None,
        strategy_registry: StrategyRegistry | None = None,
    ) -> None:
        self._database = database
        self._initial_capital = self._validate_positive_number(
            initial_capital,
            "initial_capital",
        )
        self._commission_rate = self._validate_ratio(
            commission_rate,
            "commission_rate",
        )
        self._slippage_rate = self._validate_ratio(
            slippage_rate,
            "slippage_rate",
        )
        self._data_read_source = self._validate_data_source(data_read_source)
        self._feed_factory = SQLitePandasFeedFactory(database)
        self._strategy_registry = strategy_registry or StrategyRegistry.default()
        self._param_resolver = (
            StrategyParamResolver(strategies_config, self._strategy_registry)
            if strategies_config is not None
            else None
        )

    @classmethod
    def from_config(
        cls, database: SQLiteDatabase, config: Mapping[str, Any]
    ) -> "BacktestEngine":
        """Create backtest engine from runtime config."""
        initial_capital = cls._read_number(config, ("account", "initial_capital"))
        commission_rate = cls._read_number(config, ("trading", "commission", "taker"))
        slippage_rate = cls._read_number(config, ("trading", "slippage"))
        data_read_source = cls._read_optional_string(
            config,
            ("backtest", "data_read_source"),
            default="sqlite",
        )
        return cls(
            database=database,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
            data_read_source=data_read_source,
        )

    def run(self, request: BacktestRunRequest) -> BacktestRunResult:
        """Execute one backtest run and return comprehensive performance stats."""
        strategy_class = self._validate_strategy_class(request.strategy_class)
        feed_request = BacktestDataSlice(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_timestamp=request.start_timestamp,
            end_timestamp=request.end_timestamp,
        )
        try:
            dataframe = self._feed_factory.load_dataframe(feed_request)
        except SQLiteFeedError as exc:
            raise BacktestEngineError(str(exc)) from exc

        if dataframe.empty:
            raise BacktestEngineError(
                "No candle data found in SQLite for the requested symbol/timeframe/time range"
            )

        cerebro = bt.Cerebro(stdstats=False, tradehistory=True)
        feed = self._feed_factory.build_feed(dataframe, request.timeframe)
        cerebro.adddata(feed, name=f"{request.symbol}:{request.timeframe}")
        trade_records: list[TradeRecord] = []

        def _make_wrapper(base_class: type[bt.Strategy]) -> type[bt.Strategy]:
            class _TradeRecordWrapper(base_class):  # type: ignore[valid-type,misc]
                def notify_trade(self, trade: bt.Trade) -> None:
                    super().notify_trade(trade)
                    if not trade.isclosed:
                        return
                    trade_records.append(BacktestEngine._build_trade_record(trade))

            return _TradeRecordWrapper

        wrapped_strategy = _make_wrapper(strategy_class)
        params = dict(request.strategy_params)
        if self._param_resolver is not None:
            params = self._param_resolver.resolve_for_class(strategy_class, params)
        cerebro.addstrategy(wrapped_strategy, **params)

        cerebro.broker.setcash(self._initial_capital)
        cerebro.broker.setcommission(commission=self._commission_rate)
        if self._slippage_rate > 0:
            cerebro.broker.set_slippage_perc(perc=self._slippage_rate)

        AnalyzerMount.attach_analyzers(cerebro)

        strategies = cerebro.run()

        # Extract analyzer results (step 27)
        analyzer_results = AnalyzerMount.extract_results(strategies)

        # Build unified result structure
        final_value = float(cerebro.broker.getvalue())
        pnl = final_value - self._initial_capital
        total_return_pct = (pnl / self._initial_capital) * 100.0

        # Use AnalyzerResultBuilder to transform raw analyzer outputs
        builder = AnalyzerResultBuilder()
        trade_stats = builder.build_trade_stats(analyzer_results["trades"])
        risk_metrics = builder.build_risk_metrics(
            analyzer_results["sharpe"],
            analyzer_results["drawdown"],
        )
        returns_analysis = builder.build_returns_analysis(analyzer_results["returns"])
        time_series_returns = builder.build_time_series(analyzer_results["timereturns"])

        return BacktestRunResult(
            symbol=request.symbol.strip().upper(),
            timeframe=request.timeframe.strip(),
            data_source=self._data_read_source,
            initial_capital=self._initial_capital,
            final_value=final_value,
            pnl=pnl,
            total_return_pct=total_return_pct,
            bars_processed=len(dataframe),
            trade_stats=trade_stats,
            risk_metrics=risk_metrics,
            returns_analysis=returns_analysis,
            time_series_returns=time_series_returns,
            trade_log=tuple(trade_records),
        )

    @staticmethod
    def _build_trade_record(trade: bt.Trade) -> TradeRecord:
        entry_dt = bt.num2date(trade.dtopen)
        exit_dt = bt.num2date(trade.dtclose)
        entry_price, exit_price, total_size = (
            BacktestEngine._extract_trade_fill_summary(trade)
        )
        return TradeRecord(
            entry_time=entry_dt.isoformat(),
            exit_time=exit_dt.isoformat(),
            side="long" if trade.long else "short",
            size=total_size,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_gross=float(trade.pnl),
            pnl_net=float(trade.pnlcomm),
        )

    @staticmethod
    def _extract_trade_fill_summary(trade: bt.Trade) -> tuple[float, float, float]:
        history = getattr(trade, "history", [])
        open_size = 0.0
        open_notional = 0.0
        close_size = 0.0
        close_notional = 0.0

        for record in history:
            event = getattr(record, "event", None)
            if event is None:
                continue
            raw_size = getattr(event, "size", None)
            raw_price = getattr(event, "price", None)
            if not isinstance(raw_size, (int, float)) or isinstance(raw_size, bool):
                continue
            if not isinstance(raw_price, (int, float)) or isinstance(raw_price, bool):
                continue

            size = float(raw_size)
            price = float(raw_price)
            abs_size = abs(size)
            if abs_size <= 1e-12:
                continue

            notional = abs_size * price
            if trade.long:
                if size > 0:
                    open_size += abs_size
                    open_notional += notional
                else:
                    close_size += abs_size
                    close_notional += notional
            else:
                if size < 0:
                    open_size += abs_size
                    open_notional += notional
                else:
                    close_size += abs_size
                    close_notional += notional

        entry_price = open_notional / open_size if open_size > 0 else float(trade.price)
        exit_price = (
            close_notional / close_size if close_size > 0 else float(trade.price)
        )
        total_size = open_size if open_size > 0 else close_size
        return entry_price, exit_price, total_size

    @staticmethod
    def _validate_strategy_class(
        strategy_class: type[bt.Strategy],
    ) -> type[bt.Strategy]:
        if not isinstance(strategy_class, type) or not issubclass(
            strategy_class, bt.Strategy
        ):
            raise BacktestEngineError(
                "strategy_class must be a subclass of backtrader.Strategy"
            )
        return strategy_class

    @staticmethod
    def _validate_data_source(data_read_source: str) -> str:
        if not isinstance(data_read_source, str) or not data_read_source.strip():
            raise BacktestEngineError("data_read_source must not be empty")
        normalized = data_read_source.strip().lower()
        if normalized != "sqlite":
            raise BacktestEngineError(
                "backtest.data_read_source must be 'sqlite' "
                "(CSV/Parquet runtime reads are not allowed)"
            )
        return normalized

    @staticmethod
    def _validate_positive_number(value: float, label: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise BacktestEngineError(f"{label} must be a number")
        numeric = float(value)
        if numeric <= 0:
            raise BacktestEngineError(f"{label} must be > 0")
        return numeric

    @staticmethod
    def _validate_ratio(value: float, label: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise BacktestEngineError(f"{label} must be a number")
        numeric = float(value)
        if numeric < 0 or numeric > 1:
            raise BacktestEngineError(f"{label} must be within [0, 1]")
        return numeric

    @staticmethod
    def _read_number(config: Mapping[str, Any], path: tuple[str, ...]) -> float:
        current: Any = config
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                raise BacktestEngineError(f"Missing config key: {'.'.join(path)}")
            current = current[key]
        if not isinstance(current, (int, float)) or isinstance(current, bool):
            raise BacktestEngineError(f"{'.'.join(path)} must be a number")
        return float(current)

    @staticmethod
    def _read_optional_string(
        config: Mapping[str, Any],
        path: tuple[str, ...],
        *,
        default: str,
    ) -> str:
        current: Any = config
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                return default
            current = current[key]
        if not isinstance(current, str):
            raise BacktestEngineError(f"{'.'.join(path)} must be a string")
        return current
