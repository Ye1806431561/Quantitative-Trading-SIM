"""Step 38 monitoring/security/reliability tests."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.cli import main as cli_main
from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.order_service import OrderService
from src.core.trade_service import TradeService
from src.data.market import MarketDataFetcher
from src.data.market_policy import RetryPolicy
from src.data.realtime_payloads import RealtimeMarketSnapshot
from src.data.storage import HistoricalCandleStorage
from src.live.monitor import RuntimeMonitor
from src.live.price_service import PriceService
from src.live.realtime_loop import RealtimeLoopConfig, RealtimeSimulationLoop
from src.strategies.base import LiveStrategy, StrategyContext
from src.utils.config_defaults import DEFAULT_CONFIG
from src.utils.credential_vault import (
    CredentialVaultError,
    persist_exchange_credentials,
    read_exchange_credentials,
)
from src.utils.logger import get_logger, setup_logger


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


def test_status_alert_query_reads_monitor_state(cli_files: dict[str, Path]) -> None:
    monitor_path = cli_files["data_dir"] / "monitor_state.json"
    monitor_path.parent.mkdir(parents=True, exist_ok=True)
    monitor_path.write_text(
        json.dumps(
            {
                "strategy": {"status": "running", "iteration_count": 3},
                "account": {"total_assets": 10123.45},
                "counters": {"alerts_total": 1},
                "alerts": [
                    {
                        "timestamp_ms": 1700000000000,
                        "level": "warning",
                        "category": "network",
                        "message": "network timeout; reconnect scheduled",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert _run_cli(cli_files, "status", "--alerts") == 0


def test_exchange_credentials_are_persisted_encrypted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "system": {"data_dir": str(tmp_path / "data")},
        "exchange": {"api_key": "plain-key", "api_secret": "plain-secret"},
    }
    monkeypatch.setenv("CONFIG_MASTER_KEY", "unit-test-master-key")

    vault_path = persist_exchange_credentials(config)
    assert vault_path is not None
    payload = vault_path.read_text(encoding="utf-8")
    assert "plain-key" not in payload
    assert "plain-secret" not in payload

    decrypted = read_exchange_credentials(config, master_key="unit-test-master-key")
    assert decrypted["api_key"] == "plain-key"
    assert decrypted["api_secret"] == "plain-secret"


def test_exchange_credentials_require_master_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "system": {"data_dir": str(tmp_path / "data")},
        "exchange": {"api_key": "plain-key", "api_secret": "plain-secret"},
    }
    monkeypatch.delenv("CONFIG_MASTER_KEY", raising=False)
    with pytest.raises(CredentialVaultError, match="CONFIG_MASTER_KEY"):
        persist_exchange_credentials(config)


def test_logger_masks_sensitive_fields(tmp_path: Path) -> None:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    config["system"]["log_dir"] = str(tmp_path / "logs")
    config["logging"]["files"]["main"]["path"] = str(tmp_path / "logs/main.log")
    config["logging"]["files"]["strategy"]["path"] = str(tmp_path / "logs/strategy.log")
    config["logging"]["files"]["trade"]["path"] = str(tmp_path / "logs/trade.log")
    config["logging"]["files"]["error"]["path"] = str(tmp_path / "logs/error.log")

    setup_logger(config)
    get_logger("main").info("api_key=abc123 api_secret=xyz789")
    get_logger().complete()
    text = (tmp_path / "logs/main.log").read_text(encoding="utf-8")
    assert "abc123" not in text
    assert "xyz789" not in text
    assert "api_key=***" in text


def test_market_fetcher_recovers_after_transient_network_failure() -> None:
    class NetworkError(Exception):
        pass

    class FakeExchange:
        rateLimit = 0

        def __init__(self) -> None:
            self.calls = 0

        def fetch_ticker(self, symbol: str) -> dict[str, Any]:
            self.calls += 1
            if self.calls == 1:
                raise NetworkError("temporary disconnect")
            return {"symbol": symbol, "last": 100.0}

        def fetch_order_book(self, symbol: str, limit: int | None = None) -> dict[str, Any]:
            return {"symbol": symbol, "bids": [], "asks": []}

        def fetch_ohlcv(self, symbol: str, timeframe: str = "1m", since: int | None = None, limit: int | None = None) -> list[list[Any]]:
            return []

    sleeps: list[float] = []
    fetcher = MarketDataFetcher.from_exchange(
        FakeExchange(),
        retry_policy=RetryPolicy(max_attempts=3, initial_delay_seconds=0.1),
        runtime_write_target="sqlite",
        sleep_fn=sleeps.append,
    )
    ticker = fetcher.fetch_ticker("BTC/USDT")
    assert ticker["last"] == 100.0
    assert sleeps == [0.1]


def test_strategy_crash_is_isolated_and_alerted(tmp_path: Path) -> None:
    class CrashStrategy(LiveStrategy):
        def __init__(self) -> None:
            super().__init__("crash_strategy")

        def on_initialize(self, context: StrategyContext) -> None:
            pass

        def on_run(self, market_data: dict[str, Any]) -> dict[str, Any] | None:
            raise RuntimeError("strategy crash for isolation test")

        def on_stop(self, reason: str | None) -> None:
            pass

    class StableMarketService:
        def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
            return RealtimeMarketSnapshot(
                channel="latest_price",
                symbol=symbol,
                ok=True,
                fallback=False,
                timed_out=False,
                error=None,
                fetched_at_ms=int(time.time() * 1000),
                data={"last_price": 100.0, "bid": 99.9, "ask": 100.1},
            )

        def get_klines(self, *args: Any, **kwargs: Any) -> RealtimeMarketSnapshot:
            return RealtimeMarketSnapshot(
                channel="kline",
                symbol="BTC/USDT",
                ok=True,
                fallback=False,
                timed_out=False,
                error=None,
                fetched_at_ms=int(time.time() * 1000),
                data={"timeframe": "1m", "candles": []},
            )

    db = SQLiteDatabase(":memory:")
    db.open()
    db.initialize_schema()
    try:
        account_service = AccountService(db, base_currency="USDT")
        account_service.initialize_accounts({"USDT": 10000.0, "BTC": 0.0})
        order_service = OrderService(db, account_service)
        trade_service = TradeService(db, order_service)
        market_service = StableMarketService()
        price_service = PriceService(db, account_service, market_service)
        candle_storage = HistoricalCandleStorage(db, market_service.get_klines)
        monitor = RuntimeMonitor(tmp_path / "monitor_state.json", max_alerts=20)

        loop = RealtimeSimulationLoop(
            database=db,
            account_service=account_service,
            order_service=order_service,
            trade_service=trade_service,
            market_service=market_service,
            price_service=price_service,
            candle_storage=candle_storage,
            strategy=CrashStrategy(),
            config=RealtimeLoopConfig(
                symbol="BTC/USDT",
                timeframe="1m",
                tick_interval_seconds=0.001,
                max_iterations=3,
            ),
            monitor=monitor,
        )

        loop.start()
        state = json.loads((tmp_path / "monitor_state.json").read_text(encoding="utf-8"))
        assert loop.iteration_count == 3
        assert state["strategy"]["status"] == "stopped"
        assert state["counters"]["strategy_errors"] >= 1
        assert any(alert.get("category") == "strategy_error" for alert in state.get("alerts", []))
    finally:
        db.close()
