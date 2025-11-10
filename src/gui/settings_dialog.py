"""Settings dialog for configuring environment variables."""

from __future__ import annotations

import os
from typing import Any, cast

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import pyqtSlot

from src.settings_manager import SettingsManager
from src.utils.logger import logger


class SettingsDialog(QDialog):
    """Dialog for modifying environment variables that affect application behavior."""

    # Environment variable configurations
    # Format: (env_var_name, display_name, widget_type, default_value, description)
    SETTINGS = [
        (
            "RL_DEBUG_DUMP_IMAGES",
            "Debug: Save Images",
            "checkbox",
            "false",
            "Enable saving failed debug images during automation",
        ),
        (
            "RL_DEBUG_DUMP_ALWAYS",
            "Debug: Save All Images",
            "checkbox",
            "false",
            "Enable saving all images during automation",
        ),
        (
            "RL_DEBUG_DIR",
            "Debug: Directory",
            "text",
            "debug_images",
            "Directory path for debug images",
        ),
        (
            "RL_DEBUG_MAX_IMAGES",
            "Debug: Max Images",
            "spinbox",
            "0",
            "Maximum images to save per session (0 = unlimited)",
        ),
        (
            "RL_DEBUG_IMAGE_FORMAT",
            "Debug: Image Format",
            "combo",
            "PNG",
            "Format for debug images (PNG or JPEG)",
        ),
        (
            "RL_DEBUG_JPEG_QUALITY",
            "Debug: JPEG Quality",
            "spinbox",
            "85",
            "JPEG quality (1-100, higher = better)",
        ),
        (
            "RL_LOG_LEVEL",
            "Logging: Level",
            "combo",
            "INFO",
            "Logging level for console and file output",
        ),
        (
            "RL_LOG_TO_FILE",
            "Logging: To File",
            "checkbox",
            "false",
            "Enable file logging during automation",
        ),
        (
            "RL_COLOR_SHADE_TOLERANCE",
            "Detection: Color Tolerance",
            "spinbox",
            "10",
            "Color matching tolerance (0-255)",
        ),
        (
            "RL_DROP_CHECK_TOLERANCE",
            "Detection: Drop Check Tolerance",
            "spinbox",
            "10",
            "Drop detection color tolerance (0-255)",
        ),
        (
            "RL_OPEN_BUTTON_TOLERANCE",
            "Detection: Open Button Tolerance",
            "spinbox",
            "10",
            "Open button color tolerance (0-255)",
        ),
        (
            "RL_INITIAL_DELAY",
            "Timing: Initial Delay",
            "doublespinbox",
            "1",
            "Initial delay before starting automation (seconds)",
        ),
        (
            "RL_DROP_CHECK_INTERVAL",
            "Timing: Drop Check Interval",
            "doublespinbox",
            "8",
            "Interval for checking if item view is ready (seconds)",
        ),
        (
            "RL_TESSERACT_CMD",
            "OCR: Tesseract Path",
            "text",
            "",
            "Path to Tesseract executable (if not in PATH)",
        ),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the settings dialog.

        Args:
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(600)
        self._widgets: dict[str, Any] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create and layout all settings form fields and buttons."""
        layout = QVBoxLayout(self)

        # Form layout for settings
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        for (
            env_var,
            display_name,
            widget_type,
            default_value,
            description,
        ) in self.SETTINGS:
            # Get current value from environment or use default
            current_value = os.environ.get(env_var, default_value)

            label = QLabel(display_name)
            label.setToolTip(description)

            widget: Any = None
            if widget_type == "text":
                widget = QLineEdit()
                widget.setText(str(current_value))
            elif widget_type == "checkbox":
                widget = QtWidgets.QCheckBox()
                widget.setChecked(current_value.lower() in ("true", "1", "yes"))
            elif widget_type == "spinbox":
                widget = QSpinBox()
                widget.setMinimum(0)
                if "Quality" in display_name:
                    widget.setMaximum(100)
                elif "Tolerance" in display_name:
                    widget.setMaximum(255)
                else:
                    widget.setMaximum(10000)
                try:
                    widget.setValue(int(current_value))
                except ValueError:
                    widget.setValue(int(default_value))
            elif widget_type == "doublespinbox":
                widget = QDoubleSpinBox()
                widget.setMinimum(0.0)
                widget.setMaximum(10000.0)
                widget.setDecimals(2)
                widget.setSingleStep(0.1)
                try:
                    widget.setValue(float(current_value))
                except ValueError:
                    widget.setValue(float(default_value))
            elif widget_type == "combo":
                widget = QComboBox()
                if env_var == "RL_DEBUG_IMAGE_FORMAT":
                    widget.addItems(["PNG", "JPEG"])
                elif env_var == "RL_LOG_LEVEL":
                    widget.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
                widget.setCurrentText(str(current_value))

            if widget is not None:
                widget.setToolTip(description)
                form_layout.addRow(label, widget)
                self._widgets[env_var] = widget

        layout.addLayout(form_layout)

        # Button layout
        button_layout = QtWidgets.QHBoxLayout()
        save_button = QPushButton("Save and Apply")
        cancel_button = QPushButton("Cancel")
        reset_button = QPushButton("Reset to Defaults")

        save_button.clicked.connect(self._save_settings)
        cancel_button.clicked.connect(self.reject)
        reset_button.clicked.connect(self._reset_to_defaults)

        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    @pyqtSlot()
    def _save_settings(self) -> None:
        """Save all settings to environment variables and persist to file."""
        settings_to_save = {}

        for env_var, _, widget_type, _, _ in self.SETTINGS:
            widget = self._widgets.get(env_var)
            if widget is None:
                continue

            value: str = ""
            if widget_type == "text":
                value = cast(QLineEdit, widget).text()
            elif widget_type == "checkbox":
                value = (
                    "true" if cast(QtWidgets.QCheckBox, widget).isChecked() else "false"
                )
            elif widget_type == "spinbox":
                value = str(cast(QSpinBox, widget).value())
            elif widget_type == "doublespinbox":
                value = str(cast(QDoubleSpinBox, widget).value())
            elif widget_type == "combo":
                value = cast(QComboBox, widget).currentText()

            # Set environment variable for immediate effect
            os.environ[env_var] = value
            settings_to_save[env_var] = value
            logger.info(
                "Set %s = %s",
                env_var,
                value if env_var != "RL_TESSERACT_CMD" else "***",
            )

        # Save to persistent file
        if SettingsManager.save_settings(settings_to_save):
            QtWidgets.QMessageBox.information(
                self,
                "Settings Saved",
                "Settings have been saved and will be applied on the next program restart.\n\n"
                "Settings are already active in the current session for most features.",
            )
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Save Failed",
                "Failed to save settings. Check logs for details.",
            )

        self.accept()

    @pyqtSlot()
    def _reset_to_defaults(self) -> None:
        """Reset all settings to their default values."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to their defaults?\n\n"
            "This will delete your saved settings and take effect on the next restart.",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        for env_var, _, widget_type, default_value, _ in self.SETTINGS:
            widget = self._widgets.get(env_var)
            if widget is None:
                continue

            if widget_type == "text":
                cast(QLineEdit, widget).setText(str(default_value))
            elif widget_type == "checkbox":
                cast(QtWidgets.QCheckBox, widget).setChecked(
                    default_value.lower() in ("true", "1", "yes")
                )
            elif widget_type == "spinbox":
                cast(QSpinBox, widget).setValue(int(default_value))
            elif widget_type == "doublespinbox":
                cast(QDoubleSpinBox, widget).setValue(float(default_value))
            elif widget_type == "combo":
                cast(QComboBox, widget).setCurrentText(str(default_value))

        # Delete the settings file
        if SettingsManager.reset_settings():
            QtWidgets.QMessageBox.information(
                self,
                "Settings Reset",
                "Settings have been reset to defaults. Changes take effect on the next restart.",
            )
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Reset Failed",
                "Failed to reset settings. Check logs for details.",
            )
