"""Credential runtime loading tests for CLI context."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.cli_context import CLICommandError, build_context
from src.utils.credential_vault import persist_exchange_credentials


def _write_runtime_files(tmp_path: Path, data_dir: Path) -> tuple[Path, Path, Path]:
    config_path = tmp_path / "config.yaml"
    strategies_path = tmp_path / "strategies.yaml"
    env_path = tmp_path / ".env"

    config_path.write_text(
        yaml.safe_dump(
            {
                "system": {
                    "database_path": str(tmp_path / "trading.db"),
                    "data_dir": str(data_dir),
                    "log_dir": str(tmp_path / "logs"),
                },
                "exchange": {
                    "api_key": "",
                    "api_secret": "",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    strategies_path.write_text("", encoding="utf-8")
    env_path.write_text("", encoding="utf-8")
    return config_path, strategies_path, env_path


def test_build_context_fails_fast_when_vault_exists_but_master_key_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    persist_exchange_credentials(
        {
            "system": {"data_dir": str(data_dir)},
            "exchange": {"api_key": "seed-key", "api_secret": "seed-secret"},
        },
        env={"CONFIG_MASTER_KEY": "seed-master-key"},
    )

    config_path, strategies_path, env_path = _write_runtime_files(tmp_path, data_dir)
    monkeypatch.delenv("CONFIG_MASTER_KEY", raising=False)

    with pytest.raises(CLICommandError, match="CONFIG_MASTER_KEY"):
        build_context(
            config_path=str(config_path),
            strategies_path=str(strategies_path),
            env_path=str(env_path),
        )


def test_build_context_reloads_encrypted_credentials_into_runtime_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    persist_exchange_credentials(
        {
            "system": {"data_dir": str(data_dir)},
            "exchange": {"api_key": "seed-key", "api_secret": "seed-secret"},
        },
        env={"CONFIG_MASTER_KEY": "seed-master-key"},
    )

    config_path, strategies_path, env_path = _write_runtime_files(tmp_path, data_dir)
    monkeypatch.setenv("CONFIG_MASTER_KEY", "seed-master-key")

    context = build_context(
        config_path=str(config_path),
        strategies_path=str(strategies_path),
        env_path=str(env_path),
    )
    try:
        assert context.config["exchange"]["api_key"] == "seed-key"
        assert context.config["exchange"]["api_secret"] == "seed-secret"
    finally:
        context.close()
