"""Item data management."""

from collections import OrderedDict
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import CONFIG
from src.exceptions import ItemFileError
from src.models import CategoryStats, Rarity
from src.utils.logger import logger


class ItemsConfigParser(ConfigParser):
    """
    ConfigParser subclass preserving case-sensitivity for option names.

    By default, ConfigParser converts all option names to lowercase. This subclass
    overrides optionxform() to preserve original casing, which is essential for
    maintaining correct capitalization of item names in the items file.
    """

    def optionxform(self, optionstr: str) -> str:
        """
        Preserve case sensitivity for option names.

        By default, ConfigParser lowercases all option names. This override
        returns the option name unchanged, preserving the original casing.

        Args:
            optionstr: The option name as it appears in the file.

        Returns:
            The option name unchanged (case-sensitive).
        """
        return optionstr


def create_items_parser() -> ItemsConfigParser:
    """
    Create a new ItemsConfigParser instance.

    Returns:
        A configured ItemsConfigParser ready for use.
    """
    return ItemsConfigParser()


def _find_project_root(start_path: Path) -> Path:
    """
    Locate the project root by searching for marker files.

    Climbs the directory tree looking for common project markers (.git, README.md,
    requirements.txt). This ensures robust path resolution regardless of invocation
    context or non-standard project layouts.

    Args:
        start_path: Starting path to climb from (typically this file's directory).

    Returns:
        Path to the project root directory.

    Raises:
        FileNotFoundError: If no project marker is found.
    """
    markers = [".git", "README.md", "requirements.txt"]
    current = start_path.resolve()

    # Climb up the directory tree
    while current != current.parent:  # Stop at filesystem root
        for marker in markers:
            if (current / marker).exists():
                return current
        current = current.parent

    # Fallback: if no marker found, try climbing up 2 levels from start_path
    # (assumes structure like src/data/items.py)
    fallback = start_path.resolve().parents[2]
    if fallback.exists():
        return fallback

    raise FileNotFoundError(
        "Could not find project root. Ensure .git, README.md, or requirements.txt exists."
    )


