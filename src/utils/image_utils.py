"""Image processing and screen capture utilities."""

from typing import Optional, Tuple, Callable
import uuid

import pytesseract  # type: ignore[import-untyped]
from PIL import Image, ImageGrab
import numpy as np

from src.config import CONFIG, ColorRGB, ScreenRegion
from src.exceptions import OCRError
from src.utils.logger import logger
from src.utils.retry import retry_with_backoff
from src.utils.window_utils import window_manager


# Session ID for organizing debug images (generated on first use).
_SESSION_ID: Optional[str] = None

# Optional callback for handling OCR configuration warnings (e.g., for Qt signal emission)
_ocr_warning_callback: Optional[Callable[[str], None]] = None


def _get_session_id() -> str:
    """
    Get or create a session ID for organizing debug images.

    Returns:
        Session ID string (first 8 characters of a UUID).
    """
    global _SESSION_ID  # pylint: disable=global-statement
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex[:8]
    return _SESSION_ID


def set_ocr_warning_callback(callback: Optional[Callable[[str], None]]) -> None:
    """
    Set a callback function for OCR configuration warnings.

    This allows the GUI or other components to handle OCR warnings through Qt signals
    or other mechanisms without coupling image_utils directly to GUI code.

    Args:
        callback: Optional callback function that takes a warning message string.
                 Pass None to disable the callback.
    """
    global _ocr_warning_callback  # pylint: disable=global-statement
    _ocr_warning_callback = callback


