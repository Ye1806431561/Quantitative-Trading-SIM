"""Runtime monitor state and alert persistence (step 38)."""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any, Mapping

from src.utils.logger import get_logger

DEFAULT_STATE: dict[str, Any] = {
    "strategy": {
        "name": None,
        "symbol": None,
        "timeframe": None,
        "status": "idle",
        "started_at_ms": None,
        "stopped_at_ms": None,
        "last_tick_ms": None,
        "iteration_count": 0,
        "last_error": None,
    },
    "account": {
        "base_currency": None,
        "total_assets": None,
        "base_cash": None,
        "positions_value": None,
        "updated_at_ms": None,
    },
    "counters": {
        "alerts_total": 0,
        "strategy_errors": 0,
        "network_errors": 0,
        "reconnect_attempts": 0,
    },
    "alerts": [],
}


class RuntimeMonitor:
    """Keep live runtime status observable via monitor_state.json."""

    def __init__(
        self,
        state_path: Path,
        *,
        max_alerts: int = 50,
        now_ms_fn: callable | None = None,
    ) -> None:
        self._path = state_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max_alerts = max(1, int(max_alerts))
        self._now_ms_fn = now_ms_fn or (lambda: int(time.time() * 1000))
        self._logger = get_logger("main")
        self._state = self._load_state()

    @classmethod
    def from_config(cls, config: Mapping[str, Any], *, max_alerts: int = 50) -> "RuntimeMonitor":
        try:
            path = monitor_state_path(config)
        except Exception:
            path = Path("data") / "monitor_state.json"
        return cls(path, max_alerts=max_alerts)

    def mark_started(self, *, strategy_name: str, symbol: str, timeframe: str) -> None:
        now = self._now_ms_fn()
        strategy = self._state["strategy"]
        strategy.update(
            {
                "name": strategy_name,
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "running",
                "started_at_ms": now,
                "stopped_at_ms": None,
                "last_tick_ms": None,
                "iteration_count": 0,
                "last_error": None,
            }
        )
        self._persist()
        self._logger.info(
            "Runtime monitor started strategy={} symbol={} timeframe={}",
            strategy_name,
            symbol,
            timeframe,
        )

    def mark_iteration(self, *, iteration_count: int, timestamp_ms: int) -> None:
        strategy = self._state["strategy"]
        strategy["iteration_count"] = int(iteration_count)
        strategy["last_tick_ms"] = int(timestamp_ms)
        self._persist()

    def record_account_change(
        self,
        *,
        base_currency: str,
        total_assets: float,
        base_cash: float,
        positions_value: float,
    ) -> None:
        account = self._state["account"]
        previous_total = account.get("total_assets")
        account.update(
            {
                "base_currency": base_currency,
                "total_assets": float(total_assets),
                "base_cash": float(base_cash),
                "positions_value": float(positions_value),
                "updated_at_ms": self._now_ms_fn(),
            }
        )
        if previous_total is not None and abs(float(total_assets) - float(previous_total)) > 1e-9:
            delta = float(total_assets) - float(previous_total)
            self.record_alert(
                level="info",
                category="account_change",
                message=f"total assets changed by {delta:.8f}",
                details={"total_assets": total_assets, "delta": delta},
            )
        else:
            self._persist()

    def record_network_issue(self, *, message: str, reconnect_attempted: bool) -> None:
        counters = self._state["counters"]
        counters["network_errors"] = int(counters["network_errors"]) + 1
        if reconnect_attempted:
            counters["reconnect_attempts"] = int(counters["reconnect_attempts"]) + 1
        self.record_alert(
            level="warning",
            category="network",
            message=message,
            details={"reconnect_attempted": reconnect_attempted},
        )

    def record_strategy_error(self, *, stage: str, error: Exception) -> None:
        counters = self._state["counters"]
        counters["strategy_errors"] = int(counters["strategy_errors"]) + 1
        message = f"{stage} failed: {error.__class__.__name__}: {error}"
        self._state["strategy"]["last_error"] = message
        self.record_alert(
            level="error",
            category="strategy_error",
            message=message,
            details={"stage": stage},
        )

    def record_alert(
        self,
        *,
        level: str,
        category: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        alert = {
            "timestamp_ms": self._now_ms_fn(),
            "level": level,
            "category": category,
            "message": message,
            "details": dict(details or {}),
        }
        alerts = self._state["alerts"]
        alerts.append(alert)
        if len(alerts) > self._max_alerts:
            del alerts[: len(alerts) - self._max_alerts]
        counters = self._state["counters"]
        counters["alerts_total"] = int(counters["alerts_total"]) + 1
        self._persist()
        getattr(self._logger, level if level in {"debug", "info", "warning", "error"} else "info")(
            "monitor_alert category={} message={}",
            category,
            message,
        )

    def mark_stopped(self, *, reason: str | None = None) -> None:
        strategy = self._state["strategy"]
        strategy["status"] = "stopped"
        strategy["stopped_at_ms"] = self._now_ms_fn()
        if reason:
            strategy["last_error"] = reason
        self._persist()

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def _load_state(self) -> dict[str, Any]:
        if not self._path.exists():
            return copy.deepcopy(DEFAULT_STATE)

        try:
            loaded = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return copy.deepcopy(DEFAULT_STATE)
        if not isinstance(loaded, dict):
            return copy.deepcopy(DEFAULT_STATE)

        state = copy.deepcopy(DEFAULT_STATE)
        for section in ("strategy", "account", "counters"):
            payload = loaded.get(section)
            if isinstance(payload, dict):
                state[section].update(payload)
        alerts = loaded.get("alerts")
        if isinstance(alerts, list):
            state["alerts"] = [item for item in alerts if isinstance(item, dict)][-self._max_alerts :]
        return state

    def _persist(self) -> None:
        self._path.write_text(
            json.dumps(self._state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def monitor_state_path(config: Mapping[str, Any]) -> Path:
    """Build monitor state file path under `system.data_dir`."""
    system = config.get("system")
    if not isinstance(system, Mapping):
        raise ValueError("config.system is required")
    data_dir = system.get("data_dir")
    if not isinstance(data_dir, str) or not data_dir.strip():
        raise ValueError("config.system.data_dir must be non-empty")
    return Path(data_dir).expanduser() / "monitor_state.json"
