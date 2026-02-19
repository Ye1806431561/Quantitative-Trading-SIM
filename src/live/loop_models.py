"""Data models for real-time simulation loop (Phase 3 Step 29)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class RealtimeLoopError(RuntimeError):
    """Raised when real-time loop operations fail."""


@dataclass(frozen=True)
class RealtimeLoopConfig:
    """Configuration for real-time simulation loop."""

    symbol: str
    timeframe: str
    tick_interval_seconds: float = 1.0
    max_iterations: int | None = None


@dataclass(frozen=True)
class LoopIterationResult:
    """Result of one loop iteration."""

    iteration: int
    timestamp_ms: int
    latest_price: float | None
    strategy_signal: Mapping[str, Any] | None
    orders_matched: int
    error: str | None
