"""
Unit tests for RAM Optimization Mode, Warning Dialog, and Window Lifecycle in FluidCursor.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from core.config import CursorConfig
from ui.settings_window import SettingsWindow
from ui.tray import CursorTrayIcon

app = QApplication.instance() or QApplication(sys.argv)

class TestRAMOptimization(unittest.TestCase):

    def setUp(self):
        self.config = CursorConfig()
        self.config.save = lambda *args, **kwargs: None

    def test_default_ram_optimization_is_enabled(self):
        """Verify that RAM optimization is enabled by default."""
        self.assertTrue(self.config.ram_optimization_mode)

    def test_ui_elements_exist(self):
        """Verify that RAM optimization switch and Flush RAM button exist in SettingsWindow."""
        win = SettingsWindow(self.config, lambda: None, None)
        self.assertTrue(hasattr(win, "s_card_ram"))
        self.assertTrue(hasattr(win, "card_flush_ram"))
        self.assertTrue(win.s_card_ram.isChecked())
        win.deleteLater()

    def test_toggle_off_warning_cancelled(self):
        """When user cancels the warning dialog, RAM optimization must remain enabled."""
        win = SettingsWindow(self.config, lambda: None, None)
        self.assertTrue(self.config.ram_optimization_mode)

        # Mock MessageBox.exec to simulate clicking "Keep Enabled" (return False)
        with patch("ui.settings_window.MessageBox") as MockMsgBox:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = False
            MockMsgBox.return_value = mock_dialog

            # Trigger toggle off
            win._on_ram_opt_toggle_requested(False)

            # Verification: should stay True
            self.assertTrue(self.config.ram_optimization_mode)
            self.assertTrue(win.s_card_ram.isChecked())
            MockMsgBox.assert_called_once()

        win.deleteLater()

    def test_toggle_off_warning_confirmed(self):
        """When user confirms the warning dialog, RAM optimization is disabled."""
        win = SettingsWindow(self.config, lambda: None, None)
        self.assertTrue(self.config.ram_optimization_mode)

        # Mock MessageBox.exec to simulate clicking "Disable" (return True)
        with patch("ui.settings_window.MessageBox") as MockMsgBox:
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = True
            MockMsgBox.return_value = mock_dialog

            # Trigger toggle off
            win._on_ram_opt_toggle_requested(False)

            # Verification: should become False
            self.assertFalse(self.config.ram_optimization_mode)
            MockMsgBox.assert_called_once()

        win.deleteLater()

    def test_close_destroys_when_ram_optimization_enabled(self):
        """When RAM optimization is enabled, closeEvent destroys window and invokes callback."""
        destroyed_called = False
        def on_destroyed():
            nonlocal destroyed_called
            destroyed_called = True

        self.config.ram_optimization_mode = True
        win = SettingsWindow(self.config, lambda: None, None, on_destroy_callback=on_destroyed)
        
        mock_event = MagicMock()
        win.closeEvent(mock_event)
        
        self.assertTrue(destroyed_called)
        mock_event.ignore.assert_called_once()

    def test_close_retains_when_ram_optimization_disabled(self):
        """When RAM optimization is disabled, closeEvent merely hides the window without destroying."""
        destroyed_called = False
        def on_destroyed():
            nonlocal destroyed_called
            destroyed_called = True

        self.config.ram_optimization_mode = False
        win = SettingsWindow(self.config, lambda: None, None, on_destroy_callback=on_destroyed)
        
        mock_event = MagicMock()
        win.closeEvent(mock_event)
        
        self.assertFalse(destroyed_called)
        win.deleteLater()

    def test_tray_lazy_recreation(self):
        """Verify CursorTrayIcon recreates settings window on demand if it was destroyed."""
        mock_overlay = MagicMock()
        mock_overlay.config = self.config
        mock_overlay.cursor_mgr = None
        mock_overlay.cloner = None

        tray = CursorTrayIcon(mock_overlay, None)
        self.assertIsNone(tray.settings_window)

        with patch("ui.settings_window.SettingsWindow.show") as mock_show:
            tray._open_settings()
            self.assertIsNotNone(tray.settings_window)
            mock_show.assert_called_once()
            tray.settings_window.deleteLater()

if __name__ == "__main__":
    unittest.main()
