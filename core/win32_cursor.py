"""
Win32 low-level API interface for FluidCursor.
Handles:
- Per-Monitor V2 DPI awareness
- Sub-millisecond hardware cursor position queries
- Direct mouse button state queries (GetAsyncKeyState)
- Non-blocking global hotkey checks
- Safe system cursor hiding and restoration
- Extended window click-through styles (WS_EX_TRANSPARENT, WS_EX_NOACTIVATE)
"""

import ctypes
from ctypes import wintypes
import atexit
import logging

logger = logging.getLogger("FluidCursor.Win32")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Set DPI awareness (Per-Monitor V2 = -4)
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception as e:
    logger.warning(f"Could not set DPI awareness context: {e}")

# Virtual Keys
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_F9 = 0x78
VK_F8 = 0x77
VK_ESCAPE = 0x1B
VK_CONTROL = 0x11
VK_SHIFT = 0x10

# System Cursors
OCR_NORMAL = 32512       # Standard arrow
OCR_IBEAM = 32513        # Text select
OCR_WAIT = 32514         # Busy / Loading
OCR_CROSS = 32515        # Precision crosshair
OCR_UP = 32516           # Up arrow
OCR_SIZENWSE = 32642     # Diagonal resize 1
OCR_SIZENESW = 32643     # Diagonal resize 2
OCR_SIZEWE = 32644       # Horizontal resize
OCR_SIZENS = 32645       # Vertical resize
OCR_SIZEALL = 32646      # Move / 4-way
OCR_NO = 32648           # Slashed circle / Not allowed
OCR_HAND = 32649         # Link hand
OCR_APPSTARTING = 32650  # Arrow with loading spinner

OCR_ALL_MAP = {
    OCR_NORMAL: "normal",
    OCR_IBEAM: "ibeam",
    OCR_WAIT: "wait",
    OCR_CROSS: "cross",
    OCR_UP: "up",
    OCR_SIZENWSE: "sizenwse",
    OCR_SIZENESW: "sizenesw",
    OCR_SIZEWE: "sizewe",
    OCR_SIZENS: "sizens",
    OCR_SIZEALL: "sizeall",
    OCR_NO: "no",
    OCR_HAND: "hand",
    OCR_APPSTARTING: "appstarting",
}

SPI_SETCURSORS = 0x0057
SPIF_SENDCHANGE = 0x02

# Window Styles
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", wintypes.POINT),
    ]


