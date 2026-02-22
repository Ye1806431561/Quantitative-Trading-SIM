"""Type definitions for historical candle storage."""

from __future__ import annotations

from dataclasses import dataclass


class HistoricalDataStorageError(RuntimeError):
    """Raised when historical candle download or persistence fails."""


@dataclass(frozen=True)
class CandleDownloadRequest:
    """Request payload for downloading a historical candle range."""

    symbol: str
    timeframe: str
    start_timestamp: int
    end_timestamp: int
    batch_size: int = 500


@dataclass(frozen=True)
class CandleDownloadResult:
    """Summary returned after a successful download and persistence run."""

    symbol: str
    timeframe: str
    dataset_name: str
    start_timestamp: int
    end_timestamp: int
    downloaded_count: int
    stored_count: int
    expected_count: int
    coverage_ratio: float
    first_timestamp: int | None
    last_timestamp: int | None
    span_days: float
