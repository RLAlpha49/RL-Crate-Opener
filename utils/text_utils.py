"""
This module contains utility functions for handling text in the Rocket League item system.

Functions:
    clean_text: Cleans the input text by keeping only alphanumeric characters and spaces.
    get_rarity: Determines the rarity of an item.
"""

import re


def clean_text(text):
    """
    Cleans the input text by keeping only alphanumeric characters and spaces.

    Args:
        text (str): The text to be cleaned.

    Returns:
        str: The cleaned text.
    """
    # Use a regular expression to keep only alphanumeric characters and spaces
    cleaned_text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return cleaned_text


def get_rarity(item):
    """
    Determines the rarity of an item.

    Args:
        item (str): The item whose rarity is to be determined.

    Returns:
        str: The rarity of the item. If the rarity is not recognized, returns "Unknown".
    """
    rarities = ["Uncommon", "Very Rare", "Rare", "Import", "Exotic", "Black Market"]
    for rarity in rarities:
        if rarity.lower() in item.lower():
            return rarity
    return "Unknown"  # If rarity is not recognized
