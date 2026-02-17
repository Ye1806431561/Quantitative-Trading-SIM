"""Configuration loading with precedence: defaults < YAML < environment."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.utils.config_defaults import (
    DEFAULT_CONFIG,
    DEFAULT_STRATEGIES_CONFIG,
    ENV_OVERRIDES,
)
from src.utils.config_validation import (
    ConfigValidationError,
    require_mapping,
    validate_config,
    validate_strategies_config,
)


def load_config(
    config_path: str | Path = "config/config.yaml",
    env_path: str | Path = ".env",
) -> dict[str, Any]:
    """Load runtime config with precedence: defaults < YAML < environment."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    yaml_values = _load_yaml_mapping(config_path)
    _validate_known_keys(yaml_values, DEFAULT_CONFIG)
    _deep_merge(config, yaml_values)

    load_dotenv(dotenv_path=env_path, override=False)
    _apply_env_overrides(config)
    validate_config(config)
    return config


def load_strategies_config(
    config_path: str | Path = "config/strategies.yaml",
) -> dict[str, Any]:
    """Load strategy config with precedence: defaults < YAML."""
    config = copy.deepcopy(DEFAULT_STRATEGIES_CONFIG)
    yaml_values = _load_yaml_mapping(config_path)
    _validate_known_keys(yaml_values, DEFAULT_STRATEGIES_CONFIG)
    _deep_merge(config, yaml_values)
    validate_strategies_config(config)
    return config


def _load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}

    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        return {}

    loaded = yaml.safe_load(content)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigValidationError(f"YAML root must be a mapping: {file_path}")
    return loaded


def _deep_merge(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        current_value = target.get(key)
        if isinstance(current_value, dict) and isinstance(value, dict):
            _deep_merge(current_value, value)
            continue
        target[key] = value


def _validate_known_keys(values: dict[str, Any], schema: dict[str, Any], path: str = "") -> None:
    for key, value in values.items():
        full_path = f"{path}.{key}" if path else key
        if key not in schema:
            raise ConfigValidationError(f"Unsupported config key: {full_path}")
        if not isinstance(value, dict):
            continue
        schema_value = schema[key]
        if not isinstance(schema_value, dict):
            raise ConfigValidationError(f"Unexpected nested mapping at: {full_path}")
        _validate_known_keys(value, schema_value, full_path)


def _apply_env_overrides(config: dict[str, Any]) -> None:
    for env_name, targets in ENV_OVERRIDES.items():
        raw = os.getenv(env_name)
        if raw is None or not raw.strip():
            continue
        for path, parser in targets:
            parsed = parser(raw)
            _set_nested(config, path, parsed)


def _set_nested(config: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    if len(path) < 2:
        raise ConfigValidationError(f"Invalid config path: {'.'.join(path)}")
    current = require_mapping(config, (path[0],))
    for key in path[1:-1]:
        nested = current.get(key)
        if not isinstance(nested, dict):
            raise ConfigValidationError(f"Invalid config path: {'.'.join(path)}")
        current = nested
    current[path[-1]] = value
