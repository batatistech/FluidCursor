"""
Cursor vector styles and theme renderers for FluidCursor.
Renders high-DPI vector cursors with QPainter, maintaining the hotspot strictly at (0, 0).
"""

import math
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QColor,
    QPen,
    QBrush,
    QRadialGradient,
    QLinearGradient,
    QImage
)

import time

class CursorRenderer:
    """Draws vector cursors anchored precisely at hotspot (0, 0)."""

    @staticmethod
    def draw_cloned_cursor(
        painter: QPainter,
        x: float,
        y: float,
        scale: float,
        tilt_deg: float,
        qimg: QImage,
        hotspot_x: int,
        hotspot_y: int,
        is_clicking: bool
    ):
        """Renders a cloned native Windows cursor with physics, scale, and tilt while preserving hotspot alignment."""
        painter.save()
        painter.translate(x, y)
        if abs(tilt_deg) > 0.01:
            painter.rotate(tilt_deg)
        painter.scale(scale, scale)

        # Soft drop shadow
        painter.save()
        painter.translate(1.5, 2.0)
        # Draw shadow silhouette if desired, or draw image with subtle transparency
        painter.restore()

        # The image top-left is placed at (-hotspot_x, -hotspot_y) so the hotspot is exactly at (0, 0)
        painter.drawImage(QPointF(-float(hotspot_x), -float(hotspot_y)), qimg)
        painter.restore()

    @staticmethod
    def draw_cursor(
        painter: QPainter,
        x: float,
        y: float,
        scale: float,
        tilt_deg: float,
        theme_name: str,
        size: int,
        primary_color_hex: str,
        border_color_hex: str,
        is_clicking: bool,
        cursor_type: str = "normal"
    ):
        # Theme palettes are intrinsic. Only Custom Colors may use the user palette;
        # text/link/resize roles always keep a legible, consistent Windows-like scheme.
        if cursor_type != "normal":
            primary_color_hex, border_color_hex = "#FFFFFF", "#17202A"
        elif theme_name != "custom_arrow":
            primary_color_hex, border_color_hex = {
                "aero_modern": ("#FFFFFF", "#1E293B"),
                "neon_glow": ("#E7FCFF", "#00D2FF"),
                "macos_fluid": ("#0F172A", "#FFFFFF"),
                "cyber_arrow": ("#F3FBFF", "#18C7E3"),
                "minimal_dot": ("#FFFFFF", "#64748B"),
            }.get(theme_name, ("#FFFFFF", "#1E293B"))
        painter.save()
        # Translate to exact hotspot position
        painter.translate(x, y)

        # Base scale factor relative to standard 24px
        s = size / 24.0

        # Scale from hotspot (0, 0)
        painter.scale(scale, scale)

        # Dispatch based on active system cursor type
        if cursor_type == "wait":
            CursorRenderer._draw_wait_spinner(painter, s, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "appstarting":
            # Normal cursor + mini orbiting spinner
            if abs(tilt_deg) > 0.01:
                painter.rotate(tilt_deg)
            CursorRenderer._draw_aero_modern(painter, s, primary_color_hex, border_color_hex, is_clicking)
            CursorRenderer._draw_mini_spinner(painter, s, border_color_hex)
        elif cursor_type == "ibeam":
            CursorRenderer._draw_ibeam(painter, s, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "sizewe":
            CursorRenderer._draw_resize_double(painter, s, 0.0, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "sizens":
            CursorRenderer._draw_resize_double(painter, s, 90.0, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "sizenwse":
            CursorRenderer._draw_resize_double(painter, s, 45.0, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "sizenesw":
            CursorRenderer._draw_resize_double(painter, s, 135.0, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "sizeall":
            CursorRenderer._draw_resize_all(painter, s, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "hand":
            if abs(tilt_deg) > 0.01:
                painter.rotate(tilt_deg)  # Follow the complete movement heading, including downward motion.
            CursorRenderer._draw_hand(painter, s, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "cross":
            CursorRenderer._draw_crosshair(painter, s, primary_color_hex, border_color_hex, is_clicking)
        elif cursor_type == "no":
            CursorRenderer._draw_not_allowed(painter, s, is_clicking)
        else:
            # Standard arrow with dynamic tilt
            if abs(tilt_deg) > 0.01:
                painter.rotate(tilt_deg)

            if theme_name == "neon_glow":
                CursorRenderer._draw_neon_glow(painter, s, primary_color_hex, border_color_hex, is_clicking)
            elif theme_name == "macos_fluid":
                CursorRenderer._draw_macos_fluid(painter, s, primary_color_hex, border_color_hex, is_clicking)
            elif theme_name == "cyber_arrow":
                CursorRenderer._draw_cyber_arrow(painter, s, primary_color_hex, border_color_hex, is_clicking)
            elif theme_name == "minimal_dot":
                CursorRenderer._draw_minimal_dot(painter, s, primary_color_hex, border_color_hex, is_clicking)
            else:
                CursorRenderer._draw_aero_modern(painter, s, primary_color_hex, border_color_hex, is_clicking)

        painter.restore()

    @staticmethod
    def draw_motion_ghosts(painter, points, win_x, win_y, theme_name, size,
                           fill, outline, cursor_type="normal", cloned=None):
        """Draw bounded, fading replicas behind the live cursor; preserve painter state."""
        count = 0
        for x, y, age in points[-9:]:
            local_x, local_y = x - win_x, y - win_y
            if age >= 1.0 or not (-45 <= local_x <= 340 and -45 <= local_y <= 340):
                continue
            painter.save()
            painter.setOpacity(0.37 * (1.0 - age) ** 1.6)
            if cloned is not None:
                image, hotspot_x, hotspot_y = cloned
                CursorRenderer.draw_cloned_cursor(painter, local_x, local_y,
                    0.94, 0.0, image, hotspot_x, hotspot_y, False)
            else:
                CursorRenderer.draw_cursor(painter, local_x, local_y, 0.94,
                    0.0, theme_name, size, fill, outline, False, cursor_type)
            painter.restore()
            count += 1
        return count

    @staticmethod
    def _create_standard_arrow_path(s: float) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(0.0, 0.0)                                # Tip
        path.lineTo(0.0 * s, 19.5 * s)                       # Left vertical edge
        path.lineTo(4.8 * s, 15.5 * s)                       # Left notch
        path.lineTo(8.5 * s, 23.5 * s)                       # Stem bottom-left
        path.lineTo(12.0 * s, 22.0 * s)                      # Stem bottom-right
        path.lineTo(8.3 * s, 14.2 * s)                       # Stem inner-right
        path.lineTo(15.2 * s, 14.2 * s)                      # Right wing tip
        path.closeSubpath()
        return path

    @staticmethod
    def _draw_aero_modern(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        path = CursorRenderer._create_standard_arrow_path(s)

        # 1. Soft drop shadow (offset +1.5, +2.5)
        painter.save()
        painter.translate(1.5 * s, 2.5 * s)
        painter.fillPath(path, QColor(0, 0, 0, 75))
        painter.restore()

        # 2. Main fill with subtle gradient
        fill_color = QColor(prim_hex)
        border_color = QColor(border_hex)

        grad = QLinearGradient(0, 0, 15 * s, 20 * s)
        if is_clicking:
            grad.setColorAt(0.0, fill_color.lighter(130))
            grad.setColorAt(1.0, fill_color)
        else:
            grad.setColorAt(0.0, fill_color)
            grad.setColorAt(1.0, fill_color.darker(110))

        painter.setBrush(QBrush(grad))
        pen = QPen(border_color, 1.8 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

        # 3. Inner highlight accent
        inner_path = QPainterPath()
        inner_path.moveTo(1.2 * s, 2.2 * s)
        inner_path.lineTo(1.2 * s, 16.5 * s)
        inner_path.lineTo(4.5 * s, 14.0 * s)
        highlight_pen = QPen(QColor(255, 255, 255, 140 if not is_clicking else 200), 1.0 * s)
        painter.setPen(highlight_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(inner_path)

    @staticmethod
    def _draw_macos_fluid(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        path = CursorRenderer._create_standard_arrow_path(s)

        # Drop shadow
        painter.save()
        painter.translate(2.0 * s, 3.0 * s)
        painter.fillPath(path, QColor(0, 0, 0, 90))
        painter.restore()

        # Crisp border & dark fill
        fill_color = QColor("#0F172A" if prim_hex == "#FFFFFF" else prim_hex)
        stroke_color = QColor("#FFFFFF" if border_hex == "#1E293B" else border_hex)

        painter.setBrush(QBrush(fill_color))
        pen = QPen(stroke_color, 2.2 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

    @staticmethod
    def _draw_neon_glow(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        path = CursorRenderer._create_standard_arrow_path(s)

        # Neon outer glow layers
        glow_color = QColor(border_hex if border_hex != "#1E293B" else "#00D2FF")
        for i in (3, 2, 1):
            glow_color.setAlpha(35 * i)
            glow_pen = QPen(glow_color, (3.5 + i * 2.5) * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # Core fill
        core_color = QColor(prim_hex)
        painter.setBrush(QBrush(core_color))
        core_pen = QPen(QColor("#FFFFFF"), 1.6 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(core_pen)
        painter.drawPath(path)

    @staticmethod
    def _draw_cyber_arrow(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        # Sci-Fi chevron style
        path = QPainterPath()
        path.moveTo(0.0, 0.0)
        path.lineTo(4.0 * s, 18.0 * s)
        path.lineTo(7.5 * s, 13.0 * s)
        path.lineTo(12.0 * s, 21.0 * s)
        path.lineTo(14.5 * s, 19.5 * s)
        path.lineTo(10.0 * s, 11.5 * s)
        path.lineTo(15.5 * s, 10.5 * s)
        path.closeSubpath()

        # Shadow
        painter.save()
        painter.translate(2.0 * s, 2.0 * s)
        painter.fillPath(path, QColor(0, 0, 0, 80))
        painter.restore()

        fill = QColor(prim_hex)
        border = QColor(border_hex)
        painter.setBrush(QBrush(fill))
        pen = QPen(border, 1.8 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.drawPath(path)

    @staticmethod
    def _draw_minimal_dot(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        # Precision gaming ring with center point
        # Hotspot at (0, 0)
        outer_radius = 9.0 * s
        inner_radius = 2.5 * s

        # Outer ring
        ring_color = QColor(border_hex)
        ring_color.setAlpha(180 if not is_clicking else 255)
        pen = QPen(ring_color, 2.0 * s)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0.0, 0.0), outer_radius, outer_radius)

        # Center dot
        dot_color = QColor(prim_hex)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(QPointF(0.0, 0.0), inner_radius, inner_radius)

    @staticmethod
    def _draw_wait_spinner(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        # Rotating circular spinner
        r = 11.0 * s
        angle = (time.time() * 450.0) % 360.0

        # Shadow
        painter.save()
        painter.translate(1.5 * s, 2.0 * s)
        pen_shadow = QPen(QColor(0, 0, 0, 70), 3.0 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_shadow)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(-r, -r, r * 2, r * 2), int(angle * 16), int(270 * 16))
        painter.restore()

        # Spinning Arc
        arc_color = QColor(border_hex if border_hex != "#1E293B" else "#00D2FF")
        pen_arc = QPen(arc_color, 3.0 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_arc)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(-r, -r, r * 2, r * 2), int(angle * 16), int(270 * 16))

        # Center pulse dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(prim_hex)))
        painter.drawEllipse(QPointF(0.0, 0.0), 2.8 * s, 2.8 * s)

    @staticmethod
    def _draw_mini_spinner(painter: QPainter, s: float, border_hex: str):
        # Mini spinner orbiting beside the arrow cursor
        mx, my = 17.0 * s, 11.0 * s
        r = 5.0 * s
        angle = (time.time() * 500.0) % 360.0

        pen = QPen(QColor(border_hex if border_hex != "#1E293B" else "#00D2FF"), 2.0 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(mx - r, my - r, r * 2, r * 2), int(angle * 16), int(260 * 16))

    @staticmethod
    def _draw_ibeam(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        """A centered, high-contrast text caret with clearly defined serifs."""
        path = QPainterPath()
        h, w = 10.0 * s, 4.8 * s
        path.moveTo(-w, -h); path.lineTo(w, -h)
        path.moveTo(0, -h); path.lineTo(0, h)
        path.moveTo(-w, h); path.lineTo(w, h)
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.translate(0.85*s, 1.2*s)
        painter.setPen(QPen(QColor(0, 0, 0, 105), 5.0*s,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)
        painter.translate(-0.85*s, -1.2*s)
        painter.setPen(QPen(QColor(border_hex), 4.3*s,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)
        painter.setPen(QPen(QColor(prim_hex), 2.25*s,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)
        painter.restore()

    @staticmethod
    def _draw_resize_double(painter: QPainter, s: float, angle_deg: float, prim_hex: str, border_hex: str, is_clicking: bool):
        painter.save()
        if abs(angle_deg) > 0.01:
            painter.rotate(angle_deg)

        # Double-ended arrow centered at (0, 0)
        path = QPainterPath()
        path.moveTo(-11.5 * s, 0.0)
        path.lineTo(-6.0 * s, -4.5 * s)
        path.lineTo(-6.0 * s, -1.8 * s)
        path.lineTo(6.0 * s, -1.8 * s)
        path.lineTo(6.0 * s, -4.5 * s)
        path.lineTo(11.5 * s, 0.0)
        path.lineTo(6.0 * s, 4.5 * s)
        path.lineTo(6.0 * s, 1.8 * s)
        path.lineTo(-6.0 * s, 1.8 * s)
        path.lineTo(-6.0 * s, 4.5 * s)
        path.closeSubpath()

        # Shadow
        painter.save()
        painter.translate(1.5 * s, 2.0 * s)
        painter.fillPath(path, QColor(0, 0, 0, 80))
        painter.restore()

        # Fill & Border
        painter.setBrush(QBrush(QColor(prim_hex)))
        painter.setPen(QPen(QColor(border_hex), 1.8 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

        # Center split notch
        pen_notch = QPen(QColor(border_hex), 1.5 * s)
        painter.setPen(pen_notch)
        painter.drawLine(QPointF(0.0, -2.5 * s), QPointF(0.0, 2.5 * s))

        painter.restore()

    @staticmethod
    def _draw_resize_all(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        # 4-way move cross pointer
        painter.save()
        # Draw horizontal double arrow
        CursorRenderer._draw_resize_double(painter, s * 0.9, 0.0, prim_hex, border_hex, is_clicking)
        # Draw vertical double arrow
        CursorRenderer._draw_resize_double(painter, s * 0.9, 90.0, prim_hex, border_hex, is_clicking)
        # Center precision dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(border_hex)))
        painter.drawEllipse(QPointF(0.0, 0.0), 3.0 * s, 3.0 * s)
        painter.restore()

    @staticmethod
    def _draw_hand(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        """Compact pointing hand with an exact fingertip hotspot and clear knuckles."""
        painter.save()
        painter.scale(s*.91, s*.91)
        shape=QPainterPath()
        shape.moveTo(-2.1,2.1)
        shape.cubicTo(-2.1,-.7,2.1,-.7,2.1,2.1)
        shape.lineTo(2.1,11.2)
        shape.cubicTo(3.4,8.1,6.8,8.2,7.1,11.6)
        shape.cubicTo(9.1,9.5,11.9,10.5,12.0,13.8)
        shape.cubicTo(14.1,12.9,16.4,14.5,16.2,17.2)
        shape.lineTo(15.0,21.0)
        shape.cubicTo(14.1,24.8,12.4,26.2,8.2,26.2)
        shape.lineTo(3.2,26.2)
        shape.cubicTo(.8,26.2,-1.0,25.2,-2.7,22.8)
        shape.lineTo(-7.9,15.9)
        shape.cubicTo(-10.1,12.8,-7.3,10.4,-5.0,12.0)
        shape.lineTo(-2.1,15.2)
        shape.closeSubpath()
        # Single silhouette without oversized finger joints or fingernails.
        painter.save()
        painter.translate(.7,1.0)
        painter.fillPath(shape,QColor(0,0,0,55))
        painter.restore()
        fill=QLinearGradient(-3,-2,15,28)
        base=QColor(prim_hex)
        fill.setColorAt(0,base.lighter(105))
        fill.setColorAt(1,base.darker(106))
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(QColor(border_hex),1.4,Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(shape)
        knuckles=QPainterPath()
        knuckles.moveTo(7.0,11.8);knuckles.cubicTo(7.1,13.4,6.6,15.4,6.4,16.3)
        knuckles.moveTo(12.0,13.9);knuckles.cubicTo(12.0,15.8,11.5,17.0,10.8,18.2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(border_hex),.8,Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(knuckles)
        painter.setPen(QPen(QColor(255,255,255,105),.7))
        painter.drawLine(QPointF(-.4,3),QPointF(-.4,10))
        painter.restore()

    @staticmethod
    def _draw_crosshair(painter: QPainter, s: float, prim_hex: str, border_hex: str, is_clicking: bool):
        # Precision crosshair centered at (0, 0)
        r = 9.0 * s
        gap = 3.0 * s
        length = 11.0 * s

        # Outer ring
        painter.setPen(QPen(QColor(border_hex), 1.6 * s))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0.0, 0.0), r, r)

        # Cross ticks
        pen_tick = QPen(QColor(prim_hex), 2.0 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_tick)
        painter.drawLine(QPointF(-length, 0.0), QPointF(-gap, 0.0))
        painter.drawLine(QPointF(gap, 0.0), QPointF(length, 0.0))
        painter.drawLine(QPointF(0.0, -length), QPointF(0.0, -gap))
        painter.drawLine(QPointF(0.0, gap), QPointF(0.0, length))

    @staticmethod
    def _draw_not_allowed(painter: QPainter, s: float, is_clicking: bool):
        # Prohibited circle with slash centered at (0, 0)
        r = 10.0 * s

        # Shadow
        painter.save()
        painter.translate(1.5 * s, 2.0 * s)
        painter.setPen(QPen(QColor(0, 0, 0, 70), 2.4 * s))
        painter.drawEllipse(QPointF(0.0, 0.0), r, r)
        painter.drawLine(QPointF(-r * 0.7, -r * 0.7), QPointF(r * 0.7, r * 0.7))
        painter.restore()

        # Red Ring & Slash
        pen_red = QPen(QColor("#EF4444"), 2.4 * s)
        painter.setPen(pen_red)
        painter.setBrush(QBrush(QColor(239, 68, 68, 35)))
        painter.drawEllipse(QPointF(0.0, 0.0), r, r)
        painter.drawLine(QPointF(-r * 0.7, -r * 0.7), QPointF(r * 0.7, r * 0.7))

    @staticmethod
    def draw_ripple(painter: QPainter, ripple):
        """Draws a smooth expanding click shockwave ring."""
        alpha_byte = int(max(0.0, min(1.0, ripple.current_alpha)) * 220)
        if alpha_byte <= 0:
            return

        r, g, b = ripple.color
        pen_color = QColor(r, g, b, alpha_byte)
        pen = QPen(pen_color, ripple.line_width * (1.0 - ripple.progress * 0.4))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(ripple.x, ripple.y), ripple.radius, ripple.radius)

    @staticmethod
    def draw_precision_dot(painter: QPainter, hw_x: float, hw_y: float, with_white_outline: bool = True):
        """
        Renders a precision targeting dot at the exact physical mouse position.
        Features a high-contrast multi-layer reticle:
        1. Outer dark drop shadow rim (for contrast on bright/white backgrounds)
        2. Crisp pure white outline ring
        3. Vibrant center pinpoint core
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if with_white_outline:
            # 1. Subtle dark drop shadow border
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
            painter.drawEllipse(QPointF(hw_x, hw_y), 3.8, 3.8)

            # 2. Crisp pure white outline
            painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
            painter.drawEllipse(QPointF(hw_x, hw_y), 2.8, 2.8)

            # 3. Vibrant center pinpoint core
            painter.setBrush(QBrush(QColor(255, 30, 86, 255)))
            painter.drawEllipse(QPointF(hw_x, hw_y), 1.5, 1.5)
        else:
            painter.setPen(QPen(QColor(0, 0, 0, 200), 2.5))
            painter.setBrush(QBrush(QColor(255, 0, 80, 255)))
            painter.drawEllipse(QPointF(hw_x, hw_y), 1.8, 1.8)

        painter.restore()
