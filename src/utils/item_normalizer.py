"""Item name normalization and fuzzy matching utilities for OCR text."""

import re
from difflib import SequenceMatcher
from typing import Optional, Tuple


# Rarity constant representing Black Market rarity tier.
BLACK_MARKET = "Black Market"
# Set of all valid rarity levels in Rocket League.
RARITIES = {"Base", "Sport", "Special", "Deluxe", "Import", "Exotic", BLACK_MARKET}

# Maps lowercase rarity keywords to canonical rarity names.
RARITY_KEYWORDS = {
    "base": "Base",
    "sport": "Sport",
    "special": "Special",
    "deluxe": "Deluxe",
    "import": "Import",
    "exotic": "Exotic",
    "black market": BLACK_MARKET,
    "blackmarket": BLACK_MARKET,
}

# Set of all valid item types that can drop from Rocket League crates.
ITEM_TYPES = {
    "Animated Decal",
    "Antenna",
    "Body",
    "Decal",
    "Goal Explosion",
    "Paint Finish",
    "Player Banner",
    "Rocket Boost",
    "Topper",
    "Trail",
    "Wheels",
}


def normalize_item_text(text: str) -> str:
    """
    Normalize item text to standard capitalization and spacing.

    Performs multiple passes to fix OCR artifacts:
    1. Removes leading/trailing whitespace and quotes.
    2. Removes leading digits (OCR artifacts).
    3. Cleans non-alphanumeric characters.
    4. Handles camelCase by inserting spaces.
    5. Splits known concatenated words.
    6. Applies title case.

    Args:
        text: Raw OCR text from image.

    Returns:
        Normalized text (title-cased, properly spaced).
    """
    # Remove leading/trailing whitespace and OCR artifacts
    text = re.sub(r"^[\s'\"]+", "", text)  # Remove leading whitespace and quotes
    text = re.sub(r"[\s'\"]+$", "", text)  # Remove trailing whitespace and quotes

    # Remove leading digits that are likely OCR artifacts
    text = re.sub(r"^[\d\s]+([a-zA-Z])", r"\1", text)

    # Remove characters not in the whitelist (keep apostrophes, ampersands, slashes, colons)
    text = re.sub(r"[^a-zA-Z0-9\s'&/:]", "", text)

    # Insert spaces between lowercase and uppercase letters for camelCase
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    # Handle transitions from uppercase followed by lowercase to uppercase
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)

    # Try to split unknown concatenated words by comparing against known items
    # This handles cases like "Deluxetrail" that don't have camelCase patterns
    from src.data.items import item_manager  # pylint: disable=import-outside-toplevel

    words = text.split()
    split_words = []
    # Precompute categories to avoid repeated file reads
    all_categories = item_manager.get_all_categories()

    for word in words:
        # Try to find splits by checking if rarity prefixes match known patterns
        split_word = _try_split_concatenated_word(word, all_categories)
        if split_word and split_word != word:
            split_words.extend(split_word.split())
        else:
            split_words.append(word)

    text = " ".join(split_words)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip().title()


def _try_split_concatenated_word(word: str, all_categories: list) -> Optional[str]:
    """
    Attempt to split a concatenated word using known rarity/type patterns.

    Handles cases like "Deluxetrail" → "Deluxe Trail" by checking if the word
    starts with a known rarity keyword followed by a recognized item type or category.

    Args:
        word: Single word that may be concatenated.
        all_categories: Precomputed list of category statistics to avoid repeated file reads.

    Returns:
        Split version of word if recognized pattern found, None otherwise.
    """
    word_lower = word.lower()

    # Try each rarity as a potential prefix
    for rarity in RARITY_KEYWORDS:
        rarity_lower = rarity.lower()
        if word_lower.startswith(rarity_lower):
            # Found a rarity prefix, extract the rest
            remainder = word[len(rarity) :]
            if remainder:  # Make sure there's something left
                # Check if this rarity + remainder matches any known item or category
                test_text = f"{rarity} {remainder}"
                test_normalized = test_text.strip().title()

                # First check if it matches a category name
                for category_stats in all_categories:
                    if category_stats.name == test_normalized:
                        return test_normalized

                # Then check if this item exists in any category
                for category_stats in all_categories:
                    if test_normalized in category_stats.items:
                        return test_normalized

    return None


