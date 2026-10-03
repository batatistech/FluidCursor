"""
System Tray Manager for FluidCursor.
Provides a modern system tray icon with quick toggles, settings access, and emergency restoration.
"""

from PyQt6.QtWidgets import QSystemTrayIcon
from ui.tray_palette import TrayPalette
from core.i18n import tr
from core.theme_preference import system_tray_theme, interface_theme
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QPalette, QCursor
from PyQt6.QtCore import Qt, QTimer

class CursorTrayIcon(QSystemTrayIcon):
    def __init__(self, overlay, settings_window=None, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.settings_window = settings_window
        self.settings_launcher = None
        if self.settings_window:
            self.settings_window.on_destroy_callback = self._on_settings_destroyed

        # Generate sleek procedural icon
        self._tray_theme = system_tray_theme()
        self.setIcon(self._create_tray_icon())
        self._theme_timer = QTimer(self)
        self._theme_timer.setInterval(4000)
        self._theme_timer.timeout.connect(self.refresh_theme)
        self._theme_timer.start()
        self.setToolTip(f"{self._tr('Enable Animated Cursor')}: {self.overlay.config.toggle_hotkey}")

        # Non-modal QWidget avoids native QMenu tracking blocking the Qt event loop.
        self.menu = TrayPalette()
        self.menu.set_theme(interface_theme(self.overlay.config.ui_theme))
        self.menu.set_language(self.overlay.config.language)

        # Title / Info
        title_action = QAction(self._tr("FluidCursor Active"), self)
        title_action.setEnabled(False)
        self.menu.addAction(title_action)
        self.title_action = title_action

        self.menu.addSeparator()

        # Toggle Action
        self.toggle_action = QAction(f"{self._tr('Enable Animated Cursor')} ({self.overlay.config.toggle_hotkey})", self)
        self.toggle_action.setCheckable(True)
        self.toggle_action.setChecked(self.overlay.config.enabled)
        self.toggle_action.triggered.connect(self._on_toggle_clicked)
        self.menu.addAction(self.toggle_action)

        # Settings
        self.settings_action = QAction(self._tr("Settings & Customization..."), self)
        self.settings_action.triggered.connect(self._open_settings)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        # Emergency Restore
        self.restore_action = QAction(self._tr("Restore Windows Cursor"), self)
        self.restore_action.triggered.connect(self._restore_system_cursor)
        self.menu.addAction(self.restore_action)

        # Exit
        self.exit_action = QAction(self._tr("Exit FluidCursor"), self)
        self.exit_action.triggered.connect(self._exit_app)
        self.menu.addAction(self.exit_action)

        self.menu.aboutToShow.connect(lambda: self.overlay.set_tray_menu_open(True))
        self.menu.aboutToHide.connect(lambda: self.overlay.set_tray_menu_open(False))
        # Queue menu presentation outside Explorer’s synchronous tray callback.
        self.setContextMenu(None)
        self.activated.connect(self._on_tray_activated)

        # Wire up overlay toggle callback to update tray check state
        self.overlay.on_state_toggled = self.update_state
        self.update_state(self.overlay.config.enabled)

    def _tr(self, text):
        return tr(text, self.overlay.config.language)

    def refresh_theme(self):
        theme = system_tray_theme()
        self.menu.set_theme(interface_theme(self.overlay.config.ui_theme))
        if theme != self._tray_theme:
            self._tray_theme = theme
            self.setIcon(self._create_tray_icon())

    def _create_tray_icon(self) -> QIcon:
        from ui.tray_icon import create_tray_icon
        return create_tray_icon(self._tray_theme)

    def _on_toggle_clicked(self):
        self.overlay.toggle_enabled()

    def _on_settings_destroyed(self):
        self.settings_window = None

    def _settings_changed(self):
        self.overlay.invalidate_render()
        self.update_state(self.overlay.config.enabled)

    def update_state(self, is_enabled: bool):
        self.menu.set_theme(interface_theme(self.overlay.config.ui_theme))
        if self.menu._language != self.overlay.config.language:
            self.menu.set_language(self.overlay.config.language)
        self.toggle_action.setChecked(is_enabled)
        self.toggle_action.setText(f"{self._tr('Enable Animated Cursor')} ({self.overlay.config.toggle_hotkey})")
        self.settings_action.setText(self._tr('Settings & Customization...'))
        self.restore_action.setText(self._tr('Restore Windows Cursor'))
        self.exit_action.setText(self._tr('Exit FluidCursor'))
        if is_enabled:
            self.title_action.setText(self._tr("FluidCursor Active"))
            self.setToolTip(f"{self._tr('FluidCursor Active')} ({self.overlay.config.toggle_hotkey})")
        else:
            self.title_action.setText(self._tr("FluidCursor Paused"))
            self.setToolTip(f"{self._tr('FluidCursor Paused')} ({self.overlay.config.toggle_hotkey})")
        if self.settings_window:
            try:
                self.settings_window.update_enabled_state(is_enabled)
            except Exception:
                pass

    def _open_settings(self):
        if self.settings_launcher is not None:
            self.settings_launcher()
            return
        if self.settings_window is None:
            from ui.settings_window import SettingsWindow
            self.settings_window = SettingsWindow(
                self.overlay.config,
                self._settings_changed,
                self.overlay.cursor_mgr,
                cloner=self.overlay.cloner,
                on_destroy_callback=self._on_settings_destroyed
            )
        self.settings_window.show()
        self.settings_window.activateWindow()
        self.settings_window.raise_()

    def _restore_system_cursor(self):
        # Restoring without pausing immediately re-hides the cursor next tick.
        if self.overlay.config.enabled:
            self.overlay.toggle_enabled()
        else:
            self.overlay.cursor_mgr.restore_system_cursor()
        self.showMessage(
            "FluidCursor",
            self._tr("Windows system cursor has been restored."),
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _exit_app(self):
        self.overlay.cursor_mgr.restore_system_cursor()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context:
            self.overlay.set_tray_menu_open(True)
            QTimer.singleShot(0, self._show_context_menu)
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_settings()

    def _show_context_menu(self):
        if not self.menu.isVisible():
            self.menu.popup(QCursor.pos())
