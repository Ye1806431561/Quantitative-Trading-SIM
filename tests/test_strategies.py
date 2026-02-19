from __future__ import annotations

import pytest

from src.core.enums import StrategyRunStatus
from src.live.simulator import StrategyLifecycleDriver
from src.strategies.base import StrategyContext, StrategyLifecycleError, StrategyOrderEvent, StrategyTradeEvent
from src.strategies.lifecycle_demo_strategy import LifecycleProbeStrategy


def test_strategy_lifecycle_callbacks_fire_in_expected_order() -> None:
    strategy = LifecycleProbeStrategy()
    context = StrategyContext(
        strategy_id="run-001",
        symbol="BTC/USDT",
        timeframe="1h",
        parameters={"fast_period": 10, "slow_period": 30},
    )
    driver = StrategyLifecycleDriver(strategy, context)

    driver.start()
    signal = driver.on_market_data({"close": 50_100.0})
    driver.on_order_update(
        StrategyOrderEvent(
            order_id="ORD-1",
            symbol="BTC/USDT",
            status="filled",
            filled=0.2,
        )
    )
    driver.on_trade_update(
        StrategyTradeEvent(
            trade_id="TRD-1",
            order_id="ORD-1",
            symbol="BTC/USDT",
            price=50_100.0,
            amount=0.2,
            fee=10.02,
        )
    )
    driver.stop(reason="manual-stop")

    assert signal == {"action": "hold"}
    assert strategy.status is StrategyRunStatus.STOPPED
    assert strategy.events == [
        "initialize:BTC/USDT:1h",
        "run:50100.0",
        "order:ORD-1:filled",
        "trade:TRD-1:0.2",
        "stop:manual-stop",
    ]


def test_driver_requires_start_before_on_market_data() -> None:
    strategy = LifecycleProbeStrategy()
    context = StrategyContext(strategy_id="run-000", symbol="BTC/USDT", timeframe="1h")
    driver = StrategyLifecycleDriver(strategy, context)

    with pytest.raises(StrategyLifecycleError, match="driver.start\\(\\)"):
        driver.on_market_data({"close": 1.0})


def test_driver_requires_start_before_on_order_update() -> None:
    strategy = LifecycleProbeStrategy()
    context = StrategyContext(strategy_id="run-000", symbol="BTC/USDT", timeframe="1h")
    driver = StrategyLifecycleDriver(strategy, context)

    with pytest.raises(StrategyLifecycleError, match="driver.start\\(\\)"):
        driver.on_order_update(
            StrategyOrderEvent(
                order_id="ORD-0",
                symbol="BTC/USDT",
                status="open",
                filled=0.0,
            )
        )


def test_driver_requires_start_before_on_trade_update() -> None:
    strategy = LifecycleProbeStrategy()
    context = StrategyContext(strategy_id="run-000", symbol="BTC/USDT", timeframe="1h")
    driver = StrategyLifecycleDriver(strategy, context)

    with pytest.raises(StrategyLifecycleError, match="driver.start\\(\\)"):
        driver.on_trade_update(
            StrategyTradeEvent(
                trade_id="TRD-0",
                order_id="ORD-0",
                symbol="BTC/USDT",
                price=50_000.0,
                amount=0.01,
                fee=0.0,
            )
        )


def test_driver_requires_start_before_stop() -> None:
    strategy = LifecycleProbeStrategy()
    context = StrategyContext(strategy_id="run-000", symbol="BTC/USDT", timeframe="1h")
    driver = StrategyLifecycleDriver(strategy, context)

    with pytest.raises(StrategyLifecycleError, match="driver.start\\(\\)"):
        driver.stop(reason="manual-stop")


def test_strategy_cannot_run_before_initialize() -> None:
    strategy = LifecycleProbeStrategy()
    with pytest.raises(StrategyLifecycleError, match="before run"):
        strategy.run({"close": 1.0})


def test_strategy_cannot_initialize_twice() -> None:
    strategy = LifecycleProbeStrategy()
    context = StrategyContext(strategy_id="run-002", symbol="ETH/USDT", timeframe="15m")
    strategy.initialize(context)
    assert strategy.status is StrategyRunStatus.RUNNING

    with pytest.raises(StrategyLifecycleError, match="initialized once"):
        strategy.initialize(context)


def test_strategy_cannot_stop_before_initialize() -> None:
    strategy = LifecycleProbeStrategy()
    assert strategy.status is StrategyRunStatus.PENDING

    with pytest.raises(StrategyLifecycleError, match="before stop"):
        strategy.stop(reason="manual-stop")


def test_strategy_cannot_notify_order_after_stop() -> None:
    strategy = LifecycleProbeStrategy()
    context = StrategyContext(strategy_id="run-003", symbol="BTC/USDT", timeframe="1h")
    strategy.initialize(context)
    strategy.stop(reason="manual-stop")
    assert strategy.status is StrategyRunStatus.STOPPED

    with pytest.raises(StrategyLifecycleError, match="before notify_order"):
        strategy.notify_order(
            StrategyOrderEvent(
                order_id="ORD-2",
                symbol="BTC/USDT",
                status="filled",
                filled=0.1,
            )
        )


def test_strategy_cannot_notify_trade_after_stop() -> None:
    strategy = LifecycleProbeStrategy()
    context = StrategyContext(strategy_id="run-004", symbol="BTC/USDT", timeframe="1h")
    strategy.initialize(context)
    strategy.stop(reason="manual-stop")
    assert strategy.status is StrategyRunStatus.STOPPED

    with pytest.raises(StrategyLifecycleError, match="before notify_trade"):
        strategy.notify_trade(
            StrategyTradeEvent(
                trade_id="TRD-2",
                order_id="ORD-2",
                symbol="BTC/USDT",
                price=50_200.0,
                amount=0.1,
                fee=5.02,
            )
        )
