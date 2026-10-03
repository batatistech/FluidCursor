"""Regression coverage for bilingual settings and monochrome Windows tray icons."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from core.i18n import tr
from core.config import CursorConfig
from ui.tray_icon import create_tray_icon
from ui.settings_window import SettingsWindow

class LocalizationThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_solid_monochrome_icons(self):
        for theme, target in [('dark', 255), ('light', 0)]:
            icon = create_tray_icon(theme)
            for size in (16, 20, 24, 32):
                img = icon.pixmap(size, size).toImage()
                visible = [img.pixelColor(x,y) for y in range(size) for x in range(size)
                           if img.pixelColor(x,y).alpha() >= 245]
                self.assertTrue(visible)
                self.assertTrue(all(abs(getattr(px,ch)()-target) <= 2
                    for px in visible for ch in ('red','green','blue')))

    def test_language_config_and_fallback(self):
        self.assertEqual(tr('Appearance','ar'),'المظهر')
        self.assertEqual(tr('Untranslated message','ar'),'Untranslated message')
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'config.json')
            cfg = CursorConfig(language='ar')
            cfg.save(path)
            self.assertEqual(CursorConfig.load(path).language,'ar')
            content=json.loads(Path(path).read_text(encoding='utf-8'))
            content['language']='invalid'
            Path(path).write_text(json.dumps(content),encoding='utf-8')
            self.assertEqual(CursorConfig.load(path).language,'en')

    def test_arabic_settings_are_rtl_and_lazy_page_translated(self):
        cfg = CursorConfig(language='ar',fun_enabled=False)
        cfg.save=lambda *a,**kw:None
        win=SettingsWindow(cfg,lambda:None,None)
        try:
            win.show();QTest.qWait(150)
            self.assertEqual(win.layoutDirection(),Qt.LayoutDirection.RightToLeft)
            self.assertEqual(win.windowTitle(),tr('FluidCursor Settings','ar'))
            names=[label.text() for label in win.basic_interface.findChildren(QLabel)]
            self.assertIn(tr('Movement smoothness','ar'),names)
            self.assertEqual(win.s_combo_language.itemText(0),tr('English','ar'))
            win.stackedWidget.setCurrentWidget(win.app_interface)
            QTest.qWait(650)
            self.assertTrue(any(label.text()==tr('Primary fill color','ar')
                                for label in win.app_interface.findChildren(QLabel)))
        finally:
            win.hide();win.deleteLater();self.app.processEvents()

    def test_language_switch_requests_rebuild_without_changing_cursor(self):
        cfg=CursorConfig(language='en')
        cfg.save=lambda *a,**kw:None
        calls=[]
        win=SettingsWindow(cfg,lambda:calls.append('config'),None,
                           on_language_changed=lambda:calls.append('rebuild'))
        try:
            win.s_combo_language.setCurrentIndex(1)
            QTest.qWait(60)
            self.assertEqual(cfg.language,'ar')
            self.assertEqual(calls,['config','rebuild'])
        finally:
            win.hide();win.deleteLater();self.app.processEvents()

    def test_theme_change_updates_tray_without_repainting_every_check(self):
        from ui.tray import CursorTrayIcon
        cfg=CursorConfig(language='ar')
        overlay=MagicMock()
        overlay.config=cfg
        with patch('ui.tray.system_tray_theme',return_value='dark') as theme:
            tray=CursorTrayIcon(overlay)
            try:
                self.assertIn('الإعدادات',tray.settings_action.text())
                with patch.object(tray,'setIcon',wraps=tray.setIcon) as redraw:
                    tray.refresh_theme()
                    self.assertEqual(redraw.call_count,0)
                    theme.return_value='light'
                    tray.refresh_theme()
                    self.assertEqual(redraw.call_count,1)
                    self.assertEqual(tray._tray_theme,'light')
            finally:
                tray._theme_timer.stop();tray.menu.close();tray.deleteLater()

if __name__=='__main__':
    unittest.main()
