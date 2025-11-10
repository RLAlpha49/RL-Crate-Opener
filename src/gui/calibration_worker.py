"""Worker responsible for running the calibration routine on a background thread."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from src.core.drop_opener import DropOpener
from src.utils.logger import logger


class CalibrationWorker(QObject):
    """Execute the calibration steps without blocking the GUI thread."""

    validation_failed = pyqtSignal(str)
    step_started = pyqtSignal(int, str)
    step_completed = pyqtSignal(int, bool, str, object)
    calibration_finished = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize the calibration worker with a DropOpener instance."""
        super().__init__()
        self._opener = DropOpener(configure_signals=False, configure_pyautogui=False)
        self._is_running = False

    @pyqtSlot()
    def run_calibration(self) -> None:
        """Run the calibration workflow using the non-interactive API."""

        if self._is_running:
            return

        self._is_running = True
        try:
            if not self._opener.validate_setup():
                message = (
                    "Setup validation failed. Please ensure Rocket League is running at "
                    "1920x1080 borderless."
                )
                self.validation_failed.emit(message)
                return

            # Call the non-interactive API to get structured results
            overall_success, steps_results = (
                self._opener.run_calibration_noninteractive()
            )

            # Emit signals for each step
            for step_result in steps_results:
                step_number = step_result["step_number"]
                success = step_result["success"]
                message = step_result["message"]
                region_image = step_result["region_image"]

                self.step_started.emit(step_number, step_result["step_name"])
                self.step_completed.emit(step_number, success, message, region_image)

                if not success:
                    logger.warning(
                        "Calibration step %d failed: %s", step_number, message
                    )

            # Emit final result with actual overall_success value
            self.calibration_finished.emit(overall_success)

            if overall_success:
                logger.info("Calibration completed successfully")
            else:
                logger.warning("Calibration finished with issues")

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("Unhandled exception during calibration", exc_info=exc)
            self.error_occurred.emit(str(exc))
        finally:
            self._is_running = False
