"""CLI runtime/system/order command tests (step 37)."""

from __future__ import annotations

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


@pytest.mark.parametrize(
    "command",
    [
        ("order",),
        ("order", "place", "--symbol", "BTC/USDT", "--side", "buy", "--type", "limit"),
        ("order", "cancel"),
        ("cleanup",),
    ],
)
def test_runtime_required_arguments_validation(
    cli_files: dict[str, Path],
    command: tuple[str, ...],
) -> None:
    assert _run_cli(cli_files, *command) == 2


def test_start_stop_status_and_disk(cli_files: dict[str, Path]) -> None:
    assert _run_cli(cli_files, "startup") == 0
    assert _run_cli(cli_files, "status") == 0
    assert _run_cli(cli_files, "status", "--alerts") == 0
    assert _run_cli(cli_files, "status", "--disk") == 0
    assert _run_cli(cli_files, "stop") == 0


def test_balance_and_positions_commands(cli_files: dict[str, Path]) -> None:
    assert _run_cli(cli_files, "start") == 0
    assert _run_cli(cli_files, "balance") == 0
    assert _run_cli(cli_files, "positions") == 0


def test_order_place_list_cancel_commands(cli_files: dict[str, Path]) -> None:
    assert _run_cli(
        cli_files,
        "order",
        "place",
        "--symbol",
        "BTC/USDT",
        "--side",
        "buy",
        "--type",
        "limit",
        "--amount",
        "0.2",
        "--price",
        "100.0",
    ) == 0
    assert _run_cli(cli_files, "order", "list", "--symbol", "BTC/USDT") == 0

    conn = sqlite3.connect(cli_files["db"])
    order_id = conn.execute("SELECT id FROM orders ORDER BY created_at DESC LIMIT 1;").fetchone()[0]
    conn.close()

    assert _run_cli(cli_files, "order", "cancel", "--order-id", str(order_id)) == 0


def test_reconcile_command(cli_files: dict[str, Path]) -> None:
    assert _run_cli(cli_files, "start") == 0

    conn = sqlite3.connect(cli_files["db"])
    conn.execute(
        """
        INSERT INTO orders(id, symbol, type, side, price, amount, filled, status, created_at, updated_at)
        VALUES ('ORD-BUY', 'BTC/USDT', 'market', 'buy', 100.0, 1.0, 1.0, 'filled', 1, 1);
        """
    )
    conn.execute(
        """
        INSERT INTO orders(id, symbol, type, side, price, amount, filled, status, created_at, updated_at)
        VALUES ('ORD-SELL', 'BTC/USDT', 'market', 'sell', 120.0, 0.4, 0.4, 'filled', 2, 2);
        """
    )
    conn.execute(
        """
        INSERT INTO trades(order_id, symbol, side, price, amount, fee, timestamp)
        VALUES ('ORD-BUY', 'BTC/USDT', 'buy', 100.0, 1.0, 0.0, 1);
        """
    )
    conn.execute(
        """
        INSERT INTO trades(order_id, symbol, side, price, amount, fee, timestamp)
        VALUES ('ORD-SELL', 'BTC/USDT', 'sell', 120.0, 0.4, 0.0, 2);
        """
    )
    conn.commit()
    conn.close()

    assert _run_cli(cli_files, "reconcile") == 0

    conn = sqlite3.connect(cli_files["db"])
    row = conn.execute(
        "SELECT symbol, amount, entry_price, realized_pnl FROM positions WHERE symbol = 'BTC/USDT';"
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "BTC/USDT"
    assert row[1] == pytest.approx(0.6)
    assert row[2] == pytest.approx(100.0)
    assert row[3] == pytest.approx(8.0)
