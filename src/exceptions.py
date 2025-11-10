"""Custom exceptions for the application."""


class RLDropOpenerError(Exception):
    """Base exception for all application errors."""


class WindowNotFoundError(RLDropOpenerError):
    """Raised when the Rocket League window cannot be found."""


class InvalidResolutionError(RLDropOpenerError):
    """Raised when the game is not running at the required resolution."""


class ItemFileError(RLDropOpenerError):
    """Raised when there's an error reading or writing the items file."""


class OCRError(RLDropOpenerError):
    """Raised when OCR fails to extract text."""
