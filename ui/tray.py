"""
System Tray Manager for FluidCursor.
Provides a modern system tray icon with quick toggles, settings access, and emergency restoration.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import Qt

class CursorTrayIcon(QSystemTrayIcon):
    def __init__(self, overlay, settings_window, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.settings_window = settings_window

        # Generate sleek procedural icon
        self.setIcon(self._create_tray_icon())
        self.setToolTip("FluidCursor - Animated Windows Cursor (F9 to toggle)")

        # Create menu
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #38BDF8;
                color: #0F172A;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 8px;
            }
        """)

        # Title / Info
        title_action = QAction("FluidCursor Active", self)
        title_action.setEnabled(False)
        self.menu.addAction(title_action)
        self.title_action = title_action

        self.menu.addSeparator()

        # Toggle Action
        self.toggle_action = QAction("Enable Animated Cursor (F9)", self)
        self.toggle_action.setCheckable(True)
        self.toggle_action.setChecked(self.overlay.config.enabled)
        self.toggle_action.triggered.connect(self._on_toggle_clicked)
        self.menu.addAction(self.toggle_action)

        # Settings
        self.settings_action = QAction("Settings & Customization...", self)
        self.settings_action.triggered.connect(self._open_settings)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        # Emergency Restore
        self.restore_action = QAction("Restore Windows Cursor", self)
        self.restore_action.triggered.connect(self._restore_system_cursor)
        self.menu.addAction(self.restore_action)

        # Exit
        self.exit_action = QAction("Exit FluidCursor", self)
        self.exit_action.triggered.connect(self._exit_app)
        self.menu.addAction(self.exit_action)

        self.setContextMenu(self.menu)
        self.activated.connect(self._on_tray_activated)

        # Wire up overlay toggle callback to update tray check state
        self.overlay.on_state_toggled = self.update_state

    def _create_tray_icon(self) -> QIcon:
        """Draws a crisp, high-contrast cursor icon."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw a stylish pointer shape
        from core.theme import CursorRenderer
        path = CursorRenderer._create_standard_arrow_path(1.0)

        painter.save()
        painter.translate(6, 4)
        # Drop shadow
        painter.fillPath(path, QColor(0, 0, 0, 100))
        # Foreground
        painter.setBrush(QColor("#00D2FF"))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawPath(path)
        painter.restore()

        painter.end()
        return QIcon(pixmap)

    def _on_toggle_clicked(self):
        self.overlay.toggle_enabled()

    def update_state(self, is_enabled: bool):
        self.toggle_action.setChecked(is_enabled)
        if is_enabled:
            self.title_action.setText("FluidCursor Active")
            self.setToolTip("FluidCursor - Active (F9 to toggle)")
        else:
            self.title_action.setText("FluidCursor Paused")
            self.setToolTip("FluidCursor - Paused (F9 to toggle)")

    def _open_settings(self):
        if self.settings_window:
            self.settings_window.show()
            self.settings_window.activateWindow()
            self.settings_window.raise_()

    def _restore_system_cursor(self):
        self.overlay.cursor_mgr.restore_system_cursor()
        self.showMessage(
            "FluidCursor",
            "Windows system cursor has been restored.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _exit_app(self):
        self.overlay.cursor_mgr.restore_system_cursor()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_settings()
