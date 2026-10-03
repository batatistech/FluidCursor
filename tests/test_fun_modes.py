"""Fun is opt-in, preserves normal preferences and never moves native input."""
import os, sys, unittest, tempfile, math
from unittest.mock import MagicMock, patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QImage, QPainter
from core.config import CursorConfig
from core.fun_modes import FunEngine
from ui.overlay import CursorOverlay
from ui.settings_window import SettingsWindow

class FunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_config_defaults_and_persistence(self):
        cfg = CursorConfig()
        self.assertFalse(cfg.fun_enabled)
        self.assertEqual(cfg.fun_mode, 'chain')
        cfg.fun_enabled = True
        cfg.fun_mode = 'tile'
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'settings.json')
            cfg.save(path)
            loaded = CursorConfig.load(path)
            self.assertTrue(loaded.fun_enabled)
            self.assertEqual(loaded.fun_mode, 'tile')
            self.assertEqual(loaded.cursor_theme, cfg.cursor_theme)
    def test_particles_bounded_and_mode_reset(self):
        cfg = CursorConfig(fun_enabled=True, fun_mode='stardust', fun_particles=100)
        fun = FunEngine()
        with patch('core.fun_modes.time.perf_counter') as clock:
            for i in range(500):
                clock.return_value = 100 + i * .12
                fun.update(cfg, 300 + i * 2, 280, 300 + i * 2, 280)
            self.assertLessEqual(len(fun.particles), 16)
            self.assertEqual(fun.mode, 'stardust')
            cfg.fun_mode = 'tile'
            fun.update(cfg, 100, 200, 100, 200)
            self.assertEqual(len(fun.particles), 0)
            self.assertEqual(fun.mode, 'tile')
            cfg.fun_enabled = False
            fun.update(cfg, 100, 200, 100, 200)
            self.assertIsNone(fun.mode)

    def test_all_modes_draw_without_affecting_input(self):
        cfg = CursorConfig(fun_enabled=True)
        engine = FunEngine()
        image = QImage(192, 192, QImage.Format.Format_ARGB32_Premultiplied)
        for mode in ('chain', 'tile', 'stardust'):
            cfg.fun_mode = mode
            engine.update(cfg, 100, 100, 100, 100)
            image.fill(0)
            painter = QPainter(image)
            try:
                engine.draw(painter, 64, 64, 36, 36, cfg)
            finally:
                painter.end()
            self.assertTrue(any(image.pixelColor(x, y).alpha() for y in range(0, 192) for x in range(0, 192)), mode)
    def test_overlay_forces_fun_physics_without_mutating_normal_settings(self):
        cfg = CursorConfig(fun_enabled=True, fun_mode='stardust', hide_system_cursor=False,
                           use_system_cursor_clone=True, tilt_enabled=True)
        manager = MagicMock()
        manager.is_hidden = True
        manager.get_cursor_pos.return_value = (150, 160)
        manager.get_button_states.return_value = (False, False, False)
        manager.get_cursor_type.return_value = 'normal'
        manager.is_key_pressed.return_value = False
        overlay = CursorOverlay(cfg, manager)
        try:
            with patch.object(overlay.physics, 'update', wraps=overlay.physics.update) as update:
                overlay.tick()
                args = update.call_args.kwargs
                self.assertTrue(args['enable_advanced_physics'])
                self.assertEqual(args['smoothing_type'], 'spring')
                self.assertFalse(args['tilt_enabled'])
                self.assertTrue(args['snap_on_click'])
                self.assertFalse(args['ripples_enabled'])
                self.assertFalse(args['trail_enabled'])
            self.assertTrue(cfg.tilt_enabled)
            self.assertTrue(cfg.use_system_cursor_clone)
            cfg.fun_enabled = False
            overlay.tick()
            self.assertIsNone(overlay.fun.mode)
            self.assertTrue(cfg.tilt_enabled)
        finally:
            overlay.close()

    def test_fun_navigation_and_own_controls(self):
        cfg = CursorConfig()
        cfg.save = lambda *a, **k: None
        win = SettingsWindow(cfg, lambda: None, None)
        try:
            self.assertFalse(hasattr(win, 'fun_master'))
            win.stackedWidget.setCurrentWidget(win.fun_interface)
            QTest.qWait(600)
            self.assertTrue(hasattr(win, 'fun_master'))
            self.assertFalse(win.fun_master.isChecked())
            win.fun_master.setChecked(True)
            self.assertTrue(cfg.fun_enabled)
            win.fun_mode_buttons['tile'].click()
            self.assertEqual(cfg.fun_mode, 'tile')
            self.assertTrue(win.fun_card_chain.isHidden())
            self.assertFalse(win.fun_card_distance.isHidden())
            win.fun_master.setChecked(False)
            self.assertFalse(cfg.fun_enabled)
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

if __name__ == '__main__':
    unittest.main()
# Additional opt-in / compact layout regressions, intentionally isolated from user config.
class FunSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_fun_hides_native_cursor_even_if_normal_preference_is_visible(self):
        cfg = CursorConfig(fun_enabled=True, hide_system_cursor=False)
        manager = MagicMock()
        manager.is_hidden = False
        manager.get_cursor_pos.return_value = (90, 90)
        manager.get_button_states.return_value = (False, False, False)
        manager.get_cursor_type.return_value = 'normal'
        manager.is_key_pressed.return_value = False
        overlay = CursorOverlay(cfg, manager)
        try:
            overlay.tick()
            manager.hide_system_cursor.assert_called_once()
            self.assertFalse(cfg.hide_system_cursor)
            cfg.fun_enabled = False
            manager.is_hidden = True
            overlay.tick()
            manager.restore_system_cursor.assert_called_once()
        finally:
            overlay.close()
    def test_fun_page_fits_compact_window(self):
        cfg = CursorConfig()
        cfg.save = lambda *a, **k: None
        win = SettingsWindow(cfg, lambda: None, None)
        try:
            win.show()
            win.stackedWidget.setCurrentWidget(win.fun_interface)
            QTest.qWait(600)
            scroll = win.fun_interface.layout().itemAt(0).widget()
            for mode in range(3):
                win.fun_mode_buttons[('chain', 'tile', 'stardust')[mode]].click()
                for width in (760, 960):
                    win.resize(width, 600)
                    QTest.qWait(100)
                    self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()
