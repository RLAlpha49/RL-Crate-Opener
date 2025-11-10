"""Configuration settings for the Rocket League Drop Opener."""

from dataclasses import dataclass, replace
from typing import Tuple, Optional, Any, Dict
import os


@dataclass(frozen=True)
class ScreenRegion:
    """
    Represents a rectangular region on the screen.

    Attributes:
        x1: Left X coordinate.
        y1: Top Y coordinate.
        x2: Right X coordinate.
        y2: Bottom Y coordinate.
    """

    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """Return as bounding box tuple (x1, y1, x2, y2)."""
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass(frozen=True)
class OCRConfig:
    """
    Configuration for Tesseract OCR processing.

    Attributes:
        oem: OCR Engine Mode (0-3). Default is 3 (combined).
        psm: Page Segmentation Mode (0-13). Default is 6 (uniform text block).
        whitelist: Allowed characters for OCR recognition.
        lang: Tesseract language code. Default is "eng".
        debug_dump_always: Always save debug images from OCR operations.
        debug_min_length: Dump debug images if extracted text is shorter than this.
    """

    oem: int = 3
    psm: int = 6
    whitelist: str = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789- '&/:"
        "ÀÁÂÃÄÅàáâãäå"  # A variants
        "ÈÉÊËèéêë"  # E variants
        "ÌÍÎÏìíîï"  # I variants
        "ÒÓÔÕÖòóôõö"  # O variants
        "ÙÚÛÜùúûü"  # U variants
        "ÝýÿŸ"  # Y variants
        "ÑñÇç"  # N and C variants
    )
    lang: str = "eng"
    debug_dump_always: bool = False
    debug_min_length: int = 0

    @property
    def config_string(self) -> str:
        """Generate Tesseract config string with OEM, PSM, and whitelist."""
        escaped_whitelist = f"'{self.whitelist}'"
        return (
            f"--oem {self.oem} --psm {self.psm} "
            f"-c tessedit_char_whitelist={escaped_whitelist}"
        )


@dataclass(frozen=True)
class ColorRGB:
    """
    Represents an RGB color value.

    Attributes:
        r: Red component (0-255).
        g: Green component (0-255).
        b: Blue component (0-255).
    """

    r: int
    g: int
    b: int

    @property
    def as_tuple(self) -> Tuple[int, int, int]:
        """Return color as RGB tuple (r, g, b)."""
        return (self.r, self.g, self.b)


@dataclass(frozen=True)
class AppConfig:  # pylint: disable=too-many-instance-attributes
    """
    Main application configuration.

    Note on nested dataclass defaults: Nested fields like OCR (OCRConfig) use frozen
    dataclass instances as defaults. These are immutable and safe from the typical
    mutable default pitfalls (e.g., mutable lists/dicts shared across instances).
    The frozen=True constraint on all dataclasses ensures immutability at runtime.
    If mutation of configuration at runtime becomes necessary in the future,
    consider using factory functions (field(default_factory=...)) instead.
    """

    # Required screen resolution
    # pylint: disable=invalid-name
    REQUIRED_WIDTH: int = 1920
    REQUIRED_HEIGHT: int = 1080

    # Screen regions for detection
    DROP_CHECK_REGION: ScreenRegion = ScreenRegion(100, 100, 280, 281)
    DROP_FOUND_REGION: ScreenRegion = ScreenRegion(40, 330, 160, 360)
    ITEM_OPEN_REGION: ScreenRegion = ScreenRegion(725, 200, 1195, 240)
    REWARD_ITEMS_REGION: ScreenRegion = ScreenRegion(30, 130, 450, 190)
    OPEN_BUTTON_CHECK: ScreenRegion = ScreenRegion(45, 895, 260, 940)

    # Click coordinates (relative to window)
    DROP_CLICK_X: int = 100
    DROP_CLICK_Y: int = 280
    OPEN_ITEM_CLICK_X: int = 165
    OPEN_ITEM_CLICK_Y: int = 910
    CONFIRM_CLICK_X: int = 850
    CONFIRM_CLICK_Y: int = 610
    CLOSE_CLICK_X: int = 1050
    CLOSE_CLICK_Y: int = 990
    BACK_CLICK_X: int = 130
    BACK_CLICK_Y: int = 1030

    # Colors for pixel detection
    DROP_CHECK_COLOR: ColorRGB = ColorRGB(38, 62, 107)
    OPEN_BUTTON_COLOR: ColorRGB = ColorRGB(0, 2, 3)

    # Timing (in seconds)
    INITIAL_DELAY: float = 1.0
    CLICK_DELAY: float = 0.1
    OPEN_ANIMATION_DELAY: float = 8.0
    DROP_CHECK_INTERVAL: float = 8.0  # Interval for checking if item view is ready
    BACK_DELAY: float = 0.5

    # Window cache management
    WINDOW_CACHE_REFRESH_INTERVAL: int = 10

    # Tolerances
    COLOR_SHADE_TOLERANCE: int = 10
    DROP_CHECK_TOLERANCE: int = 10  # Tolerance for DROP_CHECK_COLOR pixel matching
    OPEN_BUTTON_TOLERANCE: int = 10  # Tolerance for OPEN_BUTTON_COLOR pixel matching

    # Pixel search settings
    PIXEL_SEARCH_FALLBACK: bool = (
        False  # Enable fallback pass with step=1 for sparse pixels
    )

    # OCR settings
    OCR: OCRConfig = OCRConfig()

    # File paths
    ITEMS_FILE: str = "items.txt"

    # Window title
    WINDOW_TITLE: str = "Rocket League"

    # Debug settings
    DEBUG_DUMP_IMAGES: bool = False
    DEBUG_DIR: str = "debug_images"
    DEBUG_MAX_IMAGES: int = 0  # 0 = no limit, >0 = max images per session
    DEBUG_IMAGE_FORMAT: str = "PNG"  # PNG, JPEG (PNG=lossless, JPEG=smaller file)
    DEBUG_JPEG_QUALITY: int = (
        85  # JPEG quality 1-100 (higher=better quality, larger file)
    )

    # Logging settings
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_TO_FILE: bool = False  # Enable file logging during automation
    LOG_FILE: Optional[str] = None  # Global immediate file logging path

    def with_overrides(self, **kwargs) -> "AppConfig":
        """
        Create a new AppConfig instance with specified field overrides.

        Since AppConfig is frozen, this provides a way to create modified copies
        for runtime configuration changes without mutating the original.

        Args:
            **kwargs: Field names and their new values to override

        Returns:
            A new AppConfig instance with the specified fields replaced

        Example:
            new_config = config.with_overrides(DEBUG_DUMP_IMAGES=True)
        """
        return replace(self, **kwargs)


