"""Configuration validation helpers."""

from __future__ import annotations

from typing import Any

from src.utils.config_defaults import ALLOWED_LOG_LEVELS, ALLOWED_TIMEFRAMES


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""


def validate_config(config: dict[str, Any]) -> None:
    _require_string(config, ("system", "log_dir"))
    _require_string(config, ("system", "data_dir"))
    _require_string(config, ("system", "database_path"))
    _require_log_level(config, ("system", "log_level"))

    _require_log_level(config, ("logging", "level"))
    _require_string(config, ("logging", "rotation"))
    _require_string(config, ("logging", "retention"))
    _require_string(config, ("logging", "compression"))
    _require_string(config, ("logging", "format"))

    files = _require_mapping(config, ("logging", "files"))
    for file_name in ("main", "strategy", "trade", "error"):
        if file_name not in files:
            raise ConfigValidationError(f"Missing logging.files.{file_name}")
        _require_string(config, ("logging", "files", file_name, "path"))
        _require_string(config, ("logging", "files", file_name, "rotation"))
        _require_string(config, ("logging", "files", file_name, "retention"))
        _require_log_level(config, ("logging", "files", file_name, "level"))

    _require_string(config, ("exchange", "name"))
    _require_bool(config, ("exchange", "testnet"))
    _require_bool(config, ("exchange", "rate_limit"))
    _require_string(config, ("exchange", "api_key"), allow_empty=True)
    _require_string(config, ("exchange", "api_secret"), allow_empty=True)

    _require_number(config, ("account", "initial_capital"), min_value=0.0, inclusive_min=False)
    _require_string(config, ("account", "base_currency"))

    _require_number(config, ("trading", "commission", "maker"), min_value=0.0, max_value=1.0)
    _require_number(config, ("trading", "commission", "taker"), min_value=0.0, max_value=1.0)
    _require_number(config, ("trading", "slippage"), min_value=0.0, max_value=1.0)

    max_position_size = _require_number(
        config,
        ("risk", "max_position_size"),
        min_value=0.0,
        max_value=1.0,
        inclusive_min=False,
    )
    max_total_position = _require_number(
        config,
        ("risk", "max_total_position"),
        min_value=0.0,
        max_value=1.0,
        inclusive_min=False,
    )
    _require_number(
        config,
        ("risk", "max_drawdown"),
        min_value=0.0,
        max_value=1.0,
        inclusive_min=False,
    )
    if max_position_size > max_total_position:
        raise ConfigValidationError(
            "risk.max_position_size must be <= risk.max_total_position"
        )

    timeframe = _require_string(config, ("backtest", "default_timeframe"))
    if timeframe not in ALLOWED_TIMEFRAMES:
        raise ConfigValidationError(
            f"backtest.default_timeframe must be one of {sorted(ALLOWED_TIMEFRAMES)}"
        )
    _require_int(config, ("backtest", "default_period"), min_value=1)


def validate_strategies_config(config: dict[str, Any]) -> None:
    sma = _require_mapping(config, ("sma_strategy",))
    grid = _require_mapping(config, ("grid_strategy",))
    bollinger = _require_mapping(config, ("bollinger_strategy",))

    _require_bool_value(sma, "sma_strategy.enabled")
    _require_bool_value(grid, "grid_strategy.enabled")
    _require_bool_value(bollinger, "bollinger_strategy.enabled")

    sma_params = _require_mapping(config, ("sma_strategy", "params"))
    fast = _require_int_value(sma_params, "sma_strategy.params.fast_period", min_value=1)
    slow = _require_int_value(sma_params, "sma_strategy.params.slow_period", min_value=1)
    if fast >= slow:
        raise ConfigValidationError("sma_strategy.params.fast_period must be < slow_period")
    _require_ratio_value(sma_params, "sma_strategy.params.position_size")

    grid_params = _require_mapping(config, ("grid_strategy", "params"))
    _require_int_value(grid_params, "grid_strategy.params.grid_num", min_value=1)
    _require_number_value(
        grid_params,
        "grid_strategy.params.price_range",
        min_value=0.0,
        max_value=1.0,
    )
    _require_ratio_value(grid_params, "grid_strategy.params.position_size")

    boll_params = _require_mapping(config, ("bollinger_strategy", "params"))
    _require_int_value(boll_params, "bollinger_strategy.params.period", min_value=1)
    _require_number_value(
        boll_params,
        "bollinger_strategy.params.std_dev",
        min_value=0.0,
        inclusive_min=False,
    )
    _require_ratio_value(boll_params, "bollinger_strategy.params.position_size")


