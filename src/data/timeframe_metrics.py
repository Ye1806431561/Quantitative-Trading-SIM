"""Utilities for timeframe-based candle window metrics."""

from __future__ import annotations

TIMEFRAME_TO_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def timeframe_to_milliseconds(timeframe: str) -> int:
    """Return candle interval in milliseconds."""
    normalized = timeframe.strip()
    if normalized not in TIMEFRAME_TO_MS:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    return TIMEFRAME_TO_MS[normalized]


def estimate_expected_candle_count(start_timestamp: int, end_timestamp: int, timeframe: str) -> int:
    """Estimate expected bar count in an inclusive time window."""
    if end_timestamp < start_timestamp:
        return 0
    interval_ms = timeframe_to_milliseconds(timeframe)
    return ((end_timestamp - start_timestamp) // interval_ms) + 1


def compute_coverage_ratio(*, stored_count: int, expected_count: int) -> float:
    """Compute stored/expected coverage ratio."""
    if expected_count <= 0:
        return 0.0
    return float(stored_count) / float(expected_count)


def compute_span_days(first_timestamp: int | None, last_timestamp: int | None) -> float:
    """Compute actual covered span in days."""
    if first_timestamp is None or last_timestamp is None:
        return 0.0
    if last_timestamp < first_timestamp:
        return 0.0
    return (last_timestamp - first_timestamp) / 86_400_000
