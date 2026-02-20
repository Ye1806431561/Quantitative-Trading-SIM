"""Tests for BacktraderAdapter (Step 30).

Covers:
- Initialisation & warmup
- Signal generation (buy/sell)
- History-only signals are ignored (only last-bar signal is emitted)
- Input protocol compatibility (snapshot → OHLCV)
- Output protocol compatibility (always includes amount)
- Signal consistency: same strategy produces same signal in backtest & adapter
"""

from __future__ import annotations

from typing import Any

import backtrader as bt
import pytest

from src.core.enums import StrategyRunStatus
from src.strategies.adapter import BacktraderAdapter, _snapshot_to_ohlcv
from src.strategies.base import StrategyContext


# ---------------------------------------------------------------------------
# Dummy strategies
# ---------------------------------------------------------------------------

class ThresholdStrategy(bt.Strategy):
    """Buy when close > threshold, sell when close < threshold."""

    params = (("threshold", 50000),)

    def next(self):
        if self.data.close[0] > self.params.threshold:
            if not self.position:
                self.buy()
        elif self.data.close[0] < self.params.threshold:
            if self.position:
                self.sell()


class AlwaysBuyStrategy(bt.Strategy):
    """Buys on every bar — useful for testing last-bar-only capture."""

    def next(self):
        if not self.position:
            self.buy()


class SMAStrategy(bt.Strategy):
    """Simple moving average crossover — used for consistency test."""

    params = (("fast", 3), ("slow", 5))

    def __init__(self):
        self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.fast)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.slow)

    def next(self):
        if self.sma_fast[0] > self.sma_slow[0]:
            if not self.position:
                self.buy()
        elif self.sma_fast[0] < self.sma_slow[0]:
            if self.position:
                self.sell()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candle(timestamp_ms: int, close: float, *, vol: float = 100) -> dict[str, Any]:
    """Build a minimal OHLCV dict."""
    return {
        "timestamp": timestamp_ms,
        "open": close,
        "high": close + 10,
        "low": close - 10,
        "close": close,
        "volume": vol,
    }


def _make_snapshot(timestamp_ms: int, price: float) -> dict[str, Any]:
    """Build a dict that looks like what ``RealtimeSimulationLoop`` passes."""
    return {
        "symbol": "BTC/USDT",
        "timestamp": timestamp_ms,
        "latest_price": price,
        "bid": price - 5,
        "ask": price + 5,
    }


