"""Regression: first-show text and stable physical links at varying frame rates."""
import math, os, sys, unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from qfluentwidgets import SettingCard
from core.chain_physics import SPACING, advance_chain
from core.config import CursorConfig
from ui.settings_window import SettingsWindow

class LayoutChainStability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_all_descriptions_survive_first_show_and_resize(self):
        cfg = CursorConfig(); cfg.save = lambda *a, **k: None
        win = SettingsWindow(cfg, lambda: None, None)
        try:
            for width in (960, 760):
                win.resize(width, 720); win.show()
                win.stackedWidget.setCurrentWidget(win.sys_interface)
                QTest.qWait(650)
                for card in win.sys_interface.findChildren(SettingCard):
                    self.assertEqual(card.contentLabel.text(), card._full_description)
                    self.assertTrue(card.contentLabel.wordWrap())
                    self.assertGreater(card.contentLabel.height(), 0)
        finally:
            win.hide(); win.deleteLater(); self.app.processEvents()

    def test_long_chain_does_not_gain_energy_at_rest(self):
        points = []; tails = []
        for i in range(760):
            anchor = (120 + min(i, 30)*5, 100)
            advance_chain(points, anchor, 32, .007, 55, 65)
            self.assertEqual(points[0][:2], list(anchor))
            self.assertTrue(all(math.isfinite(n) for p in points for n in p))
            for a,b in zip(points,points[1:]):
                self.assertAlmostEqual(math.dist(a[:2],b[:2]),SPACING,delta=.025)
            tails.append(tuple(points[-1][:2]))
        self.assertGreater(tails[30][1],90)  # No exaggerated upward whip.
        self.assertLess(math.dist(tails[-1],(270,100+31*SPACING)),5)
        self.assertLess(max(math.dist(a,b) for a,b in zip(tails,tails[1:])),12)

    def test_variable_framerate_and_pointer_teleport_stay_finite(self):
        for dt in (.007, .016, .033):
            for liveliness in (0, 65, 100):
                points = []
                for i in range(150):
                    anchor = (100+95*math.sin(i*.13), 140+45*math.cos(i*.18))
                    if i == 80: anchor = (1400, 700)
                    advance_chain(points,anchor,32,dt,45,liveliness)
                    self.assertEqual(points[0][:2],list(anchor))
                    self.assertTrue(all(math.isfinite(n) for p in points for n in p))
                    self.assertLessEqual(math.dist(points[0][:2],points[-1][:2]),31*SPACING+.01)

if __name__ == '__main__': unittest.main()
