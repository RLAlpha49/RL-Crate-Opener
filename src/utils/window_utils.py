"""Window management utilities for Rocket League.

This module provides utilities for finding, validating, and interacting with the
Rocket League game window. It includes coordinate conversion between relative
(window-local) and absolute (screen) coordinate systems, as well as window geometry
caching and change detection for performance optimization.
"""

from typing import TYPE_CHECKING, Optional, Tuple

import pygetwindow as gw  # type: ignore[import-untyped]

from src.config import CONFIG
from src.exceptions import InvalidResolutionError, WindowNotFoundError
from src.utils.logger import logger

if TYPE_CHECKING:
    from src.config import ScreenRegion


class WindowManager:
    """Manages Rocket League window detection and interaction.

    This class handles window discovery, caching, resolution validation, and
    coordinate conversion. It uses aggressive caching with change detection to
    minimize performance-impacting window API calls while ensuring geometry changes
    are detected when they occur.

    Attributes:
        window_title: Title of the window to find and manage.
    """

    def __init__(self, window_title: Optional[str] = None):
        """
        Initialize window manager with optional window title override.

        Creates a new WindowManager instance with empty caches for window object,
        width, height, and position. Caches are populated on first get_window() call.

        Args:
            window_title: Title of the window to find (defaults to CONFIG.WINDOW_TITLE).
                         Allows override for testing or alternative window titles.
        """
        self.window_title = window_title or CONFIG.WINDOW_TITLE
        self._cached_window: Optional[gw.Win32Window] = None
        self._cached_width: Optional[int] = None
        self._cached_height: Optional[int] = None
        self._cached_left: Optional[int] = None
        self._cached_top: Optional[int] = None

    def get_window(self, use_cache: bool = True) -> gw.Win32Window:
        """
        Get the Rocket League window object with intelligent caching.

        Retrieves the window matching the configured title. If use_cache is True and
        a cached window is available, verifies it's still valid (isActive property
        accessible and geometry unchanged). If geometry has changed (window moved/resized),
        cache is invalidated and refreshed. This minimizes expensive pygetwindow calls
        while ensuring accurate data when geometry changes.

        Args:
            use_cache: Whether to use cached window if available and geometry unchanged
                      (default: True). Set to False to always fetch fresh window object.

        Returns:
            The Rocket League window object (pygetwindow Win32Window instance).

        Raises:
            WindowNotFoundError: If window with configured title is not found or
                                active on the system.

        Example:
            >>> window_mgr = WindowManager()
            >>> window = window_mgr.get_window()  # Uses cache
            >>> fresh_window = window_mgr.get_window(use_cache=False)  # Bypasses cache
        """
        if use_cache and self._cached_window is not None:
            try:
                # Verify cached window is still valid
                _ = self._cached_window.isActive
                # Check if window geometry has changed (position/size)
                if (
                    self._cached_width == self._cached_window.width
                    and self._cached_height == self._cached_window.height
                    and self._cached_left == self._cached_window.left
                    and self._cached_top == self._cached_window.top
                ):
                    return self._cached_window
                logger.debug("Window geometry changed, refreshing cache")
                self._cached_window = None
            except (AttributeError, RuntimeError, OSError):
                logger.debug("Cached window is no longer valid")
                self._cached_window = None

        windows = gw.getWindowsWithTitle(self.window_title)

        if not windows:
            raise WindowNotFoundError(
                f"Could not find window with title '{self.window_title}'. "
                "Please ensure Rocket League is running."
            )

        # Filter out the GUI window (contains "GUI" in title)
        actual_rl_windows = [w for w in windows if "GUI" not in w.title]

        if not actual_rl_windows:
            raise WindowNotFoundError(
                "Could not find Rocket League window (found windows were GUI windows). "
                "Please ensure Rocket League is running."
            )

        window = actual_rl_windows[0]
        self._cached_window = window
        self._cached_width = window.width
        self._cached_height = window.height
        self._cached_left = window.left
        self._cached_top = window.top
        logger.debug("Found window: %s", self.window_title)
        return window

    def validate_resolution(self) -> None:
        """
        Validate that the Rocket League window is at the required resolution.

        Compares the current window dimensions against CONFIG.REQUIRED_WIDTH and
        CONFIG.REQUIRED_HEIGHT. Most OCR and image recognition in the application
        is calibrated for 1920x1080, so mismatched resolutions will cause detection
        failures. Logs success at info level for troubleshooting.

        Raises:
            InvalidResolutionError: If window dimensions do not match the required
                                   1920x1080 resolution. Error message includes
                                   current dimensions and instructions to set game
                                   to 1920x1080 borderless window mode.

        Example:
            >>> window_mgr = WindowManager()
            >>> window_mgr.validate_resolution()  # Raises if not 1920x1080
        """
        window = self.get_window()

        if (
            window.width != CONFIG.REQUIRED_WIDTH
            or window.height != CONFIG.REQUIRED_HEIGHT
        ):
            raise InvalidResolutionError(
                f"Window resolution is {window.width}x{window.height}, "
                f"but {CONFIG.REQUIRED_WIDTH}x{CONFIG.REQUIRED_HEIGHT} is required. "
                f"Please set the game to 1920x1080 borderless window mode."
            )

        logger.debug("Window resolution validated: %sx%s", window.width, window.height)

    def get_absolute_coords(self, rel_x: int, rel_y: int) -> Tuple[int, int]:
        """
        Convert relative window coordinates to absolute screen coordinates.

        Window-relative coordinates (0, 0) represents the top-left corner of the
        Rocket League window. This method translates them to screen coordinates
        by adding the window's position (left, top). Useful for converting UI element
        positions detected within the game window to screen coordinates for automation.

        Args:
            rel_x: X coordinate relative to window top-left (0 = window left edge).
            rel_y: Y coordinate relative to window top-left (0 = window top edge).

        Returns:
            Tuple of (x, y) absolute screen coordinates as integers.

        Example:
            >>> window_mgr = WindowManager()
            >>> abs_x, abs_y = window_mgr.get_absolute_coords(100, 50)
            >>> # If window is at (50, 30), result is (150, 80)
        """
        window = self.get_window()
        return (int(window.left + rel_x), int(window.top + rel_y))

    def get_region_bbox(self, region: "ScreenRegion") -> Tuple[int, int, int, int]:
        """
        Get absolute bounding box for a screen region defined in window coordinates.

        Converts a relative ScreenRegion (with x1, y1, x2, y2 coordinates within the
        window) to absolute screen coordinates by adding the window's position offset.
        Used by image capture and OCR functions to determine which screen pixels to
        analyze.

        Args:
            region: ScreenRegion object with relative coordinates (x1, y1, x2, y2).

        Returns:
            Tuple of (left, top, right, bottom) as absolute screen coordinates.
            Suitable for PIL Image.crop() or similar operations.

        Example:
            >>> window_mgr = WindowManager()
            >>> region = ScreenRegion(x1=10, y1=20, x2=500, y2=300)
            >>> bbox = window_mgr.get_region_bbox(region)
            >>> # Result: (window.left+10, window.top+20, window.left+500, window.top+300)
        """
        window = self.get_window()
        return (
            int(window.left + region.x1),
            int(window.top + region.y1),
            int(window.left + region.x2),
            int(window.top + region.y2),
        )

    def refresh_cache(self) -> None:
        """
        Explicitly refresh the window cache by discarding and reloading all cached data.

        Useful when you suspect the window has been moved, resized, or closed and reopened,
        or when you want to force a fresh window lookup. This method clears all cached
        geometry data (width, height, left, top) and immediately fetches the current
        window state to populate the cache with fresh values.

        This is called automatically by get_window() when geometry changes are detected,
        but can be called manually if needed.

        Example:
            >>> window_mgr = WindowManager()
            >>> window_mgr.refresh_cache()  # Clear all caches and reload
        """
        logger.debug("Refreshing window cache")
        self._cached_window = None
        self._cached_width = None
        self._cached_height = None
        self._cached_left = None
        self._cached_top = None
        # Fetch fresh window immediately
        self.get_window(use_cache=False)

    def is_geometry_changed(self) -> bool:
        """
        Check if the window geometry (position/size) has changed since last cache.

        Compares current window dimensions and position (left, top, width, height)
        against the cached values. On first call with empty cache, automatically
        initializes the cache by calling refresh_cache() and returns False, avoiding
        unnecessary duplicate refresh operations.

        This method is used to detect when the user moves or resizes the game window,
        which may require recalibration of coordinate-dependent operations.

        Returns:
            True if window geometry (position or size) changed since last cache.
            False if unchanged, cache was empty (after initialization), or window
            became unavailable (treats unavailability as "no change detected").

        Example:
            >>> window_mgr = WindowManager()
            >>> window_mgr.refresh_cache()  # Initialize cache
            >>> if window_mgr.is_geometry_changed():
            ...     print("Window was moved or resized")
            ... else:
            ...     print("Window geometry unchanged")
        """
        # If cache is empty, initialize it and return False
        if self._cached_window is None:
            self.refresh_cache()
            return False

        try:
            window = self.get_window(use_cache=False)
            has_changed = (
                window.width != self._cached_width
                or window.height != self._cached_height
                or window.left != self._cached_left
                or window.top != self._cached_top
            )
            return has_changed
        except (AttributeError, RuntimeError, WindowNotFoundError):
            # Window unavailable or invalid, can't detect geometry change
            return False


# Global window manager instance
window_manager = WindowManager()
