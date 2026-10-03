"""UI master polish regressions; uses isolated config and never changes Windows cursors."""
import os, sys, unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PyQt6.QtWidgets import QApplication, QPushButton, QFrame
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtTest import QTest
from qfluentwidgets import SmoothMode
from core.config import CursorConfig
from ui.settings_window import SettingsWindow

class MasterPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.config = CursorConfig()
        self.config.save = lambda *args, **kwargs: None
        self.window = SettingsWindow(self.config, lambda: None, None)
        self.window.show()
        QTest.qWait(150)

    def tearDown(self):
        self.window.hide()
        self.window.deleteLater()
        self.app.processEvents()

    def navigate(self, host):
        self.window.stackedWidget.setCurrentWidget(host)
        QTest.qWait(550)
        return host.layout().itemAt(0).widget()
    def test_motion_hint_is_compact_and_opens_tilt(self):
        scroll = self.navigate(self.window.motion_interface)
        hint = next(x for x in scroll.widget().findChildren(QFrame)
                    if x.objectName() == 'tiltNavigationHint')
        self.assertEqual(hint.height(), 66)
        self.assertEqual(hint.maximumHeight(), 66)
        link = next(x for x in hint.findChildren(QPushButton)
                    if x.accessibleName() == 'Open tilt and rotation settings')
        self.assertTrue(link.isEnabled())
        self.assertEqual(link.text(), 'Open Tilt  \u2192')
        QTest.mouseClick(link, Qt.MouseButton.LeftButton)
        QTest.qWait(550)
        self.assertIs(self.window.stackedWidget.currentWidget(), self.window.tilt_interface)

    def test_wheel_is_immediate_and_does_not_animate_afterward(self):
        scroll = self.navigate(self.window.tilt_interface)
        smooth = scroll.scrollDelagate.verticalSmoothScroll
        self.assertEqual(smooth.smoothMode, SmoothMode.NO_SMOOTH)
        bar = scroll.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        event = QWheelEvent(QPointF(120,120), QPointF(120,120),
            QPoint(0,0), QPoint(0,-120), Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.ScrollUpdate, False)
        self.app.sendEvent(scroll.viewport(), event)
        immediate = bar.value()
        self.assertGreater(immediate, 0)
        QTest.qWait(300)
        self.assertEqual(bar.value(), immediate)
    def test_advanced_controls_show_only_relevant_options(self):
        self.navigate(self.window.motion_interface)
        w = self.window
        self.assertFalse(w.config.enable_advanced_physics)
        for card in (w.card_algo,w.card_stiff,w.card_damp,w.card_pred,w.card_drag):
            self.assertTrue(card.isHidden())
        w.card_adv_master.setChecked(True)
        self.assertFalse(w.card_algo.isHidden())
        w.combo_algo.setCurrentIndex(1)
        self.assertFalse(w.card_stiff.isHidden())
        self.assertFalse(w.card_damp.isHidden())
        self.assertTrue(w.card_pred.isHidden())
        self.assertTrue(w.card_drag.isHidden())
        w.combo_algo.setCurrentIndex(3)
        self.assertTrue(w.card_stiff.isHidden())
        self.assertFalse(w.card_pred.isHidden())
        w.card_adv_master.setChecked(False)
        self.assertTrue(w.card_algo.isHidden())

    def test_no_horizontal_overflow_with_advanced_spring(self):
        scroll = self.navigate(self.window.motion_interface)
        self.window.card_adv_master.setChecked(True)
        self.window.combo_algo.setCurrentIndex(1)
        for width in (960, 760):
            self.window.resize(width,600)
            QTest.qWait(220)
            self.assertEqual(scroll.horizontalScrollBar().maximum(),0)

if __name__ == '__main__':
    unittest.main()
