"""Worker object that runs the drop opener automation on a background thread."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from src.core.drop_opener import DropOpener
from src.data.items import item_manager
from src.exceptions import RLDropOpenerError
from src.utils.logger import logger


class AutomationWorker(QObject):
    """Run the DropOpener automation loop and emit progress updates."""

    progress_update = pyqtSignal(dict)
    item_opened = pyqtSignal(str, str)
    drop_processed = pyqtSignal(str, int)
    automation_finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize the automation worker with a DropOpener instance."""
        super().__init__()
        self._opener = DropOpener()
        self._is_running = False
        self._drops_processed = 0
        self._items_opened = 0

    @pyqtSlot()
    def run_automation(self) -> None:
        """Execute the automation loop on the worker thread."""

        if self._is_running:
            logger.warning("Automation worker is already running")
            return

        self._is_running = True
        self._drops_processed = 0
        self._items_opened = 0

        original_process_drop = self._opener.process_drop
        original_open_single_item = self._opener.open_single_item

        def wrapped_process_drop(category: str) -> None:
            """Wrap process_drop to track counts and emit progress signals.

            Args:
                category: Item category or rarity.
            """
            previous_item_total = self._items_opened
            self._drops_processed += 1
            self.progress_update.emit(
                {
                    "drops_processed": self._drops_processed,
                    "items_opened": self._items_opened,
                    "current_category": category,
                }
            )

            success = False
            try:
                original_process_drop(category)
                success = True
            finally:
                if success:
                    items_in_drop = self._items_opened - previous_item_total
                    self.drop_processed.emit(category, max(items_in_drop, 0))
                    self.progress_update.emit(
                        {
                            "drops_processed": self._drops_processed,
                            "items_opened": self._items_opened,
                            "current_category": category,
                        }
                    )

        def wrapped_open_single_item(category: str) -> None:
            """Wrap open_single_item to track item names and emit signals.

            Args:
                category: Item category or rarity.
            """
            # Capture item counts before and after to determine which item was opened
            items_before = item_manager.load_items()
            category_items_before = (
                dict(items_before.items(category))
                if items_before.has_section(category)
                else {}
            )

            success = False
            try:
                original_open_single_item(category)
                success = True
            except Exception:
                success = False
                raise

            if not success:
                return

            # Capture item counts after to determine which item's count increased
            items_after = item_manager.load_items()
            category_items_after = (
                dict(items_after.items(category))
                if items_after.has_section(category)
                else {}
            )

            # Find which item's count increased
            item_name = ""
            for item_key, count_after_str in category_items_after.items():
                count_before = int(category_items_before.get(item_key, 0))
                count_after = int(count_after_str)
                if count_after > count_before:
                    item_name = item_key
                    break

            self._items_opened += 1
            self.item_opened.emit(category, item_name)
            self.progress_update.emit(
                {
                    "drops_processed": self._drops_processed,
                    "items_opened": self._items_opened,
                    "current_category": category,
                }
            )

        self._opener.process_drop = wrapped_process_drop  # type: ignore[assignment]
        self._opener.open_single_item = wrapped_open_single_item  # type: ignore[assignment]

        had_error = False
        try:
            self._opener.run_automation()
        except RLDropOpenerError as exc:
            had_error = True
            self.error_occurred.emit(str(exc))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            had_error = True
            logger.exception("Unhandled exception during automation", exc_info=exc)
            self.error_occurred.emit(str(exc))
        finally:
            # Ensure method wrapping is restored and cleanup is performed
            try:
                self._opener.process_drop = original_process_drop  # type: ignore[assignment]
                self._opener.open_single_item = original_open_single_item  # type: ignore[assignment]
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug("Could not restore original methods during cleanup")

            # Ensure the opener is marked as not running
            self._opener.running = False
            self._is_running = False

            # Always emit completion signal, even if error occurred
            if not had_error:
                self.automation_finished.emit(self._drops_processed)

    @pyqtSlot()
    def request_stop(self) -> None:
        """Request a graceful shutdown of the automation loop."""
        if not self._is_running:
            return

        logger.info("Stop requested from automation worker")
        self._opener.request_shutdown()

        # Ensure keyboard hooks are cleaned up on stop request
        try:
            import keyboard

            keyboard.unhook_all()
        except Exception:  # pylint: disable=broad-exception-caught
            logger.debug("Could not unhook keyboard during stop request")
