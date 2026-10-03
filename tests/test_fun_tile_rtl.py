"""Native-layout regressions for Arabic/English Fun mode tiles."""
import os
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from core.config import CursorConfig
from core.i18n import tr
from ui.settings_window import SettingsWindow, FunModeButton

class FunTileRTLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def open_page(self, language, theme):
        config = CursorConfig(language=language, ui_theme=theme, fun_enabled=False)
        config.save = lambda *args, **kwargs: None
        window = SettingsWindow(config, lambda: None, None)
        window.resize(960, 720)
        window.show()
        window.stackedWidget.setCurrentWidget(window.fun_interface)
        window._load_page(window.fun_interface)
        QTest.qWait(650)
        self.app.processEvents()
        return window, config

    def test_grid_order_and_icon_text_spacing_in_both_languages_and_themes(self):
        for language in ('ar', 'en'):
            for theme in ('dark', 'light'):
                with self.subTest(language=language, theme=theme):
                    window, config = self.open_page(language, theme)
                    try:
                        buttons = window.fun_mode_buttons
                        first, second = buttons['tile'], buttons['stardust']
                        self.assertIsInstance(first, FunModeButton)
                        self.assertEqual(len(buttons), 8)
                        self.assertEqual(first.y(), second.y())
                        self.assertEqual(first.x() > second.x(), language == 'ar')
                        for button in buttons.values():
                            icon = button.iconLabel.geometry()
                            title = button.titleLabel.geometry()
                            description = button.descriptionLabel.geometry()
                            self.assertEqual(icon.x() > title.x(), language == 'ar')
                            self.assertGreaterEqual(abs(icon.x() - title.x()), 36)
                            self.assertLessEqual(title.bottom(), description.top())
                            self.assertGreater(description.width(), 160)
                            self.assertGreater(description.bottom(), 0)
                            self.assertLessEqual(description.bottom(), button.height())
                        self.assertEqual(first.titleLabel.text(), tr('FOLLOWER TILE', language))
                        self.assertEqual(first.descriptionLabel.text(), tr('A tiny glassy companion', language))
                    finally:
                        window.hide(); window.deleteLater(); self.app.processEvents()

    def test_arabic_tiles_remain_clickable_and_select_only_one_mode(self):
        window, config = self.open_page('ar', 'dark')
        try:
            choice = window.fun_mode_buttons['stardust']
            QTest.mouseClick(choice, Qt.MouseButton.LeftButton,
                             pos=choice.descriptionLabel.geometry().center())
            self.assertEqual(config.fun_mode, 'stardust')
            self.assertTrue(choice.isChecked())
            self.assertFalse(window.fun_mode_buttons['tile'].isChecked())
        finally:
            window.hide(); window.deleteLater(); self.app.processEvents()

    def test_light_panel_headings_and_status_have_readable_ink(self):
        window, _ = self.open_page('ar', 'light')
        try:
            from PyQt6.QtWidgets import QLabel
            heading = [label for label in window.fun_interface.findChildren(QLabel)
                       if label.text() == tr('Choose your experience', 'ar')]
            self.assertEqual(len(heading), 1)
            self.assertIn('#26334A', heading[0].styleSheet())
            self.assertIn('#117C66', window.fun_status_title.styleSheet())
            self.assertIn('#40516A', window.fun_status_description.styleSheet())
            self.assertIn('#1C2A3B', window.fun_mode_buttons['tile'].titleLabel.styleSheet())
        finally:
            window.hide(); window.deleteLater(); self.app.processEvents()

if __name__ == '__main__':
    unittest.main()
