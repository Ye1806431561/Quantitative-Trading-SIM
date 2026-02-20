# Bollinger Step 33 Fixes Design

## Scope
- Track progress archive in git
- Align Bollinger strategy to rebound/pullback rules
- Rename stddev to dev across config/code/tests
- Clean progress.md line-number pollution

## Behavior
- Buy: close crosses above lower band after being below
- Close: close crosses below upper band after being above
- Close at mid band for profit-taking (long-only)

## Config
- `bollinger_strategy.params.dev` is the single source of truth
