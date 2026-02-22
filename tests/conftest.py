"""Global pytest hooks for suite categorization."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Default all tests to `unit` unless explicitly marked as integration."""
    for item in items:
        if item.get_closest_marker("integration") is None:
            item.add_marker(pytest.mark.unit)
