"""Automation control panel for the Rocket League Drop Opener GUI."""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from src.gui.automation_worker import AutomationWorker
from src.gui.styles import PADDING_BASE, Theme, _PALETTES
from src.utils.logger import logger


class AutomationPanel(QtWidgets.QWidget):
    """Widget providing start/stop controls and live automation feedback."""

    automation_started = QtCore.pyqtSignal()
    progress_updated = QtCore.pyqtSignal(dict)
    item_opened_signal = QtCore.pyqtSignal()
    drop_processed_signal = QtCore.pyqtSignal(str, int)
    automation_finished_signal = QtCore.pyqtSignal(int)
    automation_error_signal = QtCore.pyqtSignal(str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Initialize the automation control panel.

        Args:
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self._worker: AutomationWorker | None = None
        self._thread: QtCore.QThread | None = None
        self._is_running = False
        self._last_drops = 0
        self._last_items = 0
        self._status_palette = _PALETTES[Theme.DARK]
        self._had_error = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create buttons, labels, and layouts for the panel."""

        self._start_button = QtWidgets.QPushButton("Start Automation", self)
        self._stop_button = QtWidgets.QPushButton("Stop Automation", self)
        self._stop_button.setEnabled(False)

        # Set button styling
        button_style = """
            QPushButton {
                background-color: #2e8b57;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2d7a4f;
            }
            QPushButton:pressed {
                background-color: #1f5a38;
            }
            QPushButton:disabled {
                background-color: #4a5568;
                color: #9ca3af;
            }
        """

        stop_button_style = """
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c62828;
            }
            QPushButton:pressed {
                background-color: #ad1d1d;
            }
            QPushButton:disabled {
                background-color: #4a5568;
                color: #9ca3af;
            }
        """

        self._start_button.setStyleSheet(button_style)
        self._stop_button.setStyleSheet(stop_button_style)

        self._status_label = QtWidgets.QLabel("Ready", self)
        self._status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        status_font = QtGui.QFont()
        status_font.setPointSize(11)
        status_font.setBold(True)
        self._status_label.setFont(status_font)

        self._progress_label = QtWidgets.QLabel("Drops: 0 | Items: 0", self)
        self._progress_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        progress_font = QtGui.QFont("Consolas")
        progress_font.setStyleHint(QtGui.QFont.StyleHint.TypeWriter)
        progress_font.setPointSize(10)
        self._progress_label.setFont(progress_font)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(PADDING_BASE)
        button_row.addWidget(self._start_button)
        button_row.addWidget(self._stop_button)
        button_row.addStretch()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(
            PADDING_BASE,
            PADDING_BASE,
            PADDING_BASE,
            PADDING_BASE,
        )
        layout.setSpacing(PADDING_BASE)
        layout.addLayout(button_row)
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress_label)
        layout.addStretch()

        self.setLayout(layout)

        self._start_button.clicked.connect(self._handle_start)
        self._stop_button.clicked.connect(self._handle_stop)

        self._set_status("Ready", self._status_palette.status_info)

    def _set_status(self, message: str, color: str) -> None:
        """Update the status label text and color.

        Args:
            message: Status text to display.
            color: Hex color value for the text.
        """
        self._status_label.setText(message)
        self._status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    @QtCore.pyqtSlot()
    def _handle_start(self) -> None:
        """Start automation by creating the worker thread and connecting signals."""
        if self._is_running:
            return

        self._start_button.setEnabled(False)
        self._stop_button.setEnabled(True)
        self._set_status("Running...", self._status_palette.status_info)
        self._had_error = False

        self._thread = QtCore.QThread(self)
        self._worker = AutomationWorker()

        self._worker.progress_update.connect(self._on_progress_update)
        self._worker.item_opened.connect(self._on_item_opened)
        self._worker.drop_processed.connect(self._on_drop_processed)
        self._worker.automation_finished.connect(self._on_automation_finished)
        self._worker.error_occurred.connect(self._on_error_occurred)

        self._thread.started.connect(self._worker.run_automation)
        self._thread.finished.connect(self._cleanup_thread)

        self._worker.moveToThread(self._thread)
        self._thread.start()

        self._is_running = True
        self.automation_started.emit()

    @QtCore.pyqtSlot()
    def _handle_stop(self) -> None:
        """Request the worker thread to stop automation gracefully."""
        if not self._is_running:
            return

        self._stop_button.setEnabled(False)
        self._set_status("Stopping...", self._status_palette.status_warning)

        if self._worker is not None:
            self._worker.request_stop()

    @QtCore.pyqtSlot(dict)
    def _on_progress_update(self, data: dict) -> None:
        """Update progress counters from worker data.

        Args:
            data: Dictionary containing 'drops_processed' and 'items_opened' keys.
        """
        drops = int(data.get("drops_processed", self._last_drops))
        items = int(data.get("items_opened", self._last_items))
        self._last_drops = drops
        self._last_items = items
        self._progress_label.setText(f"Drops: {drops} | Items: {items}")
        self.progress_updated.emit(data)

    @QtCore.pyqtSlot(str, str)
    def _on_item_opened(self, category: str, item_name: str) -> None:
        """Handle individual item opening events.

        Args:
            category: Item category or rarity.
            item_name: Name of the opened item.
        """
        name_display = item_name or "Unknown Item"
        logger.debug("Item opened: %s from %s", name_display, category)
        self.item_opened_signal.emit()

    @QtCore.pyqtSlot(str, int)
    def _on_drop_processed(self, category: str, item_count: int) -> None:
        """Log and emit drop completion events.

        Args:
            category: Drop category or rarity.
            item_count: Number of items in the drop.
        """
        logger.info("Drop processed: %s (%d items)", category, item_count)
        self.drop_processed_signal.emit(category, item_count)

    @QtCore.pyqtSlot(int)
    def _on_automation_finished(self, total_drops: int) -> None:
        """Handle automation completion and clean up resources.

        Args:
            total_drops: Total number of drops processed.
        """
        if not self._had_error:
            self._last_drops = total_drops
            self._set_status("Stopped", self._status_palette.status_success)
            self._progress_label.setText(
                f"Drops: {self._last_drops} | Items: {self._last_items}"
            )

        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        self._is_running = False

        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(5000)

        if not self._had_error:
            logger.info("Automation completed: %d drops processed", total_drops)
        self.automation_finished_signal.emit(total_drops)

    @QtCore.pyqtSlot(str)
    def _on_error_occurred(self, error_message: str) -> None:
        """Handle and display worker thread errors.

        Args:
            error_message: Error description from the worker.
        """
        self._had_error = True
        self._set_status(f"Error: {error_message}", self._status_palette.status_error)
        QtWidgets.QMessageBox.critical(self, "Automation Error", error_message)

        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        self._is_running = False

        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(5000)

        logger.error("Automation error: %s", error_message)
        self.automation_error_signal.emit(error_message)

    def _cleanup_thread(self) -> None:
        """Disconnect all signals and clean up worker and thread objects."""
        worker_ref = self._worker
        thread_ref = self._thread

        if worker_ref is not None:
            worker_signals = (
                (worker_ref.progress_update, self._on_progress_update),
                (worker_ref.item_opened, self._on_item_opened),
                (worker_ref.drop_processed, self._on_drop_processed),
                (worker_ref.automation_finished, self._on_automation_finished),
                (worker_ref.error_occurred, self._on_error_occurred),
            )
            for signal, slot in worker_signals:
                try:
                    signal.disconnect(slot)
                except TypeError:
                    pass
            worker_ref.deleteLater()
            self._worker = None

        if thread_ref is not None:
            if worker_ref is not None:
                try:
                    thread_ref.started.disconnect(worker_ref.run_automation)
                except (TypeError, AttributeError):
                    pass
            try:
                thread_ref.finished.disconnect(self._cleanup_thread)
            except TypeError:
                pass
            thread_ref.deleteLater()
            self._thread = None

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        """Clean up the worker thread when the panel is closed.

        Args:
            event: The close event.
        """
        if self._is_running:
            self._handle_stop()
            if self._thread is not None:
                self._thread.quit()
                self._thread.wait(5000)
            self._cleanup_thread()

        super().closeEvent(event)