def extract_rarity_and_type(text: str) -> Tuple[Optional[str], str]:
    """
    Extract rarity level and item type from item text.

    Handles both space-separated ("Deluxe Wheels") and concatenated ("Deluxewheel")
    formats. Checks for multi-word rarities (e.g., "Black Market") before single words.

    Args:
        text: Normalized item text.

    Returns:
        Tuple of (rarity, item_type) where rarity can be None if not found.

    Examples:
        "Deluxe Wheels" → ("Deluxe", "Wheels")
        "Black Market Topper" → ("Black Market", "Topper")
        "Importbody" → ("Import", "body")
    """
    words = text.lower().split()
    detected_rarity = None
    item_type = text.lower()

    # First try space-separated format
    if words:
        first_word = words[0]

        # Check for two-word rarities first (e.g., "black market")
        if len(words) >= 2:
            two_word = f"{words[0]} {words[1]}"
            if two_word in RARITY_KEYWORDS:
                detected_rarity = RARITY_KEYWORDS[two_word]
                type_words = words[2:]
                item_type = " ".join(type_words) if type_words else ""
                return detected_rarity, item_type

            # Check single word
            if first_word in RARITY_KEYWORDS:
                detected_rarity = RARITY_KEYWORDS[first_word]
                type_words = words[1:]
                item_type = " ".join(type_words) if type_words else ""
                return detected_rarity, item_type

        # Single word case
        elif first_word in RARITY_KEYWORDS:
            detected_rarity = RARITY_KEYWORDS[first_word]
            type_words = words[1:]
            item_type = " ".join(type_words) if type_words else ""
            return detected_rarity, item_type

    # If no space-separated rarity found, try to extract from concatenated form
    # E.g., "importbody" -> check if it starts with a rarity keyword
    text_lower = text.lower()
    for rarity_keyword, rarity_value in RARITY_KEYWORDS.items():
        # Skip multi-word rarities in this phase
        if " " in rarity_keyword:
            continue

        if text_lower.startswith(rarity_keyword):
            # Found a match - extract rarity and rest as type
            detected_rarity = rarity_value
            item_type = text_lower[len(rarity_keyword) :].strip()
            # Try to add space between rarity and type for readability
            return detected_rarity, item_type

    return detected_rarity, item_type.lower()


def fuzzy_match_item(
    normalized_text: str, threshold: float = 0.6
) -> Optional[Tuple[str, str]]:
    """
    Find the best matching known item using fuzzy string matching.

    Tries exact match first (case-insensitive), then falls back to fuzzy matching
    using SequenceMatcher if threshold is met.

    Args:
        normalized_text: Normalized item text (e.g., "Deluxe Wheels").
        threshold: Minimum similarity ratio (0.0-1.0) to accept a match.

    Returns:
        Tuple of (canonical_key, category_name) if match found, None otherwise.
    """
    from src.data.items import item_manager  # pylint: disable=import-outside-toplevel

    rarity, item_type = extract_rarity_and_type(normalized_text)

    # Get all known items with their categories
    all_categories = item_manager.get_all_categories()
    known_items = {}  # Maps canonical key to category

    for cat_stats in all_categories:
        category_name = cat_stats.name
        for item_key in cat_stats.items:
            # Normalize the key for comparison (lowercase, no spaces)
            canonical_key = item_key.lower().replace(" ", "")
            known_items[canonical_key] = (item_key, category_name)

    # Try to find exact match first (case-insensitive)
    normalized_input = normalized_text.lower().replace(" ", "")
    if normalized_input in known_items:
        item_key, category = known_items[normalized_input]
        return item_key, category

    # Try to find fuzzy match
    best_match = None
    best_score = threshold
    best_category: str | None = None

    for canonical_key, (original_key, category) in known_items.items():
        # Compare with item type if we detected a rarity
        if rarity:
            # Try matching just the type part against known items
            comparison_text = item_type.lower().replace(" ", "")
            comparison_item = canonical_key.replace(rarity.lower(), "", 1).strip()
        else:
            comparison_text = normalized_text.lower().replace(" ", "")
            comparison_item = canonical_key

        similarity = SequenceMatcher(None, comparison_text, comparison_item).ratio()

        if similarity > best_score:
            best_score = similarity
            best_match = original_key
            best_category = category

    if best_match and best_category is not None:
        return best_match, best_category

    return None


def normalize_and_map_item(
    ocr_text: str,
) -> Optional[Tuple[str, str]]:
    """
    Complete pipeline: normalize raw OCR text and map to known item.

    Combines normalization, rarity/type extraction, and fuzzy matching to find
    the canonical item name from raw OCR output.

    Args:
        ocr_text: Raw text from OCR image extraction.

    Returns:
        Tuple of (canonical_key, display_name) if match found, None otherwise.
    """
    # Normalize the text
    normalized = normalize_item_text(ocr_text)

    if not normalized:
        return None

    # Try to match to known item - returns (item_key, category)
    match_result = fuzzy_match_item(normalized)

    if not match_result:
        return None

    matched_key, _ = match_result

    return matched_key, matched_key
