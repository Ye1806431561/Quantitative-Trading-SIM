"""Shared validation helpers for domain models."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar


class DomainValidationError(ValueError):
    """Raised when domain model validation fails."""


TEnum = TypeVar("TEnum")


def _require_key(data: Mapping[str, Any], key: str) -> Any:
    if key not in data:
        raise DomainValidationError(f"Missing field: {key}")
    return data[key]


def require_str(data: Mapping[str, Any], key: str) -> str:
    value = _require_key(data, key)
    if not isinstance(value, str):
        raise DomainValidationError(f"{key} must be a string")
    if not value.strip():
        raise DomainValidationError(f"{key} must not be empty")
    return value.strip()


def require_enum(data: Mapping[str, Any], key: str, enum_cls: type[TEnum]) -> TEnum:
    raw = _require_key(data, key)
    try:
        return enum_cls(raw)  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover - specific message follows
        raise DomainValidationError(f"{key} must be one of {[e.value for e in enum_cls]}") from exc


def require_positive_number(data: Mapping[str, Any], key: str, allow_zero: bool = False) -> float:
    value = _require_key(data, key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise DomainValidationError(f"{key} must be a number")
    numeric = float(value)
    if allow_zero and numeric < 0:
        raise DomainValidationError(f"{key} must be >= 0")
    if not allow_zero and numeric <= 0:
        raise DomainValidationError(f"{key} must be > 0")
    return numeric


def optional_positive_number(
    data: Mapping[str, Any],
    key: str,
    allow_zero: bool = False,
    default: float | None = None,
) -> float | None:
    if key not in data or data[key] is None:
        return default
    return require_positive_number(data, key, allow_zero=allow_zero)


def require_ratio(data: Mapping[str, Any], key: str, inclusive_min: bool = False) -> float:
    value = _require_key(data, key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise DomainValidationError(f"{key} must be a number")
    numeric = float(value)
    lower_ok = numeric >= 0 if inclusive_min else numeric > 0
    if not lower_ok or numeric > 1:
        raise DomainValidationError(f"{key} must be within (0, 1]" if inclusive_min else "(0, 1]")
    return numeric


def require_non_negative(data: Mapping[str, Any], key: str) -> float:
    return require_positive_number(data, key, allow_zero=True)


def require_timestamp(data: Mapping[str, Any], key: str) -> int:
    from datetime import datetime, timezone

    value = _require_key(data, key)

    # Accept numeric timestamps (int / float).
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = int(value)
        if numeric < 0:
            raise DomainValidationError(f"{key} must be >= 0")
        return numeric

    # Accept datetime objects (produced by SQLite PARSE_DECLTYPES).
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp())

    # Accept string timestamps produced by SQLite CURRENT_TIMESTAMP.
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except (ValueError, TypeError) as exc:
            raise DomainValidationError(
                f"{key} must be a timestamp number or ISO-format string"
            ) from exc

    raise DomainValidationError(f"{key} must be a timestamp number or ISO-format string")


def optional_timestamp(data: Mapping[str, Any], key: str) -> int | None:
    if key not in data or data[key] is None:
        return None
    return require_timestamp(data, key)
