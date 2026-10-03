"""Regression checks for user-requested shortcut, long chain and physical toys."""
import math, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import MagicMock
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage,QPainter
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from core.hotkeys import hotkey_vk,normalize_hotkey,HOTKEY_CHOICES
from core.chain_physics import advance_chain,SPACING
from core.fun_modes import MODES,FunEngine
from core.theme import CursorRenderer
from ui.settings_window import SettingsWindow
from ui.overlay import CursorOverlay
from ui.tray_icon import create_tray_icon

class FeaturePolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
    def manager(self):
        m=MagicMock();m.get_cursor_pos.return_value=(320,320)
        m.get_button_states.return_value=(False,False,False)
        m.get_cursor_type.return_value='normal'
        m.is_key_pressed.return_value=False;m.is_hidden=False
        return m
    def test_hotkey_mapping_and_migration(self):
        self.assertEqual(normalize_hotkey(' f7 '),'F7')
        self.assertEqual(normalize_hotkey('F1'),'F9')
        self.assertEqual(hotkey_vk('F7'),0x76)
        self.assertEqual(len(HOTKEY_CHOICES),7)
        with tempfile.TemporaryDirectory() as directory:
            file=str(Path(directory)/'config.json')
            CursorConfig(toggle_hotkey='F1',tilt_strength=3.5).save(file)
            loaded=CursorConfig.load(file)
            self.assertEqual(loaded.toggle_hotkey,'F9')
            self.assertEqual(loaded.tilt_strength,1)
    def test_shortcut_only_triggers_on_selected_key_press_edge(self):
        cfg=CursorConfig(toggle_hotkey='F7',hide_system_cursor=False)
        m=self.manager()
        down={}
        m.is_key_pressed.side_effect=lambda key:bool(down.get(key,False))
        overlay=CursorOverlay(cfg,m)
        try:
            down[hotkey_vk('F9')]=True
            overlay.tick();self.assertTrue(cfg.enabled)
            down[hotkey_vk('F9')]=False
            down[hotkey_vk('F7')]=True
            overlay.tick();self.assertFalse(cfg.enabled)
            overlay.tick();self.assertFalse(cfg.enabled)
            down[hotkey_vk('F7')]=False;overlay.tick()
            down[hotkey_vk('F7')]=True;overlay.tick()
            self.assertTrue(cfg.enabled)
        finally:overlay.close()
    def test_settings_shortcut_updates_presentation(self):
        cfg=CursorConfig();cfg.save=lambda *args,**kwargs:None
        win=SettingsWindow(cfg,lambda:None,None)
        try:
            self.assertEqual(win.s_combo_hotkey.currentText(),'F9')
            win.s_combo_hotkey.setCurrentIndex(HOTKEY_CHOICES.index('F7'))
            self.assertEqual(cfg.toggle_hotkey,'F7')
            self.assertIn('F7',win.basic_lbl_master_desc.text())
            self.assertEqual(win.s_combo_hotkey.currentText(),'F7')
        finally:win.hide();win.deleteLater();self.app.processEvents()
    def test_long_chain_constrained_and_canvas_tracks_mode(self):
        cfg=CursorConfig(fun_enabled=True,fun_mode='chain',fun_chain_length=32,
                         fun_chain_swing=80,hide_system_cursor=False)
        m=self.manager();overlay=CursorOverlay(cfg,m)
        try:
            overlay.tick()
            self.assertEqual((overlay.win_w,overlay.win_h),(480,480))
            self.assertEqual(len(overlay.fun.chain_points),32)
            self.assertAlmostEqual(overlay.fun.chain_points[0][1],
                                   overlay.physics.y+22.5*overlay.physics.scale)
            for i in range(1,70):
                m.get_cursor_pos.return_value=(320+int(110*math.sin(i*.11)),320)
                overlay.tick()
                for a,b in zip(overlay.fun.chain_points,overlay.fun.chain_points[1:]):
                    self.assertAlmostEqual(math.dist(a[:2],b[:2]),SPACING,delta=.01)
                    self.assertTrue(all(math.isfinite(v) for v in b))
            cfg.fun_chain_length=12;overlay.tick()
            self.assertEqual(overlay.win_w,288)
        finally:overlay.close()
    def test_physics_liveliness_and_pinned_anchor(self):
        calm=[];lively=[]
        for x in [100,180]+[180]*25:
            advance_chain(calm,(x,100),32,.016,55,0)
            advance_chain(lively,(x,100),32,.016,55,100)
        self.assertEqual(calm[0][:2],[180,100])
        self.assertEqual(lively[0][:2],[180,100])
        self.assertNotEqual(calm[-1][:2],lively[-1][:2])
    def test_fun_toys_do_not_modify_normal_settings(self):
        cfg=CursorConfig(fun_enabled=True,fun_mode='yoyo',tilt_strength=.47)
        engine=FunEngine();engine.update(cfg,150,150,150,150,anchor=(159,172))
        before=tuple(engine.yoyo)
        engine.update(cfg,150,150,150,150,clicking=True,anchor=(159,172))
        self.assertLess(engine.yoyo[3],before[3])
        self.assertEqual(engine.yoyo_anchor,(159,172))
        cfg.fun_mode='ribbon'
        for i in range(20):engine.update(cfg,150+i*5,150+i,150+i*5,150+i)
        self.assertEqual(len(engine.ribbon_points),18)
        self.assertEqual(cfg.tilt_strength,.47)
    def test_tray_icon_and_hand_have_clean_contrast(self):
        icon=create_tray_icon()
        for size in (16,24,32,48):
            image=icon.pixmap(size,size).toImage()
            self.assertEqual(image.pixelColor(size-1,0).alpha(),0)
            solid=[image.pixelColor(x,y) for x in range(size) for y in range(size)]
            self.assertTrue(any(c.red()>235 and c.alpha()>230 for c in solid))
            light=create_tray_icon('light').pixmap(size,size).toImage()
            self.assertTrue(any(light.pixelColor(x,y).red()<25 and light.pixelColor(x,y).alpha()>120
                                for x in range(size) for y in range(size)))
        image=QImage(120,120,QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0);p=QPainter(image)
        try:CursorRenderer.draw_cursor(p,45,38,1,0,'aero_modern',28,
                                       '#FFFFFF','#101010',False,'hand')
        finally:p.end()
        solid=[(x,y) for x in range(120) for y in range(120)
               if image.pixelColor(x,y).alpha()>130]
        self.assertGreater(len(solid),150)
        self.assertLess(max(y for x,y in solid),76)
    def test_status_and_tilt_controls_are_compact(self):
        cfg=CursorConfig();cfg.save=lambda *args,**kwargs:None
        win=SettingsWindow(cfg,lambda:None,None)
        try:
            win.show();QTest.qWait(180)
            from qfluentwidgets import CardWidget
            status=win.basic_interface.findChild(CardWidget,'cursorStatusHero')
            self.assertLessEqual(status.height(),60)
            win.stackedWidget.setCurrentWidget(win.tilt_interface)
            QTest.qWait(620)
            self.assertEqual((win.t_slider_tstr.minimum(),win.t_slider_tstr.maximum()),(0,100))
            win.t_slider_tstr.setValue(0)
            self.assertEqual(cfg.tilt_strength,0)
        finally:win.hide();win.deleteLater();self.app.processEvents()

if __name__=='__main__': unittest.main()
