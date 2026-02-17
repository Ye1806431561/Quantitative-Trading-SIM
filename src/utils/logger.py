"""Loguru logging setup for console and rotating file outputs."""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.utils.config_defaults import DEFAULT_CONFIG

LOG_TYPES = ("main", "strategy", "trade")
_ACTIVE_LOGGER = logger
_SENSITIVE_KEYWORDS = ("api_key", "api_secret", "token", "password", "secret")
_SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|api[_-]?secret|token|password|secret)\b\s*[:=]\s*([^\s,;]+)"
)


def setup_logger(config: dict[str, Any]) -> Any:
    """Configure loguru handlers using validated runtime config."""
    global _ACTIVE_LOGGER

    logger.remove()
    _ACTIVE_LOGGER = logger.patch(_redact_record)

    logging_cfg = _read_mapping(config, ("logging",))
    system_cfg = _read_mapping(config, ("system",))
    log_format = _read_string(logging_cfg, "format")
    console_level = _read_string(logging_cfg, "level")

    log_dir = Path(_read_string(system_cfg, "log_dir"))
    log_dir.mkdir(parents=True, exist_ok=True)

    _ACTIVE_LOGGER.add(
        sys.stderr,
        level=console_level,
        format=log_format,
        colorize=True,
        backtrace=True,
        diagnose=False,
    )

    files_cfg = _read_mapping(logging_cfg, "files")
    for log_type in ("main", "strategy", "trade", "error"):
        file_cfg = _read_mapping(files_cfg, log_type)
        _add_file_handler(
            log_type=log_type,
            file_cfg=file_cfg,
            log_format=log_format,
            compression=_read_string(logging_cfg, "compression"),
        )

    _ACTIVE_LOGGER.bind(log_type="main").info(
        "Logger initialized. console_level={} log_dir={}",
        console_level,
        log_dir,
    )
    return _ACTIVE_LOGGER


def get_logger(log_type: str = "main") -> Any:
    """Return a bound logger for main/strategy/trade log streams."""
    if log_type not in LOG_TYPES:
        raise ValueError(f"log_type must be one of {LOG_TYPES}")
    return _ACTIVE_LOGGER.bind(log_type=log_type)


def get_default_logger_config() -> dict[str, Any]:
    """Return a deep copy of default logger-related config."""
    return copy.deepcopy(DEFAULT_CONFIG)


def _add_file_handler(
    log_type: str,
    file_cfg: dict[str, Any],
    log_format: str,
    compression: str,
) -> None:
    path = Path(_read_string(file_cfg, "path"))
    path.parent.mkdir(parents=True, exist_ok=True)
    _ACTIVE_LOGGER.add(
        path,
        level=_read_string(file_cfg, "level"),
        rotation=_read_string(file_cfg, "rotation"),
        retention=_read_string(file_cfg, "retention"),
        compression=compression,
        format=log_format,
        enqueue=True,
        backtrace=True,
        diagnose=False,
        filter=_build_filter(log_type),
    )


def _build_filter(log_type: str):
    if log_type == "error":
        return lambda record: record["level"].name in {"ERROR", "CRITICAL"}
    return lambda record: record["extra"].get("log_type", "main") == log_type


def _redact_record(record: dict[str, Any]) -> None:
    record["message"] = _redact_text(record["message"])
    masked_extra: dict[str, Any] = {}
    for key, value in record["extra"].items():
        key_lower = key.lower()
        if any(keyword in key_lower for keyword in _SENSITIVE_KEYWORDS):
            masked_extra[key] = "***"
            continue
        if isinstance(value, str):
            masked_extra[key] = _redact_text(value)
            continue
        masked_extra[key] = value
    record["extra"] = masked_extra


def _redact_text(value: str) -> str:
    return _SENSITIVE_PATTERN.sub(r"\1=***", value)


def _read_mapping(data: dict[str, Any], key_path: tuple[str, ...] | str) -> dict[str, Any]:
    keys = (key_path,) if isinstance(key_path, str) else key_path
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"Missing logging config key: {'.'.join(keys)}")
        current = current[key]
    if not isinstance(current, dict):
        raise ValueError(f"Expected mapping for key: {'.'.join(keys)}")
    return current


def _read_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected non-empty string for key: {key}")
    return value.strip()
