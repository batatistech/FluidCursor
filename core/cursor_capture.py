"""
Cursor Capture and Cloning Engine for FluidCursor.
Captures and decodes active Windows system cursors (including custom registry themes like Point.er Black+)
into high-quality QImages, preserving exact pixel shapes, alpha channels, and hotspot alignments.
"""

import winreg
import os
import ctypes
from ctypes import wintypes
from typing import Tuple, Optional, Dict
from PyQt6.QtGui import QImage, QColor
from PyQt6.QtCore import Qt

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

IMAGE_CURSOR = 2
LR_LOADFROMFILE = 0x0010

user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
user32.LoadCursorW.restype = wintypes.HANDLE
user32.CopyIcon.argtypes = [wintypes.HANDLE]
user32.CopyIcon.restype = wintypes.HANDLE
user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
user32.GetIconInfo.restype = wintypes.BOOL
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.LoadImageW.restype = wintypes.HANDLE

gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
gdi32.GetBitmapBits.argtypes = [wintypes.HANDLE, wintypes.LONG, ctypes.c_void_p]
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HANDLE, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]

class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HANDLE),
        ("hbmColor", wintypes.HANDLE),
    ]

class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG),
        ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG),
        ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD),
        ("bmBitsPixel", wintypes.WORD),
        ("bmBits", ctypes.c_void_p),
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


def capture_hcursor(h_cursor: int) -> Optional[Tuple[QImage, int, int]]:
    """
    Decodes a Windows HCURSOR handle into (QImage, hotspot_x, hotspot_y).
    Supports both 32-bit modern color cursors and monochrome AND/XOR mask cursors.
    """
    if not h_cursor:
        return None

    ii = ICONINFO()
    if not user32.GetIconInfo(h_cursor, ctypes.byref(ii)):
        return None

    hotspot_x = int(ii.xHotspot)
    hotspot_y = int(ii.yHotspot)

    qimg = None

    try:
        # Case A: 32-bit Color Cursor (hbmColor is present)
        if ii.hbmColor:
            bm = BITMAP()
            gdi32.GetObjectW(ii.hbmColor, ctypes.sizeof(BITMAP), ctypes.byref(bm))
            w = bm.bmWidth
            h = bm.bmHeight

            screen_dc = user32.GetDC(0)
            mem_dc = gdi32.CreateCompatibleDC(screen_dc)

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = w
            bmi.bmiHeader.biHeight = -h  # top-down
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0  # BI_RGB

            buf = (ctypes.c_ubyte * (w * h * 4))()
            gdi32.GetDIBits(
                mem_dc,
                ii.hbmColor,
                0,
                h,
                ctypes.byref(buf),
                ctypes.byref(bmi),
                0  # DIB_RGB_COLORS
            )

            qimg = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            ctypes.memmove(int(qimg.constBits()), ctypes.byref(buf), w * h * 4)

            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(0, screen_dc)

        # Case B: Standard Monochrome AND/XOR Mask Cursor (hbmColor is NULL)
        elif ii.hbmMask:
            bm = BITMAP()
            gdi32.GetObjectW(ii.hbmMask, ctypes.sizeof(BITMAP), ctypes.byref(bm))
            w = bm.bmWidth
            h = bm.bmHeight // 2  # top half is AND mask, bottom half is XOR mask

            mask_bytes = (ctypes.c_ubyte * (bm.bmWidthBytes * bm.bmHeight))()
            gdi32.GetBitmapBits(ii.hbmMask, len(mask_bytes), ctypes.byref(mask_bytes))

            qimg = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            qimg.fill(0)

            and_offset = 0
            xor_offset = bm.bmWidthBytes * h

            for y in range(h):
                row_and = and_offset + y * bm.bmWidthBytes
                row_xor = xor_offset + y * bm.bmWidthBytes
                for x in range(w):
                    byte_idx = x // 8
                    bit_idx = 7 - (x % 8)
                    and_bit = (mask_bytes[row_and + byte_idx] >> bit_idx) & 1
                    xor_bit = (mask_bytes[row_xor + byte_idx] >> bit_idx) & 1

                    if and_bit == 0 and xor_bit == 0:
                        qimg.setPixelColor(x, y, QColor(0, 0, 0, 255))      # Black border / shadow
                    elif and_bit == 0 and xor_bit == 1:
                        qimg.setPixelColor(x, y, QColor(255, 255, 255, 255))  # White fill
                    elif and_bit == 1 and xor_bit == 1:
                        qimg.setPixelColor(x, y, QColor(30, 30, 30, 255))   # Inverted fallback
                    # and_bit == 1, xor_bit == 0 is fully transparent

    except Exception:
        qimg = None
    finally:
        if ii.hbmMask:
            gdi32.DeleteObject(ii.hbmMask)
        if ii.hbmColor:
            gdi32.DeleteObject(ii.hbmColor)

    if qimg and not qimg.isNull():
        return qimg, hotspot_x, hotspot_y
    return None


