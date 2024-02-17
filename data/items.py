"""
This module contains functions for loading, updating, calculating probabilities,
and sorting items from a configuration file. The items are categorized and each
item has a rarity.

Functions:
    load_items: Load items from the configuration file.
    update_items: Update the count of a specific item in a category.
    calculate_probabilities: Calculate and print the probabilities of each rarity in each category.
    sort_text_file: Sorts the items in the text file by category and item name.
    custom_sort: Determines the sort order of items based on their rarity and length.
"""

import os
import sys
from configparser import ConfigParser

from utils.text_utils import clean_text, get_rarity  # pylint: disable=E0401


# Gets directory of program
base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
items_file_path = os.path.join(base_dir, "items.txt")


def load_items():
    """
    Load items from the configuration file.

    Returns:
        ConfigParser: A ConfigParser object containing the items.
    """
    items = ConfigParser()
    items.read(items_file_path)
    return items


def update_items(category, item):
    """
    Update the count of a specific item in a category.

    Args:
        category (str): The category of the item.
        item (str): The item to update.
    """
    items = load_items()

    # Clean the item name to remove unwanted characters
    item = clean_text(item)

    # Ensure the category exists
    if not items.has_section(category):
        items.add_section(category)

    # Ensure the item exists within the category
    if items.has_option(category, item):
        items.set(
            str(category), str(item), str(int(items.get(str(category), str(item))) + 1)
        )
    else:
        items.set(category, str(item), "1")

    with open(items_file_path, "w", encoding="utf-8") as configfile:
        items.write(configfile)


def calculate_probabilities():
    """
    Calculate and print the probabilities of each rarity in each category.

    This function loads items from the configuration file, calculates the total
    number of items in each category, and the number of items in each rarity.
    It then calculates the probability of each rarity in each category and
    prints them.
    """
    categories = load_items()

    for category in categories.sections():
        print(f"Category: {category}")
        # Gets total number of items in category
        total_items = sum(int(count) for count in categories[category].values())

        # Creates a list of amount of items with rarity
        rarities = {
            "Uncommon": 0,
            "Rare": 0,
            "Very Rare": 0,
            "Import": 0,
            "Exotic": 0,
            "Black Market": 0,
        }

        # Adds items to their respective rarity
        for item, count in categories[category].items():
            rarity = get_rarity(item)
            rarities[rarity] += int(count)

        # Calculate probabilities
        for rarity, count in rarities.items():
            probability = count / total_items
            # Will not print probabilities of 0%
            if probability > 0:
                print(f"{rarity}: {probability * 100:.2f}%")

        print()


def sort_text_file():
    """
    Sorts the items in the text file by category and item name.

    This function reads the items from the text file, sorts them by category and item name,
    and then overwrites the file with the sorted items.
    """
    # Read the existing file and store its contents in a data structure
    with open(items_file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    categories = {}

    current_category = None
    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_category = line[1:-1]
            categories[current_category] = []
        elif line:  # Ignore empty lines
            categories[current_category].append(line)

    # Sort the items within each category
    for category, items in categories.items():
        sorted_items = sorted(items, key=custom_sort)
        categories[category] = sorted_items

    # Overwrite the file with sorted contents
    with open(items_file_path, "w", encoding="utf-8") as file:
        for category, items in categories.items():
            file.write(f"[{category}]\n")
            for item in items:
                file.write(f"{item}\n")
            file.write("\n")


def custom_sort(item):
    """
    Determines the sort order of items based on their rarity and length.

    Args:
        item (str): The item to be sorted.

    Returns:
        tuple: A tuple containing the index of the item's rarity in the
        rarities list and the length of the item.
    """
    rarities = {
        "Uncommon": 0,
        "Rare": 1,
        "Very Rare": 2,
        "Import": 3,
        "Exotic": 4,
        "Black Market": 5,
    }
    rarity = get_rarity(item)
    rarity_index = rarities.get(rarity, len(rarities))
    return rarity_index, len(item)
