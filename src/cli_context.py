"""CLI runtime context and shared helpers (step 37)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from rich.console import Console

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.order_service import OrderService
from src.core.trade_service import TradeService
from src.utils.config import load_config, load_strategies_config

console = Console()


class CLICommandError(RuntimeError):
    """Raised when a CLI command fails with an explainable error."""


@dataclass
class CLIContext:
    """Runtime objects shared by all CLI commands."""

    config: dict[str, Any]
    strategies_config: dict[str, Any]
    database: SQLiteDatabase
    account_service: AccountService
    order_service: OrderService
    trade_service: TradeService

    def close(self) -> None:
        self.database.close()


def build_context(
    *,
    config_path: str,
    strategies_path: str,
    env_path: str,
) -> CLIContext:
    """Load config, open database, and build core services."""
    config = load_config(config_path=config_path, env_path=env_path)
    strategies_config = load_strategies_config(config_path=strategies_path)

    database = SQLiteDatabase.from_config(config)
    database.open()
    database.initialize_schema()

    account_service = AccountService.from_config(database, config)
    order_service = OrderService(database, account_service)
    trade_service = TradeService(database, order_service)

    return CLIContext(
        config=config,
        strategies_config=strategies_config,
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
    )


def parse_param_pairs(pairs: list[str] | None) -> dict[str, Any]:
    """Parse repeated --param key=value arguments into a dictionary."""
    parsed: dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise CLICommandError(f"参数格式错误: {pair}（应为 key=value）")
        key, raw_value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise CLICommandError(f"参数键不能为空: {pair}")
        parsed[key] = _coerce_value(raw_value.strip())
    return parsed


def resolve_time_range_ms(
    *,
    start_ms: int | None,
    end_ms: int | None,
    days: int | None,
) -> tuple[int, int]:
    """Resolve time range from explicit timestamps or trailing days."""
    if start_ms is not None or end_ms is not None:
        if start_ms is None or end_ms is None:
            raise CLICommandError("必须同时提供 --start-ms 和 --end-ms")
        if start_ms < 0 or end_ms < 0:
            raise CLICommandError("时间戳必须 >= 0")
        if start_ms > end_ms:
            raise CLICommandError("start-ms 不能大于 end-ms")
        return int(start_ms), int(end_ms)

    days_value = int(days or 30)
    if days_value <= 0:
        raise CLICommandError("days 必须 > 0")

    now_ms = int(time.time() * 1000)
    start = now_ms - days_value * 24 * 3600 * 1000
    return start, now_ms


def runtime_state_path(config: Mapping[str, Any]) -> Path:
    """Return runtime status file path under configured data dir."""
    system = config.get("system")
    if not isinstance(system, Mapping):
        raise CLICommandError("配置缺失: system")

    data_dir = system.get("data_dir")
    if not isinstance(data_dir, str) or not data_dir.strip():
        raise CLICommandError("配置缺失: system.data_dir")

    path = Path(data_dir).expanduser() / "runtime_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_runtime_state(config: Mapping[str, Any]) -> dict[str, Any]:
    path = runtime_state_path(config)
    if not path.exists():
        return {"running": False, "updated_at_ms": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"running": False, "updated_at_ms": None}
    if not isinstance(payload, dict):
        return {"running": False, "updated_at_ms": None}
    if "running" not in payload:
        payload["running"] = False
    return payload


def write_runtime_state(config: Mapping[str, Any], state: Mapping[str, Any]) -> Path:
    path = runtime_state_path(config)
    content = dict(state)
    content["updated_at_ms"] = int(time.time() * 1000)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _coerce_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"

    try:
        if raw.startswith("0") and raw != "0" and not raw.startswith("0."):
            raise ValueError
        return int(raw)
    except ValueError:
        pass

    try:
        return float(raw)
    except ValueError:
        return raw
