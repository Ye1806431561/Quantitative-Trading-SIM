"""Default configuration values and environment override mappings."""

from __future__ import annotations

from typing import Any, Callable


ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
ALLOWED_TIMEFRAMES = {"1m", "5m", "15m", "1h", "4h", "1d"}

DEFAULT_CONFIG: dict[str, Any] = {
    "system": {
        "log_level": "INFO",
        "log_dir": "logs",
        "data_dir": "data",
        "database_path": "data/database/trading.db",
    },
    "logging": {
        "level": "INFO",
        "rotation": "00:00",
        "retention": "7 days",
        "compression": "zip",
        "format": (
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        "files": {
            "main": {
                "path": "logs/app_{time:YYYY-MM-DD}.log",
                "rotation": "500 MB",
                "retention": "7 days",
                "level": "INFO",
            },
            "strategy": {
                "path": "logs/strategy_{time:YYYY-MM-DD}.log",
                "rotation": "100 MB",
                "retention": "14 days",
                "level": "DEBUG",
            },
            "trade": {
                "path": "logs/trade_{time:YYYY-MM-DD}.log",
                "rotation": "50 MB",
                "retention": "30 days",
                "level": "INFO",
            },
            "error": {
                "path": "logs/error_{time:YYYY-MM-DD}.log",
                "rotation": "100 MB",
                "retention": "30 days",
                "level": "ERROR",
            },
        },
    },
    "exchange": {
        "name": "binance",
        "testnet": True,
        "rate_limit": True,
        "api_key": "",
        "api_secret": "",
    },
    "market_data": {
        "runtime_write_target": "sqlite",
        "retry": {
            "max_attempts": 3,
            "initial_delay_seconds": 0.2,
            "backoff_multiplier": 2.0,
            "max_delay_seconds": 2.0,
        },
    },
    "account": {
        "initial_capital": 10000.0,
        "base_currency": "USDT",
    },
    "trading": {
        "commission": {
            "maker": 0.001,
            "taker": 0.001,
        },
        "slippage": 0.0005,
    },
    "risk": {
        "max_position_size": 0.3,
        "max_total_position": 0.8,
        "max_drawdown": 0.2,
    },
    "backtest": {
        "default_timeframe": "1h",
        "default_period": 90,
        "data_read_source": "sqlite",
    },
}

DEFAULT_STRATEGIES_CONFIG: dict[str, Any] = {
    "sma_strategy": {
        "enabled": True,
        "params": {"fast_period": 10, "slow_period": 30, "position_size": 0.2},
    },
    "grid_strategy": {
        "enabled": False,
        "params": {"grid_num": 10, "price_range": 0.1, "position_size": 0.1},
    },
    "bollinger_strategy": {
        "enabled": False,
        "params": {"period": 20, "std_dev": 2.0, "position_size": 0.2},
    },
}


def parse_str(raw: str) -> str:
    return raw.strip()


def parse_log_level(raw: str) -> str:
    return raw.strip().upper()


EnvParser = Callable[[str], Any]
EnvTarget = tuple[tuple[str, ...], EnvParser]
ENV_OVERRIDES: dict[str, tuple[EnvTarget, ...]] = {
    "LOG_LEVEL": (
        (("system", "log_level"), parse_log_level),
        (("logging", "level"), parse_log_level),
    ),
    "DATABASE_PATH": ((("system", "database_path"), parse_str),),
    "EXCHANGE_API_KEY": ((("exchange", "api_key"), parse_str),),
    "EXCHANGE_API_SECRET": ((("exchange", "api_secret"), parse_str),),
}
