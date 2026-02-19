"""Realtime payload model and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RealtimeMarketSnapshot:
    """Unified response shape for real-time market reads."""

    channel: str
    symbol: str
    ok: bool
    fallback: bool
    timed_out: bool
    error: str | None
    fetched_at_ms: int
    data: dict[str, Any]


def normalize_ticker_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("ticker payload must be a mapping")
    return {
        "last_price": _as_float(payload.get("last") or payload.get("close")),
        "bid": _as_float(payload.get("bid")),
        "ask": _as_float(payload.get("ask")),
        "exchange_timestamp": _as_int(payload.get("timestamp")),
    }


def normalize_order_book_payload(
    payload: Mapping[str, Any],
    *,
    limit: int | None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("order book payload must be a mapping")
    return {
        "limit": limit,
        "bids": _normalize_levels(payload.get("bids")),
        "asks": _normalize_levels(payload.get("asks")),
        "exchange_timestamp": _as_int(payload.get("timestamp")),
    }


def normalize_ohlcv_payload(payload: list[list[Any]], *, timeframe: str) -> dict[str, Any]:
    if not isinstance(payload, list):
        raise ValueError("ohlcv payload must be a list")
    candles: list[dict[str, float | int]] = []
    for item in payload:
        if not isinstance(item, (list, tuple)) or len(item) < 6:
            raise ValueError("ohlcv item must contain [timestamp, open, high, low, close, volume]")
        candles.append(
            {
                "timestamp": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            }
        )
    return {"timeframe": timeframe, "candles": candles}


def _normalize_levels(raw_levels: Any) -> list[list[float]]:
    if raw_levels is None:
        return []
    if not isinstance(raw_levels, list):
        raise ValueError("order book levels must be a list")
    normalized: list[list[float]] = []
    for level in raw_levels:
        if not isinstance(level, (list, tuple)) or len(level) < 2:
            raise ValueError("each order book level must have [price, amount]")
        normalized.append([float(level[0]), float(level[1])])
    return normalized


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
