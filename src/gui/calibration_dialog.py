"""Modal dialog presenting the calibration workflow with live updates."""

from __future__ import annotations

from typing import Dict, Optional

from PIL import Image
from PyQt6.QtCore import QThread, Qt, pyqtSlot
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from src.utils.logger import logger

from .calibration_worker import CalibrationWorker
from .styles import FONT_SIZE_LARGE, PADDING_BASE, get_active_palette


class CalibrationDialog(QDialog):
    """Display calibration progress with inline image previews."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the calibration dialog and start the calibration worker.

        Args:
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self.setWindowTitle("Calibration Mode")
        self.setModal(True)
        self.setMinimumSize(720, 640)

        self._palette = get_active_palette()
        self._worker: Optional[CalibrationWorker] = None
        self._thread: Optional[QThread] = None
        self._is_running = False
        self._last_success: Optional[bool] = None
        self._step_groups: Dict[int, QGroupBox] = {}
        self._step_status_labels: Dict[int, QLabel] = {}
        self._step_message_labels: Dict[int, QLabel] = {}
        self._step_image_labels: Dict[int, QLabel] = {}

        self._overall_status_label: Optional[QLabel] = None
        self._progress_bar: Optional[QProgressBar] = None
        self._close_button: Optional[QPushButton] = None

        self._setup_ui()
        self._start_calibration()

    def _setup_ui(self) -> None:
        """Create and layout all UI elements for the calibration dialog."""
        title_font = QFont()
        title_font.setPointSize(FONT_SIZE_LARGE)
        title_font.setBold(True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(
            PADDING_BASE, PADDING_BASE, PADDING_BASE, PADDING_BASE
        )
        main_layout.setSpacing(PADDING_BASE)

        title_label = QLabel("Calibration Mode", self)
        title_label.setFont(title_font)

        description_label = QLabel(
            "Verifying screen regions and element detection. Please keep Rocket League focused.",
            self,
        )
        description_label.setWordWrap(True)

        main_layout.addWidget(title_label)
        main_layout.addWidget(description_label)

        # Checklist panel
        checklist_frame = QFrame(self)
        checklist_frame.setFrameShape(QFrame.Shape.StyledPanel)
        checklist_frame.setStyleSheet(
            """
            QFrame {
                border: 1px solid %s;
                border-radius: 6px;
                background-color: %s;
            }
            """
            % (self._palette.border, self._palette.background_secondary)
        )

        checklist_layout = QVBoxLayout()
        checklist_layout.setContentsMargins(
            PADDING_BASE, PADDING_BASE, PADDING_BASE, PADDING_BASE
        )
        checklist_layout.setSpacing(PADDING_BASE // 2)

        checklist_title = QLabel("Pre-Calibration Checklist", checklist_frame)
        checklist_title.setFont(title_font)

        checklist_items = [
            "- Screen resolution is 1920x1080p (borderless)",
            "- Rocket League window is active and visible",
            "- You are on the 'Drops' tab in your inventory",
        ]

        checklist_layout.addWidget(checklist_title)
        for item in checklist_items:
            label = QLabel(item, checklist_frame)
            label.setStyleSheet(f"color: {self._palette.text_secondary};")
            checklist_layout.addWidget(label)

        checklist_frame.setLayout(checklist_layout)
        main_layout.addWidget(checklist_frame)

        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)

        steps_container = QVBoxLayout()
        steps_container.setSpacing(PADDING_BASE)

        step_definitions = {
            1: "Reward Items Text Check",
            2: "Open Button Color Check",
            3: "Item Opening Calibration",
        }

        for step_number, step_name in step_definitions.items():
            group_box = QGroupBox(self)
            group_box.setTitle(f"Step {step_number}: {step_name}")
            group_box.setStyleSheet(
                """
                QGroupBox {
                    font-weight: bold;
                }
                """
            )

            group_layout = QVBoxLayout()
            group_layout.setSpacing(PADDING_BASE // 2)

            status_label = QLabel("Pending...", group_box)
            self._set_status_label(
                status_label, "Pending...", self._palette.text_secondary
            )

            message_label = QLabel("Awaiting results...", group_box)
            message_label.setStyleSheet(f"color: {self._palette.text_secondary};")
            message_label.setWordWrap(True)

            image_label = QLabel("Image will appear here...", group_box)
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setMinimumSize(320, 120)
            image_label.setFrameShape(QFrame.Shape.StyledPanel)
            image_label.setStyleSheet(
                """
                QLabel {
                    background-color: %s;
                    color: %s;
                }
                """
                % (self._palette.background_tertiary, self._palette.text_secondary)
            )
            image_label.setScaledContents(False)

            group_layout.addWidget(status_label)
            group_layout.addWidget(message_label)
            group_layout.addWidget(image_label)

            group_box.setLayout(group_layout)
            steps_container.addWidget(group_box)

            self._step_groups[step_number] = group_box
            self._step_status_labels[step_number] = status_label
            self._step_message_labels[step_number] = message_label
            self._step_image_labels[step_number] = image_label

        steps_frame = QFrame(self)
        steps_frame.setFrameShape(QFrame.Shape.NoFrame)
        steps_frame.setLayout(steps_container)
        main_layout.addWidget(steps_frame)

        self._overall_status_label = QLabel("Status: Initializing...", self)
        self._set_status_label(
            self._overall_status_label,
            "Status: Initializing...",
            self._palette.status_info,
        )
        main_layout.addWidget(self._overall_status_label)

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setRange(0, 3)
        self._progress_bar.setValue(0)
        main_layout.addWidget(self._progress_bar)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._close_button = QPushButton("Close", self)
        self._close_button.setEnabled(False)
        self._close_button.clicked.connect(self.accept)
        button_row.addWidget(self._close_button)

        main_layout.addLayout(button_row)
        self.setLayout(main_layout)

    def _start_calibration(self) -> None:
        """Create and start the calibration worker thread with signal connections."""
        self._thread = QThread(self)
        self._worker = CalibrationWorker()

        self._worker.validation_failed.connect(self._on_validation_failed)
        self._worker.step_started.connect(self._on_step_started)
        self._worker.step_completed.connect(self._on_step_completed)
        self._worker.calibration_finished.connect(self._on_calibration_finished)
        self._worker.error_occurred.connect(self._on_error_occurred)

        self._thread.started.connect(self._worker.run_calibration)
        self._thread.finished.connect(self._cleanup_thread)

        self._worker.moveToThread(self._thread)
        self._thread.start()

        self._is_running = True
        self._set_status_label(
            self._overall_status_label,
            "Status: Running calibration...",
            self._palette.status_info,
        )

    def _set_status_label(self, label: Optional[QLabel], text: str, color: str) -> None:
        """Update a label's text and color styling.

        Args:
            label: The label widget to update (or None).
            text: Text content for the label.
            color: Hex color value for the text.
        """
        if label is None:
            return
        label.setText(text)
        label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _request_thread_stop(self) -> None:
        """Request the worker thread to quit and wait for completion."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(5000)

    def _safe_disconnect(self, signal, slot) -> None:
        """Safely disconnect a signal-slot connection.

        Args:
            signal: The signal to disconnect.
            slot: The slot to disconnect from.
        """
        try:
            signal.disconnect(slot)
        except (TypeError, RuntimeError):
            pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Clean up resources when the dialog closes.

        Args:
            event: The close event.
        """
        if self._is_running:
            self._request_thread_stop()
        self._cleanup_thread()
        super().closeEvent(event)

    def _cleanup_thread(self) -> None:
        """Disconnect all signals and dispose of worker and thread objects."""
        worker = self._worker
        thread = self._thread

        if worker is not None:
            for signal, slot in (
                (worker.validation_failed, self._on_validation_failed),
                (worker.step_started, self._on_step_started),
                (worker.step_completed, self._on_step_completed),
                (worker.calibration_finished, self._on_calibration_finished),
                (worker.error_occurred, self._on_error_occurred),
            ):
                self._safe_disconnect(signal, slot)
            worker.deleteLater()

        self._worker = None

        if thread is not None:
            if worker is not None:
                self._safe_disconnect(thread.started, worker.run_calibration)
            self._safe_disconnect(thread.finished, self._cleanup_thread)
            thread.deleteLater()

        self._thread = None

    def _pil_to_qpixmap(self, pil_image: Image.Image) -> QPixmap:
        """Convert a PIL image to a Qt pixmap.

        Args:
            pil_image: The PIL image to convert.

        Returns:
            A QPixmap object, or an empty pixmap if conversion fails.
        """
        try:
            converted = pil_image.convert("RGB")
            data = converted.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                converted.width,
                converted.height,
                converted.width * 3,
                QImage.Format.Format_RGB888,
            )
            return QPixmap.fromImage(qimage)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to convert calibration image to pixmap: %s", exc)
            return QPixmap()

    @pyqtSlot(str)
    def _on_validation_failed(self, error_message: str) -> None:
        """Handle validation failure from the worker.

        Args:
            error_message: Description of the validation error.
        """
        self._set_status_label(
            self._overall_status_label,
            f"Status: Validation Failed - {error_message}",
            self._palette.status_error,
        )
        QMessageBox.critical(self, "Validation Failed", error_message)
        self._last_success = False
        self._is_running = False
        if self._close_button is not None:
            self._close_button.setEnabled(True)
        self._request_thread_stop()

    @pyqtSlot(int, str)
    def _on_step_started(self, step_number: int, step_name: str) -> None:
        """Update UI when a calibration step begins.

        Args:
            step_number: The step number (1-3).
            step_name: Descriptive name of the step.
        """
        group_box = self._step_groups.get(step_number)
        if group_box is not None:
            group_box.setTitle(f"Step {step_number}: {step_name}")

        status_label = self._step_status_labels.get(step_number)
        if status_label is not None:
            self._set_status_label(
                status_label, "Running...", self._palette.status_info
            )

        message_label = self._step_message_labels.get(step_number)
        if message_label is not None:
            message_label.setText("Processing... please wait")

        if self._progress_bar is not None:
            self._progress_bar.setValue(step_number - 1)

        self._set_status_label(
            self._overall_status_label,
            f"Status: Running Step {step_number}...",
            self._palette.status_info,
        )

    @pyqtSlot(int, bool, str, object)
    def _on_step_completed(
        self, step_number: int, success: bool, message: str, pil_image: object
    ) -> None:
        """Update UI when a calibration step completes.

        Args:
            step_number: The step number (1-3).
            success: Whether the step completed successfully.
            message: Result message to display.
            pil_image: Optional PIL image to display.
        """
        status_label = self._step_status_labels.get(step_number)
        status_text = "Success" if success else "Failed"
        status_color = (
            self._palette.status_success if success else self._palette.status_warning
        )
        if status_label is not None:
            self._set_status_label(status_label, status_text, status_color)

        message_label = self._step_message_labels.get(step_number)
        if message_label is not None:
            message_label.setText(message)

        if isinstance(pil_image, Image.Image):
            pixmap = self._pil_to_qpixmap(pil_image)
            image_label = self._step_image_labels.get(step_number)
            if image_label is not None and not pixmap.isNull():
                image_label.setPixmap(pixmap)

        if self._progress_bar is not None:
            self._progress_bar.setValue(step_number)

        logger.info("Calibration step %d: %s", step_number, message)

    @pyqtSlot(bool)
    def _on_calibration_finished(self, success: bool) -> None:
        """Handle calibration completion from the worker.

        Args:
            success: Whether the calibration completed successfully.
        """
        color = (
            self._palette.status_success if success else self._palette.status_warning
        )
        summary = (
            "Status: Calibration Complete"
            if success
            else "Status: Calibration Finished with warnings"
        )
        self._set_status_label(self._overall_status_label, summary, color)

        # Press back button to return to drop inventory section BEFORE showing dialog
        if self._worker is not None:
            try:
                from src.config import CONFIG  # pylint: disable=import-outside-toplevel

                # Use the opener's click_at method to ensure window-relative coordinates
                self._worker._opener.click_at(  # pylint: disable=protected-access
                    CONFIG.BACK_CLICK_X,
                    CONFIG.BACK_CLICK_Y,
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        if success:
            QMessageBox.information(
                self,
                "Calibration Complete",
                (
                    "Calibration completed successfully. Captured images have been saved to "
                    "debug_images/calibration/. If any steps show unexpected results, "
                    "adjust CONFIG values in config.py."
                ),
            )

        self._last_success = success
        self._is_running = False
        if self._close_button is not None:
            self._close_button.setEnabled(True)

        self._request_thread_stop()

    @pyqtSlot(str)
    def _on_error_occurred(self, error_message: str) -> None:
        """Handle errors from the calibration worker.

        Args:
            error_message: Description of the error.
        """
        self._set_status_label(
            self._overall_status_label,
            f"Status: Error - {error_message}",
            self._palette.status_error,
        )
        QMessageBox.critical(self, "Calibration Error", error_message)
        logger.error("Calibration error: %s", error_message)
        self._last_success = False
        self._is_running = False
        if self._close_button is not None:
            self._close_button.setEnabled(True)
        self._request_thread_stop()

    @property
    def last_success(self) -> Optional[bool]:
        """Return whether the last calibration run finished successfully."""

        return self._last_success
