"""Compact status, minimal tray icon, animal-mode retirement and inertial chain."""
import math, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from core.fun_modes import MODES, FunEngine
from core.chain_physics import SPACING, advance_chain
from ui.tray_icon import create_tray_icon
from ui.settings_window import SettingsWindow
from ui.overlay import CursorOverlay

class CompactChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_retired_fish_migrates_without_erasing_other_preferences(self):
        self.assertNotIn('fish', MODES)
        self.assertEqual(CursorConfig().fun_mode, 'chain')
        with tempfile.TemporaryDirectory() as folder:
            file = str(Path(folder) / 'config.json')
            cfg = CursorConfig(fun_mode='fish', fun_enabled=True, cursor_theme='minimal_dot')
            cfg.save(file)
            new = CursorConfig.load(file)
            self.assertEqual(new.fun_mode, 'chain')
            self.assertTrue(new.fun_enabled)
            self.assertEqual(new.cursor_theme, 'minimal_dot')
    def test_chain_is_pinned_to_tail_but_moves_after_cursor_stops(self):
        points = []
        advance_chain(points, (109, 123), 16, .016)
        self.assertEqual(points[0][:2], [109, 123])
        self.assertAlmostEqual(points[-1][1], 123 + 15 * SPACING)
        advance_chain(points, (170, 123), 16, .016)
        self.assertEqual(points[0][:2], [170, 123])
        self.assertLess(points[-1][0], 160, 'Chain must not snap to cursor')
        before = tuple(points[-1][:2])
        for _ in range(20):
            advance_chain(points, (170, 123), 16, .016)
        self.assertGreater(math.dist(before, points[-1][:2]), 5)
        for first, second in zip(points, points[1:]):
            self.assertAlmostEqual(math.dist(first[:2], second[:2]), SPACING, delta=.01)

    def test_tray_icon_is_white_with_black_outline_and_transparency(self):
        icon = create_tray_icon()
        self.assertFalse(icon.isNull())
        for size in (16, 24, 32, 48):
            img = icon.pixmap(size, size).toImage()
            self.assertEqual(img.pixelColor(size - 1, 0).alpha(), 0)
            pixels = [img.pixelColor(x, y) for y in range(size) for x in range(size)]
            self.assertTrue(any(c.red() > 230 and c.green() > 230 and c.blue() > 230
                                and c.alpha() > 220 for c in pixels))
            black = create_tray_icon('light').pixmap(size, size).toImage()
            opaque_black = [black.pixelColor(x,y) for y in range(size) for x in range(size)
                            if black.pixelColor(x,y).alpha() > 245]
            self.assertTrue(opaque_black)
            self.assertTrue(all(c.red() < 10 and c.green() < 10 and c.blue() < 10
                                for c in opaque_black))
    def test_overlay_anchors_chain_to_rendered_arrow_stem(self):
        cfg = CursorConfig(fun_enabled=True, fun_mode='chain', hide_system_cursor=False)
        manager = MagicMock()
        manager.is_hidden = True
        manager.get_cursor_pos.return_value = (180, 180)
        manager.get_button_states.return_value = (False, False, False)
        manager.get_cursor_type.return_value = 'normal'
        manager.is_key_pressed.return_value = False
        overlay = CursorOverlay(cfg, manager)
        try:
            with patch.object(overlay.fun, 'update', wraps=overlay.fun.update) as update:
                overlay.tick()
                anchor = update.call_args.kwargs['anchor']
            self.assertAlmostEqual(anchor[0], overlay.physics.x + 9 * overlay.physics.scale)
            self.assertAlmostEqual(anchor[1], overlay.physics.y + 22.5 * overlay.physics.scale)
            self.assertEqual(overlay.fun.chain_points[0][:2], list(anchor))
        finally:
            overlay.close()

    def test_status_card_is_compact_and_toggle_still_functions(self):
        cfg = CursorConfig()
        cfg.save = lambda *args, **kwargs: None
        win = SettingsWindow(cfg, lambda: None, None)
        try:
            win.resize(760, 600)
            win.show()
            QTest.qWait(250)
            card = win.basic_lbl_master_title.parentWidget()
            hero = win.basic_interface.findChild(type(win.basic_interface), 'not-found')
            from qfluentwidgets import CardWidget
            hero = win.basic_interface.findChild(CardWidget, 'cursorStatusHero')
            self.assertIsNotNone(hero)
            self.assertLessEqual(hero.height(), 118)
            win.basic_switch_master.setChecked(False)
            self.assertFalse(cfg.enabled)
            self.assertIn('paused', win.basic_lbl_master_title.text().lower())
            win.basic_switch_master.setChecked(True)
            self.assertTrue(cfg.enabled)
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()