def _ctx(warmup: list[dict] | None = None) -> StrategyContext:
    params: dict[str, Any] = {}
    if warmup is not None:
        params["warmup_candles"] = warmup
    return StrategyContext(
        strategy_id="test",
        symbol="BTC/USDT",
        timeframe="1h",
        parameters=params,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInitialisation:
    def test_status_running_after_init(self):
        adapter = BacktraderAdapter("A", ThresholdStrategy)
        adapter.initialize(_ctx())
        assert adapter.status == StrategyRunStatus.RUNNING
        assert adapter.name == "A"

    def test_warmup_candles_loaded(self):
        warmup = [_make_candle(i * 1000, 40000) for i in range(5)]
        adapter = BacktraderAdapter("W", ThresholdStrategy, lookback_window=10)
        adapter.initialize(_ctx(warmup))
        assert len(adapter._history) == 5

    def test_warmup_accepts_snapshot_format(self):
        """warmup_candles may also be snapshot dicts (latest_price)."""
        warmup = [_make_snapshot(i * 1000, 40000) for i in range(3)]
        adapter = BacktraderAdapter("S", ThresholdStrategy, lookback_window=10)
        adapter.initialize(_ctx(warmup))
        assert len(adapter._history) == 3
        assert adapter._history[0]["close"] == 40000


class TestSignalGeneration:
    def test_buy_signal_when_condition_met(self):
        adapter = BacktraderAdapter(
            "Buy", ThresholdStrategy,
            bt_params={"threshold": 50000},
            min_bars=2, position_size=0.5,
        )
        adapter.initialize(_ctx())

        # Feed bars below threshold — no signal
        for i in range(5):
            sig = adapter.on_run(_make_candle((i + 1) * 1000, 40000))
        assert sig is None  # still below

        # Feed bar above threshold — BUY
        sig = adapter.on_run(_make_candle(6000, 51000))
        assert sig is not None
        assert sig["action"] == "buy"
        assert sig["type"] == "market"
        assert sig["amount"] == 0.5  # must be present

    def test_sell_signal_when_condition_met(self):
        adapter = BacktraderAdapter(
            "Sell", ThresholdStrategy,
            bt_params={"threshold": 50000},
            min_bars=2, position_size=0.3,
        )
        adapter.initialize(_ctx())

        # First trigger a buy (need position before sell fires)
        for i in range(3):
            adapter.on_run(_make_candle((i + 1) * 1000, 51000))

        # Then drop below threshold
        sig = adapter.on_run(_make_candle(4000, 49000))
        assert sig is not None
        assert sig["action"] == "sell"
        assert sig["amount"] == 0.3

    def test_no_signal_below_min_bars(self):
        adapter = BacktraderAdapter(
            "MinBars", ThresholdStrategy, min_bars=5,
        )
        adapter.initialize(_ctx())

        for i in range(4):
            sig = adapter.on_run(_make_candle((i + 1) * 1000, 51000))
        assert sig is None  # only 4 bars, need 5


class TestPastSignalIgnored:
    """Verify that signals generated on historical bars in the sliding
    window are NOT forwarded — only the *last* bar matters."""

    def test_history_signal_not_leaked(self):
        """If the strategy buys on historical bars but NOT on the last bar,
        the adapter must return None."""
        # ThresholdStrategy buys when close > threshold.
        # Feed 3 bars above threshold (buy triggers on bar 1, fills bar 2,
        # subsequent bars: position held, no new buy).
        # Then feed bar 4 at exactly threshold (no buy, no sell condition).
        adapter = BacktraderAdapter(
            "Leak", ThresholdStrategy,
            bt_params={"threshold": 50000},
            min_bars=2, position_size=0.1,
        )
        adapter.initialize(_ctx())

        # Bars above threshold
        for i in range(3):
            adapter.on_run(_make_candle((i + 1) * 3600_000, 51000))

        # Bar 4: exactly at threshold — no buy (not > 50000), no sell (not < 50000)
        sig = adapter.on_run(_make_candle(4 * 3600_000, 50000))
        assert sig is None, (
            f"Expected None (hold) on neutral bar, got {sig}"
        )

    def test_current_bar_signal_captured(self):
        """If the strategy signals on the last bar, it IS returned."""
        adapter = BacktraderAdapter(
            "Curr", ThresholdStrategy,
            bt_params={"threshold": 50000},
            min_bars=2, position_size=0.1,
        )
        adapter.initialize(_ctx())

        # Bar 1: below threshold, no position → no signal
        adapter.on_run(_make_candle(1 * 3600_000, 49000))
        # Bar 2: above threshold → BUY on the current (last) bar
        sig = adapter.on_run(_make_candle(2 * 3600_000, 51000))
        assert sig is not None
        assert sig["action"] == "buy"


class TestInputProtocol:
    """Adapter must accept both OHLCV dicts and loop snapshot dicts."""

    def test_snapshot_format_accepted(self):
        adapter = BacktraderAdapter(
            "Snap", ThresholdStrategy,
            bt_params={"threshold": 100},
            min_bars=2, position_size=0.1,
        )
        adapter.initialize(_ctx())

        adapter.on_run(_make_snapshot(1000, 50))
        sig = adapter.on_run(_make_snapshot(2000, 200))
        assert sig is not None
        assert sig["action"] == "buy"

    def test_ohlcv_format_accepted(self):
        adapter = BacktraderAdapter(
            "OHLCV", ThresholdStrategy,
            bt_params={"threshold": 100},
            min_bars=2, position_size=0.1,
        )
        adapter.initialize(_ctx())

        adapter.on_run(_make_candle(1000, 50))
        sig = adapter.on_run(_make_candle(2000, 200))
        assert sig is not None
        assert sig["action"] == "buy"


class TestOutputProtocol:
    """Signal dict must contain ``amount`` and valid ``type``."""

    def test_amount_always_present(self):
        adapter = BacktraderAdapter(
            "Amt", ThresholdStrategy,
            bt_params={"threshold": 100},
            min_bars=2, position_size=0.25,
        )
        adapter.initialize(_ctx())
        adapter.on_run(_make_candle(1000, 50))
        sig = adapter.on_run(_make_candle(2000, 200))
        assert sig is not None
        assert "amount" in sig
        assert sig["amount"] == 0.25

    def test_type_is_market_by_default(self):
        adapter = BacktraderAdapter(
            "Type", ThresholdStrategy,
            bt_params={"threshold": 100},
            min_bars=2,
        )
        adapter.initialize(_ctx())
        adapter.on_run(_make_candle(1000, 50))
        sig = adapter.on_run(_make_candle(2000, 200))
        assert sig is not None
        assert sig["type"] == "market"


class TestSignalConsistency:
    """Core Step-30 acceptance: same strategy on same data must produce
    the same signal in backtest Cerebro and in BacktraderAdapter."""

    @staticmethod
    def _build_candles(n: int = 20) -> list[dict[str, Any]]:
        """Deterministic price series that triggers SMA crossover."""
        prices = []
        for i in range(n):
            if i < 10:
                prices.append(100 + i * 2)  # uptrend
            else:
                prices.append(120 - (i - 10) * 3)  # downtrend
        return [_make_candle(i * 3600_000, p) for i, p in enumerate(prices)]

    def test_sma_signal_matches_backtest(self):
        """Run same SMAStrategy on same data via Cerebro and via Adapter,
        verify the signal at the last bar is identical."""
        import pandas as pd

        candles = self._build_candles(20)

        # --- Backtest path (raw Cerebro) ---
        df = pd.DataFrame(candles)
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("datetime").sort_index()

        bt_signal: dict[str, Any] = {"action": None}
        total = len(df)

        class _BTCapture(SMAStrategy):
            def buy(self, *a: Any, **kw: Any) -> Any:
                if len(self) == total:
                    bt_signal["action"] = "buy"
                return super().buy(*a, **kw)

            def sell(self, *a: Any, **kw: Any) -> Any:
                if len(self) == total:
                    bt_signal["action"] = "sell"
                return super().sell(*a, **kw)

        cerebro = bt.Cerebro(stdstats=False)
        cerebro.broker.setcash(1e12)  # match adapter's unlimited cash
        feed = bt.feeds.PandasData(
            dataname=df, open="open", high="high", low="low",
            close="close", volume="volume", openinterest=None,
            timeframe=bt.TimeFrame.Minutes,
        )
        cerebro.adddata(feed)
        cerebro.addstrategy(_BTCapture, fast=3, slow=5)
        cerebro.run()

        # --- Adapter path ---
        adapter = BacktraderAdapter(
            "SMA", SMAStrategy,
            bt_params={"fast": 3, "slow": 5},
            min_bars=2, position_size=0.1,
        )
        adapter.initialize(_ctx())

        adapter_signal = None
        for c in candles:
            adapter_signal = adapter.on_run(c)

        # --- Compare ---
        bt_action = bt_signal["action"]
        adapter_action = adapter_signal["action"] if adapter_signal else None
        assert bt_action == adapter_action, (
            f"Signal mismatch: backtest={bt_action}, adapter={adapter_action}"
        )
