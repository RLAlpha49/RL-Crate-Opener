"""Core drop opener automation logic."""

from __future__ import annotations

import contextlib
import signal
import time
from pathlib import Path
from typing import Optional, Callable

import keyboard
import pyautogui

from src.config import CONFIG, ColorRGB, ScreenRegion
from src.data.items import item_manager
from src.exceptions import (
    WindowNotFoundError,
    InvalidResolutionError,
    RLDropOpenerError,
    OCRError,
)
from src.utils.image_utils import image_processor
from src.utils.logger import logger
from src.utils.text_utils import parse_lines
from src.utils.item_normalizer import normalize_and_map_item
from src.utils.window_utils import window_manager


# Flag to prevent multiple signal handler registrations in the same process.
_SIGNAL_HANDLERS_REGISTERED = False


@contextlib.contextmanager
def keyboard_hotkey(hotkey_combo: str, callback: Callable[[], None]):
    """
    Context manager for keyboard hotkey registration with automatic cleanup.

    Registers a keyboard hotkey on entry and unregisters all keyboard hooks on exit
    to ensure resources are freed even if exceptions occur.

    Args:
        hotkey_combo: Hotkey combination string (e.g., "ctrl+c").
        callback: Callable to invoke when hotkey is pressed.

    Yields:
        Boolean indicating whether hotkey registration succeeded.
    """
    success = False
    try:
        keyboard.add_hotkey(hotkey_combo, callback)
        logger.debug("Keyboard hotkey registered: %s", hotkey_combo)
        success = True
        yield success
    except (RuntimeError, KeyError, OSError) as e:
        logger.warning("Could not register keyboard hotkey '%s': %s", hotkey_combo, e)
        yield success
    finally:
        try:
            keyboard.unhook_all()
            logger.debug("Keyboard hooks unregistered")
        except (RuntimeError, KeyError, ValueError) as e:
            logger.debug("Could not unhook keyboard: %s", e)


