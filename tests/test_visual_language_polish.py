"""Regression: distinctive tray identity, Arabic menu and non-clipping settings."""
import os
import unittest
from unittest.mock import MagicMock, patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from core.i18n import tr
from ui.tray import CursorTrayIcon
from ui.tray_icon import create_tray_icon
from ui.settings_window import SettingsWindow, BaseSettingCard

class VisualLanguagePolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_motion_mark_is_centred_and_monochrome(self):
        for theme, rgb in [('dark', 255), ('light', 0)]:
            for size in (16, 20, 24, 32):
                image = create_tray_icon(theme).pixmap(size, size).toImage()
                coords = [(x,y) for y in range(size) for x in range(size)
                          if image.pixelColor(x,y).alpha()>40]
                self.assertTrue(coords)
                xs,ys=zip(*coords)
                self.assertAlmostEqual((min(xs)+max(xs))/2,(size-1)/2,delta=1.5)
                self.assertAlmostEqual((min(ys)+max(ys))/2,(size-1)/2,delta=1.5)
                self.assertGreaterEqual(min(xs),2)
                self.assertGreaterEqual(min(ys),2)
                solid=[image.pixelColor(x,y) for x,y in coords
                       if image.pixelColor(x,y).alpha()>=245]
                self.assertTrue(solid)
                self.assertTrue(all(abs(c.red()-rgb)<2 and abs(c.blue()-rgb)<2 for c in solid))
        image=create_tray_icon('dark').pixmap(32,32).toImage()
        # The bead sits toward the upper-right; this must not revert to a pointer.
        self.assertGreater(image.pixelColor(25,10).alpha(),180)
        self.assertEqual(image.pixelColor(7,7).alpha(),0)

    def test_tray_uses_arabic_direction_and_real_checkmark(self):
        cfg=CursorConfig(language='ar')
        overlay=MagicMock();overlay.config=cfg
        with patch('ui.tray.system_tray_theme',return_value='dark'):
            tray=CursorTrayIcon(overlay)
        try:
            self.assertEqual(tray.menu.layoutDirection(),Qt.LayoutDirection.RightToLeft)
            self.assertGreaterEqual(tray.menu.width(),290)
            button=tray.menu._action_buttons[tray.toggle_action]
            self.assertNotIn(chr(0x2713),button.text())
            self.assertFalse(button.icon().isNull())
            pixels = button.icon().pixmap(14,14).toImage()
            self.assertTrue(any(pixels.pixelColor(x,y).alpha()>50
                                for y in range(14) for x in range(14)))
            self.assertNotIn('[x]',button.text())
            cfg.language='en';tray.update_state(True)
            self.assertEqual(tray.menu.layoutDirection(),Qt.LayoutDirection.LeftToRight)
        finally:
            tray._theme_timer.stop();tray.menu.hide();tray.deleteLater()

    def test_polished_localization_uses_concise_terms(self):
        for term in ('FluidCursor Active','Tilt angle multiplier','FIDGET SPINNER',
                     'Performance & memory','Settings & Customization...'):
            translated=tr(term,'ar')
            self.assertNotEqual(term,translated)
            self.assertTrue(any('\u0600'<=c<='\u06ff' for c in translated))
    def test_arabic_cards_fit_and_wrap_on_every_page(self):
        cfg=CursorConfig(language='ar',fun_enabled=False)
        cfg.save=lambda *a,**k:None
        win=SettingsWindow(cfg,lambda:None,None)
        try:
            win.resize(760,700);win.show()
            for name in ('basic','app','motion','click','tilt','fun','sys'):
                host=getattr(win,name+'_interface')
                win.stackedWidget.setCurrentWidget(host)
                win._load_page(host)
                QTest.qWait(700)
                cards=[c for c in host.findChildren(BaseSettingCard) if c.isVisible()]
                self.assertTrue(cards,name)
                for card in cards:
                    self.assertTrue(card.titleLabel.wordWrap(),card.titleLabel.text())
                    self.assertEqual(card.contentLabel.text(),card._full_description)
                    if card.contentLabel.text():
                        self.assertGreaterEqual(card.contentLabel.y(),
                           card.titleLabel.geometry().bottom(),card.titleLabel.text())
                        self.assertLess(card.contentLabel.geometry().bottom(),
                           card.height(),card.titleLabel.text())
                scroll=host if name in ('basic','sys') else host.layout().itemAt(0).widget()
                self.assertEqual(scroll.horizontalScrollBar().maximum(),0,name)
        finally:
            win.hide();win.deleteLater();self.app.processEvents()

if __name__=='__main__':unittest.main()
