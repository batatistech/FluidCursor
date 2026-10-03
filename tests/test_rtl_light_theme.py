"""Regression coverage for real light mode, Arabic geometry and theme-aware tray."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import isDarkTheme
from core.config import CursorConfig
from core import theme_preference
from ui.settings_window import SettingsWindow
from ui.tray import CursorTrayIcon

class RTLAndThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window(self, language='ar', theme='light'):
        cfg = CursorConfig(language=language, ui_theme=theme)
        cfg.save = lambda *a, **k: None
        return SettingsWindow(cfg, lambda: None, None)
    def test_opaque_consistent_window_background_in_both_themes(self):
        for mode, is_light in (('light', True), ('dark', False)):
            win = self.window('ar', mode)
            try:
                win.show()
                win.stackedWidget.setCurrentWidget(win.app_interface)
                win._load_page(win.app_interface)  # Deferred page may still be queued.
                QTest.qWait(300)
                self.assertFalse(win.isMicaEffectEnabled())
                expected = '#f7f9fc' if is_light else '#202124'
                self.assertEqual(win.backgroundColor.name(), expected)
                image = win.grab().toImage()
                # Navigation and bare page must share a coherent opaque theme.
                for x, y in ((850, 130), (340, 92)):
                    color = image.pixelColor(x, y)
                    self.assertTrue(all(value >= 220 if is_light else value <= 75
                                        for value in (color.red(), color.green(), color.blue())))
                self.assertLess(win.a_card_clone.switchButton.geometry().right(),
                                win.a_card_clone.titleLabel.geometry().left())
            finally:
                win.hide(); win.deleteLater(); self.app.processEvents()

    def test_preferences_validate_without_changing_user_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'config.json')
            CursorConfig(ui_theme='light').save(path)
            self.assertEqual(CursorConfig.load(path).ui_theme, 'light')
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            data['ui_theme'] = 'invalid'
            Path(path).write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(CursorConfig.load(path).ui_theme, 'system')

    def test_windows_app_and_taskbar_themes_are_independent(self):
        with patch.object(theme_preference, 'windows_theme',
                          side_effect=lambda key: 'light' if key == 'AppsUseLightTheme' else 'dark'):
            self.assertEqual(theme_preference.interface_theme('system'), 'light')
            self.assertEqual(theme_preference.system_tray_theme(), 'dark')
            self.assertEqual(theme_preference.interface_theme('dark'), 'dark')

    def test_arabic_light_cards_are_readable_and_really_mirrored(self):
        win = self.window()
        try:
            win.show(); win.stackedWidget.setCurrentWidget(win.sys_interface)
            QTest.qWait(480)
            self.assertFalse(isDarkTheme())
            self.assertIn('background-color: #FFFFFF', win.styleSheet())
            self.assertNotIn('#2B2B2B', win.styleSheet())
            card = win.s_card_hide
            self.assertLess(card.switchButton.geometry().right(), card.titleLabel.geometry().left())
            self.assertEqual(card.titleLabel.alignment() & Qt.AlignmentFlag.AlignLeft,
                             Qt.AlignmentFlag.AlignLeft)
            ink = card.titleLabel.grab().toImage()
            xs = [x for y in range(ink.height()) for x in range(ink.width())
                  if ink.pixelColor(x, y).alpha() > 100 and ink.pixelColor(x, y).red() < 110]
            self.assertTrue(xs)
            self.assertGreater(min(xs), card.titleLabel.width() * 0.4)
            self.assertIn('#1C2A3B', card.titleLabel.styleSheet())
            self.assertEqual(card.switchButton.getOnText(), '')
            self.assertEqual(card.switchButton.getOffText(), '')
            self.assertGreaterEqual(win.titleBar.titleLabel.width(), win.titleBar.titleLabel.fontMetrics().horizontalAdvance(win.windowTitle()))
            self.assertGreaterEqual(card.height(), 90)
            self.assertEqual(win.s_combo_ui_theme.currentText(), 'الوضع الفاتح')
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

    def test_english_dark_styling_still_works(self):
        win = self.window('en', 'dark')
        try:
            self.assertTrue(isDarkTheme())
            self.assertIn('#2B2B2B', win.styleSheet())
            self.assertIn('#F3F6FC', win.s_card_hide.titleLabel.styleSheet())
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

    def test_theme_choice_uses_existing_settings_rebuild(self):
        calls = []
        win = self.window('ar', 'system')
        win.on_config_changed = lambda: calls.append('config')
        win.on_language_changed = lambda: calls.append('rebuild')
        try:
            win.s_combo_ui_theme.setCurrentIndex(2)
            QTest.qWait(50)
            self.assertEqual(win.config.ui_theme, 'light')
            self.assertEqual(calls, ['config', 'rebuild'])
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()
    def test_tray_menu_follows_application_theme_but_icon_follows_taskbar(self):
        config = CursorConfig(language='ar', ui_theme='light')
        overlay = MagicMock(); overlay.config = config
        with patch('ui.tray.system_tray_theme', return_value='dark'):
            tray = CursorTrayIcon(overlay)
            try:
                self.assertEqual(tray._tray_theme, 'dark')
                self.assertEqual(tray.menu._theme, 'light')
                self.assertEqual(tray.menu.palette().color(QPalette.ColorRole.Window).name(), '#ffffff')
                self.assertIn('#FFFFFF', tray.menu.styleSheet())
                config.ui_theme = 'dark'
                tray.update_state(True)
                self.assertEqual(tray.menu._theme, 'dark')
                self.assertIn('#09090B', tray.menu.styleSheet())
            finally:
                tray._theme_timer.stop(); tray.menu.close(); tray.hide(); tray.deleteLater()

    def test_manual_theme_switch_restores_custom_styles(self):
        win = self.window('en', 'dark')
        try:
            win.s_combo_ui_theme.setCurrentIndex(2)
            self.assertFalse(isDarkTheme())
            self.assertIn('background-color: #FFFFFF', win.styleSheet())
            win.s_combo_ui_theme.setCurrentIndex(1)
            self.assertTrue(isDarkTheme())
            self.assertIn('background-color: #2B2B2B', win.styleSheet())
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

    def test_arabic_combobox_arrows_and_fun_labels_are_mirrored(self):
        win = self.window()
        try:
            self.assertEqual(win.s_combo_language.layoutDirection(), Qt.LayoutDirection.RightToLeft)
            self.assertEqual(win.s_combo_hotkey.layoutDirection(), Qt.LayoutDirection.RightToLeft)
            self.assertIn('text-align: right', win.s_combo_language.styleSheet())
            win.resize(960, 720)
            win.show(); win.stackedWidget.setCurrentWidget(win.fun_interface)
            win._load_page(win.fun_interface)  # Build deferred Fun page before inspecting.
            QTest.qWait(650)
            self.app.processEvents()
            chain = win.fun_mode_buttons['chain']
            self.assertGreater(chain.iconLabel.x(), chain.titleLabel.x())
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

    def test_card_accent_edge_mirrors_with_language(self):
        for language, edge in [('ar', 'left'), ('en', 'right')]:
            win = self.window(language, 'light')
            try:
                win.show(); win.stackedWidget.setCurrentWidget(win.sys_interface)
                QTest.qWait(230)
                card = win.s_card_hide
                image = card.grab().toImage()
                y = card.height() // 2
                left = image.pixelColor(3, y)
                right = image.pixelColor(card.width() - 4, y)
                if edge == 'left':
                    self.assertLess(left.green(), right.green())
                else:
                    self.assertLess(right.green(), left.green())
            finally:
                win.hide(); win.deleteLater(); self.app.processEvents()
    def test_manual_theme_switch_restores_custom_styles(self):
        win = self.window('en', 'dark')
        try:
            win.s_combo_ui_theme.setCurrentIndex(2)
            self.assertFalse(isDarkTheme())
            self.assertIn('background-color: #FFFFFF', win.styleSheet())
            win.s_combo_ui_theme.setCurrentIndex(1)
            self.assertTrue(isDarkTheme())
            self.assertIn('background-color: #2B2B2B', win.styleSheet())
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

    def test_arabic_combobox_arrows_and_fun_labels_are_mirrored(self):
        win = self.window()
        try:
            self.assertEqual(win.s_combo_language.layoutDirection(), Qt.LayoutDirection.RightToLeft)
            self.assertEqual(win.s_combo_hotkey.layoutDirection(), Qt.LayoutDirection.RightToLeft)
            self.assertIn('text-align: right', win.s_combo_language.styleSheet())
            win.resize(960, 720)
            win.show(); win.stackedWidget.setCurrentWidget(win.fun_interface)
            win._load_page(win.fun_interface)  # Build deferred Fun page before inspecting.
            QTest.qWait(650)
            self.app.processEvents()
            chain = win.fun_mode_buttons['chain']
            self.assertGreater(chain.iconLabel.x(), chain.titleLabel.x())
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

if __name__ == '__main__':
    unittest.main()
