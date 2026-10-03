"""Non-modal tray panel: avoids the Windows/Qt QMenu tracking loop blocking cursor frames."""
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSize, QPointF
from PyQt6.QtGui import QPalette, QColor, QIcon, QPixmap, QPainter, QPen
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame, QApplication


def _check_icon(ink):
    """Render the check as pixels: U+2713 triggers ~20 MB Qt font fallback."""
    image = QPixmap(36, 36)
    image.fill(Qt.GlobalColor.transparent)
    if ink:
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(ink), 4.5, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(QPointF(6, 18), QPointF(14, 26))
        painter.drawLine(QPointF(14, 26), QPointF(30, 9))
        painter.end()
    return QIcon(image)


class TrayPalette(QWidget):
    aboutToShow = pyqtSignal()
    aboutToHide = pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName('fluidTrayPalette')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedWidth(255)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#09090B'))
        palette.setColor(QPalette.ColorRole.Text, QColor('#F5F5F6'))
        self.setPalette(palette)
        self.setStyleSheet('''
            QMenu { background-color: #09090B; }
            QMenu::item:selected { background-color: #25252F; }
            QWidget#fluidTrayPalette {background-color: #09090B; border:1px solid #292931;
                border-radius:10px;}
            QPushButton {text-align:left; color:#F5F5F6; background:transparent; border:0;
                border-radius:5px; padding:8px 12px; font:13px 'Segoe UI';}
            QPushButton:hover, QPushButton:focus {background-color:#25252F;}
            QPushButton:disabled {color:#91919C;}
            QFrame#traySeparator {background-color:#303037; border:0; max-height:1px;}
        ''')
        self.layout_box = QVBoxLayout(self)
        self.layout_box.setContentsMargins(6, 7, 6, 7)
        self.layout_box.setSpacing(2)
        self._base_style = self.styleSheet()
        self._dark_style = self._base_style
        self._theme = "dark"
        self._check_icons = {"dark": _check_icon("#F5F5F6"),
                             "light": _check_icon("#233246")}
        self._blank_check_icon = _check_icon(None)
        self._language = "en"
        self._action_buttons = {}
        self.hide()

    def set_language(self, language):
        """Change menu direction and padding without recreating the tray process."""
        language = "ar" if language == "ar" else "en"
        if self._language == language:
            return
        self._language = language
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if language == "ar" else Qt.LayoutDirection.LeftToRight)
        self.setFixedWidth(306 if language == "ar" else 255)
        self._refresh_style()

    def set_theme(self, theme):
        """Restyle the quick menu without blocking the animated cursor."""
        theme = "light" if theme == "light" else "dark"
        if theme == self._theme: return
        self._theme = theme
        if theme == "light":
            self._base_style = (
                "QWidget#fluidTrayPalette {background:#FFFFFF; border:1px solid #D7E1EB; border-radius:10px;}"
                "QPushButton {text-align:left; color:#233246; background:transparent; border:0;"
                "border-radius:5px; padding:8px 12px; font:13px Segoe UI;}"
                "QPushButton:hover, QPushButton:focus {background:#E9F1F9;}"
                "QPushButton:disabled {color:#78879B;}"
                "QFrame#traySeparator {background:#DCE5EE; border:0; max-height:1px;}"
            )
        else:
            self._base_style = self._dark_style
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF" if theme == "light" else "#09090B"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#233246" if theme == "light" else "#F5F5F6"))
        self.setPalette(palette)
        self._refresh_style()
        for action, button in self._action_buttons.items():
            if action.isCheckable():
                button.setIcon(self._check_icons[theme] if action.isChecked()
                               else self._blank_check_icon)

    def _refresh_style(self):
        style = self._base_style
        if self._language == "ar":
            style += "\nQPushButton {text-align:right; padding:9px 14px; font-family: Segoe UI; font-size:13px;}"
        self.setStyleSheet(style)

    def addAction(self, action):
        button = QPushButton(self)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._action_buttons[action] = button
        def refresh():
            button.setText(action.text().replace('&', ''))
            if action.isCheckable():
                button.setIconSize(QSize(14, 14))
                button.setIcon(self._check_icons[self._theme] if action.isChecked()
                               else self._blank_check_icon)
            button.setEnabled(action.isEnabled())
        action.changed.connect(refresh)
        refresh()
        def fire():
            self.hide()
            action.trigger()
        button.clicked.connect(fire)
        self.layout_box.addWidget(button)
        return action

    def addSeparator(self):
        line = QFrame(self)
        line.setObjectName('traySeparator')
        line.setFixedHeight(1)
        self.layout_box.addSpacing(3)
        self.layout_box.addWidget(line)
        self.layout_box.addSpacing(3)
    def popup(self, pos):
        self.adjustSize()
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        x = min(max(bounds.left(), pos.x()), bounds.right() - self.width() + 1)
        y = max(bounds.top(), pos.y() - self.height())
        if y + self.height() > bounds.bottom():
            y = bounds.bottom() - self.height() + 1
        self.move(x, y)
        self.show()
        self.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        self.aboutToShow.emit()
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        self.aboutToHide.emit()
        super().hideEvent(event)

    def eventFilter(self, source, event):
        if self.isVisible() and event.type() == QEvent.Type.MouseButtonPress:
            widget = source if isinstance(source, QWidget) else None
            if widget is not None and widget is not self and not self.isAncestorOf(widget):
                self.hide()
        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
    def prewarm(self):
        """Create/show the Windows tool window before the animated cursor starts.

        First display can stall Qt for ~0.5 seconds on this PC; do it while the
        ordinary Windows cursor is still visible, never on the first right-click.
        """
        self.blockSignals(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        try:
            self.show()
            self.hide()
        finally:
            self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
            self.blockSignals(False)
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and self.isVisible():
            # Unlike QMenu, a non-modal tool window must dismiss itself when
            # the user activates another application or taskbar surface.
            if not self.isActiveWindow():
                self.hide()
