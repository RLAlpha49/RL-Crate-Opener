"""Persistent settings management for environment variables.

This module handles saving and loading application settings to/from a JSON file,
allowing settings to persist across program restarts. Settings are loaded at
application startup and applied as environment variables before config initialization.

Environment variable precedence:
1. Shell environment variables (highest priority - for CI/CD)
2. Saved settings file (user preferences)
3. Hardcoded defaults in config.py (lowest priority)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.utils.logger import logger


class SettingsManager:
    """Manages persistent application settings stored in JSON format."""

    # Path to the settings file where user preferences are persisted.
    SETTINGS_FILE = Path("settings.json")

    # Available settings with default values and types.
    # Each entry is a tuple of (default_value, type_name).
    AVAILABLE_SETTINGS = {
        "RL_DEBUG_DUMP_IMAGES": ("false", "bool"),
        "RL_DEBUG_DUMP_ALWAYS": ("false", "bool"),
        "RL_DEBUG_DIR": ("debug_images", "str"),
        "RL_DEBUG_MAX_IMAGES": ("0", "int"),
        "RL_DEBUG_IMAGE_FORMAT": ("PNG", "str"),
        "RL_DEBUG_JPEG_QUALITY": ("85", "int"),
        "RL_LOG_LEVEL": ("INFO", "str"),
        "RL_LOG_TO_FILE": ("false", "bool"),
        "RL_LOG_FILE": ("", "str"),
        "RL_COLOR_SHADE_TOLERANCE": ("10", "int"),
        "RL_DROP_CHECK_TOLERANCE": ("10", "int"),
        "RL_OPEN_BUTTON_TOLERANCE": ("10", "int"),
        "RL_INITIAL_DELAY": ("1", "float"),
        "RL_DROP_CHECK_INTERVAL": ("8", "float"),
        "RL_ITEMS_FILE": ("items.txt", "str"),
        "RL_WINDOW_CACHE_REFRESH_INTERVAL": ("10", "int"),
        "RL_TESSERACT_CMD": ("", "str"),
    }

    @classmethod
    def load_settings(cls) -> dict[str, str]:
        """
        Load settings from the settings file.

        Only loads settings that are NOT already set as environment variables.
        This respects the precedence: shell env vars > saved file > defaults.

        Returns:
            Dictionary of loaded settings (env_var_name -> value)
        """
        settings: dict[str, str] = {}

        if not cls.SETTINGS_FILE.exists():
            logger.debug("Settings file does not exist yet: %s", cls.SETTINGS_FILE)
            return settings

        try:
            with open(cls.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.warning(
                    "Settings file format is invalid, expected dict, got %s",
                    type(data).__name__,
                )
                return settings

            # Load settings only if not already in environment
            for env_var, value in data.items():
                if env_var not in os.environ:
                    settings[env_var] = str(value)
                    logger.debug("Loaded setting from file: %s", env_var)
                else:
                    logger.debug("Skipped setting %s (already in environment)", env_var)

        except json.JSONDecodeError as e:
            logger.warning("Settings file is not valid JSON: %s", e)
        except (OSError, IOError) as e:
            logger.warning("Failed to load settings file: %s", e)

        return settings

    @classmethod
    def apply_settings(cls, settings: dict[str, str]) -> None:
        """
        Apply settings as environment variables.

        Args:
            settings: Dictionary of settings (env_var_name -> value)
        """
        for env_var, value in settings.items():
            os.environ[env_var] = value

    @classmethod
    def load_and_apply(cls) -> None:
        """Load settings from file and apply them as environment variables."""
        settings = cls.load_settings()
        cls.apply_settings(settings)
        if settings:
            logger.info("Loaded %d settings from file", len(settings))

    @classmethod
    def save_settings(cls, settings: dict[str, Any]) -> bool:
        """
        Save settings to the settings file.

        Filters to only save known settings (AVAILABLE_SETTINGS keys).

        Args:
            settings: Dictionary of settings to save (env_var_name -> value)

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Filter to only known settings
            filtered_settings = {
                k: v for k, v in settings.items() if k in cls.AVAILABLE_SETTINGS
            }

            if not filtered_settings:
                logger.warning("No valid settings to save")
                return False

            # Create parent directory if it doesn't exist
            cls.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

            with open(cls.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(filtered_settings, f, indent=2)

            logger.info("Saved %d settings to file", len(filtered_settings))
            return True

        except (OSError, IOError, TypeError) as e:
            logger.error("Failed to save settings file: %s", e)
            return False

    @classmethod
    def get_saved_settings(cls) -> dict[str, Any]:
        """
        Get currently saved settings from file without applying them.

        Returns:
            Dictionary of saved settings, or empty dict if file doesn't exist
        """
        if not cls.SETTINGS_FILE.exists():
            return {}

        try:
            with open(cls.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.warning("Failed to read saved settings: %s", e)
            return {}

    @classmethod
    def reset_settings(cls) -> bool:
        """
        Delete the settings file (reset to defaults).

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if cls.SETTINGS_FILE.exists():
                cls.SETTINGS_FILE.unlink()
                logger.info("Settings file deleted")
                return True
            return False
        except OSError as e:
            logger.error("Failed to delete settings file: %s", e)
            return False
