from __future__ import annotations

import pytest

from src.utils.config import ConfigValidationError, load_config, load_strategies_config


def test_load_config_uses_defaults_when_yaml_missing(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for env_name in ("LOG_LEVEL", "DATABASE_PATH", "EXCHANGE_API_KEY", "EXCHANGE_API_SECRET"):
        monkeypatch.delenv(env_name, raising=False)

    config = load_config(
        config_path=tmp_path / "missing.yaml",
        env_path=tmp_path / ".env",
    )

    assert config["system"]["log_level"] == "INFO"
    assert config["system"]["database_path"] == "data/database/trading.db"
    assert config["account"]["initial_capital"] == 10000.0
    assert config["exchange"]["api_key"] == ""


def test_load_config_yaml_overrides_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for env_name in ("LOG_LEVEL", "DATABASE_PATH", "EXCHANGE_API_KEY", "EXCHANGE_API_SECRET"):
        monkeypatch.delenv(env_name, raising=False)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
system:
  log_level: WARNING
account:
  initial_capital: 25000.0
risk:
  max_position_size: 0.2
        """.strip(),
        encoding="utf-8",
    )

    config = load_config(config_path=config_file, env_path=tmp_path / ".env")

    assert config["system"]["log_level"] == "WARNING"
    assert config["account"]["initial_capital"] == 25000.0
    assert config["risk"]["max_position_size"] == 0.2


def test_load_config_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
system:
  log_level: WARNING
logging:
  level: WARNING
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("LOG_LEVEL", "error")
    monkeypatch.setenv("DATABASE_PATH", "/tmp/test_trading.db")
    monkeypatch.setenv("EXCHANGE_API_KEY", "demo-key")
    monkeypatch.setenv("EXCHANGE_API_SECRET", "demo-secret")

    config = load_config(config_path=config_file, env_path=tmp_path / ".env")

    assert config["system"]["log_level"] == "ERROR"
    assert config["logging"]["level"] == "ERROR"
    assert config["system"]["database_path"] == "/tmp/test_trading.db"
    assert config["exchange"]["api_key"] == "demo-key"
    assert config["exchange"]["api_secret"] == "demo-secret"


def test_load_config_rejects_invalid_risk_values(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for env_name in ("LOG_LEVEL", "DATABASE_PATH", "EXCHANGE_API_KEY", "EXCHANGE_API_SECRET"):
        monkeypatch.delenv(env_name, raising=False)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
risk:
  max_position_size: 0.9
  max_total_position: 0.8
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="max_position_size"):
        load_config(config_path=config_file, env_path=tmp_path / ".env")


def test_load_config_rejects_non_sqlite_runtime_write_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    for env_name in ("LOG_LEVEL", "DATABASE_PATH", "EXCHANGE_API_KEY", "EXCHANGE_API_SECRET"):
        monkeypatch.delenv(env_name, raising=False)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
market_data:
  runtime_write_target: csv
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="runtime_write_target"):
        load_config(config_path=config_file, env_path=tmp_path / ".env")


def test_load_config_rejects_non_sqlite_backtest_data_read_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    for env_name in ("LOG_LEVEL", "DATABASE_PATH", "EXCHANGE_API_KEY", "EXCHANGE_API_SECRET"):
        monkeypatch.delenv(env_name, raising=False)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
backtest:
  data_read_source: csv
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="data_read_source"):
        load_config(config_path=config_file, env_path=tmp_path / ".env")


def test_load_strategies_config_rejects_invalid_sma_window(tmp_path) -> None:
    strategies_file = tmp_path / "strategies.yaml"
    strategies_file.write_text(
        """
sma_strategy:
  params:
    fast_period: 30
    slow_period: 10
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="fast_period"):
        load_strategies_config(config_path=strategies_file)
