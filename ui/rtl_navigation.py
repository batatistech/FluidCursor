"""Mirror Qt Fluent's manually painted navigation items for Arabic settings."""
from PyQt6.QtCore import Qt, QRectF, QPoint
from PyQt6.QtGui import QPainter, QColor, QCursor
import qfluentwidgets.components.navigation.navigation_widget as nav

_original_paint = nav.NavigationPushButton.paintEvent
_original_indicator = nav.NavigationPushButton.indicatorRect
_original_base_indicator = nav.NavigationWidget.indicatorRect
_original_arrow = nav.NavigationTreeItem._drawDropDownArrow
_installed = False


def _indicator(self):
    if self.layoutDirection() != Qt.LayoutDirection.RightToLeft:
        return _original_indicator(self)
    return QRectF(self.width() - self._margins().right() - 4, 10, 3, 16)


def _paint(self, event):
    if self.layoutDirection() != Qt.LayoutDirection.RightToLeft:
        return _original_paint(self, event)
    p = QPainter(self)
    p.setRenderHints(QPainter.RenderHint.Antialiasing |
                     QPainter.RenderHint.TextAntialiasing |
                     QPainter.RenderHint.SmoothPixmapTransform)
    p.setPen(Qt.PenStyle.NoPen)
    if self.isPressed: p.setOpacity(.7)
    if not self.isEnabled(): p.setOpacity(.4)
    c = 255 if nav.isDarkTheme() else 0
    m = self._margins()
    bounds = self.rect()
    hit = bounds.translated(self.mapToGlobal(QPoint()))
    if self._canDrawIndicator():
        p.setBrush(QColor(c, c, c, 6 if self.isEnter else 10))
        p.drawRoundedRect(bounds, 5, 5)
        p.setBrush(nav.autoFallbackThemeColor(self.lightIndicatorColor, self.darkIndicatorColor))
        p.drawRoundedRect(self.indicatorRect(), 1.5, 1.5)
    elif ((self.isEnter and hit.contains(QCursor.pos())) or self.isAboutSelected) and self.isEnabled():
        p.setBrush(QColor(c, c, c, 6 if self.isAboutSelected else 10))
        p.drawRoundedRect(bounds, 5, 5)
    nav.drawIcon(self._icon, p, QRectF(self.width()-27.5-m.right(), 10, 16, 16))
    if not self.isCompacted:
        p.setFont(self.font())
        p.setPen(self.textColor())
        text_rect = QRectF(13+m.left(), 0, max(0, self.width()-57-m.left()-m.right()), self.height())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, self.text())
    p.end()


def _arrow(self):
    if self.layoutDirection() != Qt.LayoutDirection.RightToLeft:
        return _original_arrow(self)
    if self.isCompacted or self.treeWidget().isLeaf(): return
    p = QPainter(self)
    p.setRenderHints(QPainter.RenderHint.Antialiasing)
    if self.isPressed: p.setOpacity(.7)
    if not self.isEnabled(): p.setOpacity(.4)
    p.translate(20, 18)
    p.rotate(self.arrowAngle)
    nav.FIF.ARROW_DOWN.render(p, QRectF(-5, -5, 9.6, 9.6))
    p.end()


def _base_indicator(self):
    if self.layoutDirection() != Qt.LayoutDirection.RightToLeft:
        return _original_base_indicator(self)
    return QRectF(self.width() - self._margins().right() - 4, 10, 3, 16)


def install():
    """Only the disposable settings process imports this module."""
    global _installed
    if _installed: return
    nav.NavigationPushButton.paintEvent = _paint
    nav.NavigationPushButton.indicatorRect = _indicator
    nav.NavigationWidget.indicatorRect = _base_indicator
    nav.NavigationTreeItem._drawDropDownArrow = _arrow
    _installed = True
