"""Color-isolation and real ghost-rendering regressions."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from core.physics import CursorPhysics
from core.theme import CursorRenderer
from ui.settings_window import SettingsWindow

class PaletteAndGhostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def render(self, theme, role, fill, border):
        image = QImage(96, 96, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        CursorRenderer.draw_cursor(painter, 36, 36, 1, 0, theme, 28,
                                   fill, border, False, role)
        painter.end()
        return bytes(image.constBits().asstring(image.sizeInBytes()))
    def test_only_custom_arrow_obeys_palette(self):
        for theme in ('aero_modern', 'neon_glow', 'macos_fluid',
                      'cyber_arrow', 'minimal_dot'):
            self.assertEqual(self.render(theme, 'normal', '#ff0000', '#00ff00'),
                             self.render(theme, 'normal', '#0000ff', '#ffff00'), theme)
        self.assertNotEqual(self.render('custom_arrow', 'normal', '#ff0000', '#00ff00'),
                            self.render('custom_arrow', 'normal', '#0000ff', '#ffff00'))
        for role in ('hand', 'ibeam', 'sizewe', 'sizenwse', 'appstarting'):
            self.assertEqual(self.render('custom_arrow', role, '#ff0000', '#00ff00'),
                             self.render('custom_arrow', role, '#0000ff', '#ffff00'), role)

    def test_palette_controls_follow_selected_theme_and_clone(self):
        config = CursorConfig(cursor_theme='aero_modern', use_system_cursor_clone=False)
        config.save = lambda *args, **kwargs: None
        window = SettingsWindow(config, lambda: None, None)
        try:
            window.show()
            window.stackedWidget.setCurrentWidget(window.app_interface)
            QTest.qWait(550)
            self.assertFalse(window.card_prim.isEnabled())
            window.combo_theme.setCurrentIndex(5)
            self.assertTrue(window.card_prim.isEnabled())
            self.assertTrue(window.card_border.isEnabled())
            window.a_card_clone.setChecked(True)
            self.assertFalse(window.card_prim.isEnabled())
            window.a_card_clone.setChecked(False)
            self.assertTrue(window.card_prim.isEnabled())
            window.combo_theme.setCurrentIndex(2)
            self.assertFalse(window.card_border.isEnabled())
        finally:
            window.hide(); window.deleteLater(); self.app.processEvents()
    def test_trail_samples_are_bounded_and_expire(self):
        clock = [0.0]
        with patch('core.physics.time.perf_counter', side_effect=lambda: clock[0]):
            physics = CursorPhysics(100, 100)
            for i in range(1, 36):
                clock[0] = i * .007
                physics.update(100 + i * 15, 100, False, False, False,
                               tilt_enabled=False, trail_enabled=True)
            self.assertGreater(len(physics.trail_points), 1)
            self.assertLessEqual(len(physics.trail_points), 9)
            for i in range(36, 130):
                clock[0] = i * .007
                physics.update(625, 100, False, False, False,
                               tilt_enabled=False, trail_enabled=True)
            self.assertEqual(physics.trail_points, [])
            clock[0] += .007
            physics.update(650, 100, False, False, False,
                           tilt_enabled=False, trail_enabled=False)
            self.assertEqual(physics.trail_points, [])

    def test_ghosts_are_drawn_and_fade(self):
        image = QImage(160, 96, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        count = CursorRenderer.draw_motion_ghosts(painter,
            [(25, 30, .1), (100, 30, .8)], 0, 0, 'aero_modern', 28,
            '#ff0000', '#00ff00')
        painter.end()
        alpha = lambda x: max(image.pixelColor(xx, yy).alpha()
            for xx in range(x, x + 24) for yy in range(30, 65))
        self.assertEqual(count, 2)
        self.assertGreater(alpha(25), alpha(100))
        self.assertGreater(alpha(100), 0)

if __name__ == '__main__':
    unittest.main()
