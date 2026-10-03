"""Tiny monochrome mascot matching the FluidCursor application icon."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _draw_mascot(painter, ink):
    """One clear pointer silhouette, cut-out smile, and a tiny motion sparkle."""
    body = QPainterPath()
    body.moveTo(6.0, 26.5)
    body.cubicTo(4.9, 27.1, 4.2, 26.0, 5.0, 24.3)
    body.lineTo(12.3, 5.3)
    body.cubicTo(12.9, 3.6, 14.6, 3.6, 15.5, 5.1)
    body.lineTo(24.0, 24.5)
    body.cubicTo(24.9, 26.3, 23.9, 27.3, 22.6, 26.8)
    body.lineTo(17.3, 25.0)
    body.cubicTo(15.1, 24.2, 14.0, 24.3, 12.0, 25.0)
    body.lineTo(7.5, 26.6)
    body.cubicTo(6.8, 26.8, 6.3, 26.7, 6.0, 26.5)
    body.closeSubpath()
    painter.drawPath(body)
    # Negative-space facial features have no new colors or font dependencies.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor('black'), 2.0, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    for left in (9.0, 15.3):
        eye = QPainterPath()
        eye.moveTo(left, 19.2)
        eye.cubicTo(left + .7, 18.3, left + 1.25, 17.0, left + 2.4, 19.2)
        painter.drawPath(eye)
    painter.drawLine(12, 22, 17, 22)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(ink)
    # Single spark retains the source image's playful identity at tray scale.
    star = QPainterPath()
    star.moveTo(25.8, 7.3)
    star.cubicTo(26.2, 9.0, 26.6, 9.6, 28.1, 10.0)
    star.cubicTo(26.5, 10.4, 26.1, 11.1, 25.8, 12.8)
    star.cubicTo(25.4, 11.1, 24.8, 10.4, 23.5, 10.0)
    star.cubicTo(25.0, 9.6, 25.4, 9.0, 25.8, 7.3)
    star.closeSubpath()
    painter.drawPath(star)


def create_tray_icon(theme="dark"):
    """Theme-colored artwork, pre-rendered once; no work on cursor frames."""
    icon = QIcon()
    ink = QColor('#000000' if theme == 'light' else '#FFFFFF')
    for size in (16, 20, 24, 32, 48, 64):
        factor = 4
        high = QPixmap(size * factor, size * factor)
        high.fill(Qt.GlobalColor.transparent)
        painter = QPainter(high)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        scale = size * .91 * factor / 32
        painter.translate((size * factor - 32 * scale) / 2,
                          (size * factor - 32 * scale) / 2)
        painter.scale(scale, scale)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ink)
        _draw_mascot(painter, ink)
        painter.end()
        icon.addPixmap(high.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation))
    return icon
