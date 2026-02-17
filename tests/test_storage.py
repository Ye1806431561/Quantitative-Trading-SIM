"""Tests for historical candle download and SQLite storage (Phase 1 Step 15)."""

from __future__ import annotations

from typing import Any

import pytest

from src.core.database import SQLiteDatabase
from src.data.storage import (
    CandleDownloadRequest,
    HistoricalCandleStorage,
    HistoricalDataStorageError,
)


class ScriptedFetcher:
    """Simple scripted fetcher that returns preloaded OHLCV pages."""

    def __init__(self, pages: list[list[list[Any]]]) -> None:
        self._pages = list(pages)
        self.calls: list[dict[str, Any]] = []

    def set_pages(self, pages: list[list[list[Any]]]) -> None:
        self._pages = list(pages)

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: int | None = None,
        limit: int | None = None,
    ) -> list[list[Any]]:
        self.calls.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "since": since,
                "limit": limit,
            }
        )
        if not self._pages:
            return []
        return self._pages.pop(0)


@pytest.fixture
def storage(tmp_path):
    database = SQLiteDatabase(tmp_path / "storage.db")
    database.initialize_schema()
    fetcher = ScriptedFetcher([])
    service = HistoricalCandleStorage(database=database, fetcher=fetcher)
    yield service, fetcher, database
    database.close()


def test_download_and_store_writes_candles_and_returns_summary(storage) -> None:
    service, fetcher, database = storage
    fetcher.set_pages([
        [
            [1000, 100.0, 105.0, 95.0, 101.0, 10.0],
            [2000, 101.0, 106.0, 99.0, 104.0, 11.0],
        ],
        [
            [3000, 104.0, 108.0, 103.0, 107.0, 12.0],
            [4000, 107.0, 110.0, 106.0, 109.0, 13.0],  # filtered by end_timestamp
        ],
    ])
    request = CandleDownloadRequest(
        symbol="btc/usdt",
        timeframe="1h",
        start_timestamp=1000,
        end_timestamp=3500,
        batch_size=2,
    )

    result = service.download_and_store(request)

    assert result.symbol == "BTC/USDT"
    assert result.timeframe == "1h"
    assert result.dataset_name == "BTC_USDT_1h"
    assert result.downloaded_count == 3
    assert [call["since"] for call in fetcher.calls] == [1000, 2001]

    with database.transaction() as tx:
        count = tx.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = ?;",
            ("BTC/USDT", "1h"),
        ).fetchone()[0]
    assert count == 3


def test_query_candles_filters_time_range_and_orders_ascending(storage) -> None:
    service, _, database = storage
    with database.transaction() as tx:
        tx.executemany(
            """
            INSERT INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            [
                ("BTC/USDT", "1h", 3000, 1.0, 3.0, 0.5, 2.0, 10.0),
                ("BTC/USDT", "1h", 1000, 1.0, 2.0, 0.5, 1.5, 10.0),
                ("BTC/USDT", "1h", 2000, 1.5, 2.5, 1.0, 2.0, 12.0),
                ("ETH/USDT", "1h", 2000, 1.0, 2.0, 0.8, 1.2, 9.0),
            ],
        )

    candles = service.query_candles(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1500,
        end_timestamp=3500,
    )

    assert [candle.timestamp for candle in candles] == [2000, 3000]
    assert all(candle.symbol == "BTC/USDT" for candle in candles)
    assert all(candle.timeframe == "1h" for candle in candles)


def test_download_rejects_invalid_time_range(storage) -> None:
    service, _, _ = storage
    request = CandleDownloadRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=2000,
        end_timestamp=1000,
    )

    with pytest.raises(HistoricalDataStorageError, match="start_timestamp must be <="):
        service.download_and_store(request)


def test_download_rejects_invalid_timeframe(storage) -> None:
    service, _, _ = storage
    request = CandleDownloadRequest(
        symbol="BTC/USDT",
        timeframe="2h",
        start_timestamp=1000,
        end_timestamp=2000,
    )

    with pytest.raises(HistoricalDataStorageError, match="timeframe must be one of"):
        service.download_and_store(request)


def test_download_rejects_invalid_ohlcv_payload(storage) -> None:
    service, fetcher, _ = storage
    fetcher.set_pages([[[1000, 1.0, 2.0]]])  # Missing OHLCV fields.
    request = CandleDownloadRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1000,
        end_timestamp=2000,
    )

    with pytest.raises(HistoricalDataStorageError, match="invalid OHLCV row"):
        service.download_and_store(request)