# Global config instance (modified by environment variable overrides below).
CONFIG = AppConfig()


# Helper functions for parsing environment variables with default values.


def _get_bool(name: str) -> bool:
    """
    Parse an environment variable as a boolean.

    Recognizes common truthy strings (case-insensitive): "true", "1", "yes", "on"
    All other values are treated as False.

    Args:
        name: Environment variable name

    Returns:
        Boolean value (False if not set)
    """
    value = os.environ.get(name, "").lower().strip()
    return value in ("true", "1", "yes", "on")


def _get_int(name: str) -> Optional[int]:
    """
    Parse an environment variable as an integer.

    Args:
        name: Environment variable name

    Returns:
        Integer value or None if not set or invalid
    """
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _get_float(name: str) -> Optional[float]:
    """
    Parse an environment variable as a float.

    Args:
        name: Environment variable name

    Returns:
        Float value or None if not set or invalid
    """
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _get_string(name: str) -> Optional[str]:
    """
    Get an environment variable as a string.

    Args:
        name: Environment variable name

    Returns:
        String value or None if not set
    """
    value = os.environ.get(name, "").strip()
    return value if value else None


# Apply environment variable overrides if present
# All override variables use the RL_ prefix for clarity
_overrides: Dict[str, Any] = {}

# Boolean: RL_DEBUG_DUMP_IMAGES - enable debug image dumping
if _get_bool("RL_DEBUG_DUMP_IMAGES"):
    _overrides["DEBUG_DUMP_IMAGES"] = True

# OCRConfig overrides for debug settings
_ocr_overrides: Dict[str, Any] = {}

# Boolean: RL_DEBUG_DUMP_ALWAYS - enable dumping debug images for all OCR operations
if _get_bool("RL_DEBUG_DUMP_ALWAYS"):
    _ocr_overrides["debug_dump_always"] = True

# Boolean: RL_LOG_TO_FILE - enable file logging during automation
if _get_bool("RL_LOG_TO_FILE"):
    _overrides["LOG_TO_FILE"] = True

# String: RL_LOG_FILE - global immediate file logging path
if (log_file := _get_string("RL_LOG_FILE")) is not None:
    _overrides["LOG_FILE"] = log_file

# String: RL_DEBUG_DIR - directory path for debug images
if (debug_dir := _get_string("RL_DEBUG_DIR")) is not None:
    _overrides["DEBUG_DIR"] = debug_dir

# String: RL_LOG_LEVEL - logging level
if (log_level := _get_string("RL_LOG_LEVEL")) is not None:
    # Validate log level
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    log_level_upper = log_level.upper()
    if log_level_upper in valid_levels:
        _overrides["LOG_LEVEL"] = log_level_upper
    else:
        print(
            f"[CONFIG WARNING] Invalid LOG_LEVEL '{log_level}', "
            f"must be one of {valid_levels}. Using INFO."
        )
        _overrides["LOG_LEVEL"] = "INFO"

