"""Regression tests for cursor proportions, resize orientation and the tray hot path."""
import os, sys, unittest, time
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPainter, QColor
from core.config import CursorConfig
from core.cursor_capture import SystemCursorCloner
from core.theme import CursorRenderer
from ui.overlay import CursorOverlay

class CursorPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def ink_rows(image):
        return [y for y in range(image.height())
                if any(image.pixelColor(x, y).alpha() > 15 for x in range(image.width()))]

    def test_cloned_beam_matches_pointer_visible_size_and_preserves_hotspot(self):
        clone=SystemCursorCloner()
        arrow,_,_=clone.get_cloned_cursor('normal')
        beam,hx,hy=clone.get_cloned_cursor('ibeam')
        arrow_ink=self.ink_rows(arrow);beam_ink=self.ink_rows(beam)
        self.assertGreater(len(arrow_ink),0)
        self.assertLessEqual(len(beam_ink),len(arrow_ink)*1.35)
        self.assertTrue(0 <= hx < beam.width() and 0 <= hy < beam.height())

    def test_diagonal_resize_orientations(self):
        for role, sign in [('sizenwse',1),('sizenesw',-1)]:
            image=QImage(96,96,QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(0)
            p=QPainter(image)
            try:
                CursorRenderer.draw_cursor(p,48,48,1,0,'aero_modern',28,
                    '#FFFFFF','#15151A',False,role)
            finally: p.end()
            # Check correlation of diagonal pixels around the hotspot.
            points=[(x-48,y-48) for y in range(96) for x in range(96)
                    if image.pixelColor(x,y).alpha()>180]
            self.assertGreater(len(points),30)
            covariance=sum(x*y for x,y in points)
            self.assertGreater(covariance*sign,100,role)

    def test_unknown_native_cursor_never_decodes_inside_tick(self):
        config=CursorConfig(hide_system_cursor=True,tilt_enabled=False,
                            ripples_enabled=False,use_system_cursor_clone=True)
        manager=MagicMock()
        manager.get_cursor_pos.return_value=(300,200)
        manager.get_button_states.return_value=(False,False,False)
        manager.is_key_pressed.return_value=False
        manager.get_cursor_type.return_value='custom'
        manager.active_cursor_handle=0xBEEF
        manager.active_cursor_visible=True
        manager.is_hidden=True
        overlay=CursorOverlay(config,manager)
        try:
            with patch.object(overlay.cloner,'get_cursor_by_handle',side_effect=AssertionError('blocking capture')):
                for i in range(12): overlay.tick()
                manager.active_cursor_visible=False
                for i in range(12): overlay.tick()
        finally: overlay.close()

    def test_cloned_beam_draws_with_subpixel_hotspot(self):
        clone=SystemCursorCloner()
        beam,hx,hy=clone.get_cloned_cursor('ibeam')
        canvas=QImage(128,128,QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(0)
        painter=QPainter(canvas)
        try:
            CursorRenderer.draw_cloned_cursor(painter,64.0,64.0,1.0,0.0,
                                              beam,hx,hy,False)
        finally: painter.end()
        ink=self.ink_rows(canvas)
        self.assertGreater(len(ink),0)
        self.assertLessEqual(len(ink),30)

    def test_tray_menu_suspends_reassertion_without_stopping_cursor(self):
        from ui.tray import CursorTrayIcon
        config=CursorConfig(hide_system_cursor=False,enabled=False)
        manager=MagicMock();manager.get_cursor_pos.return_value=(10,10)
        manager.is_key_pressed.return_value=False
        overlay=CursorOverlay(config,manager)
        tray=CursorTrayIcon(overlay)
        try:
            overlay._next_topmost_check=0
            tray.menu.aboutToShow.emit()
            self.assertTrue(overlay.tray_menu_open)
            overlay._maintain_topmost()
            self.assertEqual(overlay._next_topmost_check,0)
            tray.menu.aboutToHide.emit()
            self.assertFalse(overlay.tray_menu_open)
            self.assertGreater(overlay._next_topmost_check,time.monotonic())
        finally:
            tray.hide();tray.deleteLater();overlay.close()
