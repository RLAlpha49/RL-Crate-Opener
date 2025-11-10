"""Logging configuration for the application."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "rl_drop_opener",
    level: Optional[int] = None,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Create and configure a new logger instance.

    Logging level and file path can be controlled via:
    - RL_LOG_LEVEL environment variable (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    - RL_LOG_FILE environment variable for file logging path.

    Args:
        name: Logger name.
        level: Logging level as integer (e.g., logging.DEBUG). Defaults to INFO.
        log_file: Optional file path for file logging.

    Returns:
        Configured logger instance with console and optional file handlers.
    """
    # Determine logging level from parameter or environment
    if level is None:
        level_str = os.environ.get("RL_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)

    # Ensure level is an integer
    if not isinstance(level, int):
        level = logging.INFO

    # Determine log file from parameter or environment
    if log_file is None:
        log_file_str = os.environ.get("RL_LOG_FILE")
        if log_file_str:
            log_file = Path(log_file_str)

    app_logger = logging.getLogger(name)
    app_logger.setLevel(level)

    # Remove existing handlers
    app_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    app_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        try:
            # Ensure parent directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            app_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            app_logger.warning("Could not set up file logging to %s: %s", log_file, e)

    return app_logger


def configure_logger(
    name: str = "rl_drop_opener",
    level: Optional[int] = None,
    log_file: Optional[Path] = None,
) -> None:
    """
    Update the configuration of an existing logger instance.

    Updates the handlers on a logger instance by name without replacing the logger itself.
    All modules calling logging.getLogger(name) will see the updated configuration.

    This function clears all existing handlers and replaces them with new ones.

    Args:
        name: Logger name to configure (must match the logger used elsewhere).
        level: Logging level as integer. If None, preserves current level.
        log_file: Optional file path for file logging.

    Example:
        configure_logger(log_file=Path("app.log"))
        # All subsequent logs go to console and file.
    """
    app_logger = logging.getLogger(name)

    # Update level if provided
    if level is not None:
        app_logger.setLevel(level)

    # Remove existing handlers (but preserve the logger instance)
    app_logger.handlers.clear()

    # Always add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(app_logger.level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    app_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        try:
            # Ensure parent directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(app_logger.level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            app_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            app_logger.warning("Could not set up file logging to %s: %s", log_file, e)


# Global logger instance
logger = setup_logger()
