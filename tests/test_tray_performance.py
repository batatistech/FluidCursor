"""Regressions for asynchronous tray popup, hand rotation and adaptive polling."""
import os,sys,unittest,time
from PyQt6.QtCore import QTimer
from unittest.mock import MagicMock
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QImage,QPainter
from core.config import CursorConfig
from core.theme import CursorRenderer
from ui.overlay import CursorOverlay
from ui.tray import CursorTrayIcon
class TrayPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def make_overlay(self):
        config=CursorConfig(hide_system_cursor=False,tilt_enabled=False,ripples_enabled=False)
        mgr=MagicMock();mgr.get_cursor_pos.return_value=(120,140)
        mgr.get_button_states.return_value=(False,False,False)
        mgr.is_key_pressed.return_value=False;mgr.get_cursor_type.return_value='normal'
        mgr.is_hidden=False
        return CursorOverlay(config,mgr),mgr
    def test_idle_polling_and_menu_cadence(self):
        overlay,mgr=self.make_overlay()
        try:
            for _ in range(20):overlay.tick()
            self.assertEqual(overlay.timer.interval(),30)
            mgr.get_cursor_pos.return_value=(180,140);overlay.tick()
            self.assertEqual(overlay.timer.interval(),7)
            overlay.set_tray_menu_open(True)
            self.assertEqual(overlay.timer.interval(),7)
            for i in range(20):
                mgr.get_cursor_pos.return_value=(180+i*3, 140)
                overlay.tick()
                self.assertEqual(overlay.timer.interval(),7)
            overlay.set_tray_menu_open(False)
            self.assertEqual(overlay.timer.interval(),7)
        finally:overlay.close()
    def test_context_signal_opens_without_native_context_menu(self):
        overlay,_=self.make_overlay();tray=CursorTrayIcon(overlay)
        try:
            self.assertIsNone(tray.contextMenu())
            tray.activated.emit(tray.ActivationReason.Context)
            self.assertTrue(overlay.tray_menu_open)
            QTest.qWait(80)
            self.assertTrue(tray.menu.isVisible())
            self.assertEqual(overlay.timer.interval(),7)
            tray.menu.hide();self.app.processEvents()
            self.assertFalse(overlay.tray_menu_open)
        finally:
            tray.menu.hide();tray.hide();tray.deleteLater();overlay.close()
    def test_hand_reorients_for_downward_heading(self):
        def render(tilt):
            img=QImage(180,180,QImage.Format.Format_ARGB32_Premultiplied);img.fill(0)
            painter=QPainter(img)
            try:CursorRenderer.draw_cursor(painter,90,90,1,tilt,'aero_modern',28,
                       '#FFFFFF','#1E293B',False,'hand')
            finally:painter.end()
            pts=[(x,y) for y in range(180) for x in range(180)
                 if img.pixelColor(x,y).alpha()>90]
            return sum(y for x,y in pts)/len(pts)
        # Downward steering rotates the hand about its fixed fingertip.
        self.assertLess(render(-155),render(0)-5)
    def test_warmed_popup_does_not_block_cursor_event_loop(self):
        overlay,_=self.make_overlay();tray=CursorTrayIcon(overlay)
        pulse=QTimer(); pulse.setInterval(7)
        start=time.perf_counter(); previous=[start]; gaps=[]
        def observe():
            now=time.perf_counter()
            gaps.append((now-start,(now-previous[0])*1000))
            previous[0]=now
        pulse.timeout.connect(observe)
        try:
            tray.menu.prewarm()
            start=time.perf_counter(); previous[0]=start
            pulse.start()
            QTimer.singleShot(80,lambda:tray.activated.emit(tray.ActivationReason.Context))
            QTimer.singleShot(300,tray.menu.hide)
            QTest.qWait(380)
            during=[gap for t,gap in gaps if .08<=t<=.3]
            self.assertGreater(len(during),15)
            self.assertLess(max(during),90,'Tray popup blocked the cursor loop')
        finally:
            pulse.stop();tray.menu.hide();tray.hide();tray.deleteLater();overlay.close()

if __name__=='__main__':unittest.main()