# Integer: RL_COLOR_SHADE_TOLERANCE - color matching tolerance value
if (tolerance := _get_int("RL_COLOR_SHADE_TOLERANCE")) is not None:
    # Validate range: 0-255
    if 0 <= tolerance <= 255:
        _overrides["COLOR_SHADE_TOLERANCE"] = tolerance
    else:
        print(
            f"[CONFIG WARNING] RL_COLOR_SHADE_TOLERANCE {tolerance} out of range [0-255], "
            f"using default {CONFIG.COLOR_SHADE_TOLERANCE}."
        )

# Integer: RL_DROP_CHECK_TOLERANCE - drop check region color tolerance
if (drop_tolerance := _get_int("RL_DROP_CHECK_TOLERANCE")) is not None:
    # Validate range: 0-255
    if 0 <= drop_tolerance <= 255:
        _overrides["DROP_CHECK_TOLERANCE"] = drop_tolerance
    else:
        print(
            f"[CONFIG WARNING] RL_DROP_CHECK_TOLERANCE {drop_tolerance} out of range [0-255], "
            f"using default {CONFIG.DROP_CHECK_TOLERANCE}."
        )

# Integer: RL_OPEN_BUTTON_TOLERANCE - open button region color tolerance
if (button_tolerance := _get_int("RL_OPEN_BUTTON_TOLERANCE")) is not None:
    # Validate range: 0-255
    if 0 <= button_tolerance <= 255:
        _overrides["OPEN_BUTTON_TOLERANCE"] = button_tolerance
    else:
        print(
            f"[CONFIG WARNING] RL_OPEN_BUTTON_TOLERANCE {button_tolerance} out of range [0-255], "
            f"using default {CONFIG.OPEN_BUTTON_TOLERANCE}."
        )

# Float: RL_INITIAL_DELAY - initial delay before starting automation
if (delay := _get_float("RL_INITIAL_DELAY")) is not None:
    _overrides["INITIAL_DELAY"] = delay

# Float: RL_DROP_CHECK_INTERVAL - interval for checking if item view is ready
if (check_interval := _get_float("RL_DROP_CHECK_INTERVAL")) is not None:
    _overrides["DROP_CHECK_INTERVAL"] = check_interval

# String: RL_ITEMS_FILE - items file path
if (items_file := _get_string("RL_ITEMS_FILE")) is not None:
    _overrides["ITEMS_FILE"] = items_file

# Integer: RL_WINDOW_CACHE_REFRESH_INTERVAL - window cache refresh interval
if (cache_interval := _get_int("RL_WINDOW_CACHE_REFRESH_INTERVAL")) is not None:
    _overrides["WINDOW_CACHE_REFRESH_INTERVAL"] = cache_interval

# Integer: RL_DEBUG_MAX_IMAGES - maximum debug images to save per session
if (debug_max_images := _get_int("RL_DEBUG_MAX_IMAGES")) is not None:
    _overrides["DEBUG_MAX_IMAGES"] = debug_max_images

# String: RL_DEBUG_IMAGE_FORMAT - format for debug images (PNG or JPEG)
if (image_format := _get_string("RL_DEBUG_IMAGE_FORMAT")) is not None:
    # Validate format
    image_format_upper = image_format.upper()
    if image_format_upper in ("PNG", "JPEG"):
        _overrides["DEBUG_IMAGE_FORMAT"] = image_format_upper
    else:
        print(
            f"[CONFIG WARNING] Invalid DEBUG_IMAGE_FORMAT '{image_format}', "
            f"must be 'PNG' or 'JPEG'. Using PNG."
        )
        _overrides["DEBUG_IMAGE_FORMAT"] = "PNG"

# Integer: RL_DEBUG_JPEG_QUALITY - quality for JPEG debug images (1-100)
if (jpeg_quality := _get_int("RL_DEBUG_JPEG_QUALITY")) is not None:
    # Validate range: 1-100
    if 1 <= jpeg_quality <= 100:
        _overrides["DEBUG_JPEG_QUALITY"] = jpeg_quality
    else:
        print(
            f"[CONFIG WARNING] RL_DEBUG_JPEG_QUALITY {jpeg_quality} out of range [1-100], "
            f"using default {CONFIG.DEBUG_JPEG_QUALITY}."
        )

# Apply OCR-specific overrides first if any exist
if _ocr_overrides:
    new_ocr_config = replace(CONFIG.OCR, **_ocr_overrides)
    CONFIG = replace(CONFIG, OCR=new_ocr_config)

# Apply all overrides to create the final CONFIG
if _overrides:
    CONFIG = CONFIG.with_overrides(**_overrides)
