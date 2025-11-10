"""Data models for the application."""

from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class Rarity(Enum):
    """
    Item rarity levels in Rocket League drops.

    Ordered from highest (rarest) to lowest rarity for sorting purposes.
    """

    SPORT = "Sport"
    SPECIAL = "Special"
    DELUXE = "Deluxe"
    IMPORT = "Import"
    EXOTIC = "Exotic"
    BLACK_MARKET = "Black Market"
    UNKNOWN = "Unknown"

    @classmethod
    def from_string(cls, text: str) -> "Rarity":
        """
        Parse rarity from text using case-insensitive substring matching.

        Args:
            text: Text to parse for rarity keywords.

        Returns:
            Matching Rarity enum value or UNKNOWN if no match found.
        """
        text_lower = text.replace(" ", "").lower()
        for rarity in cls:
            if rarity.value.replace(" ", "").lower() in text_lower:
                return rarity
        return cls.UNKNOWN

    @classmethod
    def order(cls, rarity: "Rarity") -> int:
        """
        Get the sort order for a rarity level (lower = higher rarity).

        Args:
            rarity: Rarity enum value.

        Returns:
            Integer order for sorting (lower values are higher rarity).
        """
        rarity_order = {
            cls.BLACK_MARKET: 0,
            cls.EXOTIC: 1,
            cls.IMPORT: 2,
            cls.DELUXE: 3,
            cls.SPECIAL: 4,
            cls.SPORT: 5,
            cls.UNKNOWN: 6,
        }
        return rarity_order.get(rarity, 999)


class ItemType:
    """
    Helper for item type extraction and sorting in drop rewards.

    Defines canonical ordering for all known item types in Rocket League drops.
    """

    # Define the canonical sort order for item types (alphabetical)
    TYPE_ORDER = {
        "Animated Decal": 0,
        "Antenna": 1,
        "Body": 2,
        "Decal": 3,
        "Goal Explosion": 4,
        "Paint Finish": 5,
        "Player Banner": 6,
        "Rocket Boost": 7,
        "Topper": 8,
        "Trail": 9,
        "Wheels": 10,
    }

    @staticmethod
    def extract_type(item_name: str) -> str:
        """
        Extract the item type from a full item name.

        Searches for known types, prioritizing longer type names (e.g., "Animated Decal"
        before "Decal"). Returns the original name if no known type is found.

        Args:
            item_name: Full item name (e.g., "Import Body", "Rare Decal").

        Returns:
            Item type (e.g., "Body", "Decal") or original name if no match.
        """
        # Try to match known types (prioritize longer types like "Animated Decal")
        sorted_types = sorted(ItemType.TYPE_ORDER.keys(), key=len, reverse=True)
        for item_type in sorted_types:
            if item_name.endswith(item_type):
                return item_type
        return item_name

    @staticmethod
    def order(item_type: str) -> int:
        """
        Get the sort order for an item type.

        Args:
            item_type: Item type string.

        Returns:
            Integer order for sorting (lower values appear first).
        """
        return ItemType.TYPE_ORDER.get(item_type, 999)


@dataclass
class Item:
    """
    Represents a single item with its category and count.

    Attributes:
        name: Name of the item
        category: Category the item belongs to
        count: Number of this item obtained
    """

    name: str
    category: str
    count: int = 1

    @property
    def rarity(self) -> Rarity:
        """Determine the rarity of this item by parsing its name."""
        return Rarity.from_string(self.name)


@dataclass
class CategoryStats:
    """
    Aggregated statistics for a category of drop items.

    Tracks item counts and calculates rarity-based probabilities for a drop category
    (e.g., "Golden Pumpkin '23").

    Attributes:
        name: Name of the category.
        items: Dictionary mapping item names to their counts.
    """

    name: str
    items: Dict[str, int] = field(default_factory=dict)

    @property
    def total_items(self) -> int:
        """Total number of items collected in this category."""
        return sum(self.items.values())

    def get_rarity_counts(self) -> Dict[Rarity, int]:
        """
        Aggregate item counts by rarity level.

        Parses each item name to extract its rarity, then sums counts by rarity.

        Returns:
            Dictionary mapping Rarity enum values to total counts.
        """
        rarity_counts: Dict[Rarity, int] = {
            rarity: 0 for rarity in Rarity if rarity != Rarity.UNKNOWN
        }

        for item_name, count in self.items.items():
            rarity = Rarity.from_string(item_name)
            if rarity != Rarity.UNKNOWN:
                rarity_counts[rarity] += count

        return rarity_counts

    def get_probabilities(self) -> "OrderedDict[Rarity, float]":
        """
        Calculate drop probability for each rarity, ordered by rarity hierarchy.

        Returns OrderedDict ordered from highest rarity (rarest) to lowest rarity
        (most common in item drops), ensuring consistent output across Python versions.

        The sort uses Rarity.order() which returns lower values for rarer items:
        - BLACK_MARKET=0 (rarest)
        - EXOTIC=1
        - IMPORT=2
        - DELUXE=3
        - SPECIAL=4
        - SPORT=5 (most common item type)

        Ascending sort by rarity order results in rarest rarities appearing first.

        Returns:
            OrderedDict of rarity to probability (0.0-1.0), sorted by rarity hierarchy
            (rarest items first, regardless of frequency in drops).
        """
        if self.total_items == 0:
            return OrderedDict()

        rarity_counts = self.get_rarity_counts()
        # Create dict with probabilities
        probs = {
            rarity: count / self.total_items
            for rarity, count in rarity_counts.items()
            if count > 0
        }
        # Sort by Rarity.order() ascending (rarest items first)
        # Construct OrderedDict for explicit ordering stability
        sorted_pairs = sorted(probs.items(), key=lambda x: Rarity.order(x[0]))
        return OrderedDict(sorted_pairs)
