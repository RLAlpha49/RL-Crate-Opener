"""Widget that renders category and rarity statistics during automation."""

from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.data.items import item_manager
from src.models import Rarity
from src.utils.logger import logger

from .styles import FONT_SIZE_LARGE, PADDING_BASE, get_active_palette


class StatsWidget(QWidget):
    """Present live category and rarity statistics."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the statistics widget and load data from file.

        Args:
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self._category_stats: Dict[str, Dict[Rarity, int]] = {}
        self._total_drops = 0
        self._total_items = 0
        self._palette = get_active_palette()
        self._category_items: Dict[str, QTreeWidgetItem] = {}

        self._total_drops_label: QLabel | None = None
        self._total_items_label: QLabel | None = None
        self._tree_widget: QTreeWidget | None = None

        self._setup_ui()
        self._refresh_from_file()

    def _setup_ui(self) -> None:
        """Create and layout all UI elements for the statistics widget."""
        title_font = QFont()
        title_font.setPointSize(FONT_SIZE_LARGE)
        title_font.setBold(True)

        title_label = QLabel("Statistics", self)
        title_label.setFont(title_font)

        total_drops_label = QLabel("Total Drops: 0", self)
        total_items_label = QLabel("Total Items: 0", self)

        tree_widget = QTreeWidget(self)
        tree_widget.setColumnCount(3)
        tree_widget.setHeaderLabels(["Category / Rarity", "Count", "Percentage"])
        tree_widget.setSortingEnabled(False)
        tree_widget.setUniformRowHeights(True)
        tree_widget.setIndentation(20)
        tree_widget.setStyleSheet(
            f"""
            QTreeWidget {{
                background-color: {self._palette.background_secondary};
                color: {self._palette.text_primary};
                border: 1px solid {self._palette.border};
                border-radius: 4px;
            }}
            QTreeWidget::item {{
                padding: 4px;
                border: none;
            }}
            QTreeWidget::item:selected {{
                background-color: {self._palette.accent_hover};
            }}
            QTreeWidget::item:hover {{
                background-color: {self._palette.background_tertiary};
            }}
            QHeaderView::section {{
                background-color: {self._palette.background_tertiary};
                color: {self._palette.text_primary};
                padding: 4px;
                border: 1px solid {self._palette.border};
                font-weight: bold;
            }}
            QScrollBar:vertical {{
                background-color: {self._palette.background_secondary};
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self._palette.accent_primary};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self._palette.accent_hover};
            }}
            """
        )

        refresh_button = QPushButton("Refresh from File", self)
        refresh_button.clicked.connect(self._refresh_from_file)

        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet(
            f"""
            QFrame {{
                border: 1px solid {self._palette.border};
                border-radius: 6px;
                background-color: {self._palette.background_primary};
            }}
            """
        )

        inner_layout = QVBoxLayout()
        inner_layout.setContentsMargins(
            PADDING_BASE,
            PADDING_BASE,
            PADDING_BASE,
            PADDING_BASE,
        )
        inner_layout.setSpacing(PADDING_BASE)
        inner_layout.addWidget(title_label)
        inner_layout.addWidget(total_drops_label)
        inner_layout.addWidget(total_items_label)
        inner_layout.addWidget(tree_widget, stretch=1)
        inner_layout.addWidget(refresh_button)
        frame.setLayout(inner_layout)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(frame)
        self.setLayout(root_layout)

        self._total_drops_label = total_drops_label
        self._total_items_label = total_items_label
        self._tree_widget = tree_widget

    def _update_display(self) -> None:
        """Update the statistics tree widget with current data."""
        if (
            self._tree_widget is None
            or self._total_drops_label is None
            or self._total_items_label is None
        ):
            return

        self._total_drops_label.setText(f"Total Drops: {self._total_drops}")
        self._total_items_label.setText(f"Total Items: {self._total_items}")

        category_font = QFont()
        category_font.setBold(True)

        # Sort categories by rarity (rarest drop type first)
        category_rarity_map = {
            "Black Market Drop": 0,
            "Exotic Drop": 1,
            "Import Drop": 2,
            "Deluxe Drop": 3,
            "Special Drop": 4,
            "Sport Drop": 5,
        }
        sorted_categories = sorted(
            self._category_stats.keys(),
            key=lambda x: category_rarity_map.get(x, 999),
        )
        for category_name in sorted_categories:
            rarity_counts = self._category_stats.get(category_name, {})
            category_total = sum(rarity_counts.values())

            if category_name not in self._category_items:
                category_item = QTreeWidgetItem(
                    [category_name, str(category_total), "-"]
                )
                category_item.setFont(0, category_font)
                # Right-align count column
                category_item.setTextAlignment(
                    1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                category_item.setTextAlignment(
                    2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._tree_widget.addTopLevelItem(category_item)
                self._category_items[category_name] = category_item
            else:
                category_item = self._category_items[category_name]
                category_item.setText(1, str(category_total))

            if category_total == 0:
                category_item.takeChildren()
                continue

            category_item.takeChildren()
            for rarity in sorted(rarity_counts.keys(), key=Rarity.order):
                count = rarity_counts[rarity]
                # Skip items with zero count to reduce clutter
                if count == 0:
                    continue
                percentage = (count / category_total) * 100 if category_total else 0
                child_item = QTreeWidgetItem(
                    [
                        rarity.name.replace("_", " ").title(),
                        str(count),
                        f"{percentage:.1f}%",
                    ]
                )
                # Right-align count and percentage columns
                child_item.setTextAlignment(
                    1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                child_item.setTextAlignment(
                    2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._apply_rarity_color(child_item, rarity)
                category_item.addChild(child_item)

        self._tree_widget.expandAll()

        # Auto-expand columns to fit content
        for i in range(self._tree_widget.columnCount()):
            self._tree_widget.resizeColumnToContents(i)

    def _apply_rarity_color(self, item: QTreeWidgetItem, rarity: Rarity) -> None:
        """Apply rarity-appropriate colors to a tree item.

        Args:
            item: The tree widget item to color.
            rarity: The rarity level to determine the color.
        """
        color_map = {
            Rarity.BLACK_MARKET: self._palette.status_error,
            Rarity.EXOTIC: self._palette.accent_primary,
            Rarity.IMPORT: self._palette.status_info,
        }
        color_value = color_map.get(rarity, self._palette.text_primary)
        brush = QBrush(QColor(color_value))
        item.setForeground(0, brush)
        item.setForeground(1, brush)
        item.setForeground(2, brush)

    @pyqtSlot()
    def _refresh_from_file(self) -> None:
        """Reload statistics data from the persistent items file."""
        categories = item_manager.get_all_categories()
        self._category_stats.clear()
        self._category_items.clear()
        self._total_drops = 0
        self._total_items = 0
        if self._tree_widget is not None:
            self._tree_widget.clear()
        for category in categories:
            rarity_counts = category.get_rarity_counts()
            self._category_stats[category.name] = rarity_counts
            self._total_items += category.total_items
            self._total_drops += 1
        logger.debug("Statistics refreshed from items file")
        self._update_display()

    @pyqtSlot()
    def on_item_opened(self) -> None:
        """Refresh statistics when an item is opened."""
        self._refresh_from_file()

    @pyqtSlot(str, int)
    def on_drop_processed(self, category: str, item_count: int) -> None:
        """Update statistics when a drop is processed.

        Args:
            category: The drop category.
            item_count: Number of items in the drop.
        """
        logger.debug("Drop processed update for %s: %d items", category, item_count)
        self._total_drops += 1
        self._update_display()

    @pyqtSlot()
    def on_automation_started(self) -> None:
        """Clear statistics when automation begins."""
        self._category_stats.clear()
        self._category_items.clear()
        self._total_drops = 0
        self._total_items = 0
        self._update_display()

    @pyqtSlot(int)
    def on_automation_finished(self) -> None:
        """Refresh statistics when automation completes."""
        if self._tree_widget is not None:
            self._update_display()
            self._refresh_from_file()
