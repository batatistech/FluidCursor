"""Keep the tray artwork compact without resizing the Windows icon slot."""
import os
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from ui.tray_icon import create_tray_icon

class TrayIconSizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_pointer_has_clear_transparent_padding(self):
        icon = create_tray_icon()
        for size in (16, 20, 24, 32):
            image = icon.pixmap(size, size).toImage()
            points = [(x, y) for y in range(size) for x in range(size)
                      if image.pixelColor(x, y).alpha() > 40]
            self.assertTrue(points)
            xs, ys = zip(*points)
            self.assertGreaterEqual(min(xs), 2)
            self.assertGreaterEqual(min(ys), 2)
            self.assertLessEqual(max(xs), size - 3)
            self.assertLessEqual(max(ys), size - 3)
            self.assertLessEqual(max(ys) - min(ys) + 1, int(size * 0.80))
