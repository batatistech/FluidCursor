"""Catch regressions in manually drawn Arabic navigation and title controls."""
import os
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from ui.settings_window import SettingsWindow
from qfluentwidgets.components.navigation.navigation_widget import NavigationTreeWidget


class RTLNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_arabic_window_buttons_and_sidebar_do_not_overlap(self):
        for theme in ('dark', 'light'):
            cfg = CursorConfig(language='ar', ui_theme=theme)
            cfg.save = lambda *args, **kwargs: None
            win = SettingsWindow(cfg, lambda: None, None)
            try:
                win.show()
                win.stackedWidget.setCurrentWidget(win.app_interface)
                win._load_page(win.app_interface)  # Populate even if Qt router restored this page already.
                QTest.qWait(650)
                title = win.titleBar
                xs = [getattr(title, n).mapTo(win, QPoint()).x()
                      for n in ('minBtn', 'maxBtn', 'closeBtn')]
                self.assertEqual(xs, [win.width()-138, win.width()-92, win.width()-46])
                self.assertEqual(title.layoutDirection(), Qt.LayoutDirection.LeftToRight)
                self.assertFalse(win.navigationInterface.panel.menuButton.isVisible())
                items = win.navigationInterface.findChildren(NavigationTreeWidget)
                self.assertTrue(items)
                for item in items:
                    self.assertGreaterEqual(item.mapTo(win, QPoint()).y(), 48)
                    self.assertGreater(item.indicatorRect().x(), item.width()-10)
                    self.assertGreater(item.itemWidget.indicatorRect().x(), item.width()-10)
                card = win.a_card_clone
                self.assertGreaterEqual(card.width()-card.iconLabel.geometry().right(), 16)
                self.assertGreaterEqual(card.iconLabel.x()-card.titleLabel.geometry().right(), 12)
                self.assertLess(card.switchButton.geometry().right(), card.titleLabel.x())
            finally:
                win.hide(); win.deleteLater(); self.app.processEvents()

    def test_english_native_control_layout_unmodified(self):
        cfg = CursorConfig(language='en', ui_theme='light')
        cfg.save = lambda *args, **kwargs: None
        win = SettingsWindow(cfg, lambda: None, None)
        try:
            win.show(); QTest.qWait(100)
            self.assertTrue(win.navigationInterface.panel.menuButton.isVisible())
            self.assertEqual(win.navigationInterface.layoutDirection(), Qt.LayoutDirection.LeftToRight)
            self.assertLess(win.navigationInterface.x(), win.width()/2)
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

if __name__ == '__main__':
    unittest.main()
