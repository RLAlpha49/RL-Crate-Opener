"""
This module contains utility functions for handling windows in the Rocket League game.

Functions:
    get_rl_window: Finds the Rocket League window by its title and returns it.
"""

import pygetwindow as gw


def get_rl_window():
    """
    Get the Rocket League window.

    This function finds the Rocket League window by its title and returns it.
    If the window is not found, it returns None.

    Returns:
        window: The Rocket League window, or None if not found.
    """
    # Find the Rocket League window by its title
    windows = gw.getWindowsWithTitle("Rocket League")
    return windows[0] if windows else None
