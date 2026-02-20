# Strategy Param Management Design

## Scope
- Load strategy parameters from `config/strategies.yaml` at startup
- Apply parameters to both backtest and live strategy instances
- Allow explicit parameters to override config values
- Reject unknown or disabled strategy usage

## Decisions
- Use a centralized registry and parameter resolver shared by backtest and live paths
- Read configuration once at startup (no hot reload)
- Parameter priority (low to high): strategy defaults < config file < explicit parameters
- Preserve long-only behavior; strategy logic unchanged

## Behavior
- If a strategy is disabled in config, creation is rejected
- If a strategy name is unknown, creation is rejected
- If an explicit parameter key is unknown for that strategy, raise a validation error

## Backtest Flow
- Resolve strategy class from registry
- Merge parameters using resolver
- Create strategy instance with merged parameters

## Live Flow
- Resolve strategy class from registry
- Merge parameters using resolver
- Pass merged parameters into `StrategyContext.parameters` and strategy constructor

## Testing
- Backtest: modifying `config/strategies.yaml` changes actual strategy parameters
- Live: modifying `config/strategies.yaml` changes `StrategyContext.parameters` and strategy behavior
