"""Prevent the tray check glyph from loading Qt's huge font fallback cache."""
import os
import unittest
from unittest.mock import MagicMock, patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from core.config import CursorConfig
from ui.tray import CursorTrayIcon


def visible_pixels(icon):
    image = icon.pixmap(14, 14).toImage()
    return [image.pixelColor(x, y) for y in range(14) for x in range(14)
            if image.pixelColor(x, y).alpha() > 70]


class TrayMemoryRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_vector_check_is_visible_and_never_a_text_glyph(self):
        cfg = CursorConfig(language='en', ui_theme='dark', enabled=True)
        overlay = MagicMock(); overlay.config = cfg
        with patch('ui.tray.system_tray_theme', return_value='dark'):
            tray = CursorTrayIcon(overlay)
        try:
            action = tray.toggle_action
            button = tray.menu._action_buttons[action]
            self.assertNotIn(chr(0x2713), button.text())
            self.assertNotIn('[x]', button.text())
            self.assertIn('Enable Animated Cursor', button.text())
            self.assertGreater(len(visible_pixels(button.icon())), 4)
            action.setChecked(False)
            self.assertEqual(visible_pixels(button.icon()), [])
            action.setChecked(True)
            self.assertGreater(len(visible_pixels(button.icon())), 4)
        finally:
            tray._theme_timer.stop()
            tray.menu.hide(); tray.deleteLater(); self.app.processEvents()

    def test_icon_respects_light_theme_and_arabic_without_font_marker(self):
        cfg = CursorConfig(language='ar', ui_theme='dark', enabled=True)
        overlay = MagicMock(); overlay.config = cfg
        with patch('ui.tray.system_tray_theme', return_value='dark'):
            tray = CursorTrayIcon(overlay)
        try:
            button = tray.menu._action_buttons[tray.toggle_action]
            self.assertNotIn(chr(0x2713), button.text())
            self.assertTrue(visible_pixels(button.icon()))
            tray.menu.set_theme('light')
            light = visible_pixels(button.icon())
            self.assertTrue(light)
            self.assertTrue(all(max(c.red(),c.green(),c.blue()) < 110 for c in light))
            tray.menu.set_theme('dark')
            dark = visible_pixels(button.icon())
            self.assertTrue(dark)
            self.assertTrue(all(min(c.red(),c.green(),c.blue()) > 180 for c in dark))
            self.assertEqual(tray.menu._language, 'ar')
        finally:
            tray._theme_timer.stop()
            tray.menu.hide(); tray.deleteLater(); self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