def read_nested(config: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = config
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise ConfigValidationError(f"Missing config key: {'.'.join(path)}")
        current = current[key]
    return current


def require_mapping(config: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    return _require_mapping(config, path)


def _require_mapping(config: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    value = read_nested(config, path)
    if not isinstance(value, dict):
        raise ConfigValidationError(f"{'.'.join(path)} must be a mapping")
    return value


def _require_string(
    config: dict[str, Any],
    path: tuple[str, ...],
    allow_empty: bool = False,
) -> str:
    value = read_nested(config, path)
    if not isinstance(value, str):
        raise ConfigValidationError(f"{'.'.join(path)} must be a string")
    if not allow_empty and not value.strip():
        raise ConfigValidationError(f"{'.'.join(path)} must not be empty")
    return value.strip()


def _require_log_level(config: dict[str, Any], path: tuple[str, ...]) -> str:
    value = _require_string(config, path).upper()
    if value not in ALLOWED_LOG_LEVELS:
        raise ConfigValidationError(
            f"{'.'.join(path)} must be one of {sorted(ALLOWED_LOG_LEVELS)}"
        )
    return value


def _require_bool(config: dict[str, Any], path: tuple[str, ...]) -> bool:
    value = read_nested(config, path)
    if not isinstance(value, bool):
        raise ConfigValidationError(f"{'.'.join(path)} must be a boolean")
    return value


def _require_number(
    config: dict[str, Any],
    path: tuple[str, ...],
    min_value: float | None = None,
    max_value: float | None = None,
    inclusive_min: bool = True,
    inclusive_max: bool = True,
) -> float:
    value = read_nested(config, path)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigValidationError(f"{'.'.join(path)} must be a number")
    numeric = float(value)
    _check_range(
        path=".".join(path),
        value=numeric,
        min_value=min_value,
        max_value=max_value,
        inclusive_min=inclusive_min,
        inclusive_max=inclusive_max,
    )
    return numeric


def _require_int(config: dict[str, Any], path: tuple[str, ...], min_value: int | None = None) -> int:
    value = read_nested(config, path)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigValidationError(f"{'.'.join(path)} must be an integer")
    if min_value is not None and value < min_value:
        raise ConfigValidationError(f"{'.'.join(path)} must be >= {min_value}")
    return value


def _require_bool_value(data: dict[str, Any], key_path: str) -> bool:
    key = key_path.split(".")[-1]
    value = data.get(key)
    if not isinstance(value, bool):
        raise ConfigValidationError(f"{key_path} must be a boolean")
    return value


def _require_int_value(data: dict[str, Any], key_path: str, min_value: int | None = None) -> int:
    key = key_path.split(".")[-1]
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigValidationError(f"{key_path} must be an integer")
    if min_value is not None and value < min_value:
        raise ConfigValidationError(f"{key_path} must be >= {min_value}")
    return value


def _require_number_value(
    data: dict[str, Any],
    key_path: str,
    min_value: float | None = None,
    max_value: float | None = None,
    inclusive_min: bool = True,
    inclusive_max: bool = True,
) -> float:
    key = key_path.split(".")[-1]
    value = data.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigValidationError(f"{key_path} must be a number")
    numeric = float(value)
    _check_range(
        path=key_path,
        value=numeric,
        min_value=min_value,
        max_value=max_value,
        inclusive_min=inclusive_min,
        inclusive_max=inclusive_max,
    )
    return numeric


def _require_ratio_value(data: dict[str, Any], key_path: str) -> float:
    return _require_number_value(
        data,
        key_path,
        min_value=0.0,
        max_value=1.0,
        inclusive_min=False,
    )


def _check_range(
    path: str,
    value: float,
    min_value: float | None,
    max_value: float | None,
    inclusive_min: bool = True,
    inclusive_max: bool = True,
) -> None:
    if min_value is not None:
        if inclusive_min and value < min_value:
            raise ConfigValidationError(f"{path} must be >= {min_value}")
        if not inclusive_min and value <= min_value:
            raise ConfigValidationError(f"{path} must be > {min_value}")
    if max_value is not None:
        if inclusive_max and value > max_value:
            raise ConfigValidationError(f"{path} must be <= {max_value}")
        if not inclusive_max and value >= max_value:
            raise ConfigValidationError(f"{path} must be < {max_value}")
