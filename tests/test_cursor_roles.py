"""Cursor role mapping, native fallbacks, tray theme and configuration regression tests."""
import ctypes
import json
import os
import sys
import tempfile
import unittest
from ctypes import wintypes
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QPalette
from core.config import CursorConfig
from core import win32_cursor as wc
from core.cursor_capture import SystemCursorCloner, user32
from ui.settings_window import SettingsWindow
from ui.tray import CursorTrayIcon
class TestCursorRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
    def test_role_setting_defaults_and_migrates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'config.json')
            with open(path, 'w') as file:
                json.dump({'cursor_size': 41}, file)
            loaded = CursorConfig.load(path)
            self.assertTrue(loaded.match_cursor_roles)
            loaded.match_cursor_roles = False
            loaded.save(path)
            self.assertFalse(CursorConfig.load(path).match_cursor_roles)
    def test_standard_handle_mapping_and_unknown_detection(self):
        manager = wc.Win32CursorManager()
        try:
            with patch.object(wc.user32, 'GetCursorInfo', return_value=1):
                for number, role in wc.OCR_ALL_MAP.items():
                    handle = user32.LoadCursorW(None, ctypes.cast(number,wintypes.LPCWSTR))
                    manager._ci.hCursor = handle
                    self.assertEqual(manager.get_cursor_type(0,0), role)
                    self.assertEqual(manager.active_cursor_handle, int(handle))
                original = user32.LoadCursorW(None, ctypes.cast(wc.OCR_HAND,wintypes.LPCWSTR))
                duplicate = user32.CopyIcon(original)
                try:
                    manager._ci.hCursor = duplicate
                    self.assertEqual(manager.get_cursor_type(0,0), 'custom')
                finally:
                    user32.DestroyIcon(duplicate)
        finally:
            manager.restore_system_cursor()
    def test_unfamiliar_native_cursor_preserves_shape(self):
        # The live app may intentionally blank shared OCR cursors; use a
        # controlled visible cursor to test custom-shape caching independent
        # of the desktop's current cursor visibility state.
        from PyQt6.QtGui import QImage, QColor
        cloner = SystemCursorCloner()
        visible = QImage(32, 32, QImage.Format.Format_RGBA8888)
        visible.fill(QColor(255, 255, 255, 255))
        with patch('core.cursor_capture.capture_hcursor', return_value=(visible, 3, 4)) as capture:
            for handle in (123456, 123457, 123458):
                result = cloner.get_cursor_by_handle(handle)
                self.assertIsNotNone(result)
                self.assertEqual((result[0].width(), result[1:]), (32, (3, 4)))
                self.assertIs(cloner.get_cursor_by_handle(handle), result)
            self.assertEqual(capture.call_count, 3)
        transparent = QImage(16, 16, QImage.Format.Format_RGBA8888)
        transparent.fill(0)
        with patch('core.cursor_capture.capture_hcursor', return_value=(transparent, 0, 0)):
            self.assertIsNone(cloner.get_cursor_by_handle(123459))

    def test_tray_menu_is_explicitly_black(self):
        overlay = MagicMock()
        overlay.config = CursorConfig()
        tray = CursorTrayIcon(overlay)
        try:
            self.assertEqual(tray.menu.palette().color(QPalette.ColorRole.Window).name(), '#09090b')
            self.assertIn('background-color: #09090B', tray.menu.styleSheet())
            self.assertIn('background-color: #25252F', tray.menu.styleSheet())
        finally:
            tray.hide()
            tray.deleteLater()
    def test_appearance_role_switch_changes_config(self):
        config = CursorConfig()
        config.save = lambda *args: None
        callback = MagicMock()
        window = SettingsWindow(config, callback, None)
        try:
            window.show()
            window.stackedWidget.setCurrentWidget(window.app_interface)
            QTest.qWait(600)
            self.assertTrue(window.a_card_roles.isChecked())
            window.a_card_roles.setChecked(False)
            self.assertFalse(config.match_cursor_roles)
            callback.assert_called()
            window.a_card_roles.setChecked(True)
            self.assertTrue(config.match_cursor_roles)
        finally:
            window.hide()
            window.deleteLater()
            self.app.processEvents()

class TestOverlayRoleRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
    def test_known_roles_render_and_visible_customs_avoid_duplicates(self):
        from ui.overlay import CursorOverlay
        from core.theme import CursorRenderer
        native = user32.LoadCursorW(None, ctypes.cast(wc.OCR_HAND,wintypes.LPCWSTR))
        duplicate = user32.CopyIcon(native)
        config = CursorConfig()
        config.hide_system_cursor = True
        config.tilt_enabled = False
        config.ripples_enabled = False
        manager = MagicMock()
        manager.get_cursor_pos.return_value = (300, 240)
        manager.get_button_states.return_value = (False,False,False)
        manager.is_key_pressed.return_value = False
        manager.is_hidden = True
        manager.active_cursor_handle = int(duplicate)
        manager.active_cursor_visible = True
        manager.get_cursor_type.return_value = 'custom'
        overlay = CursorOverlay(config, manager)
        try:
            with patch.object(CursorRenderer, 'draw_cursor') as vector, patch.object(CursorRenderer, 'draw_cloned_cursor') as clone:
                overlay.tick()
                vector.assert_not_called()
                clone.assert_not_called()
                manager.get_cursor_type.return_value = 'hand'
                overlay.tick()
                self.assertEqual(clone.call_count, 1)
                config.match_cursor_roles = False
                overlay.tick()
                self.assertEqual(clone.call_count, 2)
        finally:
            overlay.close()
            user32.DestroyIcon(duplicate)
    def test_vector_mode_switches_text_link_and_resize_shapes(self):
        from ui.overlay import CursorOverlay
        from core.theme import CursorRenderer
        config = CursorConfig()
        config.hide_system_cursor = False
        config.use_system_cursor_clone = False
        config.tilt_enabled = False
        config.ripples_enabled = False
        manager = MagicMock()
        manager.get_cursor_pos.return_value = (200, 150)
        manager.get_button_states.return_value = (False,False,False)
        manager.is_key_pressed.return_value = False
        manager.is_hidden = False
        manager.get_cursor_type.side_effect = ('ibeam','hand','sizewe')
        overlay = CursorOverlay(config, manager)
        try:
            with patch.object(CursorRenderer, 'draw_cursor') as draw:
                for role in ('ibeam','hand','sizewe'):
                    overlay.tick()
                    self.assertEqual(draw.call_args.kwargs['cursor_type'], role)
                config.match_cursor_roles = False
                overlay.tick()
                self.assertEqual(draw.call_args.kwargs['cursor_type'], 'normal')
                self.assertEqual(manager.get_cursor_type.call_count, 3)
        finally:
            overlay.close()

if __name__ == '__main__':
    unittest.main()