class ImageProcessor:
    """
    Handles screenshot capture, image processing, and OCR text extraction.

    Provides functions for capturing screen regions, extracting text via Tesseract,
    searching for pixel colors, and saving debug images for troubleshooting.
    """

    def __init__(self) -> None:
        """
        Initialize the image processor with Tesseract OCR configuration.

        If RL_TESSERACT_CMD environment variable is set, configures pytesseract
        to use that path. Validates the path exists and warns if not found.
        """
        import os  # pylint: disable=import-outside-toplevel
        from pathlib import Path  # pylint: disable=import-outside-toplevel

        self.ocr_config = CONFIG.OCR

        # Configure Tesseract path if RL_TESSERACT_CMD is set
        tesseract_cmd = os.environ.get("RL_TESSERACT_CMD", "").strip()
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            logger.debug("Tesseract command set to: %s", tesseract_cmd)

            # Validate that the Tesseract executable exists
            if not Path(tesseract_cmd).exists():
                warning_msg = (
                    f"RL_TESSERACT_CMD points to non-existent path: {tesseract_cmd}. "
                    "OCR may fail. Ensure Tesseract is installed or update RL_TESSERACT_CMD."
                )
                logger.warning(warning_msg)
                # Print concise console message for faster UX feedback
                print(
                    f"[WARNING] Tesseract path not found: {tesseract_cmd}\n"
                    "Please correct RL_TESSERACT_CMD or install Tesseract."
                )
                # Emit warning through callback if registered (e.g., for Qt signal)
                if _ocr_warning_callback:
                    _ocr_warning_callback(warning_msg)

    def capture_region(self, region: ScreenRegion) -> Image.Image:
        """
        Capture a screenshot of a specific screen region.

        Args:
            region: ScreenRegion to capture.

        Returns:
            PIL Image object of the captured region.
        """
        bbox = window_manager.get_region_bbox(region)
        return ImageGrab.grab(bbox=bbox)

    def extract_text(self, image: Image.Image, region_name: str = "ocr") -> str:
        """
        Extract text from an image using Tesseract OCR with automatic retry.

        Only retries on transient OCR errors (pytesseract.TesseractError, OSError).
        Other exceptions propagate immediately without retrying.

        Args:
            image: PIL Image to process.
            region_name: Name of the region for debug logging.

        Returns:
            Extracted text (lowercase, whitespace trimmed).

        Raises:
            OCRError: If OCR fails after all retry attempts.
        """

        def _ocr_with_config() -> str:
            text = pytesseract.image_to_string(
                image, config=self.ocr_config.config_string, lang=self.ocr_config.lang
            )
            return text.strip().lower()

        try:
            # Retry OCR with exponential backoff (3 attempts, 200-400ms backoff)
            # Only retry on transient OCR/IO errors, not on other exceptions
            text = retry_with_backoff(
                _ocr_with_config,
                max_attempts=3,
                backoff_ms=200,
                retry_on=(pytesseract.TesseractError, OSError),
            )
            return text
        except (pytesseract.TesseractError, OSError) as e:
            # Known transient OCR errors - wrap as OCRError
            self._save_debug_image(image, f"{region_name}_ocr_error")
            raise OCRError(
                f"Failed to extract text from image after retries: {e}"
            ) from e

    def capture_and_extract_text(
        self, region: ScreenRegion, region_name: str = "unknown"
    ) -> str:
        """
        Capture a screen region and extract text from it via OCR.

        Args:
            region: ScreenRegion to capture.
            region_name: Name of the region for debug logging.

        Returns:
            Extracted text (may be empty string if OCR found no text).
        """
        image = self.capture_region(region)
        text = self.extract_text(image, region_name)

        ocr_config = self.ocr_config
        should_dump = (
            (CONFIG.DEBUG_DUMP_IMAGES and not text)
            or (ocr_config.debug_dump_always)
            or (
                ocr_config.debug_min_length > 0
                and len(text) < ocr_config.debug_min_length
            )
        )

        if should_dump:
            self._save_debug_image(image, f"{region_name}_ocr_result")

        return text

    def _search_pixel_numpy(
        self,
        screenshot: Image.Image,
        region: ScreenRegion,
        color: ColorRGB,
        tolerance: int,
    ) -> Optional[Tuple[int, int]]:
        """
        Search for a pixel using numpy array vectorized comparison.

        Efficiently finds color matches in large regions by using numpy's
        vectorized operations.

        Args:
            screenshot: PIL Image to search.
            region: ScreenRegion containing the original coordinates.
            color: Target RGB color.
            tolerance: Maximum allowed difference per channel.

        Returns:
            Tuple of (x, y) window-relative coordinates (region origin offset applied)
            if found, None otherwise.
        """
        img_array = np.array(screenshot)
        # Handle both RGB and RGBA images
        if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
            img_rgb = img_array[:, :, :3]
            target_rgb = np.array(color.as_tuple)
            # Vectorized color matching with tolerance
            matches = np.all(
                np.abs(img_rgb.astype(int) - target_rgb) <= tolerance, axis=2
            )
            if np.any(matches):
                y_coords, x_coords = np.nonzero(matches)
                # Return first match
                return (region.x1 + int(x_coords[0]), region.y1 + int(y_coords[0]))
        return None

    def search_pixel(
        self, color: ColorRGB, region: ScreenRegion, tolerance: int = 0
    ) -> Optional[Tuple[int, int]]:
        """
        Search for a pixel of a specific color within a region.

        **Coordinate Space Convention**: Returns window-relative coordinates (x, y)
        representing the absolute pixel position in the Rocket League window.
        Coordinates are computed as: (region.x1 + relative_x, region.y1 + relative_y).
        These coordinates can be used directly with window_manager functions and
        must NOT be passed back to get_region_bbox() or other region-offset functions,
        as they are already in window-relative space.

        Uses numpy array vectorized comparison for efficient color matching.
        Falls back to pure Pillow with step-size heuristic for sparse grid scanning.
        As a final fallback (when enabled), performs a full scan with step=1 for missed pixels.

        Step-size heuristic trade-offs:
        - Small regions (<50k px): step=1 (thorough scan, no performance impact)
        - Medium regions (50k-150k px): step=2 (good speed/accuracy balance)
        - Large regions (>150k px): step=3-4 (significant speedup, possible miss if color is sparse)
        - High tolerance (>10): increases step by 1 (tolerant matching allows wider steps)
        - Grid-based scanning may miss isolated pixels, but OCR regions are typically dense

        When PIXEL_SEARCH_FALLBACK or DEBUG_DUMP_IMAGES is enabled, a final pass with
        step=1 is performed if standard scans return None, ensuring no sparse pixels are missed.

        Args:
            color: Target color to search for
            region: ScreenRegion to search in (must have window-relative coordinates)
            tolerance: Color matching tolerance (shade difference allowed)

        Returns:
            Tuple of (x, y) window-relative coordinates if found, None otherwise.
            Coordinates are already offset by the region position and can be used
            directly with window manager functions (no further offset should be applied).
        """
        screenshot = self.capture_region(region)
        width = region.x2 - region.x1
        height = region.y2 - region.y1
        area = width * height

        # NOTE: All coordinates returned from this function are WINDOW-RELATIVE.
        # We add region.x1 and region.y1 to convert from region-relative to window-relative.
        # Callers should NOT apply these offsets again or double-offset will occur.

        # Try numpy-based vectorized comparison for better performance
        numpy_result = self._search_pixel_numpy(screenshot, region, color, tolerance)
        if numpy_result is not None:
            return numpy_result

        # Fallback: pure Pillow approach with step size heuristic
        # Calculate step based on region area and tolerance
        step = 1
        if area > 150000:
            step = 4
        elif area > 50000:
            step = 2

        # Increase step for high tolerance (more lenient matching can afford wider sampling)
        if tolerance > 10:
            step += 1

        if step > 1:
            logger.debug(
                "Large region (%dx%d, area=%d, tolerance=%d), using step=%d",
                width,
                height,
                area,
                tolerance,
                step,
            )

        for x in range(0, width, step):
            for y in range(0, height, step):
                try:
                    pixel_color = screenshot.getpixel((x, y))
                except (AttributeError, IndexError):
                    continue

                # Ensure pixel_color is a tuple of three integers
                if isinstance(pixel_color, tuple) and len(pixel_color) >= 3:
                    rgb_color = (
                        int(pixel_color[0]),
                        int(pixel_color[1]),
                        int(pixel_color[2]),
                    )
                    if self._colors_match(rgb_color, color.as_tuple, tolerance):
                        return (region.x1 + x, region.y1 + y)

        # Final fallback: full scan with step=1 if configured or debug mode enabled
        # This catches sparse pixels that stepped scan might miss
        # Use a time budget to avoid excessive scanning on large regions (100ms max)
        if (CONFIG.PIXEL_SEARCH_FALLBACK or CONFIG.DEBUG_DUMP_IMAGES) and step > 1:
            import time  # pylint: disable=import-outside-toplevel

            logger.debug(
                "Performing fallback pixel search with step=1 for region (%dx%d)",
                width,
                height,
            )
            fallback_start_time = time.perf_counter()
            fallback_time_budget = 0.1  # 100ms time budget for fallback pass

            for x in range(0, width):
                for y in range(0, height):
                    # Check time budget periodically (every 100 iterations)
                    if (x * height + y) % 100 == 0:
                        elapsed = time.perf_counter() - fallback_start_time
                        if elapsed > fallback_time_budget:
                            logger.debug(
                                "Fallback pixel search time budget exceeded (%.1fms > %.1fms)",
                                elapsed * 1000,
                                fallback_time_budget * 1000,
                            )
                            return None

                    try:
                        pixel_color = screenshot.getpixel((x, y))
                    except (AttributeError, IndexError):
                        continue

                    # Ensure pixel_color is a tuple of three integers
                    if isinstance(pixel_color, tuple) and len(pixel_color) >= 3:
                        rgb_color = (
                            int(pixel_color[0]),
                            int(pixel_color[1]),
                            int(pixel_color[2]),
                        )
                        if self._colors_match(rgb_color, color.as_tuple, tolerance):
                            return (region.x1 + x, region.y1 + y)

        return None

    def pixel_exists(
        self, color: ColorRGB, region: ScreenRegion, tolerance: int = 0
    ) -> bool:
        """
        Check if a pixel of specific color exists in a region.

        **Coordinate Space**: Returns True/False for window-relative coordinates
        (see search_pixel() for details on coordinate convention).

        Args:
            color: Target RGB color.
            region: ScreenRegion to check. Must be window-relative coordinates.
            tolerance: Color matching tolerance (shade difference allowed).

        Returns:
            True if matching pixel is found, False otherwise.
        """
        return self.search_pixel(color, region, tolerance) is not None

    @staticmethod
    def _colors_match(
        actual: Tuple[int, int, int], target: Tuple[int, int, int], tolerance: int
    ) -> bool:
        """
        Check if two RGB colors match within tolerance.

        Args:
            actual: Actual RGB color tuple.
            target: Target RGB color tuple.
            tolerance: Maximum allowed difference per channel (0-255).

        Returns:
            True if all channels match within tolerance.
        """
        return all(abs(a - t) <= tolerance for a, t in zip(actual, target))

    @staticmethod
    def _save_debug_image(image: Image.Image, region_name: str) -> None:
        """
        Save a debug image to disk if DEBUG_DUMP_IMAGES is enabled.

        Images are saved under debug_images/sessions/<session_id>/ directory with
        timestamps. If DEBUG_MAX_IMAGES > 0, stops saving when session limit is reached.

        Image format and quality are configurable via:
        - DEBUG_IMAGE_FORMAT: 'PNG' (lossless) or 'JPEG' (compressed, default: PNG).
        - DEBUG_JPEG_QUALITY: 1-100 for JPEG quality (default: 85).

        Args:
            image: PIL Image object to save.
            region_name: Label for the region being debugged (used in filename).
        """
        if not CONFIG.DEBUG_DUMP_IMAGES:
            return

        try:
            from datetime import datetime  # pylint: disable=import-outside-toplevel
            from pathlib import Path  # pylint: disable=import-outside-toplevel

            session_id = _get_session_id()
            debug_dir = Path(CONFIG.DEBUG_DIR) / "sessions" / session_id
            debug_dir.mkdir(exist_ok=True, parents=True)

            # Check if we've hit the max images limit
            if CONFIG.DEBUG_MAX_IMAGES > 0:
                # Count images regardless of format for limit checking
                existing_images = list(debug_dir.glob("*.*"))
                if len(existing_images) >= CONFIG.DEBUG_MAX_IMAGES:
                    logger.debug(
                        "Skipped saving debug image (session limit %d reached)",
                        CONFIG.DEBUG_MAX_IMAGES,
                    )
                    return

            # Determine file extension and save parameters based on format
            image_format = CONFIG.DEBUG_IMAGE_FORMAT.upper()
            if image_format == "JPEG":
                file_ext = "jpg"
            else:
                # Default to PNG
                file_ext = "png"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = debug_dir / f"{timestamp}_{region_name}.{file_ext}"

            if image_format == "JPEG":
                image.save(
                    str(filename),
                    format="JPEG",
                    quality=CONFIG.DEBUG_JPEG_QUALITY,
                )
            else:
                image.save(str(filename), format="PNG")

            logger.debug("Saved debug image: %s (%s)", filename, image_format)
        except (OSError, IOError) as e:
            logger.warning("Failed to save debug image: %s", e)


# Global image processor instance
image_processor = ImageProcessor()
