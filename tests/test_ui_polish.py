"""Regression checks for deferred UI, responsive controls, and idle rendering."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from core.win32_cursor import Win32CursorManager
from ui.settings_window import SettingsWindow
from ui.overlay import CursorOverlay


class TestUIPolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.config = CursorConfig()
        self.config.hide_system_cursor = False
        self.config.save = lambda *args, **kwargs: None

    def test_deferred_pages_build_once_on_navigation(self):
        win = SettingsWindow(self.config, lambda: None, None)
        try:
            self.assertEqual(len(win._deferred_pages), 5)
            self.assertFalse(hasattr(win, "combo_theme"))
            win.stackedWidget.setCurrentWidget(win.app_interface)
            QTest.qWait(550)  # Fluent stacked-widget navigation is animated.
            self.assertTrue(hasattr(win, "combo_theme"))
            self.assertEqual(len(win._deferred_pages), 4)
            first = win.combo_theme
            win.stackedWidget.setCurrentWidget(win.basic_interface)
            QTest.qWait(550)
            win.stackedWidget.setCurrentWidget(win.app_interface)
            QTest.qWait(550)  # Fluent stacked-widget navigation is animated.
            self.assertIs(win.combo_theme, first)
            self.assertEqual(len(win._deferred_pages), 4)
            win.resize(760, 540)
            self.app.processEvents()
            self.assertGreaterEqual(win.a_slider_size.width(), 100)
            self.assertLessEqual(win.a_slider_size.width(), 160)
        finally:
            win.deleteLater()
            self.app.processEvents()

    def test_restore_action_pauses_before_restoring_cursor(self):
        manager = MagicMock()
        changed = MagicMock()
        win = SettingsWindow(self.config, changed, manager)
        try:
            with patch("ui.settings_window.InfoBar.success"):
                win._restore_sys_cursor()
            self.assertFalse(self.config.enabled)
            self.assertFalse(win.basic_switch_master.isChecked())
            manager.restore_system_cursor.assert_called_once()
            changed.assert_called_once()
        finally:
            win.deleteLater()
            self.app.processEvents()

    def test_idle_does_not_repaint_and_changes_invalidate(self):
        manager = Win32CursorManager()
        manager.get_cursor_pos = lambda: (100, 100)
        manager.get_cursor_type = lambda *_: "normal"
        manager.get_button_states = lambda: (False, False, False)
        manager.is_key_pressed = lambda _: False
        self.config.tilt_enabled = False
        self.config.ripples_enabled = False
        overlay = CursorOverlay(self.config, manager)
        try:
            overlay.tick()
            first_count = overlay.frame_count
            for _ in range(25):
                overlay.tick()
            self.assertEqual(overlay.frame_count, first_count)
            self.config.cursor_size += 1
            overlay.tick()
            self.assertEqual(overlay.frame_count, first_count + 1)
            overlay.invalidate_render()
            overlay.tick()
            self.assertEqual(overlay.frame_count, first_count + 2)
        finally:
            overlay.close()


    def test_all_pages_fit_compact_and_normal_windows(self):
        win = SettingsWindow(self.config, lambda: None, None)
        try:
            win.show()
            QTest.qWait(350)
            for width in (960, 760):
                win.resize(width, 600)
                QTest.qWait(200)
                for name, host in (
                    ("Essentials", win.basic_interface),
                    ("Appearance", win.app_interface),
                    ("Motion", win.motion_interface),
                    ("Click", win.click_interface),
                    ("Tilt", win.tilt_interface),
                    ("System", win.sys_interface),
                ):
                    win.stackedWidget.setCurrentWidget(host)
                    QTest.qWait(550)
                    scroll = host if name in ("Essentials", "System") else host.layout().itemAt(0).widget()
                    self.assertEqual(scroll.horizontalScrollBar().maximum(), 0, f"{name} overflow at {width}px")
        finally:
            win.hide()
            win.deleteLater()
            self.app.processEvents()


    def test_tilt_descriptions_do_not_overlap_and_groups_are_colored(self):
        from qfluentwidgets import SettingCard
        win = SettingsWindow(self.config, lambda: None, None)
        try:
            win.show()
            win.stackedWidget.setCurrentWidget(win.tilt_interface)
            QTest.qWait(700)
            cards = win.tilt_interface.findChildren(SettingCard)
            self.assertGreaterEqual(len(cards), 8)
            for card in cards:
                if not card.contentLabel.text() or not card.isVisible():
                    continue
                title = card.titleLabel.geometry()
                description = card.contentLabel.geometry()
                self.assertTrue(card.contentLabel.wordWrap())
                self.assertEqual(card.contentLabel.text(), card._full_description)
                self.assertGreaterEqual(description.top(), title.bottom(), card.titleLabel.text())
                self.assertLess(description.bottom(), card.height(), card.titleLabel.text())
                self.assertGreater(card.contentLabel.width(), 200)
                self.assertTrue(card.contentLabel.toolTip())
            self.assertNotEqual(win.group_tilt_options.accent, win.sys_interface.findChildren(
                __import__('ui.settings_window', fromlist=['SettingCardGroup']).SettingCardGroup)[0].accent)
        finally:
            win.hide()
            win.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
