"""Market data policy and config parsing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

RUNTIME_WRITE_TARGET = "sqlite"
FORBIDDEN_RUNTIME_WRITE_TARGETS = frozenset({"csv", "parquet"})


class MarketDataConfigError(ValueError):
    """Raised when market data configuration is invalid."""


class MarketDataFetchError(RuntimeError):
    """Raised when market data fetching fails after retry handling."""


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy used by market data requests."""

    max_attempts: int = 3
    initial_delay_seconds: float = 0.2
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise MarketDataConfigError("retry.max_attempts must be >= 1")
        if self.initial_delay_seconds <= 0:
            raise MarketDataConfigError("retry.initial_delay_seconds must be > 0")
        if self.backoff_multiplier < 1.0:
            raise MarketDataConfigError("retry.backoff_multiplier must be >= 1.0")
        if self.max_delay_seconds <= 0:
            raise MarketDataConfigError("retry.max_delay_seconds must be > 0")


@dataclass(frozen=True)
class ExchangeSettings:
    """Exchange selection and client wiring settings."""

    name: str
    testnet: bool
    enable_rate_limit: bool
    api_key: str
    api_secret: str


def read_exchange_settings(config: Mapping[str, Any]) -> ExchangeSettings:
    exchange_cfg = _read_mapping(config, "exchange")
    return ExchangeSettings(
        name=_read_string(exchange_cfg, "name"),
        testnet=_read_bool(exchange_cfg, "testnet", default=False),
        enable_rate_limit=_read_bool(exchange_cfg, "rate_limit", default=True),
        api_key=_read_string(exchange_cfg, "api_key", default=""),
        api_secret=_read_string(exchange_cfg, "api_secret", default=""),
    )


def read_retry_policy(config: Mapping[str, Any]) -> RetryPolicy:
    retry_cfg = _read_market_data_retry(config)
    return RetryPolicy(
        max_attempts=int(retry_cfg.get("max_attempts", 3)),
        initial_delay_seconds=float(retry_cfg.get("initial_delay_seconds", 0.2)),
        backoff_multiplier=float(retry_cfg.get("backoff_multiplier", 2.0)),
        max_delay_seconds=float(retry_cfg.get("max_delay_seconds", 2.0)),
    )


def read_runtime_write_target(config: Mapping[str, Any]) -> str:
    market_data = config.get("market_data")
    if not isinstance(market_data, Mapping):
        return RUNTIME_WRITE_TARGET
    target = market_data.get("runtime_write_target", RUNTIME_WRITE_TARGET)
    if not isinstance(target, str):
        raise MarketDataConfigError("market_data.runtime_write_target must be a string")
    return validate_runtime_write_target(target)


def validate_runtime_write_target(target: str) -> str:
    normalized = target.strip().lower()
    if normalized != RUNTIME_WRITE_TARGET:
        raise MarketDataConfigError(
            "market_data.runtime_write_target must be 'sqlite'; "
            "CSV/Parquet are only allowed in import/export/backup workflows"
        )
    return normalized


def validate_symbol(symbol: str) -> None:
    if not symbol or not symbol.strip():
        raise MarketDataConfigError("symbol must not be empty")


def _read_market_data_retry(config: Mapping[str, Any]) -> Mapping[str, Any]:
    market_data = config.get("market_data")
    if market_data is None:
        return {}
    if not isinstance(market_data, Mapping):
        raise MarketDataConfigError("market_data must be a mapping")
    retry = market_data.get("retry")
    if retry is None:
        return {}
    if not isinstance(retry, Mapping):
        raise MarketDataConfigError("market_data.retry must be a mapping")
    return retry


def _read_mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise MarketDataConfigError(f"missing config mapping: {key}")
    return value


def _read_string(data: Mapping[str, Any], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise MarketDataConfigError(f"{key} must be a string")
    if default is None and not value.strip():
        raise MarketDataConfigError(f"{key} must not be empty")
    return value.strip()


def _read_bool(data: Mapping[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise MarketDataConfigError(f"{key} must be a boolean")
    return value
