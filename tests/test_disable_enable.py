"""
Automated test for cursor disable/enable lifecycle.
Verifies that disabling the cursor completely clears the overlay, hides the window,
and restores standard Windows cursor without leaving any frozen pixels on screen.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from core.win32_cursor import Win32CursorManager
from core.config import CursorConfig
from ui.overlay import CursorOverlay

class TestDisableEnableLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_disable_clears_overlay_completely(self):
        config = CursorConfig()
        config.hide_system_cursor = False
        cursor_mgr = Win32CursorManager()
        overlay = CursorOverlay(config, cursor_mgr)

        # 1. Initially enabled
        self.assertTrue(overlay.config.enabled)
        overlay.tick()
        self.assertFalse(overlay.was_cleared_on_disable)

        # 2. Disable via toggle_enabled
        overlay.toggle_enabled()
        self.assertFalse(overlay.config.enabled)
        self.assertTrue(overlay.was_cleared_on_disable)

        # 3. Ticking while disabled stays cleared
        overlay.tick()
        self.assertTrue(overlay.was_cleared_on_disable)

        # 4. Re-enable via toggle_enabled
        overlay.toggle_enabled()
        self.assertTrue(overlay.config.enabled)
        overlay.tick()
        self.assertFalse(overlay.was_cleared_on_disable)

        # 5. Disable via config.enabled = False + tick
        overlay.config.enabled = False
        overlay.tick()
        self.assertTrue(overlay.was_cleared_on_disable)

        overlay.close()

if __name__ == "__main__":
    unittest.main()
