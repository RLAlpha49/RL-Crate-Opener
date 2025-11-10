"""Widget providing a log viewer backed by a Qt-aware logging handler."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from src.utils.logger import logger

from .styles import FONT_SIZE_LARGE, PADDING_BASE, get_active_palette


class QTextEditLogger(logging.Handler, QObject):
    """Logging handler that forwards records to a QTextEdit via Qt signals."""

    log_message = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize the logging handler with Qt signal support."""
        QObject.__init__(self)
        logging.Handler.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401 - standard logging hook
        """Emit a log record through a Qt signal.

        Args:
            record: The logging record to emit.
        """
        try:
            message = self.format(record)
        except Exception:  # pylint: disable=broad-except
            return
        self.log_message.emit(message)


class LogViewer(QWidget):
    """Display application logs in a read-only text area."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the log viewer widget and configure the logging handler.

        Args:
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self._text_edit: QTextEdit | None = None
        self._log_handler = QTextEditLogger()
        self._max_lines = 1000
        self._palette = get_active_palette()

        self._setup_ui()

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
        self._log_handler.setFormatter(formatter)
        self._log_handler.log_message.connect(self._append_log)
        logger.addHandler(self._log_handler)

    def _setup_ui(self) -> None:
        """Create and layout all UI elements for the log viewer."""
        title_font = QFont()
        title_font.setPointSize(FONT_SIZE_LARGE)
        title_font.setBold(True)

        mono_font = QFont("Consolas")
        mono_font.setStyleHint(QFont.StyleHint.TypeWriter)
        mono_font.setPointSize(9)

        title_label = QLabel("Logs", self)
        title_label.setFont(title_font)

        text_edit = QTextEdit(self)
        text_edit.setReadOnly(True)
        text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        text_edit.setFont(mono_font)
        document = text_edit.document()
        if document is not None:
            document.setMaximumBlockCount(self._max_lines)
        text_edit.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {self._palette.background_tertiary};
                color: {self._palette.text_secondary};
                border: 1px solid {self._palette.border};
                border-radius: 4px;
                padding: 4px;
            }}
            QScrollBar:vertical {{
                background-color: {self._palette.background_secondary};
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self._palette.accent_primary};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self._palette.accent_hover};
            }}
            """
        )

        clear_button = QPushButton("Clear Logs", self)
        clear_button.clicked.connect(self._clear_logs)

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

        inner_layout = QVBoxLayout()
        inner_layout.setContentsMargins(
            PADDING_BASE,
            PADDING_BASE,
            PADDING_BASE,
            PADDING_BASE,
        )
        inner_layout.setSpacing(PADDING_BASE)
        inner_layout.addWidget(title_label)
        inner_layout.addWidget(text_edit, stretch=1)
        inner_layout.addWidget(clear_button)
        frame.setLayout(inner_layout)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(frame)
        self.setLayout(root_layout)

        self._text_edit = text_edit

    @pyqtSlot(str)
    def _append_log(self, message: str) -> None:
        """Append a log message to the text editor and scroll to bottom.

        Args:
            message: The log message to append.
        """
        if self._text_edit is None:
            return

        self._text_edit.append(message)

        scrollbar = self._text_edit.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    @pyqtSlot()
    def _clear_logs(self) -> None:
        """Clear all log messages from the text editor."""
        if self._text_edit is not None:
            self._text_edit.clear()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Remove the logging handler when the widget closes.

        Args:
            event: The close event.
        """
        logger.removeHandler(self._log_handler)
        super().closeEvent(event)
