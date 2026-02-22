"""Helpers for calculating candle-window coverage metrics."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.database import SQLiteDatabase
from src.data.timeframe_metrics import (
    compute_coverage_ratio,
    compute_span_days,
    estimate_expected_candle_count,
)


@dataclass(frozen=True)
class CandleWindowStats:
    stored_count: int
    expected_count: int
    coverage_ratio: float
    first_timestamp: int | None
    last_timestamp: int | None
    span_days: float


def fetch_candle_window_stats(
    *,
    database: SQLiteDatabase,
    symbol: str,
    timeframe: str,
    start_timestamp: int,
    end_timestamp: int,
) -> CandleWindowStats:
    """Read stored bars in range and compute expected/coverage metrics."""
    expected_count = estimate_expected_candle_count(start_timestamp, end_timestamp, timeframe)
    with database.transaction() as tx:
        row = tx.execute(
            """
            SELECT
                COUNT(*) AS stored_count,
                MIN(timestamp) AS first_timestamp,
                MAX(timestamp) AS last_timestamp
            FROM candles
            WHERE symbol = ?
              AND timeframe = ?
              AND timestamp >= ?
              AND timestamp <= ?;
            """,
            (symbol, timeframe, start_timestamp, end_timestamp),
        ).fetchone()
    stored_count = int(row["stored_count"]) if row is not None else 0
    first_timestamp = int(row["first_timestamp"]) if row and row["first_timestamp"] is not None else None
    last_timestamp = int(row["last_timestamp"]) if row and row["last_timestamp"] is not None else None
    return CandleWindowStats(
        stored_count=stored_count,
        expected_count=expected_count,
        coverage_ratio=compute_coverage_ratio(
            stored_count=stored_count,
            expected_count=expected_count,
        ),
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        span_days=compute_span_days(first_timestamp, last_timestamp),
    )
