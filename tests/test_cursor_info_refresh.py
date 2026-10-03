"""Regression: GetCursorInfo can clear cbSize, causing every subsequent lookup to fail."""
import ctypes
import os
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core import win32_cursor as wc
from core.config import CursorConfig
from ui.overlay import CursorOverlay
from core.theme import CursorRenderer


class CursorInfoRefreshTests(unittest.TestCase):
    def setUp(self):
        self.manager = wc.Win32CursorManager()
        self.handles = {role: next(h for h, r in self.manager.cursor_handles.items()
                                   if r == role) for role in ('normal', 'ibeam', 'hand', 'sizewe')}
        self.roles = iter(('normal', 'ibeam', 'hand', 'sizewe'))

    def fake_query(self, address):
        ci = ctypes.cast(address, ctypes.POINTER(wc.CURSORINFO)).contents
        self.assertEqual(ci.cbSize, ctypes.sizeof(wc.CURSORINFO))
        ci.hCursor = self.handles[next(self.roles)]
        ci.flags = 1
        ci.cbSize = 0  # Observed behavior of actual Windows API on this machine.
        return 1
    def test_repeated_queries_keep_the_correct_role(self):
        with patch.object(wc.user32, 'GetCursorInfo', side_effect=self.fake_query):
            for expected in ('normal', 'ibeam', 'hand', 'sizewe'):
                self.assertEqual(self.manager.get_cursor_type(0, 0), expected)
            self.assertTrue(self.manager.active_cursor_visible)
            self.assertEqual(self.manager.active_cursor_handle, self.handles['sizewe'])

    def test_overlay_receives_each_role_on_successive_ticks(self):
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        config = CursorConfig()
        config.hide_system_cursor = False
        config.use_system_cursor_clone = False
        config.tilt_enabled = False
        config.ripples_enabled = False
        self.manager.get_cursor_pos = lambda: (100, 100)
        self.manager.get_button_states = lambda: (False, False, False)
        self.manager.is_key_pressed = lambda _: False
        overlay = CursorOverlay(config, self.manager)
        try:
            with patch.object(wc.user32, 'GetCursorInfo', side_effect=self.fake_query), \
                 patch.object(CursorRenderer, 'draw_cursor') as draw:
                for expected in ('normal', 'ibeam', 'hand', 'sizewe'):
                    overlay.tick()
                    self.assertEqual(draw.call_args.kwargs['cursor_type'], expected)
                self.assertEqual(draw.call_count, 4)
        finally:
            overlay.close()
            app.processEvents()

if __name__ == '__main__':
    unittest.main()
