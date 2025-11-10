"""Widget displaying live automation progress metrics."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from .styles import FONT_SIZE_LARGE, PADDING_BASE, get_active_palette


class ProgressWidget(QWidget):
    """Display drop and item counts alongside automation status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the progress widget with metrics display.

        Args:
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self._drops_processed = 0
        self._items_opened = 0
        self._current_category: str = "None"
        self._palette = get_active_palette()

        self._title_label: QLabel = QLabel()
        self._drops_label: QLabel = QLabel()
        self._items_label: QLabel = QLabel()
        self._category_label: QLabel = QLabel()
        self._status_label: QLabel = QLabel()

        self._setup_ui()
        self._set_status("Idle", self._palette.text_secondary)

    def _setup_ui(self) -> None:
        """Construct the widget layout and child controls."""

        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet(
            f"""
            QFrame {{
                border: 1px solid {self._palette.border};
                border-radius: 6px;
                background-color: {self._palette.background_primary};
            }}
            """
        )

        title_font = QFont()
        title_font.setPointSize(FONT_SIZE_LARGE)
        title_font.setBold(True)

        mono_font = QFont("Consolas")
        mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
        mono_font.setPointSize(10)

        self._title_label = QLabel("Progress", frame)
        self._title_label.setFont(title_font)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        separator = QFrame(frame)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self._palette.border};")

        self._drops_label = QLabel("Drops Processed: 0", frame)
        self._drops_label.setFont(mono_font)
        self._drops_label.setStyleSheet(
            f"color: {self._palette.accent_primary}; font-weight: 600;"
        )

        self._items_label = QLabel("Items Opened: 0", frame)
        self._items_label.setFont(mono_font)
        self._items_label.setStyleSheet(
            f"color: {self._palette.accent_primary}; font-weight: 600;"
        )

        self._category_label = QLabel("Current Category: None", frame)
        self._category_label.setFont(mono_font)
        self._category_label.setStyleSheet(
            f"color: {self._palette.text_secondary}; font-weight: 500;"
        )

        self._status_label = QLabel("Idle", frame)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        status_font = QFont()
        status_font.setPointSize(11)
        status_font.setBold(True)
        self._status_label.setFont(status_font)

        inner_layout = QVBoxLayout()
        inner_layout.setContentsMargins(
            PADDING_BASE,
            PADDING_BASE,
            PADDING_BASE,
            PADDING_BASE,
        )
        inner_layout.setSpacing(PADDING_BASE)
        inner_layout.addWidget(self._title_label)
        inner_layout.addWidget(separator)
        inner_layout.addWidget(self._drops_label)
        inner_layout.addWidget(self._items_label)
        inner_layout.addWidget(self._category_label)
        inner_layout.addWidget(self._status_label)
        inner_layout.addStretch()

        frame.setLayout(inner_layout)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(frame)
        self.setLayout(root_layout)

    def _set_status(self, message: str, color: str) -> None:
        """Update the status label text and color.

        Args:
            message: Status text to display.
            color: Hex color value for the text.
        """
        if self._status_label is None:
            return
        self._status_label.setText(message)
        self._status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _update_labels(self) -> None:
        """Update all metric labels with current counters."""
        if self._drops_label is not None:
            self._drops_label.setText(f"Drops Processed: {self._drops_processed}")
        if self._items_label is not None:
            self._items_label.setText(f"Items Opened: {self._items_opened}")
        if self._category_label is not None:
            self._category_label.setText(f"Current Category: {self._current_category}")

    @pyqtSlot(dict)
    def update_progress(self, data: dict) -> None:
        """Update progress metrics from worker data.

        Args:
            data: Dictionary containing 'drops_processed', 'items_opened', and 'current_category'.
        """
        self._drops_processed = int(data.get("drops_processed", self._drops_processed))
        self._items_opened = int(data.get("items_opened", self._items_opened))
        self._current_category = data.get("current_category") or "None"
        self._set_status("Running", self._palette.status_info)
        self._update_labels()

    @pyqtSlot()
    def on_automation_started(self) -> None:
        """Reset progress counters when automation begins."""
        self._drops_processed = 0
        self._items_opened = 0
        self._current_category = "None"
        self._set_status("Running", self._palette.status_info)
        self._update_labels()

    @pyqtSlot(int)
    def on_automation_finished(self, total_drops: int) -> None:
        """Update progress to show completion.

        Args:
            total_drops: Total number of drops processed.
        """
        self._drops_processed = total_drops
        self._current_category = "None"
        self._set_status("Completed", self._palette.status_success)
        self._update_labels()

    @pyqtSlot(str)
    def on_automation_error(self, error_message: str) -> None:
        """Display error status when automation fails.

        Args:
            error_message: Description of the error.
        """
        truncated = (
            error_message if len(error_message) <= 80 else f"{error_message[:77]}..."
        )
        self._set_status(f"Error: {truncated}", self._palette.status_error)
        self._current_category = "None"
        self._update_labels()
