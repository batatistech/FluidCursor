"""Fun owns its motion and UI; normal preferences stay locked and intact."""
import os, sys, unittest, tempfile
from unittest.mock import MagicMock, patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from core.fun_modes import FunEngine, smoothness_physics, MODES
from ui.settings_window import SettingsWindow
from ui.overlay import CursorOverlay

class FunPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_new_smoothness_persists_without_changing_normal_motion(self):
        cfg = CursorConfig(responsiveness=.31, spring_stiffness=340)
        with tempfile.TemporaryDirectory() as folder:
            file = os.path.join(folder, 'fun.json')
            cfg.fun_smoothness = 88
            cfg.save(file)
            loaded = CursorConfig.load(file)
            self.assertEqual(loaded.fun_smoothness, 88)
            self.assertEqual(loaded.responsiveness, .31)
            self.assertEqual(loaded.spring_stiffness, 340)
        self.assertEqual(CursorConfig().fun_smoothness, 55)
        self.assertGreater(smoothness_physics(0)[0], smoothness_physics(100)[0])
        self.assertGreater(smoothness_physics(100)[1], smoothness_physics(0)[1])
        self.assertEqual(smoothness_physics(-5), smoothness_physics(0))
        self.assertEqual(smoothness_physics(120), smoothness_physics(100))
    def test_fun_exclusively_locks_pages_and_unlocks_them(self):
        cfg = CursorConfig()
        cfg.save = lambda *a, **k: None
        win = SettingsWindow(cfg, lambda: None, None)
        try:
            win.stackedWidget.setCurrentWidget(win.fun_interface)
            QTest.qWait(650)
            self.app.processEvents()
            self.assertTrue(win.fun_card_smooth.isEnabled() is False)
            self.assertEqual(len(win.fun_mode_buttons), len(MODES))
            original = (cfg.cursor_theme, cfg.responsiveness, cfg.tilt_mode)
            win.fun_master.setChecked(True)
            for page in (win.basic_interface, win.app_interface, win.motion_interface,
                         win.click_interface, win.tilt_interface):
                self.assertFalse(page.isEnabled(), page.objectName())
                self.assertFalse(win.navigationInterface.widget(page.objectName()).isEnabled())
            self.assertTrue(win.navigationInterface.widget(win.sys_interface.objectName()).isEnabled())
            self.assertFalse(win.s_card_hide.isEnabled())
            self.assertTrue(win.fun_card_smooth.isEnabled())
            self.assertIn('locked', win.fun_status_description.text().lower())
            win.fun_slider_smooth.setValue(81)
            self.assertEqual(cfg.fun_smoothness, 81)
            win.fun_mode_buttons['tile'].click()
            self.assertTrue(win.fun_mode_buttons['tile'].isChecked())
            self.assertEqual(cfg.fun_mode, 'tile')
            self.assertEqual(original, (cfg.cursor_theme, cfg.responsiveness, cfg.tilt_mode))
            win.fun_master.setChecked(False)
            self.assertTrue(win.basic_interface.isEnabled())
            self.assertTrue(win.s_card_hide.isEnabled())
            self.assertFalse(win.fun_card_smooth.isEnabled())
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()
    def test_fun_physics_slider_controls_active_spring_only(self):
        cfg = CursorConfig(fun_enabled=True, fun_mode='chain', fun_smoothness=93,
                           spring_stiffness=321, spring_damping=19, tilt_enabled=True)
        mgr = MagicMock()
        mgr.is_hidden = True
        mgr.get_cursor_pos.return_value = (240, 280)
        mgr.get_button_states.return_value = (False, False, False)
        mgr.get_cursor_type.return_value = 'normal'
        mgr.is_key_pressed.return_value = False
        overlay = CursorOverlay(cfg, mgr)
        try:
            with patch.object(overlay.physics, 'update', wraps=overlay.physics.update) as update:
                overlay.tick()
                args = update.call_args.kwargs
                self.assertEqual((args['spring_stiffness'], args['spring_damping']), smoothness_physics(93))
                self.assertFalse(args['tilt_enabled'])
                self.assertTrue(args['snap_on_click'])
                cfg.fun_enabled = False
                overlay.tick()
                args = update.call_args.kwargs
                self.assertEqual(args['spring_stiffness'], 321)
                self.assertEqual(args['spring_damping'], 19)
            self.assertTrue(cfg.tilt_enabled)
        finally:
            overlay.close()

    def test_enabled_at_launch_redirects_to_fun_with_recovery_available(self):
        cfg = CursorConfig(fun_enabled=True)
        cfg.save = lambda *a, **k: None
        win = SettingsWindow(cfg, lambda: None, None)
        try:
            QTest.qWait(650)
            self.assertIs(win.stackedWidget.currentWidget(), win.fun_interface)
            self.assertFalse(win.basic_interface.isEnabled())
            self.assertTrue(win.sys_interface.isEnabled())
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()
