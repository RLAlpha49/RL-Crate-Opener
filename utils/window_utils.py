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

    Returns:
        window: The Rocket League window.
    """
    # Find the Rocket League window by its title
    window = gw.getWindowsWithTitle("Rocket League")[0]
    return window