class Win32CursorManager:
    """Manages system cursor visibility, coordinates, button states, and active cursor type."""
    
    def __init__(self):
        self._is_hidden = False
        self.active_cursor_handle = 0
        self.active_cursor_visible = False
        self._pt = POINT()
        self._ci = CURSORINFO()
        self._ci.cbSize = ctypes.sizeof(CURSORINFO)

        # Attach desktop station for GetCursorInfo access
        try:
            hdesk = user32.OpenInputDesktop(0, False, 0x0100)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

        # Pre-cache standard system cursor handles
        self.cursor_handles = {}
        try:
            user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
            user32.LoadCursorW.restype = wintypes.HANDLE
            for ocr_id, name in OCR_ALL_MAP.items():
                h = user32.LoadCursorW(None, ctypes.cast(ocr_id, wintypes.LPCWSTR))
                if h:
                    self.cursor_handles[h] = name
        except Exception as e:
            logger.warning(f"Could not cache system cursor handles: {e}")

        # Register atexit handler so cursor is guaranteed to restore
        atexit.register(self.restore_system_cursor)

    def get_cursor_pos(self) -> tuple[int, int]:
        """Returns the current true hardware cursor position (x, y) in screen coordinates."""
        user32.GetCursorPos(ctypes.byref(self._pt))
        return self._pt.x, self._pt.y

    def get_button_states(self) -> tuple[bool, bool, bool]:
        """Returns (is_left_down, is_right_down, is_middle_down)."""
        swapped = bool(user32.GetSystemMetrics(23))  # SM_SWAPBUTTON
        vk_l = VK_RBUTTON if swapped else VK_LBUTTON
        vk_r = VK_LBUTTON if swapped else VK_RBUTTON

        left = bool((user32.GetAsyncKeyState(vk_l) & 0x8000) or (user32.GetKeyState(vk_l) & 0x8000))
        right = bool((user32.GetAsyncKeyState(vk_r) & 0x8000) or (user32.GetKeyState(vk_r) & 0x8000))
        middle = bool((user32.GetAsyncKeyState(VK_MBUTTON) & 0x8000) or (user32.GetKeyState(VK_MBUTTON) & 0x8000))
        return left, right, middle

    def get_cursor_type(self, hw_x: int, hw_y: int) -> str:
        """
        Detects the active cursor type (normal, ibeam, wait, sizewe, sizens, etc.).
        Fast kernel query using GetCursorInfo with zero cross-process blocking.
        """
        try:
            # GetCursorInfo clears cbSize on this Windows build. Reset it for every query.
            self._ci.cbSize = ctypes.sizeof(CURSORINFO)
            if user32.GetCursorInfo(ctypes.byref(self._ci)):
                h = int(self._ci.hCursor or 0)
                self.active_cursor_handle = h
                self.active_cursor_visible = bool(self._ci.flags & 1)
                if h in self.cursor_handles:
                    return self.cursor_handles[h]
                return "custom" if h else "normal"
        except Exception:
            pass

        self.active_cursor_handle = 0
        self.active_cursor_visible = False
        return "normal"

    def is_key_pressed(self, vk_code: int) -> bool:
        """Returns True if the specified virtual key is currently pressed."""
        return bool(user32.GetAsyncKeyState(vk_code) & 0x8000)

    def _create_blank_cursor(self):
        """Creates a completely transparent 32x32 cursor handle."""
        and_mask = (ctypes.c_ubyte * 128)(*[0xFF] * 128)
        xor_mask = (ctypes.c_ubyte * 128)(*[0x00] * 128)
        return user32.CreateCursor(None, 0, 0, 32, 32, and_mask, xor_mask)

    def hide_system_cursor(self):
        """
        Hides ALL Windows system cursors (normal, loading, resize, text, etc.)
        by replacing them with transparent cursor masks.
        """
        if self._is_hidden:
            return

        try:
            for ocr_id in OCR_ALL_MAP.keys():
                h_blank = self._create_blank_cursor()
                if h_blank:
                    user32.SetSystemCursor(h_blank, ocr_id)

            self._is_hidden = True
            logger.info("All Windows system cursors hidden.")
        except Exception as e:
            logger.error(f"Failed to hide system cursors: {e}")

    def restore_system_cursor(self):
        """Restores all standard Windows system cursors."""
        if not self._is_hidden:
            return
        try:
            # SPI_SETCURSORS resets all system cursors back to default registry settings
            user32.SystemParametersInfoW(SPI_SETCURSORS, 0, 0, SPIF_SENDCHANGE)
            self._is_hidden = False
            logger.info("Windows system cursors restored.")
        except Exception as e:
            logger.error(f"Failed to restore system cursors: {e}")

    @property
    def is_hidden(self) -> bool:
        return self._is_hidden

    @staticmethod
    def force_restore():
        """Emergency static method to restore system cursor immediately."""
        try:
            user32.SystemParametersInfoW(SPI_SETCURSORS, 0, 0, SPIF_SENDCHANGE)
        except Exception:
            pass

    @staticmethod
    def apply_click_through(hwnd: int):
        """Ensures the window is completely transparent to mouse input and doesn't steal focus."""
        try:
            GetWindowLongPtr = user32.GetWindowLongPtrW if hasattr(user32, 'GetWindowLongPtrW') else user32.GetWindowLongW
            SetWindowLongPtr = user32.SetWindowLongPtrW if hasattr(user32, 'SetWindowLongPtrW') else user32.SetWindowLongW
            
            ex_style = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
            ex_style |= (WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
            SetWindowLongPtr(hwnd, GWL_EXSTYLE, ex_style)
        except Exception as e:
            logger.error(f"Failed to apply click-through styles to hwnd {hwnd}: {e}")
