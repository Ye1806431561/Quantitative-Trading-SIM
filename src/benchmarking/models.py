"""Data models for performance benchmarking (Phase 4 Step 40)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkMeta:
    """Metadata for one benchmark execution."""

    generated_at_utc: str
    benchmark_version: str


@dataclass(frozen=True)
class BenchmarkConditions:
    """Fixed conditions used for reproducible benchmark runs."""

    symbol: str
    strategy: str
    timeframe: str
    backtest_candle_count: int
    realtime_iterations: int
    order_iterations: int
    seed: int
    single_strategy: bool = True
    single_trading_pair: bool = True
    default_analyzers: bool = True
    sqlite_local: bool = True
    io_printing_disabled: bool = True


@dataclass(frozen=True)
class LatencyStats:
    """Latency distribution stats in milliseconds."""

    samples: int
    mean_ms: float
    p95_ms: float
    max_ms: float


@dataclass(frozen=True)
class BacktestBenchmarkResult:
    """Backtest benchmark result."""

    duration_seconds: float
    status: str


@dataclass(frozen=True)
class RealtimeBenchmarkResult:
    """Realtime loop benchmark result."""

    latency_ms: LatencyStats
    status: str


@dataclass(frozen=True)
class OrderBenchmarkResult:
    """Order-response benchmark result."""

    latency_ms: LatencyStats
    status: str


@dataclass(frozen=True)
class BenchmarkThresholds:
    """Threshold definitions used in evaluation."""

    backtest_target_seconds: float
    backtest_degraded_seconds: float
    realtime_p95_ms: float
    order_p95_ms: float


@dataclass(frozen=True)
class BenchmarkEvaluation:
    """Final benchmark evaluation summary."""

    status: str
    passed: bool
    exit_code: int
    warnings: tuple[str, ...] = field(default_factory=tuple)
    failures: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BenchmarkReport:
    """Top-level benchmark report payload."""

    meta: BenchmarkMeta
    conditions: BenchmarkConditions
    backtest: BacktestBenchmarkResult
    realtime: RealtimeBenchmarkResult
    order_response: OrderBenchmarkResult
    thresholds: BenchmarkThresholds
    evaluation: BenchmarkEvaluation
    improvement_items: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable report dict."""
        return {
            "meta": asdict(self.meta),
            "conditions": asdict(self.conditions),
            "backtest": asdict(self.backtest),
            "realtime": asdict(self.realtime),
            "order_response": asdict(self.order_response),
            "thresholds": asdict(self.thresholds),
            "evaluation": {
                **asdict(self.evaluation),
                "warnings": list(self.evaluation.warnings),
                "failures": list(self.evaluation.failures),
            },
            "improvement_items": list(self.improvement_items),
        }