REG_CURSOR_MAP = {
    "Arrow": "normal",
    "Hand": "hand",
    "IBeam": "ibeam",
    "Wait": "wait",
    "AppStarting": "appstarting",
    "SizeAll": "sizeall",
    "SizeWE": "sizewe",
    "SizeNS": "sizens",
    "SizeNWSE": "sizenwse",
    "SizeNESW": "sizenesw",
    "No": "no",
    "Crosshair": "cross",
    "UpArrow": "up",
}

OCR_FALLBACK_MAP = {
    "normal": 32512,
    "ibeam": 32513,
    "wait": 32514,
    "cross": 32515,
    "up": 32516,
    "sizenwse": 32642,
    "sizenesw": 32643,
    "sizewe": 32644,
    "sizens": 32645,
    "sizeall": 32646,
    "no": 32648,
    "hand": 32649,
    "appstarting": 32650,
}


class SystemCursorCloner:
    """Pre-captures and caches the active Windows cursor scheme from registry and user32."""

    def __init__(self):
        self.cursor_cache: Dict[str, Tuple[QImage, int, int]] = {}
        self.custom_cache = {}  # Decode unfamiliar HCURSORs only once per handle.
        self.pre_capture_system_cursors()
        self._normalise_text_cursor()

    def pre_capture_system_cursors(self):
        """Captures each cursor from the active Windows theme registry or default system cursors."""
        # 1. Read custom cursor paths from HKCU\Control Panel\Cursors
        captured_types = set()
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors") as key:
                for reg_name, type_name in REG_CURSOR_MAP.items():
                    try:
                        val, _ = winreg.QueryValueEx(key, reg_name)
                        if val:
                            val = os.path.expandvars(val).strip()
                            if val and os.path.exists(val):
                                h = user32.LoadImageW(None, val, IMAGE_CURSOR, 0, 0, LR_LOADFROMFILE)
                                if h:
                                    res = capture_hcursor(h)
                                    user32.DestroyIcon(h)
                                    if res:
                                        self.cursor_cache[type_name] = res
                                        captured_types.add(type_name)
                    except Exception:
                        pass
        except Exception:
            pass

        # 2. For any remaining types, load default Windows OCR cursors
        for type_name, ocr_id in OCR_FALLBACK_MAP.items():
            if type_name not in captured_types:
                try:
                    h = user32.LoadCursorW(None, ctypes.cast(ocr_id, wintypes.LPCWSTR))
                    if h:
                        res = capture_hcursor(h)
                        if res:
                            self.cursor_cache[type_name] = res
                except Exception:
                    pass

    @staticmethod
    def _ink_height(image):
        """Measure visible glyph height, not padded .cur canvas dimensions."""
        rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
        raw = bytes(rgba.constBits().asstring(rgba.sizeInBytes()))
        stride = rgba.bytesPerLine()
        rows = [y for y in range(rgba.height())
                if any(a > 16 for a in raw[y*stride+3:y*stride+rgba.width()*4:4])]
        return rows[-1] - rows[0] + 1 if rows else 0

    def _normalise_text_cursor(self):
        """Registry themes can supply a 128px I-beam beside a 32px arrow."""
        arrow = self.cursor_cache.get('normal')
        beam = self.cursor_cache.get('ibeam')
        if not arrow or not beam:
            return
        target = max(20.0, min(28.0, self._ink_height(arrow[0]) * 1.12))
        ink = self._ink_height(beam[0])
        if not ink or ink <= target * 1.35:
            return
        factor = target / ink
        image, hx, hy = beam
        resized = image.scaled(max(1, round(image.width()*factor)),
                               max(1, round(image.height()*factor)),
                               Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        self.cursor_cache['ibeam'] = (resized, hx*factor, hy*factor)

    def get_cloned_cursor(self, cursor_type: str) -> Optional[Tuple[QImage, int, int]]:
        """Returns (QImage, hotspot_x, hotspot_y) for the requested cursor type from cache."""
        if cursor_type in self.cursor_cache:
            return self.cursor_cache[cursor_type]
        return self.cursor_cache.get("normal")

    def get_cursor_by_handle(self, handle):
        """Preserve an application's own text/link/resize cursor if its handle is unknown."""
        if not handle:
            return None
        if handle not in self.custom_cache:
            image = capture_hcursor(handle)
            # A fully transparent icon is not a usable fallback cursor.
            if image:
                img = image[0].convertToFormat(QImage.Format.Format_RGBA8888)
                pixels = bytes(img.constBits().asstring(img.sizeInBytes()))
                if not any(pixels[3::4]):
                    image = None
            if len(self.custom_cache) >= 32:
                self.custom_cache.pop(next(iter(self.custom_cache)))
            self.custom_cache[handle] = image
        return self.custom_cache[handle]
