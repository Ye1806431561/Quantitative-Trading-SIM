"""CLI benchmark command tests (step 40)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.benchmarking.models import (
    BacktestBenchmarkResult,
    BenchmarkConditions,
    BenchmarkEvaluation,
    BenchmarkMeta,
    BenchmarkReport,
    BenchmarkThresholds,
    LatencyStats,
    OrderBenchmarkResult,
    RealtimeBenchmarkResult,
)
from src.cli import main as cli_main


def _run_cli(cli_files: dict[str, Path], *command: str) -> int:
    return cli_main(
        [
            "--config",
            str(cli_files["config"]),
            "--strategies",
            str(cli_files["strategies"]),
            "--env",
            str(cli_files["env"]),
            *command,
        ]
    )


@pytest.fixture
def cli_files(tmp_path: Path) -> dict[str, Path]:
    db_path = tmp_path / "trading.db"
    data_dir = tmp_path / "data"
    log_dir = tmp_path / "logs"

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "system": {
                    "database_path": str(db_path),
                    "data_dir": str(data_dir),
                    "log_dir": str(log_dir),
                }
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    strategies_path = tmp_path / "strategies.yaml"
    strategies_path.write_text("", encoding="utf-8")

    env_path = tmp_path / ".env"
    env_path.write_text("", encoding="utf-8")

    return {
        "config": config_path,
        "strategies": strategies_path,
        "env": env_path,
        "data_dir": data_dir,
    }


def _build_fake_report(*, status: str, exit_code: int) -> BenchmarkReport:
    return BenchmarkReport(
        meta=BenchmarkMeta(generated_at_utc="2026-02-22T00:00:00Z", benchmark_version="step40-v1"),
        conditions=BenchmarkConditions(
            symbol="BTC/USDT",
            strategy="sma_strategy",
            timeframe="1h",
            backtest_candle_count=8760,
            realtime_iterations=300,
            order_iterations=500,
            seed=42,
        ),
        backtest=BacktestBenchmarkResult(duration_seconds=4.2, status="pass"),
        realtime=RealtimeBenchmarkResult(
            latency_ms=LatencyStats(samples=10, mean_ms=1.0, p95_ms=2.0, max_ms=3.0),
            status="pass",
        ),
        order_response=OrderBenchmarkResult(
            latency_ms=LatencyStats(samples=10, mean_ms=1.0, p95_ms=2.0, max_ms=3.0),
            status="pass",
        ),
        thresholds=BenchmarkThresholds(
            backtest_target_seconds=5.0,
            backtest_degraded_seconds=10.0,
            realtime_p95_ms=1000.0,
            order_p95_ms=100.0,
        ),
        evaluation=BenchmarkEvaluation(
            status=status,
            passed=exit_code == 0,
            exit_code=exit_code,
            warnings=("degraded",) if status == "warning" else (),
            failures=("failed",) if status == "fail" else (),
        ),
        improvement_items=("keep watching",),
    )


def test_benchmark_command_success_generates_reports(
    cli_files: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "src.cli_benchmark.run_benchmark",
        lambda **_kwargs: _build_fake_report(status="pass", exit_code=0),
    )

    output_dir = tmp_path / "benchmarks"
    exit_code = _run_cli(
        cli_files,
        "benchmark",
        "--output-dir",
        str(output_dir),
    )
    assert exit_code == 0
    assert len(list(output_dir.glob("*.json"))) == 1
    assert len(list(output_dir.glob("*.md"))) == 1


def test_benchmark_command_warning_exit_zero(
    cli_files: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.cli_benchmark.run_benchmark",
        lambda **_kwargs: _build_fake_report(status="warning", exit_code=0),
    )

    exit_code = _run_cli(cli_files, "benchmark")
    assert exit_code == 0


def test_benchmark_command_fail_exit_one(
    cli_files: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.cli_benchmark.run_benchmark",
        lambda **_kwargs: _build_fake_report(status="fail", exit_code=1),
    )

    exit_code = _run_cli(cli_files, "benchmark")
    assert exit_code == 1


@pytest.mark.parametrize(
    "command",
    [
        ("benchmark", "--realtime-iterations", "-1"),
        ("benchmark", "--order-iterations", "0"),
        ("benchmark", "--symbol", ""),
    ],
)
def test_benchmark_invalid_arguments(cli_files: dict[str, Path], command: tuple[str, ...]) -> None:
    assert _run_cli(cli_files, *command) == 1
