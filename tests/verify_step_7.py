
import shutil
from pathlib import Path
from loguru import logger
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.config import load_config
from src.utils.logger import setup_logger, get_logger

def verify_logging():
    print("Starting Step 7 Verification: Logging Scheme")

    # 1. Load Config
    config = load_config()
    print("Config loaded successfully")

    # 2. Cleanup existing logs for clean verification
    log_dir = Path(config["system"]["log_dir"])
    if log_dir.exists():
        print(f"Cleaning up log dir: {log_dir}")
        shutil.rmtree(log_dir)
    
    # 3. Setup Logger
    print("Setting up logger...")
    setup_logger(config)
    
    # 4. Trigger logs of various levels and types
    print("Triggering logs...")
    
    # Main logger
    main_log = get_logger("main")
    main_log.debug("This is a DEBUG message for main code")
    main_log.info("This is an INFO message for main code")
    main_log.warning("This is a WARNING message for main code")
    main_log.error("This is an ERROR message for main code")
    
    # Strategy logger
    strategy_log = get_logger("strategy")
    strategy_log.debug("Strategy DEBUG: Moving Average Crossover")
    strategy_log.info("Strategy INFO: Signal generated")
    
    # Trade logger
    trade_log = get_logger("trade")
    trade_log.info("Trade INFO: Order Placed")
    
    # Error logger (implicit via catch or error level)
    try:
        1 / 0
    except ZeroDivisionError:
        main_log.exception("Caught an exception (should appear in error log)")

    # Redaction test
    main_log.info("API_KEY=1234567890abcdef")
    main_log.info("My secret is secret_value")

    # 5. Verify files exist
    print("Verifying log files...")
    
    # Note: Loguru file names might need to be resolved if they use templates like {time}
    # But since we just ran it, we can look for files in the log dir
    
    found_files = list(log_dir.glob("*.log"))
    print(f"Found log files: {[f.name for f in found_files]}")
    
    expected_types = ["app", "strategy", "trade", "error"]
    for type_prefix in expected_types:
        matches = [f for f in found_files if f.name.startswith(type_prefix)]
        if not matches:
            print(f"❌ FAIL: No log file found for {type_prefix}")
        else:
            print(f"✅ PASS: Found log file for {type_prefix}: {matches[0].name}")
            
            # Read content to check for messages
            content = matches[0].read_text(encoding='utf-8')
            
            if type_prefix == "app":
                if "INFO message for main code" in content:
                    print("  ✅ Content check passed: Info message found")
                else:
                     print("  ❌ Content check failed: Info message missing")
                
                if "API_KEY=***" in content:
                    print("  ✅ Redaction check passed: API_KEY redacted")
                elif "API_KEY=1234567890abcdef" in content:
                     print("  ❌ Redaction check failed: API_KEY visible!")
                
            if type_prefix == "error":
                 if "ZeroDivisionError" in content:
                     print("  ✅ Content check passed: Exception found")
                 else:
                     print("  ❌ Content check failed: Exception missing")

    print("Verification Complete")

if __name__ == "__main__":
    verify_logging()
