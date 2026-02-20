"""Strategy adapter: bridge bt.Strategy ↔ LiveStrategy (Step 30).

Uses a 'Run-on-Audit' approach: re-runs a lightweight Cerebro on a
sliding data window for every live tick, ensuring indicator values are
identical to backtesting.
"""

from __future__ import annotations

import collections
from typing import Any, Deque, Mapping, Type

import backtrader as bt
import pandas as pd

from src.strategies.base import LiveStrategy, StrategyContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_LOOKBACK = 100
_DEFAULT_MIN_BARS = 2
_DEFAULT_POSITION_SIZE = 0.1  # fraction of portfolio, used when BT sizer is unavailable


def _snapshot_to_ohlcv(market_data: Mapping[str, Any]) -> dict[str, Any]:
    """Convert RealtimeSimulationLoop snapshot to OHLCV dict.

    The loop passes::

        {"symbol": ..., "timestamp": ms, "latest_price": float,
         "bid": float|None, "ask": float|None}

    We synthesise an OHLCV bar from the single price point.
    """
    price = market_data.get("latest_price")
    if price is None:
        price = market_data.get("close")  # fallback: direct OHLCV dict
    if price is None:
        raise ValueError("market_data must contain 'latest_price' or 'close'")

    return {
        "timestamp": market_data.get("timestamp", 0),
        "open": market_data.get("open", price),
        "high": market_data.get("high", price),
        "low": market_data.get("low", price),
        "close": price,
        "volume": market_data.get("volume", 0),
    }


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class BacktraderAdapter(LiveStrategy):
    """Adapt a ``bt.Strategy`` for live execution via ``RealtimeSimulationLoop``.

    Parameters
    ----------
    name:
        Human-readable strategy name.
    bt_strategy_cls:
        A *class* (not instance) that subclasses ``bt.Strategy``.
    bt_params:
        Parameters forwarded to the Backtrader strategy constructor.
    lookback_window:
        Max number of bars kept in the sliding window (default 100).
    position_size:
        Default order amount emitted in the signal when the Backtrader
        strategy does not explicitly specify ``size``.
    min_bars:
        Minimum bars required before running the strategy (default 2).
    """

    def __init__(
        self,
        name: str,
        bt_strategy_cls: Type[bt.Strategy],
        bt_params: Mapping[str, Any] | None = None,
        *,
        lookback_window: int = _DEFAULT_LOOKBACK,
        position_size: float = _DEFAULT_POSITION_SIZE,
        min_bars: int = _DEFAULT_MIN_BARS,
    ) -> None:
        super().__init__(name)
        self._bt_strategy_cls = bt_strategy_cls
        self._bt_params: dict[str, Any] = dict(bt_params or {})
        self._lookback_window = lookback_window
        self._position_size = position_size
        self._min_bars = max(min_bars, 1)
        self._history: Deque[dict[str, Any]] = collections.deque(
            maxlen=lookback_window,
        )

    # ------------------------------------------------------------------
    # LiveStrategy hooks
    # ------------------------------------------------------------------

    def on_initialize(self, context: StrategyContext) -> None:
        """Load optional warmup candles from ``context.parameters``."""
        warmup_candles = context.parameters.get("warmup_candles", [])
        for candle in warmup_candles:
            self._history.append(_snapshot_to_ohlcv(candle))

    def on_run(self, market_data: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Append latest tick, replay Cerebro and return signal."""
        ohlcv = _snapshot_to_ohlcv(market_data)
        self._history.append(ohlcv)

        if len(self._history) < self._min_bars:
            return None

        df = self._build_dataframe()
        if df.empty:
            return None

        signal = self._run_cerebro(df)
        return signal

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(list(self._history))
        if "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("datetime")
            df = df.sort_index()
        return df

    def _run_cerebro(self, df: pd.DataFrame) -> dict[str, Any] | None:
        """Run one Cerebro pass and return the signal from the *last* bar."""
        cerebro = bt.Cerebro(stdstats=False)
        # Give the simulated broker unlimited cash so that orders fill
        # regardless of asset price.  This Cerebro is purely for signal
        # generation; real portfolio management is handled by the loop.
        cerebro.broker.setcash(1e12)

        feed = bt.feeds.PandasData(
            dataname=df,
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            openinterest=None,
            timeframe=bt.TimeFrame.Minutes,
        )
        cerebro.adddata(feed)

        total_bars = len(df)
        signal_box: dict[str, Any] = {
            "action": None,
            "price": None,
            "size": None,
            "exectype": None,
        }

        parent_cls = self._bt_strategy_cls

        class _SignalInterceptor(parent_cls):  # type: ignore[valid-type,misc]
            """Thin wrapper that captures buy/sell only on the *last* bar."""

            def buy(self, *args: Any, **kwargs: Any) -> Any:
                # `len(self)` is 1-based bar count processed so far.
                # It equals `total_bars` only when `next()` runs on the
                # final bar of the dataset — i.e. the "live" moment.
                if len(self) == total_bars:
                    signal_box["action"] = "buy"
                    signal_box["exectype"] = kwargs.get("exectype")
                    signal_box["price"] = kwargs.get("price")
                    signal_box["size"] = kwargs.get("size")
                return super().buy(*args, **kwargs)

            def sell(self, *args: Any, **kwargs: Any) -> Any:
                if len(self) == total_bars:
                    signal_box["action"] = "sell"
                    signal_box["exectype"] = kwargs.get("exectype")
                    signal_box["price"] = kwargs.get("price")
                    signal_box["size"] = kwargs.get("size")
                return super().sell(*args, **kwargs)

            def close(self, *args: Any, **kwargs: Any) -> Any:
                if len(self) == total_bars:
                    signal_box["action"] = "sell"  # map 'close' → 'sell'
                    signal_box["size"] = kwargs.get("size")
                return super().close(*args, **kwargs)

        cerebro.addstrategy(_SignalInterceptor, **self._bt_params)

        try:
            cerebro.run()
        except (IndexError, ValueError):
            # Insufficient data for the strategy's indicators (e.g. SMA
            # period > number of bars).  Return None (hold) until enough
            # data accumulates.
            return None

        if signal_box["action"] is None:
            return None

        # Map Backtrader exectype → loop order type
        bt_exec = signal_box["exectype"]
        order_type = "market"
        if bt_exec == bt.Order.Limit:
            order_type = "limit"
        elif bt_exec == bt.Order.Stop:
            order_type = "stop_loss"
        elif bt_exec == bt.Order.StopLimit:
            order_type = "stop_loss"

        result: dict[str, Any] = {
            "action": signal_box["action"],
            "type": order_type,
            "amount": signal_box["size"] or self._position_size,
        }
        if signal_box["price"] is not None:
            result["price"] = float(signal_box["price"])

        return result
