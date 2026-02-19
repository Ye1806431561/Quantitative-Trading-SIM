"""SQLite to PandasData bridge for Backtrader backtests."""

from __future__ import annotations

from dataclasses import dataclass

import backtrader as bt
import pandas as pd

from src.core.database import SQLiteDatabase
from src.utils.config_defaults import ALLOWED_TIMEFRAMES


class SQLiteFeedError(RuntimeError):
    """Raised when SQLite candle data cannot be transformed into a feed."""


@dataclass(frozen=True)
class BacktestDataSlice:
    """SQLite candle-query request used by the backtest engine."""

    symbol: str
    timeframe: str
    start_timestamp: int
    end_timestamp: int


class SQLitePandasFeedFactory:
    """Build Pandas dataframe and Backtrader feed from SQLite candles."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def load_dataframe(self, request: BacktestDataSlice) -> pd.DataFrame:
        """Load candles from SQLite and normalize to Backtrader-compatible dataframe."""
        symbol = self._normalize_symbol(request.symbol)
        timeframe = self._normalize_timeframe(request.timeframe)
        start_ts = self._normalize_timestamp(request.start_timestamp, "start_timestamp")
        end_ts = self._normalize_timestamp(request.end_timestamp, "end_timestamp")
        if start_ts > end_ts:
            raise SQLiteFeedError("start_timestamp must be <= end_timestamp")

        with self._database.transaction() as tx:
            rows = tx.execute(
                """
                SELECT timestamp, open, high, low, close, volume
                FROM candles
                WHERE symbol = ? AND timeframe = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC;
                """,
                (symbol, timeframe, start_ts, end_ts),
            ).fetchall()

        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        frame = pd.DataFrame.from_records(
            rows,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        frame["datetime"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        frame = frame.drop(columns=["timestamp"])
        frame = frame.set_index("datetime")
        return frame[["open", "high", "low", "close", "volume"]]

    def build_feed(self, dataframe: pd.DataFrame, timeframe: str) -> bt.feeds.PandasData:
        """Create Backtrader PandasData feed with mapped timeframe/compression."""
        normalized_timeframe = self._normalize_timeframe(timeframe)
        bt_timeframe, compression = self._to_backtrader_timeframe(normalized_timeframe)
        return bt.feeds.PandasData(
            dataname=dataframe,
            timeframe=bt_timeframe,
            compression=compression,
            openinterest=-1,
        )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        if not symbol or not symbol.strip():
            raise SQLiteFeedError("symbol must not be empty")
        return symbol.strip().upper()

    @staticmethod
    def _normalize_timeframe(timeframe: str) -> str:
        if not timeframe or not timeframe.strip():
            raise SQLiteFeedError("timeframe must not be empty")
        normalized = timeframe.strip()
        if normalized not in ALLOWED_TIMEFRAMES:
            raise SQLiteFeedError(f"timeframe must be one of {sorted(ALLOWED_TIMEFRAMES)}")
        return normalized

    @staticmethod
    def _normalize_timestamp(value: int, label: str) -> int:
        if not isinstance(value, int):
            raise SQLiteFeedError(f"{label} must be an integer")
        if value < 0:
            raise SQLiteFeedError(f"{label} must be >= 0")
        return value

    @staticmethod
    def _to_backtrader_timeframe(timeframe: str) -> tuple[int, int]:
        if timeframe == "1m":
            return bt.TimeFrame.Minutes, 1
        if timeframe == "5m":
            return bt.TimeFrame.Minutes, 5
        if timeframe == "15m":
            return bt.TimeFrame.Minutes, 15
        if timeframe == "1h":
            return bt.TimeFrame.Minutes, 60
        if timeframe == "4h":
            return bt.TimeFrame.Minutes, 240
        if timeframe == "1d":
            return bt.TimeFrame.Days, 1
        raise SQLiteFeedError(f"unsupported timeframe mapping: {timeframe}")
