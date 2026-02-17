from __future__ import annotations

import copy
from pathlib import Path

from src.utils.config_defaults import DEFAULT_CONFIG
from src.utils.logger import get_logger, setup_logger


def _build_logger_config(tmp_path: Path) -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["system"]["log_dir"] = str(tmp_path / "logs")
    config["logging"]["files"]["main"]["path"] = str(tmp_path / "logs/main.log")
    config["logging"]["files"]["strategy"]["path"] = str(tmp_path / "logs/strategy.log")
    config["logging"]["files"]["trade"]["path"] = str(tmp_path / "logs/trade.log")
    config["logging"]["files"]["error"]["path"] = str(tmp_path / "logs/error.log")
    return config


def test_setup_logger_routes_messages_to_correct_files(tmp_path) -> None:
    config = _build_logger_config(tmp_path)
    setup_logger(config)

    get_logger("main").info("main message")
    get_logger("strategy").debug("strategy message")
    get_logger("trade").info("trade message")
    get_logger("main").error("error message")

    get_logger().complete()

    main_text = (tmp_path / "logs/main.log").read_text(encoding="utf-8")
    strategy_text = (tmp_path / "logs/strategy.log").read_text(encoding="utf-8")
    trade_text = (tmp_path / "logs/trade.log").read_text(encoding="utf-8")
    error_text = (tmp_path / "logs/error.log").read_text(encoding="utf-8")

    assert "main message" in main_text
    assert "strategy message" in strategy_text
    assert "trade message" in trade_text
    assert "error message" in error_text
    assert "strategy message" not in main_text
    assert "trade message" not in main_text


def test_setup_logger_redacts_sensitive_values(tmp_path) -> None:
    config = _build_logger_config(tmp_path)
    setup_logger(config)

    get_logger("main").info("api_key=plain-value api_secret=another")
    get_logger().complete()

    main_text = (tmp_path / "logs/main.log").read_text(encoding="utf-8")
    assert "plain-value" not in main_text
    assert "another" not in main_text
    assert "api_key=***" in main_text
    assert "api_secret=***" in main_text


def test_get_logger_rejects_unknown_log_type(tmp_path) -> None:
    config = _build_logger_config(tmp_path)
    setup_logger(config)

    try:
        get_logger("unknown")
        assert False, "Expected ValueError for unknown log_type"
    except ValueError as error:
        assert "log_type must be one of" in str(error)