class DropOpener:
    """
    Automates the process of opening Rocket League item drops.

    Handles screenshot capture, OCR text extraction, pixel detection, and
    automated clicking to systematically open all available drops.
    """

    def __init__(
        self, configure_signals: bool = True, configure_pyautogui: bool = True
    ):
        """
        Initialize the drop opener with optional signal and pyautogui configuration.

        Args:
            configure_signals: Whether to register signal handlers for graceful shutdown.
                             Set to False when using DropOpener for non-interactive tasks
                             like calibration to avoid side effects.
            configure_pyautogui: Whether to set pyautogui.PAUSE for click throttling.
                               Set to False when using DropOpener for calibration to
                               avoid global configuration changes.
        """
        self.running = False
        self._opening_item = False  # Track if currently opening an item
        if configure_pyautogui:
            # Note: pyautogui.PAUSE is a global setting that affects all pyautogui calls
            # across all modules. Setting it here intentionally throttles automation speed.
            pyautogui.PAUSE = CONFIG.CLICK_DELAY
        if configure_signals:
            self.setup_signal_handlers()

    def setup_signal_handlers(self) -> None:
        """
        Register signal handlers for graceful shutdown on SIGINT and SIGTERM.

        This method is guarded by a module-level flag to ensure signal handlers
        are only registered once per process. Multiple registrations are unnecessary
        and could cause issues with signal handling.

        Note: DropOpener should be used as a singleton during a process lifetime.
        If multiple DropOpener instances are created in the same process, only the
        first call to setup_signal_handlers() will register signals; subsequent
        calls will be no-ops.
        """
        global _SIGNAL_HANDLERS_REGISTERED  # pylint: disable=global-statement
        if _SIGNAL_HANDLERS_REGISTERED:
            logger.debug("Signal handlers already registered, skipping")
            return
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        _SIGNAL_HANDLERS_REGISTERED = True
        logger.debug("Signal handlers registered")

    def request_shutdown(self) -> None:
        """Request graceful shutdown of the automation loop."""
        logger.info("Shutdown requested by user")
        self.running = False

    def _signal_handler(self, _signum, _frame):
        """Handle shutdown signals (SIGINT, SIGTERM)."""
        logger.debug("Shutdown signal received")
        self.running = False

    def validate_setup(self) -> bool:
        """
        Validate that the game is ready for automation.

        Checks that Rocket League window exists and is at required resolution.

        Returns:
            True if setup is valid, False otherwise.
        """
        try:
            window_manager.validate_resolution()
            return True
        except WindowNotFoundError as e:
            logger.error(str(e))
            print(f"\nError: {e}")
            print("Please start Rocket League and try again.\n")
            return False
        except InvalidResolutionError as e:
            logger.error(str(e))
            print(f"\nError: {e}\n")
            return False

    def run_calibration(self) -> None:
        """
        Run interactive calibration to verify screen regions and element detection.

        Guides the user through capturing calibration images and confirming that
        target UI elements are correctly detected. Results are saved to help
        debug configuration issues if automation doesn't work.
        """
        if not self.validate_setup():
            return

        print("\n" + "=" * 50)
        print("Pre-Calibration Checklist")
        print("=" * 50 + "\n")

        print("Before proceeding with calibration, please verify:")
        print("  1. Screen resolution is 1920x1080p (borderless)")
        print("  2. Rocket League window is active and visible")
        print("  3. You are on the 'Drops' tab in your inventory")
        print(
            "  4. The Drops section shows available items (red notifications visible)\n"
        )

        try:
            user_input = (
                input("Press ENTER to proceed with calibration, or 'q' to quit: ")
                .strip()
                .lower()
            )
            if user_input == "q":
                print("Calibration cancelled.\n")
                return
        except EOFError:
            print("Calibration cancelled (EOF).\n")
            return

        print("\n" + "=" * 50)
        print("Starting Calibration Mode")
        print("=" * 50 + "\n")

        # Setup debug directory for calibration images
        debug_dir = Path(CONFIG.DEBUG_DIR) / "calibration"
        debug_dir.mkdir(parents=True, exist_ok=True)
        print(f"Saving calibration images to: {debug_dir.absolute()}\n")

        print("Calibration routine:")
        print("1. Check for drop indicator pixel (DROP_CHECK_REGION)")
        print(f"   Region bbox: {CONFIG.DROP_CHECK_REGION.bbox}")

        try:
            region_image = image_processor.capture_region(CONFIG.DROP_CHECK_REGION)
            region_image.save(debug_dir / "01_drop_check_region.png")
            print("   ✓ Region image saved to 01_drop_check_region.png")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to capture DROP_CHECK_REGION: %s", e)
            print(f"   ✗ Failed to capture region: {e}")

        has_drop = self.is_drop_present()
        if has_drop:
            print("   ✓ Drop indicator found at DROP_CHECK_REGION")
        else:
            print("   ✗ No drop indicator found - this may be expected if not on drops")

        print("\n2. Check for 'REWARD ITEMS' text (REWARD_ITEMS_REGION)")
        print(f"   Region bbox: {CONFIG.REWARD_ITEMS_REGION.bbox}")

        try:
            region_image = image_processor.capture_region(CONFIG.REWARD_ITEMS_REGION)
            region_image.save(debug_dir / "02_reward_items_region.png")
            print("   ✓ Region image saved to 02_reward_items_region.png")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to capture REWARD_ITEMS_REGION: %s", e)
            print(f"   ✗ Failed to capture region: {e}")

        has_rewards = self.has_drops_available()
        if has_rewards:
            print("   ✓ 'REWARD ITEMS' text found")
        else:
            print("   ✗ 'REWARD ITEMS' text not found - check screen position")

        print("\n3. Checking open button color (OPEN_BUTTON_CHECK)")
        print(f"   Region bbox: {CONFIG.OPEN_BUTTON_CHECK.bbox}")

        try:
            region_image = image_processor.capture_region(CONFIG.OPEN_BUTTON_CHECK)
            region_image.save(debug_dir / "03_open_button_check_region.png")
            print("   ✓ Region image saved to 03_open_button_check_region.png")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to capture OPEN_BUTTON_CHECK: %s", e)
            print(f"   ✗ Failed to capture region: {e}")

        has_open_button = self.can_open_item()
        if has_open_button:
            print("   ✓ Open button color found")
        else:
            print("   ✗ Open button not found - check screen position")

        print("\n4. Opening a single item for calibration")
        print("   Clicking open button...")

        try:
            # Click open button
            self.click_at(CONFIG.OPEN_ITEM_CLICK_X, CONFIG.OPEN_ITEM_CLICK_Y)

            # Capture image of open button click area
            region_image = image_processor.capture_region(CONFIG.OPEN_BUTTON_CHECK)
            if region_image is not None:
                region_image.save(debug_dir / "04_open_button_clicked.png")
                print("   ✓ Region image saved to 04_open_button_clicked.png")

            # Click confirm
            self.click_at(CONFIG.CONFIRM_CLICK_X, CONFIG.CONFIRM_CLICK_Y)

            # Wait the full DROP_CHECK_INTERVAL duration for animation
            check_interval = CONFIG.DROP_CHECK_INTERVAL
            time.sleep(check_interval)

            # Extract item name and capture
            text = image_processor.capture_and_extract_text(CONFIG.ITEM_OPEN_REGION)

            # Capture the item name region
            region_image = image_processor.capture_region(CONFIG.ITEM_OPEN_REGION)
            if region_image and text is not None:
                region_image.save(debug_dir / "05_item_open_region.png")
                print("   ✓ Region image saved to 05_item_open_region.png")

            # Close item view
            self.click_at(CONFIG.CLOSE_CLICK_X, CONFIG.CLOSE_CLICK_Y)

            # Capture after close
            region_image = image_processor.capture_region(CONFIG.REWARD_ITEMS_REGION)
            if region_image is not None:
                region_image.save(debug_dir / "06_after_item_close.png")
                print("   ✓ Region image saved to 06_after_item_close.png")

            print("   ✓ Item opened and closed successfully")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Error during item opening calibration: %s", e)
            print(f"   ✗ Item opening calibration failed: {e}")

        print("\nCalibration check complete.")
        print("Captured region images have been saved for visual inspection.")
        print("If elements above show unexpected results,")
        print("you may need to adjust CONFIG values in config.py")
        print(f"or review the captured images in {debug_dir.absolute()}\n")

    def run_calibration_noninteractive(self) -> tuple[bool, list[dict]]:
        """
        Run non-interactive calibration returning structured results.

        This method encapsulates the three calibration checks without any print()
        or input() calls, making it suitable for GUI integration. Returns structured
        results (images, detection results) for the caller to handle presentation.

        Returns:
            Tuple of (overall_success, steps_results) where:
            - overall_success: bool indicating if all steps passed
            - steps_results: list of dicts, one per step with keys:
                - step_number: int (1, 2, or 3)
                - step_name: str
                - success: bool (did detection pass?)
                - message: str (success or failure message)
                - region_image: PIL Image or None (captured region)
                - error: str or None (exception message if capture failed)
        """
        if not self.validate_setup():
            return False, []

        debug_dir = Path(CONFIG.DEBUG_DIR) / "calibration"
        debug_dir.mkdir(parents=True, exist_ok=True)

        steps_results = []
        overall_success = True

        # Step 1: Reward items text check (formerly Step 2)
        step1_result = {
            "step_number": 1,
            "step_name": "Reward Items Text Check",
            "success": False,
            "message": "",
            "region_image": None,
            "error": None,
        }

        try:
            region_image = image_processor.capture_region(CONFIG.REWARD_ITEMS_REGION)
            if region_image is not None:
                region_image.save(debug_dir / "01_reward_items_region.png")
            step1_result["region_image"] = region_image
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to capture REWARD_ITEMS_REGION: %s", exc)
            step1_result["error"] = str(exc)
            overall_success = False

        try:
            success = self.has_drops_available()
            step1_result["success"] = success
            step1_result["message"] = (
                "'REWARD ITEMS' text found"
                if success
                else "'REWARD ITEMS' text not found"
            )
            if not success:
                overall_success = False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Detection failed for REWARD_ITEMS_REGION: %s", exc)
            step1_result["error"] = str(exc)
            step1_result["success"] = False
            step1_result["message"] = "Detection failed"
            overall_success = False

        steps_results.append(step1_result)

        # Step 2: Open button color check (formerly Step 3)
        step2_result = {
            "step_number": 2,
            "step_name": "Open Button Color Check",
            "success": False,
            "message": "",
            "region_image": None,
            "error": None,
        }

        try:
            # First, check for the open button (which clicks the drop to select it)
            success = self.can_open_item()
            step2_result["success"] = success
            step2_result["message"] = (
                "Open button color found" if success else "Open button not found"
            )
            if not success:
                overall_success = False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Detection failed for OPEN_BUTTON_CHECK: %s", exc)
            step2_result["error"] = str(exc)
            step2_result["success"] = False
            step2_result["message"] = "Detection failed"
            overall_success = False

        # Now capture the image after the drop has been opened/selected
        try:
            region_image = image_processor.capture_region(CONFIG.OPEN_BUTTON_CHECK)
            if region_image is not None:
                region_image.save(debug_dir / "02_open_button_check_region.png")
            step2_result["region_image"] = region_image
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to capture OPEN_BUTTON_CHECK: %s", exc)
            step2_result["error"] = str(exc)
            overall_success = False

        steps_results.append(step2_result)

        # Step 3: Open a single item for calibration
        step3_result = {
            "step_number": 3,
            "step_name": "Item Opening Calibration",
            "success": False,
            "message": "",
            "region_image": None,
            "error": None,
        }

        try:
            # Click open button
            self.click_at(CONFIG.OPEN_ITEM_CLICK_X, CONFIG.OPEN_ITEM_CLICK_Y)

            # Capture image of open button click area
            region_image = image_processor.capture_region(CONFIG.OPEN_BUTTON_CHECK)
            if region_image is not None:
                region_image.save(debug_dir / "03_open_button_clicked.png")

            # Click confirm
            self.click_at(CONFIG.CONFIRM_CLICK_X, CONFIG.CONFIRM_CLICK_Y)

            # Capture image of confirm area
            region_image = image_processor.capture_region(
                ScreenRegion(700, 550, 1000, 700)
            )
            if region_image is not None:
                region_image.save(debug_dir / "04_confirm_clicked.png")

            # Wait the full DROP_CHECK_INTERVAL duration for animation
            check_interval = CONFIG.DROP_CHECK_INTERVAL
            time.sleep(check_interval)

            # Capture the item name region
            region_image = image_processor.capture_region(CONFIG.ITEM_OPEN_REGION)
            if region_image is not None:
                region_image.save(debug_dir / "05_item_open_region.png")

            # Close item view
            self.click_at(CONFIG.CLOSE_CLICK_X, CONFIG.CLOSE_CLICK_Y)

            # Capture after close
            region_image = image_processor.capture_region(CONFIG.REWARD_ITEMS_REGION)
            if region_image is not None:
                region_image.save(debug_dir / "06_after_item_close.png")

            step3_result["success"] = True
            step3_result["message"] = "Item opened and closed successfully"
            step3_result["region_image"] = region_image

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Error during item opening calibration: %s", exc)
            step3_result["error"] = str(exc)
            step3_result["success"] = False
            step3_result["message"] = "Item opening failed"
            overall_success = False

        steps_results.append(step3_result)

        return overall_success, steps_results

    def click_at(self, rel_x: int, rel_y: int, delay: float | None = None) -> None:
        """
        Click at coordinates relative to the game window.

        Automatically converts relative coordinates to absolute screen coordinates,
        and enforces the configured click delay.

        Args:
            rel_x: X coordinate relative to window.
            rel_y: Y coordinate relative to window.
            delay: Optional delay after click. Uses CONFIG.CLICK_DELAY if None.
        """
        x, y = window_manager.get_absolute_coords(rel_x, rel_y)
        pyautogui.click(x, y)
        if delay is None:
            delay = CONFIG.CLICK_DELAY
        time.sleep(delay)

    def has_drops_available(self) -> bool:
        """
        Check if there are drops available to open on the current screen.

        Uses OCR to search for "REWARD ITEMS" text. Returns False on OCR failures
        to prevent blocking the automation loop.

        Returns:
            True if drops are available, False if not or on OCR error.
        """
        try:
            # Check for "REWARD ITEMS" text
            text = image_processor.capture_and_extract_text(
                CONFIG.REWARD_ITEMS_REGION, region_name="reward_items"
            )
            return "rewarditems" in text.replace(" ", "")
        except OCRError as e:
            logger.warning("OCR failed while checking for drops: %s", e)
            time.sleep(0.5)
            return False

    def is_drop_present(self) -> bool:
        """
        Check if a drop notification indicator is currently visible.

        Looks for a specific pixel color in the DROP_CHECK_REGION.

        Returns:
            True if drop indicator pixel is found.
        """
        return image_processor.pixel_exists(
            CONFIG.DROP_CHECK_COLOR,
            CONFIG.DROP_CHECK_REGION,
            CONFIG.DROP_CHECK_TOLERANCE,
        )

    def get_drop_category(self) -> Optional[str]:
        """
        Extract the drop category name from the current drop notification.

        Uses OCR to read the category text and normalizes it. Returns None if
        OCR fails or extraction fails.

        Returns:
            Normalized category name or None if extraction fails.
        """
        try:
            text = image_processor.capture_and_extract_text(
                CONFIG.DROP_FOUND_REGION, region_name="drop_found"
            )

            if not text:
                logger.warning("Failed to extract text from drop region")
                return None

            # Get the last non-empty line as category
            lines = parse_lines(text)
            if lines:
                category_text = lines[-1]
                # Normalize the category using smart normalization
                from src.utils.item_normalizer import normalize_item_text  # pylint: disable=import-outside-toplevel

                category = normalize_item_text(category_text)
                logger.info("Detected drop category: %s", category)
                return category

            return None
        except OCRError as e:
            logger.warning("OCR failed while extracting drop category: %s", e)
            time.sleep(0.5)
            return None

    def open_drop_container(self) -> None:
        """
        Click the drop container button to open the notification.

        Applies a 1-second delay after clicking to allow the UI to update.
        """
        self.click_at(CONFIG.DROP_CLICK_X, CONFIG.DROP_CLICK_Y, delay=1.0)

    def can_open_item(self) -> bool:
        """
        Check if an item can be opened (open button is enabled).

        Clicks on the drop to select it, then detects the enabled button color.
        If not found, checks for disabled button color to distinguish between
        "no drops left" and button not being visible.

        Returns:
            True if open button is enabled and clickable.
        """
        # Click on the drop to select it
        self.click_at(CONFIG.DROP_CLICK_X, CONFIG.DROP_CLICK_Y)
        # Wait for UI to update after drop selection
        time.sleep(1)

        # Check if the enabled button color exists (rgb ~0,2,3)
        enabled = image_processor.pixel_exists(
            CONFIG.OPEN_BUTTON_COLOR,
            CONFIG.OPEN_BUTTON_CHECK,
            CONFIG.OPEN_BUTTON_TOLERANCE,
        )

        # If enabled button not found, check if button is disabled (rgb ~1,11,20)
        # This indicates all drops in the category have been opened
        if not enabled:
            disabled_color = ColorRGB(1, 11, 20)
            disabled = image_processor.pixel_exists(
                disabled_color,
                CONFIG.OPEN_BUTTON_CHECK,
                CONFIG.OPEN_BUTTON_TOLERANCE,
            )
            # If disabled button is found, return False (can't open)
            if disabled:
                return False

        return enabled

    def open_single_item(self, category: str) -> None:
        """
        Open a single item from the current drop and record it.

        Clicks to open the item, waits for the animation, extracts the item name
        via OCR, records it to the items file, and closes the item view.

        Args:
            category: Category name for the item being opened.
        """
        self._opening_item = True
        try:
            # Click open button
            self.click_at(CONFIG.OPEN_ITEM_CLICK_X, CONFIG.OPEN_ITEM_CLICK_Y)

            # Click confirm
            self.click_at(CONFIG.CONFIRM_CLICK_X, CONFIG.CONFIRM_CLICK_Y)

            # Wait the full DROP_CHECK_INTERVAL duration, then extract item name
            check_interval = CONFIG.DROP_CHECK_INTERVAL
            time.sleep(check_interval)

            # Extract item name
            text = image_processor.capture_and_extract_text(CONFIG.ITEM_OPEN_REGION)

            lines = parse_lines(text)
            for line in lines:
                if line:
                    # Normalize and map the item using smart matching
                    result = normalize_and_map_item(line)
                    if result:
                        matched_key, display_name = result
                        print(f"Opened: {display_name}")
                        item_manager.update_item(category, matched_key)
                    else:
                        # Fallback: if smart matching fails, use normalize_item_text
                        from src.utils.item_normalizer import normalize_item_text  # pylint: disable=import-outside-toplevel

                        normalized_name = normalize_item_text(line)
                        if normalized_name:
                            print(f"Opened: {normalized_name}")
                            item_manager.update_item(category, normalized_name)
                    break

            # Close item view
            self.click_at(CONFIG.CLOSE_CLICK_X, CONFIG.CLOSE_CLICK_Y)

            time.sleep(0.5)
        finally:
            self._opening_item = False

    def process_drop(self, category: str) -> None:
        """
        Open all items in a drop category, one by one.

        Continues opening items until the open button is disabled (indicating
        all items have been opened) or shutdown is requested. If shutdown is
        requested while opening an item, it will be completed to avoid
        collecting incorrect data.

        Args:
            category: Category name for the drop.
        """
        print(f"\nProcessing drop: {category}")

        item_count = 0
        while self.running and self.can_open_item():
            time.sleep(0.2)
            if not self.can_open_item():
                break
            self.open_single_item(category)
            item_count += 1

        # If shutdown was requested but we were opening an item,
        # complete any remaining open operations to maintain data integrity
        if not self.running and self._opening_item:
            logger.info("Completing final item opening after shutdown request")
            # Give any pending item operations a moment to complete
            time.sleep(0.5)

        logger.info("Opened %s items from %s", item_count, category)
        print(f"Opened {item_count} items from this drop\n")

    def run_automation(self) -> None:
        """
        Run the main automation loop for opening drops.

        Repeatedly checks for available drops, opens them one by one, and saves
        the results. Can be stopped via Ctrl+C hotkey.

        The automation handles OCR failures gracefully and provides feedback on
        consecutive failures. Window geometry is monitored and cache is refreshed
        when the window moves or resizes.
        """
        if not self.validate_setup():
            return

        print("\n" + "=" * 50)
        print("Starting automation...")
        print("Press Ctrl+C to stop")
        print("=" * 50 + "\n")

        self.running = True

        # Refresh window cache to ensure fresh geometry at start
        window_manager.refresh_cache()

        time.sleep(CONFIG.INITIAL_DELAY)

        drops_processed = 0
        iterations_since_refresh = 0
        refresh_interval = CONFIG.WINDOW_CACHE_REFRESH_INTERVAL
        ocr_failures = 0  # Track consecutive OCR failures
        ocr_failure_threshold = 5  # Threshold before warning user

        try:
            with keyboard_hotkey("ctrl+c", self.request_shutdown) as hotkey_success:
                if hotkey_success:
                    print("Hotkey registered (Ctrl+C available)\n")
                    logger.info("Ctrl+C hotkey successfully registered")
                else:
                    print("Hotkey registration failed.\n")
                    logger.warning("Ctrl+C hotkey registration failed")

                while self.running:
                    try:
                        # Check for window geometry changes (position/size)
                        # This handles window moves/resizes without waiting for refresh interval
                        if window_manager.is_geometry_changed():
                            logger.debug("Window geometry changed, refreshing cache")
                            window_manager.refresh_cache()
                            iterations_since_refresh = 0

                        # Throttle window cache refresh: only refresh every N iterations
                        # or after encountering an error that might indicate stale geometry
                        iterations_since_refresh += 1
                        if iterations_since_refresh >= refresh_interval:
                            window_manager.refresh_cache()
                            iterations_since_refresh = 0

                        # Check if we're still on the drops screen
                        if not self.has_drops_available():
                            print("No more drops available or not on drops screen")
                            break

                        # Check for a drop
                        if self.is_drop_present():
                            # Get drop category
                            category = self.get_drop_category()

                            if not category:
                                logger.warning(
                                    "Could not detect drop category, skipping"
                                )
                                ocr_failures += 1
                                time.sleep(1)
                                # Refresh cache on OCR failure as geometry may have changed
                                window_manager.refresh_cache()
                                iterations_since_refresh = 0

                                # Check if consecutive OCR failures exceed threshold
                                if ocr_failures >= ocr_failure_threshold:
                                    print(
                                        f"\n[WARNING] {ocr_failures} consecutive"
                                        " OCR failures detected!"
                                    )
                                    print("See README sections for guidance:")
                                    print(
                                        "  - Configuration > Environment Variable Overrides"
                                        " (set RL_TESSERACT_CMD if needed)"
                                    )
                                    print(
                                        "  - Calibration Mode (verify region detection)"
                                    )
                                    print("  - Check logs for more details\n")
                                continue

                            # Reset OCR failure counter on successful extraction
                            ocr_failures = 0

                            # Open the drop container
                            self.open_drop_container()

                            # Process all items in the drop
                            self.process_drop(category)

                            # Sort items after each drop
                            item_manager.sort_items()

                            # Go back to drops list
                            self.click_at(CONFIG.BACK_CLICK_X, CONFIG.BACK_CLICK_Y)

                            drops_processed += 1
                            print(f"Total drops processed: {drops_processed}\n")
                        else:
                            # No drop found, wait a bit and check again
                            time.sleep(0.5)

                    except OCRError as e:
                        # Handle OCR-specific errors
                        logger.warning("OCR error during automation: %s", e)
                        ocr_failures += 1
                        time.sleep(0.5)

                        # Check if consecutive OCR failures exceed threshold
                        if ocr_failures >= ocr_failure_threshold:
                            print(
                                f"\n[WARNING] {ocr_failures} consecutive OCR failures detected!"
                            )
                            print("See README sections for guidance:")
                            print(
                                "  - Configuration > Environment Variable Overrides"
                                " (set RL_TESSERACT_CMD if needed)"
                            )
                            print("  - Calibration Mode (verify region detection)")
                            print("  - Check logs for more details\n")
                        continue
                    except RLDropOpenerError as e:
                        # Handle project-specific errors with logging
                        logger.error("Error during automation: %s", e)
                        print(f"\nError: {e}")
                        # Refresh cache on error as geometry may have changed
                        window_manager.refresh_cache()
                        iterations_since_refresh = 0
                        break
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        # Catch all other exceptions: log full details and exit
                        logger.exception("Unexpected error during automation: %s", e)
                        print(f"\nUnexpected error: {e}")
                        break
        finally:
            # Final cleanup: ensure hotkeys are always unhooked (safety net)
            try:
                keyboard.unhook_all()
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug("Could not unhook keyboard")

            # Sort items and print final summary
            item_manager.sort_items()
