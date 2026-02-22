"""Historical candle download, cache, and deduplicated SQLite persistence."""

from __future__ import annotations

from typing import Any, Protocol

from src.core.candle import Candle
from src.core.database import SQLiteDatabase
from src.data.candle_window_stats import fetch_candle_window_stats
from src.data.storage_types import (
    CandleDownloadRequest,
    CandleDownloadResult,
    HistoricalDataStorageError,
)
from src.utils.config_defaults import ALLOWED_TIMEFRAMES


class CandleFetcher(Protocol):
    """Protocol for candle-fetching clients (for example MarketDataFetcher)."""

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: int | None = None,
        limit: int | None = None,
    ) -> list[list[Any]]:
        ...


class HistoricalCandleStorage:
    def __init__(self, database: SQLiteDatabase, fetcher: CandleFetcher) -> None:
        self._database = database
        self._fetcher = fetcher
        self._request_cache: set[tuple[str, str, int, int]] = set()

    def download_and_store(self, request: CandleDownloadRequest) -> CandleDownloadResult:
        symbol = self._validate_symbol(request.symbol)
        timeframe = self._validate_timeframe(request.timeframe)
        start_timestamp, end_timestamp = self._validate_time_range(
            request.start_timestamp,
            request.end_timestamp,
        )
        batch_size = self._validate_batch_size(request.batch_size)
        cache_key = (symbol, timeframe, start_timestamp, end_timestamp)

        if self._is_range_cached(cache_key):
            return self._build_download_result(
                symbol=symbol,
                timeframe=timeframe,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                downloaded_count=0,
            )

        downloaded_count = 0
        since = start_timestamp
        while since <= end_timestamp:
            ohlcv_rows = self._fetcher.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=batch_size,
            )
            if not ohlcv_rows:
                break

            candles = self._normalize_rows(
                rows=ohlcv_rows,
                symbol=symbol,
                timeframe=timeframe,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
            if candles:
                downloaded_count += self._insert_candles(candles)

            last_timestamp = int(ohlcv_rows[-1][0])
            if last_timestamp < since:
                raise HistoricalDataStorageError(
                    "exchange returned out-of-order candles; cannot advance time cursor"
                )
            since = last_timestamp + 1
            if len(ohlcv_rows) < batch_size:
                break

        self._record_cached_range(cache_key)
        return self._build_download_result(
            symbol=symbol,
            timeframe=timeframe,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            downloaded_count=downloaded_count,
        )

    def _build_download_result(
        self,
        *,
        symbol: str,
        timeframe: str,
        start_timestamp: int,
        end_timestamp: int,
        downloaded_count: int,
    ) -> CandleDownloadResult:
        stats = fetch_candle_window_stats(
            database=self._database,
            symbol=symbol,
            timeframe=timeframe,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )
        return CandleDownloadResult(
            symbol=symbol,
            timeframe=timeframe,
            dataset_name=self.build_dataset_name(symbol, timeframe),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            downloaded_count=downloaded_count,
            stored_count=stats.stored_count,
            expected_count=stats.expected_count,
            coverage_ratio=stats.coverage_ratio,
            first_timestamp=stats.first_timestamp,
            last_timestamp=stats.last_timestamp,
            span_days=stats.span_days,
        )

    def query_candles(
        self,
        symbol: str,
        timeframe: str,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        normalized_symbol = self._validate_symbol(symbol)
        normalized_timeframe = self._validate_timeframe(timeframe)
        if start_timestamp is not None and start_timestamp < 0:
            raise HistoricalDataStorageError("start_timestamp must be >= 0")
        if end_timestamp is not None and end_timestamp < 0:
            raise HistoricalDataStorageError("end_timestamp must be >= 0")
        if (
            start_timestamp is not None
            and end_timestamp is not None
            and start_timestamp > end_timestamp
        ):
            raise HistoricalDataStorageError("start_timestamp must be <= end_timestamp")
        if limit is not None and limit <= 0:
            raise HistoricalDataStorageError("limit must be > 0")

        sql = [
            "SELECT symbol, timeframe, timestamp, open, high, low, close, volume, created_at",
            "FROM candles",
            "WHERE symbol = ? AND timeframe = ?",
        ]
        params: list[Any] = [normalized_symbol, normalized_timeframe]
        if start_timestamp is not None:
            sql.append("AND timestamp >= ?")
            params.append(start_timestamp)
        if end_timestamp is not None:
            sql.append("AND timestamp <= ?")
            params.append(end_timestamp)
        sql.append("ORDER BY timestamp ASC")
        if limit is not None:
            sql.append("LIMIT ?")
            params.append(limit)

        with self._database.transaction() as tx:
            rows = tx.execute(" ".join(sql), params).fetchall()
        return [Candle.validate(dict(row)) for row in rows]

    @staticmethod
    def build_dataset_name(symbol: str, timeframe: str) -> str:
        normalized_symbol = symbol.strip().upper().replace("/", "_").replace("-", "_")
        normalized_symbol = "_".join(part for part in normalized_symbol.split("_") if part)
        return f"{normalized_symbol}_{timeframe.strip()}"

    def _insert_candles(self, candles: list[Candle]) -> int:
        payload = [
            (
                candle.symbol,
                candle.timeframe,
                candle.timestamp,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
            )
            for candle in candles
        ]
        with self._database.transaction() as tx:
            changes_before = tx.total_changes
            tx.executemany(
                """
                INSERT OR IGNORE INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                payload,
            )
            return tx.total_changes - changes_before

    def _is_range_cached(self, cache_key: tuple[str, str, int, int]) -> bool:
        if cache_key in self._request_cache:
            return True

        symbol, timeframe, start_timestamp, end_timestamp = cache_key
        with self._database.transaction() as tx:
            row = tx.execute(
                """
                SELECT 1 FROM candle_download_cache
                WHERE symbol = ?
                  AND timeframe = ?
                  AND start_timestamp = ?
                  AND end_timestamp = ?
                LIMIT 1;
                """,
                (symbol, timeframe, start_timestamp, end_timestamp),
            ).fetchone()
        if row is None:
            return False
        self._request_cache.add(cache_key)
        return True

    def _record_cached_range(self, cache_key: tuple[str, str, int, int]) -> None:
        symbol, timeframe, start_timestamp, end_timestamp = cache_key
        with self._database.transaction() as tx:
            tx.execute(
                """
                INSERT INTO candle_download_cache(symbol, timeframe, start_timestamp, end_timestamp) VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol, timeframe, start_timestamp, end_timestamp) DO UPDATE SET last_synced_at = CURRENT_TIMESTAMP;
                """,
                (symbol, timeframe, start_timestamp, end_timestamp),
            )
        self._request_cache.add(cache_key)

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        if not symbol or not symbol.strip():
            raise HistoricalDataStorageError("symbol must not be empty")
        return symbol.strip().upper()

    @staticmethod
    def _validate_timeframe(timeframe: str) -> str:
        if not timeframe or not timeframe.strip():
            raise HistoricalDataStorageError("timeframe must not be empty")
        normalized = timeframe.strip()
        if normalized not in ALLOWED_TIMEFRAMES:
            raise HistoricalDataStorageError(
                f"timeframe must be one of {sorted(ALLOWED_TIMEFRAMES)}"
            )
        return normalized

    @staticmethod
    def _validate_time_range(start_timestamp: int, end_timestamp: int) -> tuple[int, int]:
        if start_timestamp < 0:
            raise HistoricalDataStorageError("start_timestamp must be >= 0")
        if end_timestamp < 0:
            raise HistoricalDataStorageError("end_timestamp must be >= 0")
        if start_timestamp > end_timestamp:
            raise HistoricalDataStorageError("start_timestamp must be <= end_timestamp")
        return int(start_timestamp), int(end_timestamp)

    @staticmethod
    def _validate_batch_size(batch_size: int) -> int:
        if batch_size <= 0:
            raise HistoricalDataStorageError("batch_size must be > 0")
        return int(batch_size)

    def _normalize_rows(
        self,
        *,
        rows: list[list[Any]],
        symbol: str,
        timeframe: str,
        start_timestamp: int,
        end_timestamp: int,
    ) -> list[Candle]:
        candles: list[Candle] = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) < 6:
                raise HistoricalDataStorageError("invalid OHLCV row: expected 6 values")

            timestamp = int(row[0])
            if timestamp < start_timestamp or timestamp > end_timestamp:
                continue

            candle = Candle.validate(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": timestamp,
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                }
            )
            candles.append(candle)
        candles.sort(key=lambda item: item.timestamp)
        return candles
