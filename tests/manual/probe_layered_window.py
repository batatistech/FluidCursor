import ctypes
from ctypes import wintypes
import time
import sys
import unittest
from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QPointF

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
CreateWindowInBand = user32.CreateWindowInBand
CreateWindowInBand.restype = wintypes.HWND

# Win32 structures
class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]

AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
ULW_ALPHA = 0x02
BI_RGB = 0

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_TOPMOST = 0x00000008
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

class TestUpdateLayered(unittest.TestCase):
    def test_update_layered_window_rendering(self):
        w, h = 200, 200
        hwnd = CreateWindowInBand(
            WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            'STATIC', 'Band16Layered',
            WS_POPUP | WS_VISIBLE,
            100, 100, w, h, None, None, None, None, 16
        )
        self.assertTrue(hwnd != 0, "CreateWindowInBand failed")

        # Create memory DC and 32-bit DIB
        screen_dc = user32.GetDC(0)
        mem_dc = gdi32.CreateCompatibleDC(screen_dc)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h  # top-down DIB
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        ppvBits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), 0, ctypes.byref(ppvBits), None, 0)
        old_bmp = gdi32.SelectObject(mem_dc, hbmp)

        # Wrap DIB bits in QImage
        qimg = QImage(
            ctypes.cast(ppvBits, ctypes.c_char_p),
            w, h, w * 4,
            QImage.Format.Format_ARGB32_Premultiplied
        )

        # Draw on QImage using QPainter
        qimg.fill(0) # transparent
        painter = QPainter(qimg)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QBrush(QColor(0, 210, 255, 200)))
        painter.setPen(QPen(QColor(255, 255, 255, 255), 3))
        painter.drawEllipse(QPointF(100, 100), 50, 50)
        painter.end()

        # Update layered window
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        pt_src = wintypes.POINT(0, 0)
        pt_dst = wintypes.POINT(200, 200)
        size = wintypes.SIZE(w, h)

        res = user32.UpdateLayeredWindow(
            hwnd, screen_dc,
            ctypes.byref(pt_dst), ctypes.byref(size),
            mem_dc, ctypes.byref(pt_src),
            0, ctypes.byref(blend), ULW_ALPHA
        )
        self.assertEqual(res, 1, "UpdateLayeredWindow must succeed")

        # Cleanup
        gdi32.SelectObject(mem_dc, old_bmp)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(0, screen_dc)
        user32.DestroyWindow(hwnd)

if __name__ == '__main__':
    unittest.main()
