# Quantitative Trading Simulator

## Phase 0 Step 7: Logging Scheme

### Goal
- Provide leveled logging with console + rotating file outputs.
- Keep runtime behavior configurable from `config/config.yaml`.
- Split logs by usage stream: `main`, `strategy`, `trade`, and `error`.

### Runtime Entry
- Setup function: `src/utils/logger.py` -> `setup_logger(config)`
- Stream logger accessor: `src/utils/logger.py` -> `get_logger(log_type)`

### Log Routing Rules
- Console:
  - Receives all messages above `logging.level`.
  - Uses configured log format with colorized output.
- `main` file:
  - Receives logs with `log_type=main`.
- `strategy` file:
  - Receives logs with `log_type=strategy`.
- `trade` file:
  - Receives logs with `log_type=trade`.
- `error` file:
  - Receives all `ERROR` / `CRITICAL` logs regardless of stream.

### Rotation and Retention
- Rotation and retention are configured per file in `config/config.yaml`:
  - `logging.files.main`
  - `logging.files.strategy`
  - `logging.files.trade`
  - `logging.files.error`
- Compression strategy comes from `logging.compression`.

### Sensitive Data Protection
- Logger patcher redacts sensitive key/value patterns in message text:
  - `api_key`
  - `api_secret`
  - `token`
  - `password`
  - `secret`

### Manual Drill (Acceptance)
1. Ensure dependencies are installed and config exists:
   - `pip install -r requirements.txt`
2. Run the logger drill in Python:
   ```python
   from src.utils.config import load_config
   from src.utils.logger import setup_logger, get_logger

   config = load_config()
   setup_logger(config)

   get_logger("main").debug("debug from main")
   get_logger("main").info("info from main")
   get_logger("strategy").warning("warning from strategy")
   get_logger("trade").error("error from trade")
   get_logger("main").critical("api_key=demo-key")
   ```
3. Validate console output and files:
   - Console shows multi-level events.
   - `logs/app_*.log` has main events.
   - `logs/strategy_*.log` has strategy events.
   - `logs/trade_*.log` has trade events.
   - `logs/error_*.log` has error/critical events.
   - Sensitive text appears redacted (e.g. `api_key=***`).

### Automated Checks
- `tests/test_logger.py`
  - stream routing test
  - redaction test
  - invalid stream guard
