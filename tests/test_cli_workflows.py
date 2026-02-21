"""CLI workflow command tests (step 37)."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest
import yaml

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
        "db": db_path,
        "data_dir": data_dir,
    }


def _seed_hourly_candles(db_path: Path, count: int = 60) -> tuple[int, int]:
    start_ms = 1_700_000_000_000
    rows = []
    for idx in range(count):
        timestamp = start_ms + idx * 3_600_000
        price = 100.0 + idx
        rows.append(
            (
                "BTC/USDT",
                "1h",
                timestamp,
                price,
                price + 1.0,
                price - 1.0,
                price + 0.5,
                10.0 + idx,
            )
        )

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )
    conn.commit()
    conn.close()
    return start_ms, start_ms + (count - 1) * 3_600_000


@pytest.mark.parametrize(
    "command",
    [
        ("backtest",),
        ("download",),
        ("live",),
        ("import",),
        ("export",),
    ],
)
def test_workflow_required_arguments_validation(
    cli_files: dict[str, Path],
    command: tuple[str, ...],
) -> None:
    assert _run_cli(cli_files, *command) == 2


def test_backtest_command(cli_files: dict[str, Path]) -> None:
    assert _run_cli(cli_files, "start") == 0
    start_ms, end_ms = _seed_hourly_candles(cli_files["db"])

    assert _run_cli(
        cli_files,
        "backtest",
        "--strategy",
        "sma_strategy",
        "--symbol",
        "BTC/USDT",
        "--timeframe",
        "1h",
        "--start-ms",
        str(start_ms),
        "--end-ms",
        str(end_ms),
    ) == 0


def test_backtest_output_dir_exports_reports_and_charts(
    cli_files: dict[str, Path],
    tmp_path: Path,
) -> None:
    assert _run_cli(cli_files, "start") == 0
    start_ms, end_ms = _seed_hourly_candles(cli_files["db"])

    output_dir = tmp_path / "backtest_exports"
    prefix = "cli_assert"
    assert _run_cli(
        cli_files,
        "backtest",
        "--strategy",
        "sma_strategy",
        "--symbol",
        "BTC/USDT",
        "--timeframe",
        "1h",
        "--start-ms",
        str(start_ms),
        "--end-ms",
        str(end_ms),
        "--output-dir",
        str(output_dir),
        "--prefix",
        prefix,
    ) == 0

    expected_files = [
        f"backtest_summary_{prefix}.json",
        f"backtest_summary_{prefix}.csv",
        f"equity_curve_{prefix}.json",
        f"equity_curve_{prefix}.csv",
        f"trade_log_{prefix}.json",
        f"trade_log_{prefix}.csv",
        f"equity_curve_{prefix}.png",
        f"drawdown_curve_{prefix}.png",
        f"trade_distribution_{prefix}.png",
        f"holding_time_{prefix}.png",
    ]
    for filename in expected_files:
        path = output_dir / filename
        assert path.exists(), f"missing export: {path}"
        assert path.stat().st_size > 0, f"empty export: {path}"


def test_download_command(cli_files: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeFetcher:
        def __init__(self) -> None:
            self._called = False

        def fetch_ohlcv(self, symbol: str, timeframe: str, since: int | None = None, limit: int | None = None):
            if self._called:
                return []
            self._called = True
            return [
                [1_700_100_000_000, 10.0, 11.0, 9.0, 10.5, 20.0],
                [1_700_100_060_000, 10.5, 11.2, 10.1, 10.9, 21.0],
            ]

    monkeypatch.setattr("src.cli_workflows.MarketDataFetcher.from_config", lambda _config: _FakeFetcher())

    assert _run_cli(
        cli_files,
        "download",
        "--symbol",
        "BTC/USDT",
        "--timeframe",
        "1m",
        "--start-ms",
        "1700100000000",
        "--end-ms",
        "1700100060000",
    ) == 0


def test_import_export_cleanup_commands(cli_files: dict[str, Path], tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        writer.writerow([1_600_000_000_000, 100, 110, 90, 105, 20])
        writer.writerow([1_600_000_060_000, 105, 112, 100, 110, 22])

    assert _run_cli(
        cli_files,
        "import",
        "--file",
        str(csv_path),
        "--symbol",
        "BTC/USDT",
        "--timeframe",
        "1m",
    ) == 0

    output_path = tmp_path / "exported.csv"
    assert _run_cli(
        cli_files,
        "export",
        "--symbol",
        "BTC/USDT",
        "--timeframe",
        "1m",
        "--output",
        str(output_path),
    ) == 0
    assert output_path.exists()

    assert _run_cli(cli_files, "cleanup", "--days", "1") == 0


def test_live_command_with_mock_loop(cli_files: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeLoop:
        def __init__(self) -> None:
            self.iteration_count = 2

        def start(self) -> None:
            self.iteration_count = 2

        def stop(self) -> None:
            self.iteration_count = 2

    def _fake_from_config(*_args, **_kwargs):
        return _FakeLoop()

    monkeypatch.setattr("src.cli_workflows.RealtimeSimulationLoop.from_config", _fake_from_config)

    assert _run_cli(
        cli_files,
        "live",
        "--strategy",
        "sma_strategy",
        "--symbol",
        "BTC/USDT",
        "--timeframe",
        "1m",
        "--max-iterations",
        "2",
    ) == 0
