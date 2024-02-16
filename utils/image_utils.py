"""
This module contains utility functions for handling images in the Rocket League game.

Functions:
    pixel_search_in_window: Search for a pixel of a specific color within a window.
    color_match: Check if a color matches a target color within a certain shade tolerance.
"""

from PIL import ImageGrab

from utils.window_utils import get_rl_window  # pylint: disable=E0401


def pixel_search_in_window(color, area, shade=None):
    """
    Search for a pixel of a specific color within a window.

    Args:
        color (tuple): The target color.
        area (tuple): A tuple containing the left, right, top, and bottom
        boundaries of the search area.
        shade (int, optional): The shade tolerance. Defaults to None.

    Returns:
        tuple: The coordinates of the found pixel, or None if not found.
    """
    left, right, top, bottom = area
    window = get_rl_window()
    screenshot = ImageGrab.grab(
        bbox=(window.left, window.top, window.left + 1920, window.top + 1080)
    )

    for x in range(left, right):
        for y in range(top, bottom):
            pixel_color = screenshot.getpixel((x, y))
            if color_match(pixel_color, color, shade):
                return x, y
    return None


def color_match(actual_color, target_color, shade):
    """
    Check if a color matches a target color within a certain shade tolerance.

    Args:
        actual_color (tuple): The actual color.
        target_color (tuple): The target color.
        shade (int): The shade tolerance.

    Returns:
        bool: True if the colors match within the shade tolerance, False otherwise.
    """
    for i in range(3):
        if abs(actual_color[i] - target_color[i]) > shade:
            return False
    return True
