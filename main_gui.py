"""
Rocket League Drop Opener - GUI Application

This script launches the graphical user interface for the Rocket League Drop Opener.
It provides a modern GUI alternative to the command-line interface with real-time
progress tracking, log viewing, and statistics display.

Author: Rewritten with modern Python practices
License: MIT License
"""

import sys

from src.settings_manager import SettingsManager
from src.config import CONFIG
from src.utils.logger import logger


def main() -> int:
    """
    Main GUI application entry point.

    Initializes PyQt6 application, applies theme, creates main window,
    and starts the event loop.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    import importlib  # pylint: disable=import-outside-toplevel

    # Load persistent settings BEFORE using CONFIG
    # Settings must be applied as environment variables first
    SettingsManager.load_and_apply()

    # Reload config module to pick up environment variables from settings
    import src.config  # pylint: disable=import-outside-toplevel

    importlib.reload(src.config)

    # Configure global file logging if RL_LOG_FILE is set
    if CONFIG.LOG_FILE:
        from pathlib import Path  # pylint: disable=import-outside-toplevel
        from src.utils.logger import configure_logger  # pylint: disable=import-outside-toplevel

        configure_logger(log_file=Path(CONFIG.LOG_FILE))

    try:
        logger.info("GUI application started")

        # Import GUI dependencies here to catch ImportError if PyQt6 is not installed
        from PyQt6.QtWidgets import QApplication, QMessageBox  # pylint: disable=import-outside-toplevel

        from src.config_app import APP_NAME  # pylint: disable=import-outside-toplevel
        from src.gui.main_window import MainWindow  # pylint: disable=import-outside-toplevel
        from src.gui.styles import Theme, apply_theme  # pylint: disable=import-outside-toplevel

        # Create QApplication instance
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)

        # Apply dark theme
        apply_theme(app, Theme.DARK)

        # Check RL_TESSERACT_CMD validity and register warning callback
        import os  # pylint: disable=import-outside-toplevel
        from pathlib import Path  # pylint: disable=import-outside-toplevel

        tesseract_cmd = os.environ.get("RL_TESSERACT_CMD", "").strip()
        if tesseract_cmd and not Path(tesseract_cmd).exists():
            # Show non-blocking warning message
            QMessageBox.warning(
                None,
                "Tesseract Configuration Issue",
                f"The configured Tesseract path is invalid:\n\n{tesseract_cmd}\n\n"
                "OCR functionality may not work. Please verify the path in settings "
                "or install Tesseract OCR.",
            )

        # Create and show main window
        window = MainWindow()
        window.show()

        # Execute event loop and return exit code
        return app.exec()

    except ImportError:
        logger.exception("Failed to import required module")
        print(
            "Failed to start GUI: PyQt6 module not found. Please install it:\n    pip install -r requirements.txt"
        )
        return 1

    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Failed to start GUI application")
        print(f"Failed to start GUI: {e}")
        return 1

    finally:
        logger.info("GUI application shutdown")


if __name__ == "__main__":
    sys.exit(main())
