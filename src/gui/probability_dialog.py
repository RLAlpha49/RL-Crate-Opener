"""Dialog showing drop probability breakdowns."""

from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.data.items import item_manager
from src.models import CategoryStats, Rarity
from src.utils.logger import logger

from .styles import FONT_SIZE_LARGE, PADDING_BASE, get_active_palette


class ProbabilityDialog(QDialog):
    """Modal dialog that visualizes calculated drop probabilities."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the probability dialog and load data.

        Args:
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self.setWindowTitle("Probability Calculator")
        self.setModal(True)
        self.setMinimumSize(800, 600)

        self._palette = get_active_palette()
        self._probabilities: Dict[str, OrderedDict[Rarity, float]] = {}
        self._categories: List[CategoryStats] = []

        self._tree_widget: QTreeWidget | None = None
        self._filter_input: QLineEdit | None = None
        self._sort_combo: QComboBox | None = None
        self._summary_label: QLabel | None = None
        self._monospace_font = QFont("Consolas")
        self._monospace_font.setStyleHint(QFont.StyleHint.TypeWriter)

        self._setup_ui()
        self._load_probabilities()

    def _setup_ui(self) -> None:
        """Construct the dialog layout and widgets."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            PADDING_BASE, PADDING_BASE, PADDING_BASE, PADDING_BASE
        )
        layout.setSpacing(PADDING_BASE)

        title_label = QLabel("Drop Probabilities", self)
        title_font = QFont()
        title_font.setPointSize(FONT_SIZE_LARGE)
        title_font.setBold(True)
        title_label.setFont(title_font)

        subtitle_label = QLabel(
            "Probability breakdown by category and rarity based on collected items.",
            self,
        )
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(PADDING_BASE)

        self._filter_input = QLineEdit(self)
        self._filter_input.setPlaceholderText("Filter categories...")
        self._filter_input.textChanged.connect(self._apply_filter)
        toolbar_layout.addWidget(self._filter_input)

        self._sort_combo = QComboBox(self)
        self._sort_combo.addItems(
            [
                "By Rarity (Rarest First)",
                "By Name (A-Z)",
                "By Total Items (Most First)",
            ]
        )
        self._sort_combo.currentIndexChanged.connect(self._apply_sort)
        toolbar_layout.addWidget(self._sort_combo)

        toolbar_layout.addStretch()

        refresh_button = QPushButton("Refresh", self)
        refresh_button.clicked.connect(self._load_probabilities)
        toolbar_layout.addWidget(refresh_button)

        export_button = QPushButton("Export to CSV", self)
        export_button.clicked.connect(self._export_to_csv)
        toolbar_layout.addWidget(export_button)

        layout.addLayout(toolbar_layout)

        tree_frame = QFrame(self)
        tree_frame.setStyleSheet(
            (
                "QFrame {"
                f"background-color: {self._palette.background_secondary};"
                f"border: 1px solid {self._palette.border};"
                "border-radius: 6px;"
                "}"
            )
        )
        frame_layout = QVBoxLayout(tree_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self._tree_widget = QTreeWidget(self)
        self._tree_widget.setHeaderLabels(
            ["Category / Rarity", "Count", "Percentage", "Total Items"]
        )
        self._tree_widget.setAlternatingRowColors(True)
        self._tree_widget.setSortingEnabled(False)
        self._tree_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._tree_widget.setColumnWidth(0, 300)
        self._tree_widget.setColumnWidth(1, 100)
        self._tree_widget.setColumnWidth(2, 120)
        self._tree_widget.setColumnWidth(3, 120)
        header = self._tree_widget.header()
        if header is not None:
            header.setStretchLastSection(False)
        frame_layout.addWidget(self._tree_widget)

        layout.addWidget(tree_frame, stretch=1)

        self._summary_label = QLabel("Total Categories: 0 | Total Items: 0", self)
        layout.addWidget(self._summary_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)
        layout.addLayout(buttons_layout)

    def _load_probabilities(self) -> None:
        """Fetch probabilities and refresh the tree."""

        self._probabilities = item_manager.calculate_probabilities()
        self._categories = item_manager.get_all_categories()

        logger.info("Loaded probabilities: %s categories", len(self._probabilities))

        if not self._probabilities:
            QMessageBox.information(
                self,
                "No Data",
                "No items recorded yet. Open some drops first!",
            )

        self._populate_tree()
        self._apply_sort()
        self._update_summary()
        self._apply_filter()

    def _update_summary(self) -> None:
        """Update the summary label with total categories and items count."""
        if self._summary_label is None:
            return

        total_categories = len(self._probabilities)
        total_items = sum(category.total_items for category in self._categories)
        self._summary_label.setText(
            f"Total Categories: {total_categories} | Total Items: {total_items}"
        )

    def _populate_tree(self) -> None:
        """Populate the tree widget with current probability data."""

        if self._tree_widget is None:
            return

        category_map = {category.name: category for category in self._categories}

        self._tree_widget.setSortingEnabled(False)
        self._tree_widget.clear()

        category_font = QFont()
        category_font.setBold(True)
        category_font.setPointSize(self.font().pointSize())

        for category_name, rarity_probs in self._probabilities.items():
            category_stats = category_map.get(category_name)
            total_items = category_stats.total_items if category_stats else 0
            rarity_counts = category_stats.get_rarity_counts() if category_stats else {}

            category_item = QTreeWidgetItem([category_name, "", "", str(total_items)])
            category_item.setFont(0, category_font)
            category_item.setTextAlignment(
                3, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            category_item.setBackground(
                0, QBrush(QColor(self._palette.background_secondary))
            )
            category_item.setForeground(0, QBrush(QColor(self._palette.text_primary)))
            category_item.setData(0, Qt.ItemDataRole.UserRole, category_name)
            category_item.setData(0, Qt.ItemDataRole.UserRole + 1, total_items)

            for rarity, probability in rarity_probs.items():
                count = rarity_counts.get(rarity, 0)
                child = QTreeWidgetItem(
                    [
                        rarity.value,
                        str(count),
                        f"{probability * 100:.2f}%",
                        "",
                    ]
                )
                child.setFont(1, self._monospace_font)
                child.setFont(2, self._monospace_font)
                child.setTextAlignment(
                    1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                child.setTextAlignment(
                    2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                child.setForeground(0, QBrush(QColor(self._rarity_color(rarity))))
                category_item.addChild(child)

            self._tree_widget.addTopLevelItem(category_item)

        self._tree_widget.expandAll()

        for column in range(self._tree_widget.columnCount()):
            self._tree_widget.resizeColumnToContents(column)

    def _rarity_color(self, rarity: Rarity) -> str:
        """Return a palette color for displaying rarity text.

        Args:
            rarity: The rarity level.

        Returns:
            A hex color string for the rarity.
        """
        if rarity == Rarity.BLACK_MARKET:
            return self._palette.status_error
        if rarity == Rarity.EXOTIC:
            return self._palette.accent_primary
        if rarity == Rarity.IMPORT:
            return self._palette.status_info
        if rarity == Rarity.DELUXE:
            return self._palette.status_warning
        return self._palette.text_secondary

    @pyqtSlot()
    def _apply_filter(self) -> None:
        """Filter tree items by category name using the filter input text."""
        if self._tree_widget is None or self._filter_input is None:
            return

        filter_text = self._filter_input.text().lower().strip()
        for index in range(self._tree_widget.topLevelItemCount()):
            item = self._tree_widget.topLevelItem(index)
            if item is None:
                continue
            category_name = item.data(0, Qt.ItemDataRole.UserRole) or item.text(0)
            matches = not filter_text or filter_text in category_name.lower()
            item.setHidden(not matches)

    @pyqtSlot()
    def _apply_sort(self) -> None:
        """Sort categories by the selected sort option and reapply filter."""
        if self._tree_widget is None or self._sort_combo is None:
            return

        sort_index = self._sort_combo.currentIndex()
        self._tree_widget.setSortingEnabled(False)

        items: List[QTreeWidgetItem] = []
        while self._tree_widget.topLevelItemCount() > 0:
            item = self._tree_widget.takeTopLevelItem(0)
            if item is not None:
                items.append(item)

        # Map category names to their representative rarity for sorting (matches CLI)
        category_rarity_map = {
            "Black Market Drop": 0,
            "Exotic Drop": 1,
            "Import Drop": 2,
            "Deluxe Drop": 3,
            "Special Drop": 4,
            "Sport Drop": 5,
        }

        def sort_key(item: QTreeWidgetItem) -> tuple:
            name = item.data(0, Qt.ItemDataRole.UserRole) or item.text(0)
            total = item.data(0, Qt.ItemDataRole.UserRole + 1) or 0
            if sort_index == 0:
                # By Rarity (Rarest First) - use category_rarity_map, fall back to from_string
                rarity_order = category_rarity_map.get(str(name))
                if rarity_order is None:
                    rarity = Rarity.from_string(str(name))
                    rarity_order = Rarity.order(rarity)
                return (rarity_order, str(name).lower())
            if sort_index == 1:
                # By Name (A-Z)
                return (0, str(name).lower())
            # By Total Items (Most First)
            return (-int(total), str(name).lower())

        items.sort(key=sort_key)

        for item in items:
            self._tree_widget.addTopLevelItem(item)

        self._tree_widget.expandAll()
        self._apply_filter()

    @pyqtSlot()
    def _export_to_csv(self) -> None:
        """Export probability data to a user-selected CSV file."""
        default_path = Path.cwd() / "drop_probabilities.csv"
        file_path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Export Probabilities",
            str(default_path),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path_str:
            return

        file_path = Path(file_path_str)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    [
                        "Category",
                        "Rarity",
                        "Count",
                        "Percentage",
                        "Total Items",
                    ]
                )
                category_map = {
                    category.name: category for category in self._categories
                }
                for category_name, rarity_probs in self._probabilities.items():
                    category_stats = category_map.get(category_name)
                    total_items = category_stats.total_items if category_stats else 0
                    rarity_counts = (
                        category_stats.get_rarity_counts() if category_stats else {}
                    )
                    for rarity, probability in rarity_probs.items():
                        count = rarity_counts.get(rarity, 0)
                        writer.writerow(
                            [
                                category_name,
                                rarity.value,
                                count,
                                f"{probability * 100:.2f}%",
                                total_items,
                            ]
                        )
            QMessageBox.information(
                self,
                "Export Complete",
                f"Probabilities exported to {file_path}",
            )
            logger.info("Exported probabilities to %s", file_path)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to export probabilities: %s", exc)
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Could not export probabilities:\n{exc}",
            )
