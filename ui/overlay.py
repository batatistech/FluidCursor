"""
High-Performance Native Overlay for FluidCursor.
Uses Windows Z-Band 16 (ZBID_SYSTEM_TOOLS) via CreateWindowInBand and UpdateLayeredWindow
to ensure the animated cursor renders ABOVE Windows 11 Start Menu, Taskbar, context menus,
notification center, and modern XAML islands while remaining 100% click-through.
"""

import ctypes
from ctypes import wintypes
import time
from PyQt6.QtCore import QObject, QTimer, Qt, QPointF
from PyQt6.QtGui import QImage, QPainter, QColor, QPen

from core.win32_cursor import Win32CursorManager
from core.hotkeys import hotkey_vk
from core.physics import CursorPhysics
from core.theme import CursorRenderer
from core.config import CursorConfig
from core.cursor_capture import SystemCursorCloner
from core.fun_modes import FunEngine, MODES, smoothness_physics

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Win32 Structures
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

# Win32 Constants
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

HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

# Band 16 = ZBID_SYSTEM_TOOLS (Sits above Windows 11 Start Menu, Taskbar & Context Menus)
ZBID_SYSTEM_TOOLS = 16

def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return (0, 210, 255)


class CursorOverlay(QObject):
    """
    Native Win32 Layered Window overlay operating in ZBID_SYSTEM_TOOLS.
    Draws directly using QPainter into a 32-bit premultiplied ARGB DIB.
    """

    def __init__(self, config: CursorConfig, cursor_mgr: Win32CursorManager):
        super().__init__()
        self.config = config
        self.cursor_mgr = cursor_mgr

        # Pre-capture system cursors before any blanking occurs
        self.cloner = SystemCursorCloner()
        self.fun = FunEngine()

        # Window dimensions & hotspot offset
        self.win_w = 288
        self.win_h = 288
        self.offset_x = 144
        self.offset_y = 144

        # Initialize physics at current cursor location
        init_x, init_y = self.cursor_mgr.get_cursor_pos()
        self.physics = CursorPhysics(init_x, init_y)

        # Hotkey debounce state
        self.f9_was_pressed = False
        self._last_hotkey = self.config.toggle_hotkey
        self.on_state_toggled = None
        self.was_cleared_on_disable = False
        self.frame_count = 0
        self._last_visual_state = None
        self._next_topmost_check = time.monotonic() + 1.0
        self.tray_menu_open = False
        self._idle_ticks = 0

        # Create native window in Band 16
        self.hwnd = self._create_native_window()

        # Create 32-bit DIBSection & QImage wrapper
        self._init_gdi_buffers()

        # 144Hz render timer (~7ms)
        self.timer = QTimer(self)
        self.timer.setInterval(7)
        self.timer.timeout.connect(self.tick)

    def _create_native_window(self) -> int:
        """Creates layered window in ZBID_SYSTEM_TOOLS to display over Windows 11 Start menu."""
        ex_style = (
            WS_EX_TOPMOST
            | WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_TOOLWINDOW
            | WS_EX_NOACTIVATE
        )
        style = WS_POPUP | WS_VISIBLE

        hwnd = None
        if hasattr(user32, "CreateWindowInBand"):
            try:
                CreateWindowInBand = user32.CreateWindowInBand
                CreateWindowInBand.restype = wintypes.HWND
                hwnd = CreateWindowInBand(
                    ex_style,
                    "STATIC",
                    "FluidCursorBandOverlay",
                    style,
                    -500, -500, self.win_w, self.win_h,
                    None, None, None, None,
                    ZBID_SYSTEM_TOOLS
                )
            except Exception:
                hwnd = None

        # Fallback to standard CreateWindowEx if CreateWindowInBand fails
        if not hwnd:
            CreateWindowEx = user32.CreateWindowExW
            CreateWindowEx.restype = wintypes.HWND
            hwnd = CreateWindowEx(
                ex_style,
                "STATIC",
                "FluidCursorOverlay",
                style,
                -500, -500, self.win_w, self.win_h,
                None, None, None, None
            )

        return hwnd

    def _init_gdi_buffers(self):
        """Creates high-performance 32-bit ARGB DIBSection mapped directly to QImage."""
        self.screen_dc = user32.GetDC(0)
        self.mem_dc = gdi32.CreateCompatibleDC(self.screen_dc)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self.win_w
        bmi.bmiHeader.biHeight = -self.win_h  # Negative for top-down bitmap
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        self.ppv_bits = ctypes.c_void_p()
        self.hbmp = gdi32.CreateDIBSection(
            self.mem_dc,
            ctypes.byref(bmi),
            0,
            ctypes.byref(self.ppv_bits),
            None,
            0
        )
        self.old_bmp = gdi32.SelectObject(self.mem_dc, self.hbmp)

        # Native 32-bit QImage for smooth vector rendering
        self.byte_size = self.win_w * self.win_h * 4
        self.qimg = QImage(
            self.win_w,
            self.win_h,
            QImage.Format.Format_ARGB32_Premultiplied
        )

        self.blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        self.pt_src = wintypes.POINT(0, 0)
        self.size = wintypes.SIZE(self.win_w, self.win_h)

    def _resize_canvas(self, dimension):
        """Allocate the large canvas only while a long Fun chain needs it."""
        if self.win_w == dimension:
            return
        # Release old GDI surfaces before allocating new backing memory.
        if self.mem_dc:
            gdi32.SelectObject(self.mem_dc, self.old_bmp)
            gdi32.DeleteObject(self.hbmp)
            gdi32.DeleteDC(self.mem_dc)
        if self.screen_dc:
            user32.ReleaseDC(0, self.screen_dc)
        self.qimg = None
        self.win_w = self.win_h = dimension
        self.offset_x = self.offset_y = dimension // 2
        self._init_gdi_buffers()
        if self.hwnd:
            user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0,
                                dimension, dimension, SWP_NOMOVE | SWP_NOACTIVATE)
        self.invalidate_render()

    def show(self):
        if self.hwnd:
            user32.ShowWindow(self.hwnd, 4)  # SW_SHOWNOACTIVATE
            user32.SetWindowPos(
                self.hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | 0x0040  # SWP_SHOWWINDOW
            )
        if self.config.enabled and (self.config.hide_system_cursor or self.config.fun_enabled):
            self.cursor_mgr.hide_system_cursor()
        self.timer.start()

    def invalidate_render(self):
        """Mark cached pixels stale; the next input tick renders fresh settings."""
        self._last_visual_state = None

    def update(self):
        self.invalidate_render()
        self.tick()

    def close(self):
        self.timer.stop()
        if self.cursor_mgr.is_hidden:
            self.cursor_mgr.restore_system_cursor()
        if self.hwnd and user32.IsWindow(self.hwnd):
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None

        # Clean up GDI resources
        try:
            if hasattr(self, 'mem_dc') and self.mem_dc:
                gdi32.SelectObject(self.mem_dc, self.old_bmp)
                gdi32.DeleteObject(self.hbmp)
                gdi32.DeleteDC(self.mem_dc)
            if hasattr(self, 'screen_dc') and self.screen_dc:
                user32.ReleaseDC(0, self.screen_dc)
        except Exception:
            pass

    def toggle_enabled(self):
        """Toggles custom cursor on/off."""
        self.config.enabled = not self.config.enabled
        if not self.config.enabled:
            self.cursor_mgr.restore_system_cursor()
            self.clear_window()
            self.was_cleared_on_disable = True
        else:
            if self.hwnd:
                user32.ShowWindow(self.hwnd, 4)
            if self.config.hide_system_cursor or self.config.fun_enabled:
                self.cursor_mgr.hide_system_cursor()
            self.was_cleared_on_disable = False

        if self.on_state_toggled:
            self.on_state_toggled(self.config.enabled)

    def clear_window(self):
        self.invalidate_render()
        if not self.hwnd:
            return
        self.qimg.fill(0)
        ctypes.memmove(self.ppv_bits.value, int(self.qimg.constBits()), self.byte_size)
        pt_dst = wintypes.POINT(-2000, -2000)
        user32.UpdateLayeredWindow(
            self.hwnd,
            self.screen_dc,
            ctypes.byref(pt_dst),
            ctypes.byref(self.size),
            self.mem_dc,
            ctypes.byref(self.pt_src),
            0,
            ctypes.byref(self.blend),
            ULW_ALPHA
        )
        user32.ShowWindow(self.hwnd, 0)

    def set_tray_menu_open(self, open_):
        """Avoid competing with Explorer while its tray menu is open."""
        self.tray_menu_open = bool(open_)
        # Keep full-speed tracking while the menu is open. The popup is
        # asynchronous and topmost reassertion is already suspended.
        if self.timer.interval() != 7:
            self.timer.setInterval(7)
        self._idle_ticks = 0
        if not open_:
            self._next_topmost_check = time.monotonic() + 1.0

    def _maintain_topmost(self):
        """Reassert z-order only when no tray context menu is showing."""
        if self.tray_menu_open:
            return
        now = time.monotonic()
        if now >= self._next_topmost_check:
            self._next_topmost_check = now + 1.0
            if self.hwnd:
                user32.SetWindowPos(
                    self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    def tick(self):
        # Configurable global key; rising edge prevents repeats while held.
        key = self.config.toggle_hotkey
        if key != self._last_hotkey:
            self.f9_was_pressed = False
            self._last_hotkey = key
        pressed = self.cursor_mgr.is_key_pressed(hotkey_vk(key))
        if pressed and not self.f9_was_pressed:
            self.toggle_enabled()
        self.f9_was_pressed = pressed

        if not self.config.enabled:
            if not self.was_cleared_on_disable:
                self.clear_window()
                self.was_cleared_on_disable = True
            if self.cursor_mgr.is_hidden:
                self.cursor_mgr.restore_system_cursor()
            return

        if self.was_cleared_on_disable:
            if self.hwnd:
                user32.ShowWindow(self.hwnd, 4)
            self.was_cleared_on_disable = False

        fun_active = bool(self.config.fun_enabled and self.config.fun_mode in MODES)
        target_canvas = (480 if fun_active and self.config.fun_mode == "chain"
                         and self.config.fun_chain_length > 16 else 288)
        if self.win_w != target_canvas:
            self._resize_canvas(target_canvas)
        # 2. Manage system cursor visibility
        if (self.config.hide_system_cursor or fun_active) and not self.cursor_mgr.is_hidden:
            self.cursor_mgr.hide_system_cursor()
        elif not (self.config.hide_system_cursor or fun_active) and self.cursor_mgr.is_hidden:
            self.cursor_mgr.restore_system_cursor()

        # 3. Read true hardware mouse position, button states, and active cursor type
        hw_x, hw_y = self.cursor_mgr.get_cursor_pos()
        left_down, right_down, middle_down = self.cursor_mgr.get_button_states()
        cursor_type = (self.cursor_mgr.get_cursor_type(hw_x, hw_y)
                       if (self.config.match_cursor_roles or fun_active) else "normal")
        cursor_handle = (getattr(self.cursor_mgr, "active_cursor_handle", 0)
                         if cursor_type == "custom" else 0)
        # Native app-owned cursors stay visible after replacing shared OCR handles.
        # NEVER decode an unfamiliar cursor in the 7 ms UI loop: shell/tray
        # cursors can be large and synchronous GDI capture freezes the menu.
        custom_native = (cursor_type == "custom" and self.cursor_mgr.is_hidden
                         and getattr(self.cursor_mgr, "active_cursor_visible", False))

        # 4. Advance physics simulation
        ripple_rgb = hex_to_rgb(self.config.ripple_color)
        fun_stiffness, fun_damping = smoothness_physics(self.config.fun_smoothness)
        self.physics.update(
            hw_x=hw_x,
            hw_y=hw_y,
            left_down=left_down,
            right_down=right_down,
            middle_down=middle_down,
            enable_advanced_physics=fun_active or self.config.enable_advanced_physics,
            smoothing_type="spring" if fun_active else self.config.smoothing_type,
            responsiveness=self.config.responsiveness,
            spring_stiffness=fun_stiffness if fun_active else self.config.spring_stiffness,
            spring_damping=fun_damping if fun_active else self.config.spring_damping,
            prediction_factor=self.config.prediction_factor,
            drag_friction=self.config.drag_friction,
            drag_boost=False if fun_active else self.config.drag_boost,
            shrink_factor=1.0 if fun_active else self.config.shrink_factor,
            tilt_enabled=False if fun_active else self.config.tilt_enabled,
            tilt_mode=self.config.tilt_mode,
            tilt_strength=self.config.tilt_strength,
            tilt_deadzone=self.config.tilt_deadzone,
            tilt_decay_enabled=self.config.tilt_decay_enabled,
            tilt_decay_speed=self.config.tilt_decay_speed,
            tilt_delay_enabled=self.config.tilt_delay_enabled,
            tilt_return_delay=self.config.tilt_return_delay,
            tilt_disable_return=self.config.tilt_disable_return,
            ripples_enabled=False if fun_active else self.config.ripples_enabled,
            snap_on_click=True if fun_active else self.config.snap_on_click,
            trail_enabled=False if fun_active else self.config.trail_enabled,
            ripple_color=ripple_rgb
        )

        self.fun.update(self.config, self.physics.x, self.physics.y, hw_x, hw_y,
                        self.physics.was_any_down,
                        anchor=(self.physics.x + 9.0 * self.physics.scale,
                                self.physics.y + 22.5 * self.physics.scale))
        # Preserve 7 ms input/hotkey checks while skipping unchanged GDI frames.
        visual_state = (
            round(self.physics.x, 2), round(self.physics.y, 2),
            round(self.physics.scale, 3), round(self.physics.tilt_angle, 2),
            cursor_type if not fun_active or custom_native else "fun",
            cursor_handle if custom_native else 0, custom_native, self.config.match_cursor_roles,
            self.fun.frame_key(), self.config.fun_particles,
            self.config.fun_smoothness, self.config.fun_chain_length, self.config.fun_orbit_count,
            (int(time.monotonic() * 15) if not fun_active and cursor_type in ("wait", "appstarting") else 0),
            self.physics.was_any_down,
            self.config.trail_enabled,
            tuple((round(x, 1), round(y, 1), round(age, 2))
                  for x, y, age in self.physics.trail_points),
            tuple((r.x, r.y, round(r.progress, 3)) for r in self.physics.ripples),
            (hw_x, hw_y) if self.config.show_precision_dot else None,
            self.config.show_precision_dot, self.config.precision_dot_white_outline,
            self.config.use_system_cursor_clone, self.config.cursor_theme,
            self.config.cursor_size, self.config.primary_color,
            self.config.border_color,
        )
        if visual_state == self._last_visual_state:
            self._idle_ticks += 1
            if self._idle_ticks >= 12 and not self.tray_menu_open and self.timer.interval() != 30:
                self.timer.setInterval(30)  # Idle: reduce Win32 polling and CPU wakeups.
            self._maintain_topmost()
            return
        self._idle_ticks = 0
        if self.timer.interval() != 7:
            self.timer.setInterval(7)  # Active motion: restore the 144 Hz tracking cadence.

        # 5. Screen coordinates for the layered window
        win_x = int(self.physics.x - self.offset_x)
        win_y = int(self.physics.y - self.offset_y)

        # 6. Render frame into QImage
        self.qimg.fill(0)
        painter = QPainter(self.qimg)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Draw active ripples (translated to window local coords)
        for ripple in (() if fun_active else self.physics.ripples):
            local_rx = ripple.x - win_x
            local_ry = ripple.y - win_y
            if -50 <= local_rx <= self.win_w + 50 and -50 <= local_ry <= self.win_h + 50:
                alpha_byte = int(max(0.0, min(1.0, ripple.current_alpha)) * 220)
                if alpha_byte > 0:
                    r, g, b = ripple.color
                    pen_color = QColor(r, g, b, alpha_byte)
                    pen = QPen(pen_color, ripple.line_width * (1.0 - ripple.progress * 0.4))
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(QPointF(local_rx, local_ry), ripple.radius, ripple.radius)

        # Draw animated cursor with subpixel precision
        local_cx = self.physics.x - win_x
        local_cy = self.physics.y - win_y

        tilt_angle = self.physics.tilt_angle
        # Keep resize and text cursors aligned without diagonal wobble
        if cursor_type in ("sizewe", "sizens", "sizenwse", "sizenesw", "sizeall", "ibeam", "cross", "wait"):
            tilt_angle = 0.0

        # Real ghost echoes: older cursor silhouettes fade independently of the
        # live pointer. Native app-owned cursors are never duplicated.
        if (self.config.trail_enabled and self.physics.trail_points
                and not fun_active and not custom_native):
            ghost_clone = (self.cloner.get_cloned_cursor(
                "normal" if cursor_type == "custom" else cursor_type)
                if self.config.use_system_cursor_clone else None)
            CursorRenderer.draw_motion_ghosts(
                painter, self.physics.trail_points, win_x, win_y,
                self.config.cursor_theme, self.config.cursor_size,
                self.config.primary_color, self.config.border_color,
                "normal" if cursor_type == "custom" else cursor_type,
                cloned=ghost_clone)

        if fun_active and not custom_native:
            self.fun.draw(painter, local_cx, local_cy, win_x, win_y, self.config)
        drawn = bool(custom_native or (fun_active and self.fun.mode not in ("tile", "chain", "yoyo", "ribbon", "spinner")))
        if not drawn and not fun_active and self.config.use_system_cursor_clone:
            cloned = self.cloner.get_cloned_cursor(
                "normal" if cursor_type == "custom" else cursor_type)
            if cloned:
                qimg_cursor, hx, hy = cloned
                CursorRenderer.draw_cloned_cursor(
                    painter=painter,
                    x=local_cx,
                    y=local_cy,
                    scale=self.physics.scale,
                    tilt_deg=tilt_angle,
                    qimg=qimg_cursor,
                    hotspot_x=hx,
                    hotspot_y=hy,
                    is_clicking=self.physics.was_any_down
                )
                drawn = True

        # Unknown and invisible handle: draw a safe arrow, without blocking
        # the GUI thread on CopyIcon / bitmap decoding.
        if cursor_type == "custom" and not drawn:
            cursor_type = "normal"

        if not drawn:
            CursorRenderer.draw_cursor(
                painter=painter,
                x=local_cx,
                y=local_cy,
                scale=self.physics.scale,
                tilt_deg=tilt_angle,
                theme_name="aero_modern" if fun_active else self.config.cursor_theme,
                size=24 if fun_active else self.config.cursor_size,
                primary_color_hex=self.config.primary_color,
                border_color_hex=self.config.border_color,
                is_clicking=self.physics.was_any_down,
                cursor_type="normal" if fun_active else cursor_type
            )

        # Precision dot if enabled
        if self.config.show_precision_dot and not fun_active:
            local_hx = self.physics.target_x - win_x
            local_hy = self.physics.target_y - win_y
            CursorRenderer.draw_precision_dot(
                painter,
                local_hx,
                local_hy,
                with_white_outline=self.config.precision_dot_white_outline
            )

        painter.end()

        # Copy rendered pixels from QImage to DIBSection memory
        ctypes.memmove(self.ppv_bits.value, int(self.qimg.constBits()), self.byte_size)

        # 7. Update Layered Window position and alpha bitmap in a single call
        pt_dst = wintypes.POINT(win_x, win_y)
        user32.UpdateLayeredWindow(
            self.hwnd,
            self.screen_dc,
            ctypes.byref(pt_dst),
            ctypes.byref(self.size),
            self.mem_dc,
            ctypes.byref(self.pt_src),
            0,
            ctypes.byref(self.blend),
            ULW_ALPHA
        )

        # Only count completed frames. Input and F9 polling continue at 7 ms.
        self._last_visual_state = visual_state
        self.frame_count += 1
        self._maintain_topmost()
