"""Text processing and normalization utilities."""

import re
from typing import List


# Regex for removing unwanted characters (keeps alphanumeric, spaces, ', &, /, :).
CLEAN_TEXT_REGEX = re.compile(r"[^a-zA-Z0-9\s'&/:]")
# Regex for normalizing whitespace sequences to single space.
WHITESPACE_REGEX = re.compile(r"\s+")
# Regex for inserting spaces before capital letters in camelCase words.
CAMELCASE_REGEX = re.compile(r"(?<!^)(?=[A-Z])")


def clean_text(text: str) -> str:
    """
    Clean text by removing unwanted characters and normalizing spacing.

    Keeps only alphanumeric characters, spaces, and punctuation: apostrophes,
    ampersands, slashes, colons. Removes OCR artifacts and leading/trailing punctuation.

    Args:
        text: Text to clean.

    Returns:
        Cleaned text with normalized whitespace.
    """
    # Remove leading/trailing whitespace and OCR artifacts
    text = re.sub(r"^[\s'\"]+", "", text)  # Remove leading whitespace and quotes
    text = re.sub(r"[\s'\"]+$", "", text)  # Remove trailing whitespace and quotes

    # Also remove leading digits that are likely OCR artifacts (like "4 Deluxetrail")
    # but only if followed by space or letter (to preserve things like "123 Main St")
    text = re.sub(r"^[\d\s]+([a-zA-Z])", r"\1", text)

    # Remove characters not in the whitelist (keep apostrophes, ampersands, slashes, colons)
    cleaned = CLEAN_TEXT_REGEX.sub("", text)

    # Insert spaces between lowercase and uppercase letters for camelCase
    # E.g., "importBody" -> "import Body", "deluxeTrail" -> "deluxe Trail"
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)

    # Normalize whitespace
    cleaned = WHITESPACE_REGEX.sub(" ", cleaned)
    return cleaned.strip()


def normalize_text(text: str) -> str:
    """
    Normalize text for case-insensitive comparison.

    Args:
        text: Text to normalize.

    Returns:
        Normalized text (lowercase, no spaces).
    """
    return text.replace(" ", "").lower()


def canonical_key(text: str) -> str:
    """
    Generate a canonical key for consistent item storage and lookup.

    Applies: clean → title case → normalize. Used for item identification
    across sections (e.g., rarity metadata) to ensure consistency.

    Args:
        text: Original item name/text.

    Returns:
        Canonical key for item storage.
    """
    return normalize_text(title_case(clean_text(text)))


def parse_lines(text: str) -> List[str]:
    """
    Split text into non-empty lines.

    Args:
        text: Multi-line text.

    Returns:
        List of non-empty, stripped lines.
    """
    return [line.strip() for line in text.split("\n") if line.strip()]


def title_case(text: str) -> str:
    """
    Convert text to title case.

    Args:
        text: Text to convert.

    Returns:
        Title-cased text.
    """
    return text.lower().title()
