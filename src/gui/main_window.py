"""Main window definition for the Rocket League Drop Opener GUI."""

from __future__ import annotations

from typing import cast

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter

from src.config_app import APP_LICENSE, APP_NAME, APP_VERSION

from . import styles
from .automation_panel import AutomationPanel
from .calibration_dialog import CalibrationDialog
from .log_viewer import LogViewer
from .progress_widget import ProgressWidget
from .settings_dialog import SettingsDialog
from .stats_widget import StatsWidget


class MainWindow(QtWidgets.QMainWindow):
    """Primary application window with menu, status bar, and automation controls."""

    def __init__(self) -> None:
        """Initialize the main application window with menu bar and central widget."""
        super().__init__()
        self.setWindowTitle("Rocket League Drop Opener - GUI")
        self.setMinimumSize(styles.WINDOW_MIN_WIDTH, styles.WINDOW_MIN_HEIGHT)

        self._status_bar: QtWidgets.QStatusBar | None = None
        self._automation_panel: AutomationPanel | None = None
        self._progress_widget: ProgressWidget | None = None
        self._log_viewer: LogViewer | None = None
        self._stats_widget: StatsWidget | None = None

        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()

    def _setup_menu_bar(self) -> None:
        """Create application menus mirroring the CLI structure."""

        menu_bar = cast(QtWidgets.QMenuBar, self.menuBar())

        file_menu = cast(QtWidgets.QMenu, menu_bar.addMenu("&File"))
        exit_action = QtGui.QAction("E&xit", self)
        exit_action.setShortcut(QtGui.QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(QtWidgets.QApplication.quit)
        file_menu.addAction(exit_action)

        tools_menu = cast(QtWidgets.QMenu, menu_bar.addMenu("&Tools"))
        calibration_action = QtGui.QAction("Run &Calibration", self)
        calibration_action.triggered.connect(self._handle_run_calibration)
        tools_menu.addAction(calibration_action)

        settings_action = QtGui.QAction("&Settings", self)
        settings_action.triggered.connect(self._handle_settings)
        tools_menu.addAction(settings_action)

        help_menu = cast(QtWidgets.QMenu, menu_bar.addMenu("&Help"))
        about_action = QtGui.QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _setup_central_widget(self) -> None:
        """Create splitter-based layout with automation, progress, logs, and stats widgets."""
        self._automation_panel = AutomationPanel(self)
        self._progress_widget = ProgressWidget(self)
        self._log_viewer = LogViewer(self)
        self._stats_widget = StatsWidget(self)

        self._automation_panel.automation_started.connect(
            self._progress_widget.on_automation_started
        )
        self._automation_panel.automation_started.connect(
            self._stats_widget.on_automation_started
        )
        self._automation_panel.progress_updated.connect(
            self._progress_widget.update_progress
        )
        self._automation_panel.item_opened_signal.connect(
            self._stats_widget.on_item_opened
        )
        self._automation_panel.drop_processed_signal.connect(
            self._stats_widget.on_drop_processed
        )
        self._automation_panel.automation_finished_signal.connect(
            self._progress_widget.on_automation_finished
        )
        self._automation_panel.automation_finished_signal.connect(
            self._stats_widget.on_automation_finished
        )
        self._automation_panel.automation_error_signal.connect(
            self._progress_widget.on_automation_error
        )

        top_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        top_splitter.addWidget(self._automation_panel)
        top_splitter.addWidget(self._progress_widget)
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 1)
        top_splitter.setSizes([400, 400])

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        bottom_splitter.addWidget(self._log_viewer)
        bottom_splitter.addWidget(self._stats_widget)
        bottom_splitter.setStretchFactor(0, 2)
        bottom_splitter.setStretchFactor(1, 1)
        bottom_splitter.setSizes([533, 267])

        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setSizes([200, 400])

        self.setCentralWidget(main_splitter)

    def _setup_status_bar(self) -> None:
        """Initialize the status bar with a default message."""

        self._status_bar = self.statusBar()
        self.update_status("Ready")

    def update_status(self, message: str) -> None:
        """Update the status bar message.

        Args:
            message: The status message to display.
        """
        if self._status_bar is None:
            return
        self._status_bar.showMessage(message)

    def _handle_run_calibration(self) -> None:
        """Open the calibration dialog and update the status bar based on the result."""
        self.update_status("Running calibration...")
        dialog = CalibrationDialog(cast(QtWidgets.QWidget, self))
        dialog.exec()

        if dialog.last_success is True:
            self.update_status("Calibration completed successfully")
        elif dialog.last_success is False:
            self.update_status("Calibration finished with issues")
        else:
            self.update_status("Calibration dismissed")

    def _handle_settings(self) -> None:
        """Open the settings dialog to configure environment variables."""
        self.update_status("Opening settings...")
        dialog = SettingsDialog(cast(QtWidgets.QWidget, self))
        dialog.exec()
        self.update_status("Settings dialog closed")

    def _show_about_dialog(self) -> None:
        """Display an about dialog with application information."""
        message = f"{APP_NAME}\nVersion: {APP_VERSION}\n\nLicense: {APP_LICENSE}"
        QtWidgets.QMessageBox.about(self, "About", message)