class ItemManager:
    """
    Manages item tracking, storage, and probability calculations for drops.

    Handles loading/saving items to a configuration file, updating item counts
    when new items are obtained, calculating rarity-based probabilities, and
    maintaining sorted organization of categories and items.
    """

    def __init__(self, items_file: Optional[Path] = None):
        """
        Initialize ItemManager with optional custom items file path.

        If items_file is None, uses CONFIG.ITEMS_FILE. Relative paths are resolved
        against the project root (identified by .git, README.md, or requirements.txt)
        for deterministic behavior regardless of invocation location.

        Args:
            items_file: Optional path to items file. If None, uses CONFIG.ITEMS_FILE.

        Raises:
            FileNotFoundError: If project root cannot be determined for relative paths.
        """
        if items_file is None:
            items_file_path = Path(CONFIG.ITEMS_FILE)
        else:
            items_file_path = Path(items_file)

        # Resolve relative paths against project root for determinism
        if not items_file_path.is_absolute():
            project_root = _find_project_root(Path(__file__))
            items_file_path = project_root / items_file_path

        self.items_file = items_file_path
        logger.debug(
            "Items file path: %s (absolute: %s)",
            self.items_file,
            self.items_file.is_absolute(),
        )
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create the items file if it doesn't exist."""
        if not self.items_file.exists():
            self.items_file.parent.mkdir(parents=True, exist_ok=True)
            self.items_file.touch()

    def load_items(self) -> ItemsConfigParser:
        """
        Load items from the items file into a parser.

        Returns:
            ItemsConfigParser containing categories and items.

        Raises:
            ItemFileError: If file reading fails.
        """
        try:
            items = create_items_parser()
            items.read(self.items_file, encoding="utf-8")
            return items
        except (OSError, IOError, ValueError) as e:
            raise ItemFileError(f"Failed to load items: {e}") from e

    def save_items(self, items: ItemsConfigParser) -> None:
        """
        Save items to the items file.

        Args:
            items: ItemsConfigParser to write to file.

        Raises:
            ItemFileError: If file writing fails.
        """
        try:
            with open(self.items_file, "w", encoding="utf-8") as f:
                items.write(f)
        except (OSError, IOError, TypeError) as e:
            raise ItemFileError(f"Failed to save items: {e}") from e

    def update_item(self, category: str, item_name: str) -> None:
        """
        Increment the count for an item in a category.

        Normalizes the item name to standard format (Title Case). Automatically
        creates the category if it doesn't exist.

        Validates that the category is one of the expected categories and that
        the item has a valid rarity and type before saving. If validation fails,
        the item is saved as "Unknown".

        Args:
            category: Category name for the item.
            item_name: Name of the item (will be normalized).
        """
        from src.models import ItemType  # pylint: disable=import-outside-toplevel
        from src.utils.item_normalizer import normalize_item_text  # pylint: disable=import-outside-toplevel

        items = self.load_items()

        # Normalize the item name to standard format (Title Case with spaces)
        normalized_name = normalize_item_text(item_name)
        if not normalized_name:
            return

        # Validate category
        expected_categories = {
            "Black Market Drop",
            "Exotic Drop",
            "Import Drop",
            "Deluxe Drop",
            "Special Drop",
            "Sport Drop",
        }
        if category not in expected_categories:
            logger.warning(
                "Unexpected category '%s' not in expected categories: %s. "
                "Item '%s' will be saved as 'Unknown'.",
                category,
                ", ".join(sorted(expected_categories)),
                normalized_name,
            )
            normalized_name = "Unknown"

        # Validate item rarity
        rarity = Rarity.from_string(normalized_name)
        if rarity == Rarity.UNKNOWN:
            logger.warning(
                "Item '%s' has unknown rarity. Saving as 'Unknown'.",
                normalized_name,
            )
            normalized_name = "Unknown"

        # Validate item type
        item_type = ItemType.extract_type(normalized_name)
        if item_type not in ItemType.TYPE_ORDER:
            logger.warning(
                "Item '%s' has unknown type '%s'. Saving as 'Unknown'.",
                normalized_name,
                item_type,
            )
            normalized_name = "Unknown"

        if not items.has_section(category):
            items.add_section(category)

        # Store count using normalized name as key
        current_count = items.getint(category, normalized_name, fallback=0)
        new_count = current_count + 1
        items.set(category, normalized_name, str(new_count))

        logger.info(
            "Updated %s/%s: %d -> %d",
            category,
            normalized_name,
            current_count,
            new_count,
        )
        self.save_items(items)
        # Sort items to keep categories organized
        self.sort_items()

    def get_all_categories(self) -> List[CategoryStats]:
        """
        Get all item categories with their statistics.

        Skips metadata sections (containing ':' in the name) which store rarity
        and display_name information.

        Returns:
            List of CategoryStats objects, one per category.
        """
        items = self.load_items()
        categories = []
        for category_name in items.sections():
            # Skip metadata sections (e.g., "Category:rarity")
            if ":" in category_name:
                continue
            items_dict = {
                item: items.getint(category_name, item)
                for item in items.options(category_name)
            }
            categories.append(CategoryStats(name=category_name, items=items_dict))
        return categories

    def calculate_probabilities(self) -> Dict[str, "OrderedDict[Rarity, float]"]:
        """
        Calculate drop probabilities for all categories.

        Returns OrderedDicts where each category is ordered from highest to lowest
        rarity (lower order values = higher rarity). Skips categories with zero items.

        Returns:
            Dictionary mapping category names to OrderedDicts of Rarity -> probability.
        """
        categories = self.get_all_categories()
        result = {}
        for category in categories:
            if category.total_items > 0:
                result[category.name] = category.get_probabilities()
        return result

    def print_probabilities(self) -> None:
        """
        Print calculated probabilities for all categories in sorted order.

        Categories are printed ordered by rarity (rarest drop type first), with
        rarities within each category also ordered by rarity hierarchy.
        Counts are displayed alongside percentages for clarity.
        """
        probabilities = self.calculate_probabilities()
        if not probabilities:
            print("No items recorded yet.")
            return

        # Map category names to their representative rarity for sorting
        # Categories are named after their primary/most common rarity type
        category_rarity_map = {
            "Black Market Drop": 0,  # BLACK_MARKET
            "Exotic Drop": 1,  # EXOTIC
            "Import Drop": 2,  # IMPORT
            "Deluxe Drop": 3,  # DELUXE
            "Special Drop": 4,  # SPECIAL
            "Sport Drop": 5,  # SPORT
        }

        # Sort categories by rarity (rarest drop type first)
        sorted_categories = sorted(
            probabilities.items(),
            key=lambda x: category_rarity_map.get(x[0], 999),
        )

        for category_name, rarity_probs in sorted_categories:
            print(f"\nCategory: {category_name}")
            # Get the category to access rarity counts
            category = next(
                c for c in self.get_all_categories() if c.name == category_name
            )
            rarity_counts = category.get_rarity_counts()
            # Rarities are already sorted by rarity hierarchy in get_probabilities
            for rarity, probability in rarity_probs.items():
                count = rarity_counts.get(rarity, 0)
                print(f"  {rarity.value}: {probability * 100:.2f}% ({count} items)")

    def sort_items(self) -> None:
        """
        Sort all items by rarity and type within each category.

        Reorganizes the items file so that:
        1. Categories are sorted by their rarity (highest first)
        2. Items within each category are sorted by rarity, then type, then name
        3. Associated metadata sections (rarity, display_name) are preserved

        Metadata sections are recognized by ':' in the section name and are
        automatically maintained alongside their parent categories.
        """
        items = self.load_items()
        sorted_items = create_items_parser()

        # Get all sections, filter out metadata sections, and sort by category rarity
        all_sections = [s for s in items.sections() if ":" not in s]

        # Sort categories by the rarity extracted from their name
        def category_sort_key(category: str) -> int:
            """Extract rarity from category name and return its order."""
            rarity = Rarity.from_string(category)
            return Rarity.order(rarity)

        sorted_categories = sorted(all_sections, key=category_sort_key)

        for category in sorted_categories:
            sorted_items.add_section(category)
            category_items = [
                (item, items.get(category, item)) for item in items.options(category)
            ]
            # Get rarity metadata if available
            rarity_section = f"{category}:rarity"
            rarity_metadata = {}
            if items.has_section(rarity_section):
                for item in items.options(rarity_section):
                    rarity_metadata[item] = items.get(rarity_section, item)

            # Define sort key function with explicit typing for mypy.
            # Capture rarity_metadata via default argument to avoid late-binding issues.
            # pylint: disable=dangerous-default-value
            def sort_key_impl(
                item_tuple: Tuple[str, str], meta: dict = rarity_metadata
            ) -> Tuple[int, int, int, str]:
                """Sort key for items: by rarity order, then by type, then by name."""
                return self._sort_key(item_tuple[0], meta.get(item_tuple[0]))

            category_items.sort(key=sort_key_impl)
            for item, count in category_items:
                sorted_items.set(category, item, count)

            # Copy rarity metadata section if present
            if items.has_section(rarity_section):
                sorted_items.add_section(rarity_section)
                for item in items.options(rarity_section):
                    sorted_items.set(
                        rarity_section, item, items.get(rarity_section, item)
                    )

            # Copy display_name metadata section if present
            display_section = f"{category}:display_name"
            if items.has_section(display_section):
                sorted_items.add_section(display_section)
                for item in items.options(display_section):
                    sorted_items.set(
                        display_section, item, items.get(display_section, item)
                    )

        self.save_items(sorted_items)

    @staticmethod
    def _sort_key(
        item_name: str, rarity_str: Optional[str] = None
    ) -> Tuple[int, int, int, str]:
        """
        Generate a sort key tuple for ordering items by rarity then type.

        Ensures items are ordered by:
        1. Rarity order (lower values = higher rarity)
        2. Item type order (e.g., Body before Wheels)
        3. Name length (shorter names first)
        4. Name (case-insensitive alphabetical)

        Args:
            item_name: Name of the item (canonical key, lowercase).
            rarity_str: Optional explicit rarity string value.

        Returns:
            Tuple for sorting (rarity_order, type_order, name_length, name_lower).
        """
        from src.models import ItemType  # pylint: disable=import-outside-toplevel

        # Use explicit rarity if provided, otherwise infer from item name
        if rarity_str:
            try:
                rarity = Rarity(rarity_str)
            except ValueError:
                rarity = Rarity.from_string(item_name)
        else:
            rarity = Rarity.from_string(item_name)

        rarity_order = Rarity.order(rarity)

        # Extract and order the item type
        item_type = ItemType.extract_type(item_name)
        type_order = ItemType.order(item_type)

        # Use case-insensitive comparison for sorting while preserving original names
        return (rarity_order, type_order, len(item_name), item_name.lower())


# Global item manager instance
item_manager = ItemManager()
