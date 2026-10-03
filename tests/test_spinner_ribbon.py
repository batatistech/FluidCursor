"""Regression tests for exclusive Spinner, improved Yo-yo, and Silk Ribbon."""
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QImage, QPainter
from core.config import CursorConfig
from core.fun_modes import FunEngine, MODES
from core.ribbon_physics import SPACING, NODES, advance_ribbon
from ui.settings_window import SettingsWindow

class SpinnerRibbonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_spinner_moves_click_boosts_and_coasts(self):
        cfg = CursorConfig(fun_enabled=True, fun_mode='spinner', fun_spinner_speed=85)
        engine = FunEngine()
        with patch('core.fun_modes.time.perf_counter') as clock:
            clock.return_value = 100.0
            engine.update(cfg, 140, 140, 140, 140)
            clock.return_value = 100.016
            engine.update(cfg, 180, 140, 180, 140)
            self.assertGreater(engine.spinner_velocity, 0)
            moving = engine.spinner_velocity
            clock.return_value = 100.032
            engine.update(cfg, 180, 140, 180, 140, clicking=True)
            self.assertGreater(engine.spinner_velocity, moving)
            clicked_angle = engine.spinner_angle
            for i in range(1, 330):
                clock.return_value = 100.032 + i * .016
                engine.update(cfg, 180, 140, 180, 140, clicking=False)
            self.assertLess(abs(engine.spinner_velocity), 2.0)
            self.assertNotEqual(engine.spinner_angle, clicked_angle)
        img = QImage(288, 288, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        try:
            engine.draw(painter, 144, 144, 0, 0, cfg)
        finally:
            painter.end()
        self.assertGreater(sum(img.pixelColor(x,y).alpha()>30
                               for y in range(146,204) for x in range(150,218)), 140)

    def test_yoyo_string_length_and_config_persist(self):
        cfg = CursorConfig(fun_yoyo_length=116,fun_spinner_speed=97,fun_ribbon_flow=22)
        with tempfile.TemporaryDirectory() as folder:
            filename = str(Path(folder)/'test.json')
            cfg.save(filename)
            restored = CursorConfig.load(filename)
        self.assertEqual((restored.fun_yoyo_length,restored.fun_spinner_speed,
                          restored.fun_ribbon_flow),(116,97,22))
        self.assertFalse(restored.fun_enabled)
        restored.fun_enabled = True
        restored.fun_mode = 'yoyo'
        engine = FunEngine()
        with patch('core.fun_modes.time.perf_counter') as clock:
            for frame in range(200):
                clock.return_value = 120 + frame*.016
                engine.update(restored,200,200,200,200,anchor=(209,222))
            distance = math.dist(engine.yoyo[:2],engine.yoyo_anchor)
            self.assertLessEqual(distance,restored.fun_yoyo_length+.001)
            self.assertGreater(distance,40)
            old_speed = engine.yoyo[3]
            clock.return_value = 123.216
            engine.update(restored,200,200,200,200,clicking=True,anchor=(209,222))
            self.assertLess(engine.yoyo[3],old_speed)

    def test_ribbon_constraints_variable_frames_and_pointer_jump(self):
        points=[]
        for index in range(180):
            dt=(.007,.016,.033)[index%3]
            anchor=(160+95*math.sin(index*.09),160+40*math.cos(index*.06))
            advance_ribbon(points,anchor,dt,55,70,click=index%55==0)
            self.assertEqual(points[0][:2],list(anchor))
            self.assertEqual(len(points),NODES)
            self.assertTrue(all(math.isfinite(v) for p in points for v in p))
            for first,second in zip(points,points[1:]):
                self.assertAlmostEqual(math.dist(first[:2],second[:2]),SPACING,delta=.0001)
        # A huge jump reinitializes safely without off-screen physics values.
        advance_ribbon(points,(2000,2000),.016,55,70)
        self.assertEqual(points[0][:2],[2000.,2000.])
        self.assertAlmostEqual(points[-1][1],2000+(NODES-1)*SPACING,delta=.01)
        for _ in range(400):
            advance_ribbon(points,(2000,2000),.016,55,70)
        self.assertAlmostEqual(points[-1][0],2000,delta=2.0)
        self.assertAlmostEqual(points[-1][1],2000+(NODES-1)*SPACING,delta=2.0)

    def test_fun_mode_cards_and_independent_controls(self):
        cfg=CursorConfig(); cfg.save=lambda *args,**kwargs:None
        win=SettingsWindow(cfg,lambda:None,None)
        try:
            win.show(); win.stackedWidget.setCurrentWidget(win.fun_interface)
            QTest.qWait(420)
            self.assertEqual(set(win.fun_mode_buttons),set(MODES))
            win.fun_master.setChecked(True)
            for mode,card in [('yoyo',win.fun_card_yoyo),('ribbon',win.fun_card_ribbon),
                              ('spinner',win.fun_card_spinner)]:
                win.fun_mode_buttons[mode].click()
                self.assertEqual(cfg.fun_mode,mode)
                self.assertFalse(card.isHidden())
                self.assertTrue(card.isEnabled())
            win.fun_slider_spinner.setValue(93)
            win.fun_slider_ribbon.setValue(25)
            win.fun_slider_yoyo.setValue(107)
            self.assertEqual((cfg.fun_spinner_speed,cfg.fun_ribbon_flow,
                              cfg.fun_yoyo_length),(93,25,107))
            self.assertTrue(win.basic_interface.isEnabled() is False)
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

if __name__ == '__main__': unittest.main()
