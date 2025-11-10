"""
Rocket League Drop Opener - Main Application

This script automates opening item drops in Rocket League using image recognition
and OCR to detect and categorize items.

Author: Rewritten with modern Python practices
License: MIT License
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.settings_manager import SettingsManager
from src.core.drop_opener import DropOpener
from src.data.items import item_manager
from src.utils.logger import logger, configure_logger
from src.config import CONFIG  # pylint: disable=wrong-import-order


def show_menu() -> int:
    """
    Display the main menu and get user choice.

    Menu options:
    1. Open Drops: Start automation with Ctrl+C or ESC key to stop
    2. Run Calibration: Verify screen regions and colors are correctly detected
    3. Calculate Probabilities: Sort items and display drop probability statistics
    4. Exit: Close the application

    Returns:
        User's menu choice (1-4)
    """
    try:
        while True:
            print("\n" + "=" * 50)
            print("Rocket League Drop Opener")
            print("=" * 50 + "\n")
            print("1. Open Drops (Ctrl+C or ESC to stop)")
            print("2. Run Calibration")
            print("3. Calculate Probabilities")
            print("4. Exit\n")

            choice = input("Choice: ").strip()

            # Handle empty input
            if not choice:
                print("Invalid input. Please enter a number (1-4).")
                continue

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= 4:
                    return choice_num
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
            except ValueError:
                print("Invalid input. Please enter a number (1-4).")
    except KeyboardInterrupt:
        print("\n")
        return 4  # Exit on Ctrl+C
    except EOFError:
        print()
        return 4  # Exit on EOF


def main() -> int:
    """Main application entry point."""
    import importlib  # pylint: disable=import-outside-toplevel

    # Load persistent settings BEFORE using CONFIG
    # Settings must be applied as environment variables first
    SettingsManager.load_and_apply()

    # Reload config module to pick up environment variables from settings
    import src.config  # pylint: disable=import-outside-toplevel

    importlib.reload(src.config)

    # Configure global file logging if RL_LOG_FILE is set
    if CONFIG.LOG_FILE:
        configure_logger(log_file=Path(CONFIG.LOG_FILE))

    logger.info("Application started")

    # DropOpener will be instantiated when needed (after menu choice)
    opener: Optional[DropOpener] = None
    # Track the current log file path for error reporting
    current_log_file: Optional[Path] = None

    try:
        while True:
            choice = show_menu()

            if choice == 1:
                # Create DropOpener on first use, reuse for subsequent runs
                if opener is None:
                    opener = DropOpener()

                # Open drops - enable file logging if configured
                if CONFIG.LOG_TO_FILE:
                    log_dir = Path(CONFIG.DEBUG_DIR) / "logs"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    log_file = log_dir / f"automation_{timestamp}.log"
                    current_log_file = log_file
                    # Reconfigure logger with file output (updates existing instance)
                    configure_logger(log_file=log_file)

                opener.run_automation()

            elif choice == 2:
                # Create DropOpener on first use, reuse for subsequent runs
                if opener is None:
                    opener = DropOpener()

                # Run calibration
                opener.run_calibration()

            elif choice == 3:
                # Calculate probabilities
                print("\n" + "=" * 50)
                print("Item Drop Probabilities")
                print("=" * 50)
                item_manager.sort_items()
                item_manager.print_probabilities()

            elif choice == 4:
                # Exit
                print("\nExiting...")
                break

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130  # Standard exit code for SIGINT (Ctrl+C)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Fatal error in main loop")
        print(f"\nFatal error: {e}")
        # If file logging is enabled, provide a hint about the log file
        if CONFIG.LOG_TO_FILE and current_log_file:
            print(f"Check the log file for more details: {current_log_file}")
        return 1
    finally:
        # Final safety cleanup: ensure all keyboard hooks are unregistered
        # This prevents hooks from persisting if future code paths add them outside context managers
        try:
            import keyboard  # pylint: disable=import-outside-toplevel

            keyboard.unhook_all()
        except Exception:  # pylint: disable=broad-exception-caught
            pass  # Silently ignore cleanup errors
        logger.info("Application shutdown")

    return 0


if __name__ == "__main__":
    sys.exit(main())
