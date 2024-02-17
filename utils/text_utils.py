"""
This module contains utility functions for handling text in the Rocket League item system.

Functions:
    clean_text: Cleans the input text by keeping only alphanumeric characters and spaces.
    get_rarity: Determines the rarity of an item.
"""

import re

# Compile the regular expression for cleaning text
CLEAN_TEXT_REGEX = re.compile(r"[^a-zA-Z0-9\s]")


def clean_text(text):
    """
    Cleans the input text by keeping only alphanumeric characters and spaces.

    Args:
        text (str): The text to be cleaned.

    Returns:
        str: The cleaned text.
    """
    # Use the compiled regular expression to clean the text
    cleaned_text = CLEAN_TEXT_REGEX.sub("", text)
    return cleaned_text


def get_rarity(item):
    """
    Determines the rarity of an item.

    Args:
        item (str): The item whose rarity is to be determined.

    Returns:
        str: The rarity of the item. If the rarity is not recognized, returns "Unknown".
    """
    rarities = {"Uncommon", "Very Rare", "Rare", "Import", "Exotic", "Black Market"}
    item_no_spaces = item.replace(" ", "").lower()
    for rarity in rarities:
        if rarity.replace(" ", "").lower() in item_no_spaces:
            return rarity
    return "Unknown"  # If rarity is not recognized
