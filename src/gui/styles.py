"""Centralized styling helpers for the PyQt6 GUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict

from PyQt6 import QtWidgets


class Theme(Enum):
    """Supported UI themes."""

    LIGHT = "light"
    DARK = "dark"


_ACTIVE_THEME: Theme = Theme.DARK


@dataclass(frozen=True)
class ColorPalette:
    """Color definitions for a theme."""

    background_primary: str
    background_secondary: str
    background_tertiary: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    accent_primary: str
    accent_hover: str
    accent_pressed: str
    border: str
    status_success: str
    status_warning: str
    status_error: str
    status_info: str


# Theme color palette mappings (Theme enum -> ColorPalette dataclass).
_PALETTES: Dict[Theme, ColorPalette] = {
    Theme.LIGHT: ColorPalette(
        background_primary="#f5f7fa",
        background_secondary="#ffffff",
        background_tertiary="#e6eaef",
        text_primary="#212121",
        text_secondary="#4a4a4a",
        text_disabled="#9e9e9e",
        accent_primary="#1e88e5",
        accent_hover="#1565c0",
        accent_pressed="#0d47a1",
        border="#d0d7de",
        status_success="#2e7d32",
        status_warning="#ef6c00",
        status_error="#c62828",
        status_info="#0288d1",
    ),
    Theme.DARK: ColorPalette(
        background_primary="#23272f",
        background_secondary="#2c313c",
        background_tertiary="#1c2028",
        text_primary="#f5f5f5",
        text_secondary="#cfd8dc",
        text_disabled="#7f8c8d",
        accent_primary="#64b5f6",
        accent_hover="#42a5f5",
        accent_pressed="#1e88e5",
        border="#3c4655",
        status_success="#66bb6a",
        status_warning="#ffa726",
        status_error="#ef5350",
        status_info="#29b6f6",
    ),
}


# Layout and typography constants for consistent UI sizing.
WINDOW_MIN_WIDTH = 1100  # Minimum window width in pixels.
WINDOW_MIN_HEIGHT = 800  # Minimum window height in pixels.
PADDING_BASE = 12  # Standard padding size in pixels.
PADDING_LARGE = 18  # Large padding size in pixels.
PADDING_SMALL = 8  # Small padding size in pixels.
FONT_SIZE_BASE = 13  # Base font size in points.
FONT_SIZE_LARGE = 15  # Large font size in points.
BORDER_RADIUS = 6  # Border radius for rounded corners in pixels.


def get_active_palette() -> ColorPalette:
    """Return the color palette for the currently active theme."""

    return _PALETTES[_ACTIVE_THEME]


def get_application_style() -> str:
    """Return the preferred cross-platform Qt style (Fusion).

    Returns:
        The style name string.
    """
    return "Fusion"


def get_stylesheet(theme: Theme) -> str:
    """Build a Qt style sheet (QSS) for the selected theme.

    Args:
        theme: The theme to generate the stylesheet for.

    Returns:
        A complete QSS string with theme styling rules.
    """
    palette = _PALETTES[theme]

    return f"""
        QMainWindow {{
            background-color: {palette.background_primary};
        }}

        QWidget {{
            background-color: {palette.background_secondary};
            color: {palette.text_primary};
            font-size: {FONT_SIZE_BASE}px;
        }}

        QLabel {{
            color: {palette.text_primary};
        }}

        QStatusBar {{
            background-color: {palette.background_tertiary};
            color: {palette.text_secondary};
            border-top: 1px solid {palette.border};
        }}

        QStatusBar::item {{
            border: none;
        }}

        QMenuBar {{
            background-color: {palette.background_secondary};
            color: {palette.text_primary};
        }}

        QMenuBar::item {{
            background: transparent;
            padding: 4px 12px;
            margin: 0px;
        }}

        QMenuBar::item:selected {{
            background-color: {palette.accent_primary};
            color: {palette.background_secondary};
        }}

        QMenu {{
            background-color: {palette.background_secondary};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            padding: 4px;
        }}

        QMenu::item:selected {{
            background-color: {palette.accent_hover};
            color: {palette.background_secondary};
        }}

        QPushButton {{
            background-color: {palette.accent_primary};
            color: {palette.background_secondary};
            border: none;
            border-radius: {BORDER_RADIUS}px;
            padding: 6px 14px;
            font-size: {FONT_SIZE_BASE}px;
        }}

        QPushButton:hover {{
            background-color: {palette.accent_hover};
        }}

        QPushButton:pressed {{
            background-color: {palette.accent_pressed};
        }}

        QPushButton:disabled {{
            background-color: {palette.background_tertiary};
            color: {palette.text_disabled};
        }}

        QLineEdit, QTextEdit, QComboBox, QListView {{
            background-color: {palette.background_secondary};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: {BORDER_RADIUS}px;
            padding: 4px {PADDING_SMALL}px;
        }}

        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QListView:focus {{
            border: 1px solid {palette.accent_primary};
        }}

        QToolBar {{
            background-color: {palette.background_secondary};
            border-bottom: 1px solid {palette.border};
        }}

        QToolTip {{
            background-color: {palette.background_secondary};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            padding: 4px;
        }}
    """.strip()


def apply_theme(app: QtWidgets.QApplication, theme: Theme) -> None:
    """Apply the desired theme and stylesheet to the application.

    Args:
        app: The QApplication instance.
        theme: The theme to apply.
    """
    global _ACTIVE_THEME  # pylint: disable=global-statement
    _ACTIVE_THEME = theme
    app.setStyle(get_application_style())
    app.setStyleSheet(get_stylesheet(theme))
