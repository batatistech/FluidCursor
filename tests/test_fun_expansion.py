"""Regression coverage for five independent Fun experiences and the warmed tray."""
import os,sys,unittest,tempfile,math
from unittest.mock import patch,MagicMock
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage,QPainter
from PyQt6.QtTest import QTest
from core.config import CursorConfig
from core.fun_modes import FunEngine,MODES
from ui.settings_window import SettingsWindow


class FunExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_seven_modes_render_and_chain_stays_bounded(self):
        cfg=CursorConfig(fun_enabled=True,fun_particles=70)
        engine=FunEngine()
        for mode in MODES:
            cfg.fun_mode=mode
            for i in range(24): engine.update(cfg,320,320,320,320)
            image=QImage(288,288,QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(0); p=QPainter(image)
            try: engine.draw(p,144,144,176,176,cfg)
            finally: p.end()
            self.assertGreater(sum(image.pixelColor(x,y).alpha()>0 for y in range(60,218)
                                   for x in range(60,218)),40,mode)
            if mode=='chain':
                self.assertEqual(len(engine.chain_points),cfg.fun_chain_length)
                for a,b in zip(engine.chain_points,engine.chain_points[1:]):
                    self.assertAlmostEqual(math.hypot(a[0]-b[0],a[1]-b[1]),6.5,delta=.25)
    def test_sparks_vary_in_size_and_expire(self):
        cfg=CursorConfig(fun_enabled=True,fun_mode='stardust',fun_particles=90)
        engine=FunEngine()
        with patch('core.fun_modes.time.perf_counter') as clock:
            for i in range(35):
                clock.return_value=100+i*.12
                engine.update(cfg,200+i*8,240+i*2,200+i*8,240+i*2)
            self.assertGreaterEqual(len(engine.particles),5)
            self.assertLessEqual(len(engine.particles),16)
            self.assertGreater(len({round(p[4],1) for p in engine.particles}),2)
            initial=tuple(cfg.__dict__.items())
            for i in range(36,110):
                clock.return_value=100+i*.12
                engine.update(cfg,500,500,500,500)
            self.assertEqual(len(engine.particles),0)
            self.assertEqual(initial,tuple(cfg.__dict__.items()))

    def test_chain_size_and_orbit_count_persist(self):
        cfg=CursorConfig(fun_chain_length=16,fun_orbit_count=6)
        with tempfile.TemporaryDirectory() as folder:
            path=os.path.join(folder,'fun.json');cfg.save(path)
            copy=CursorConfig.load(path)
            self.assertEqual((copy.fun_chain_length,copy.fun_orbit_count),(16,6))
            self.assertFalse(copy.fun_enabled)
        engine=FunEngine();cfg.fun_enabled=True;cfg.fun_mode='chain'
        engine.update(cfg,100,200,100,200)
        self.assertEqual(len(engine.chain_points),16)
        cfg.fun_mode='orbit';engine.update(cfg,100,200,100,200)
        self.assertEqual(engine.chain_points,[])
        cfg.fun_enabled=False;engine.update(cfg,100,200,100,200)
        self.assertIsNone(engine.mode)
    def test_mode_cards_options_and_compact_layout(self):
        cfg=CursorConfig();cfg.save=lambda *a,**k:None
        win=SettingsWindow(cfg,lambda:None,None)
        try:
            win.show(); win.stackedWidget.setCurrentWidget(win.fun_interface)
            QTest.qWait(500)
            self.assertEqual(set(win.fun_mode_buttons),set(MODES))
            win.fun_master.setChecked(True)
            scroll=win.fun_interface.layout().itemAt(0).widget()
            for mode in MODES:
                win.fun_mode_buttons[mode].click()
                self.assertEqual(cfg.fun_mode,mode)
                self.assertEqual(win.fun_card_chain.isHidden(),mode!='chain')
                self.assertEqual(win.fun_card_orbit.isHidden(),mode!='orbit')
                for width in (760,960):
                    win.resize(width,610);QTest.qWait(180)
                    print("LAYOUT_MODE",mode,"WIDTH",width,"OVER",scroll.horizontalScrollBar().maximum(),flush=True)
                    self.assertEqual(scroll.horizontalScrollBar().maximum(),0)
            win.fun_mode_buttons['chain'].click()
            win.fun_slider_chain.setValue(15)
            self.assertEqual(cfg.fun_chain_length,15)
            win.fun_mode_buttons['orbit'].click()
            win.fun_slider_orbit.setValue(5)
            self.assertEqual(cfg.fun_orbit_count,5)
            win.fun_master.setChecked(False)
            self.assertTrue(win.basic_interface.isEnabled())
        finally:
            win.hide();win.deleteLater();self.app.processEvents()

if __name__=='__main__':unittest.main()
