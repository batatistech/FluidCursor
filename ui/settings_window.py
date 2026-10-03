"""
Windows 11 Settings-Style Fluent Control Center for FluidCursor.
Built natively on FluentWindow with authentic Windows 11 sidebar navigation:
- Dedicated "Basic" landing page for all essential settings (no preview/sandbox box to prevent crashes)
- Compact Master Status Card on Basic page
- 3 Tilt dynamics modes: Velocity, Full Physics (Forward Inertia), Full Physics (Opposing Inertia)
- Tilt angle multiplier slider 0-100%
- Generous right padding (24px) preventing controls from crowding the card edge
- Clean Mica dark theme with zero black boxes behind labels
- Safe hide-to-tray on window close
- Comprehensive reactive greying out of sliders, combos, and color pickers when parent options are disabled
"""

import math
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QSize, pyqtSignal, QEvent
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QApplication,
    QPushButton,
    QButtonGroup,
    QGridLayout,
    QLabel,
    QAbstractButton,
    QSizePolicy
)

from qfluentwidgets import (
    FluentWindow,
    NavigationItemPosition,
    ScrollArea,
    SmoothMode,
    SettingCardGroup as BaseSettingCardGroup,
    SwitchSettingCard as BaseSwitchSettingCard,
    SettingCard as BaseSettingCard,
    PushSettingCard as BasePushSettingCard,
    CardWidget,
    TitleLabel,
    CaptionLabel,
    StrongBodyLabel,
    BodyLabel,
    SwitchButton,
    Slider,
    ComboBox,
    ColorDialog,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    FluentIcon as FIF,
    IconWidget,
    setTheme,
    isDarkTheme,
    Theme
)

from core.config import CursorConfig
from core.i18n import tr
from core.theme import CursorRenderer
from core.physics import CursorPhysics
from core.fun_modes import FunEngine, MODES
from core.hotkeys import HOTKEY_CHOICES, normalize_hotkey
from core.theme_preference import interface_theme
from ui.theme_styles import theme_css
from ui.rtl_navigation import install as install_rtl_navigation
from core.fun_art import FunArtwork


ACCENTS = {"tilt": "#B9A4FF", "rotation": "#B9A4FF", "motion": "#4ECFFF",
           "physics": "#4ECFFF", "click": "#FFA96B", "shockwave": "#FFA96B",
           "color": "#EE99CA", "palette": "#EE99CA", "scheme": "#EE99CA",
           "visual": "#EE99CA", "windows": "#75D4BA", "recovery": "#75D4BA",
           "performance": "#75D4BA", "core": "#4ECFFF", "fun": "#F7C56F", "play": "#F7C56F"}


def section_color(title):
    color = next((value for word, value in ACCENTS.items() if word in title.lower()), "#73CFD9")
    return theme_css(color, not isDarkTheme())


class AccentCardMixin:
    accent = "#73CFD9"

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.accent)
        color.setAlpha(14 if self.isEnabled() else 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 7, 7)
        color.setAlpha(230 if self.isEnabled() else 65)
        painter.setBrush(color)
        painter.drawRoundedRect(2 if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self.width() - 5, 13, 3, max(2, self.height() - 26), 1, 1)
        painter.end()


class SettingCard(AccentCardMixin, BaseSettingCard):
    pass


class SwitchSettingCard(AccentCardMixin, BaseSwitchSettingCard):
    pass


class PushSettingCard(AccentCardMixin, BasePushSettingCard):
    pass


class SettingCardGroup(BaseSettingCardGroup):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.accent = section_color(title)
        self.titleLabel.setStyleSheet(
            f"color: {self.accent}; font-size: 16px; font-weight: 600; background: transparent;")
        name = title.lower()
        icon = (FIF.ROTATE if ('tilt' in name or 'rotation' in name) else
                FIF.SPEED_HIGH if ('motion' in name or 'physics' in name) else
                FIF.FINGERPRINT if ('click' in name or 'shockwave' in name) else
                FIF.PALETTE if ('color' in name or 'palette' in name or 'scheme' in name) else
                FIF.SETTING if ('system' in name or 'windows' in name) else
                FIF.GAME if ('fun' in name or 'play' in name) else
                FIF.SYNC if 'recovery' in name else FIF.HOME)
        header = QHBoxLayout()
        header.setSpacing(9)
        header.setContentsMargins(0, 0, 0, 0)
        self.headerIcon = IconWidget(icon, self)
        self.headerIcon.setFixedSize(17, 17)
        self.vBoxLayout.takeAt(0)  # Replace bare heading with icon + heading.
        header.addWidget(self.headerIcon)
        header.addWidget(self.titleLabel)
        header.addStretch(1)
        self.vBoxLayout.insertLayout(0, header)

    def addSettingCard(self, card):
        card.accent = self.accent
        super().addSettingCard(card)
        card.update()


class MirrorComboBox(ComboBox):
    """Qt Fluent draws its arrow at the right even for Arabic; mirror it."""
    def paintEvent(self, event):
        if self.layoutDirection() != Qt.LayoutDirection.RightToLeft:
            return super().paintEvent(event)
        QPushButton.paintEvent(self, event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isHover: painter.setOpacity(0.8)
        elif self.isPressed: painter.setOpacity(0.7)
        arrow = QRectF(12, self.height() / 2 - 5 + self.arrowAni.y, 10, 10)
        if isDarkTheme(): FIF.ARROW_DOWN.render(painter, arrow)
        else: FIF.ARROW_DOWN.render(painter, arrow, fill="#646464")
        painter.end()


class FunModeButton(QPushButton):
    """Accessible two-line mode tile: Qt button text/icon painting is not RTL-aware."""
    def __init__(self, title, description, icon, rtl, parent=None):
        super().__init__("", parent)
        self.setObjectName("funModeChoice")
        self.setCheckable(True)
        self.setMinimumHeight(88)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 9, 14, 9)
        row.setSpacing(12)
        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(42, 42)
        self.iconLabel.setPixmap(icon.pixmap(42, 42))
        self.iconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.iconLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        column = QVBoxLayout()
        column.setSpacing(3)
        self.titleLabel = QLabel(title, self)
        self.descriptionLabel = QLabel(description, self)
        align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        for label in (self.titleLabel, self.descriptionLabel):
            label.setAlignment(align)
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.iconLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        column.addWidget(self.titleLabel)
        column.addWidget(self.descriptionLabel)
        row.addLayout(column, 1)
        self.setAccessibleName(f"{title}: {description}")
        self.setToolTip(description)
        self.toggled.connect(self._update_label_colors)
        self._update_label_colors()

    def _update_label_colors(self, *_):
        light = not isDarkTheme()
        title = '#1C2A3B' if light else '#F7F5FF'
        desc = '#53657A' if light else '#B8B1CB'
        if not self.isEnabled():
            title, desc = ('#8998AA', '#8998AA') if light else ('#777582', '#777582')
        self.titleLabel.setStyleSheet(f'background:transparent; color:{title}; font:600 13px "Segoe UI";')
        self.descriptionLabel.setStyleSheet(f'background:transparent; color:{desc}; font:12px "Segoe UI";')

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange and hasattr(self, 'titleLabel'):
            self._update_label_colors()

class FluentColorButton(QPushButton):
    """
    Sleek Windows 11-style color picker pill button.
    Displays a circular color swatch preview alongside its uppercase HEX readout,
    and opens the Fluent ColorDialog when clicked.
    Visibly dims when disabled.
    """
    colorChanged = pyqtSignal(QColor)

    def __init__(self, color: QColor, title="Choose Color", parent=None):
        super().__init__(parent)
        self.currentColor = color
        self.dialogTitle = title
        self.setFixedHeight(32)
        self.setMinimumWidth(110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_ui()
        self.clicked.connect(self._show_color_dialog)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.EnabledChange:
            self._update_ui()
        super().changeEvent(event)

    def _update_ui(self):
        hex_str = self.currentColor.name().upper()
        # Render a crisp circular swatch
        pix = QPixmap(18, 18)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isEnabled():
            p.setBrush(QBrush(self.currentColor))
            border_col = QColor(255, 255, 255, 120) if self.currentColor.lightness() < 128 else QColor(0, 0, 0, 80)
            p.setPen(QPen(border_col, 1.2))
        else:
            # Muted dim swatch when disabled
            dim_col = QColor(self.currentColor)
            dim_col.setAlpha(60)
            p.setBrush(QBrush(dim_col))
            p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))

        p.drawEllipse(1, 1, 16, 16)
        p.end()

        self.setIcon(QIcon(pix))
        self.setText(f" {hex_str}")
        self.setStyleSheet(theme_css("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #F1F5F9;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 12px;
                font-weight: 600;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.22);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.04);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: #64748B;
            }
        """, not isDarkTheme()))

    def setColor(self, color: QColor):
        self.currentColor = color
        self._update_ui()

    def _show_color_dialog(self):
        try:
            dlg = ColorDialog(self.currentColor, self.dialogTitle, self.window())
            language = getattr(getattr(self.window(), 'config', None), 'language', 'en')
            dlg.yesButton.setText(tr('OK', language))
            dlg.cancelButton.setText(tr('Cancel', language))
            dlg.colorChanged.connect(self._on_dialog_color_changed)
            dlg.exec()
        except Exception as e:
            print(f"Color dialog error: {e}")

    def _on_dialog_color_changed(self, color: QColor):
        self.setColor(color)
        self.colorChanged.emit(color)


class SettingsWindow(FluentWindow):
    """
    Native Windows 11 Settings window with collapsible sidebar navigation,
    acrylic dark theme, grouped setting cards, and zero emoji clutter.
    """

    def __init__(self, config: CursorConfig, on_config_changed, cursor_mgr, cloner=None, on_destroy_callback=None, parent=None, on_language_changed=None):
        # Set the Fluent theme BEFORE creating native titlebar/navigation widgets.
        setTheme(Theme.LIGHT if interface_theme(config.ui_theme) == "light" else Theme.DARK)
        install_rtl_navigation()
        super().__init__(parent)
        # Mica inherits the desktop wallpaper and can produce a grey page with a
        # mismatched titlebar after switching themes. Use an opaque background.
        self.setMicaEffectEnabled(False)
        self.setCustomBackgroundColor(QColor("#F7F9FC"), QColor("#202124"))
        self.backgroundColorAni.stop()  # Avoid a transient color from the preceding OS theme.
        self.setBackgroundColor(self._normalBackgroundColor())
        self.config = config
        self.on_config_changed = on_config_changed
        self.cursor_mgr = cursor_mgr
        self.cloner = cloner
        self.on_destroy_callback = on_destroy_callback
        self.on_language_changed = on_language_changed
        self._responsive_sliders = []
        self._responsive_combos = []

        # Debounce timer for saving configuration to disk (prevents disk I/O lag while scrubbing sliders)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.config.save)
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self._refresh_descriptions)

        self._active_theme = interface_theme(self.config.ui_theme)
        self._light_theme = self._active_theme == "light"
        # Already selected before FluentWindow construction; children inherit it.
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.config.language == "ar" else Qt.LayoutDirection.LeftToRight)
        # Native Windows controls always belong at the physical top-right.
        self.titleBar.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setWindowTitle(self._t("FluidCursor Settings"))
        self.titleBar.titleLabel.setMinimumWidth(0)
        if self.config.language == "ar":
            self.titleBar.titleLabel.setFixedWidth(self.titleBar.titleLabel.fontMetrics().horizontalAdvance(self.windowTitle()) + 16)
            self.titleBar.titleLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if self.config.language == "ar":
            self.setFont(QFont("Segoe UI", 10))
        self.resize(960, 720)
        self.setMinimumSize(760, 540)

        # Clean top title bar: remove return button
        self.navigationInterface.setReturnButtonVisible(False)
        # The menu button occupies the same top-right hit area as window controls in RTL.
        self.navigationInterface.setMenuButtonVisible(self.config.language != "ar")
        if self.config.language == 'ar':
            # Reserve the titlebar row after hiding the overlapping hamburger.
            self.navigationInterface.panel.vBoxLayout.setContentsMargins(0, 48, 0, 5)
        self.navigationInterface.setExpandWidth(218 if self.config.language == "ar" else 200)

        # Global stylesheet ensuring clean dark theme without black boxes behind labels
        # and distinct muted styling for disabled controls
        self.setStyleSheet("""
            ScrollArea, QScrollArea {
                border: none;
                background-color: transparent;
            }
            QLabel, BodyLabel, CaptionLabel, StrongBodyLabel, TitleLabel {
                background: transparent !important;
            }
            CardWidget {
                background-color: #2B2B2B;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            CaptionLabel:disabled {
                color: #64748B !important;
            }
            QSlider:disabled::sub-page:horizontal {
                background: #475569;
            }
            QSlider:disabled::handle:horizontal {
                background-color: #334155;
                border: 1px solid #1E293B;
            }
            QSlider:disabled::groove:horizontal {
                background-color: #334155;
            }
        """)

        self._init_sub_interfaces()
        self._apply_fun_exclusivity()
        self._apply_palette(self)
        self._appearance_timer = QTimer(self)
        self._appearance_timer.setInterval(4000)
        self._appearance_timer.timeout.connect(self._check_os_appearance)
        if self.config.ui_theme == "system": self._appearance_timer.start()

        # Expand sidebar by default for authentic Windows 11 Settings layout
        QTimer.singleShot(50, self._expand_navigation)

    def _apply_palette(self, root):
        """Recolor OUR styles only, never Qt Fluent's built-in light controls."""
        markers = ('#2B2B2B', '#F3F6FC', '#AEBCCC', '#E6F7FF', '#AAC1D5',
                   '#25292F', '#24232D', '#292C36', '#302F39', '#29263D',
                   '#203332', '#58DABF', '#E3B66A', '#A6AFBD', '#B8B1CB',
                   '#D5C6FF', '#F7F5FF', '#91E5D0', '#D6D1E4', '#D9CDFF', '#F1F5F9', '#F4F5F8', '#343044', '#414852',
                   '#464050', '#484650')
        for widget in (root, *root.findChildren(QWidget)):
            if widget is not self and not isinstance(widget, (QLabel, CardWidget, QFrame, QPushButton)):
                continue
            style = widget.styleSheet()
            original = getattr(widget, '_fc_dark_style', None)
            if original is None:
                if widget is not self and not any(marker.lower() in style.lower() for marker in markers):
                    continue
                original = style
            elif style not in (original, theme_css(original, True)):
                original = style  # An app-owned control updated its state-specific CSS.
            widget._fc_dark_style = original
            colored = theme_css(original, self._light_theme)
            if colored != style: widget.setStyleSheet(colored)

    def _check_os_appearance(self):
        if self.config.ui_theme != "system": return
        if interface_theme("system") != self._active_theme:
            self._appearance_timer.stop()
            if self.on_language_changed: self.on_language_changed()

    def _expand_navigation(self):
        self.navigationInterface.panel.expand()
        self._adjust_control_widths()
        QTimer.singleShot(200, self._refresh_descriptions)

    def _init_sub_interfaces(self):
        """Build the landing and recovery pages now; other pages on first visit."""
        self._deferred_pages = {}
        self.basic_interface = self._create_basic_interface()
        self._tune_page_labels(self.basic_interface)
        self.basic_interface.setObjectName("basicInterface")
        self.addSubInterface(self.basic_interface, FIF.HOME, self._t("Essentials"))

        # The most useful settings are closest to the landing page.
        self.app_interface = self._add_deferred_page(
            "appearanceInterface", FIF.PALETTE, self._t("Appearance"),
            self._create_appearance_interface)
        self.motion_interface = self._add_deferred_page(
            "motionInterface", FIF.SPEED_HIGH, self._t("Motion"),
            self._create_motion_interface)
        self.click_interface = self._add_deferred_page(
            "clickInterface", FIF.FINGERPRINT, self._t("Click effects"),
            self._create_click_interface)
        self.tilt_interface = self._add_deferred_page(
            "tiltInterface", FIF.ROTATE, self._t("Tilt & rotation"),
            self._create_tilt_interface)
        self.fun_interface = self._add_deferred_page(
            "funInterface", FIF.GAME, self._t("Fun!"), self._create_fun_interface)
        self.adv_interface = self.motion_interface  # Legacy alias.

        # Keep recovery available immediately, including for existing integrations.
        self.sys_interface = self._create_system_interface()
        self._tune_page_labels(self.sys_interface)
        self.sys_interface.setObjectName("systemInterface")
        self.addSubInterface(
            self.sys_interface, FIF.SETTING, self._t("System & recovery"),
            NavigationItemPosition.BOTTOM)
        self.stackedWidget.currentChanged.connect(self._load_active_page)

    def _add_deferred_page(self, name, icon, label, factory):
        host = QWidget()
        host.setObjectName(name)
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        self._deferred_pages[host] = factory
        self.addSubInterface(host, icon, label)
        return host

    def _load_active_page(self, _index):
        self._load_page(self.stackedWidget.currentWidget())

    def _load_page(self, host):
        """Populate a deferred page once, using the latest config values."""
        factory = self._deferred_pages.pop(host, None)
        if factory is not None:
            page = factory()
            self._tune_page_labels(page)
            host.layout().addWidget(page)
            self._adjust_control_widths()
            self._apply_palette(page)
            QTimer.singleShot(180, self._refresh_descriptions)

    def _tune_page_labels(self, scroll):
        """Allow descriptions to wrap instead of forcing horizontal scrolling."""
        for card in scroll.findChildren(BaseSettingCard):
            label = card.contentLabel
            card.setFixedHeight(112 if self.config.language == "ar" else 102 if len(label.text()) > 65 else 86 if label.text() else 62)
            card.vBoxLayout.setSpacing(6 if self.config.language == "ar" else 5)
            # Qt Fluent uses a zero right margin, leaving RTL icons against the edge.
            card.hBoxLayout.setContentsMargins(20, 0, 18 if self.config.language == "ar" else 0, 0)
            card.titleLabel.setMinimumWidth(0)
            card.titleLabel.setWordWrap(self.config.language == "ar")
            if self.config.language == "ar": card.titleLabel.setMinimumHeight(21)
            card.titleLabel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            card.titleLabel.setStyleSheet("color: #F3F6FC; font-family: Segoe UI; font-size: 14px; font-weight: 600;" if self.config.language == "ar" else
                                         "color: #F3F6FC; font-size: 13px; font-weight: 600;")
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            if self.config.language == "ar": label.setMinimumHeight(22)
            label.setStyleSheet("color: #AEBCCC; font-family: Segoe UI; font-size: 13px;" if self.config.language == "ar" else
                                "color: #AEBCCC; font-size: 12px;")
            # Qt mirrors AlignLeft visually under RTL; AlignRight puts Arabic text on the physical LEFT.
            align = Qt.AlignmentFlag.AlignLeft
            card.titleLabel.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            label.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            label.setToolTip(label.text())
            card.vBoxLayout.setAlignment(label, Qt.AlignmentFlag(0))
            card.vBoxLayout.setAlignment(card.titleLabel, Qt.AlignmentFlag(0))
            card._full_description = label.text()
            # The library inserts an expanding spacer before every control;
            # remove it so the text column receives the available width.
            if card.hBoxLayout.count() > 4 and card.hBoxLayout.itemAt(4).spacerItem():
                card.hBoxLayout.takeAt(4)
            card.hBoxLayout.setStretch(2, 1)
        self._localize_page(scroll)
        self._queue_description_refresh()

    def _t(self, text):
        return tr(text, self.config.language)

    def _localize_page(self, root):
        """Translate the visible Qt control tree once, outside the cursor loop."""
        for switch in root.findChildren(SwitchButton):
            switch.setOnText(""); switch.setOffText("")
        if self.config.language != 'ar': return
        for widget in [root, *root.findChildren(QWidget)]:
            if isinstance(widget, QLabel) or isinstance(widget, QAbstractButton):
                value = widget.text()
                translated = self._t(value)
                if translated != value:
                    widget.setText(translated)
            if isinstance(widget, ComboBox):
                widget.blockSignals(True)
                try:
                    for i in range(widget.count()):
                        value = widget.itemText(i)
                        widget.setItemText(i, self._t(value))
                finally:
                    widget.blockSignals(False)
            for getter, setter in (('toolTip', 'setToolTip'), ('accessibleName', 'setAccessibleName')):
                value = getattr(widget, getter)()
                if value:
                    translated = self._t(value)
                    if translated != value:
                        getattr(widget, setter)(translated)
        for card in root.findChildren(BaseSettingCard):
            if hasattr(card, '_full_description'):
                card._full_description = card.contentLabel.text()
                card._rendered_description = card._full_description
        self._queue_description_refresh()

    def _queue_description_refresh(self):
        # Coalesce resize events instead of repeatedly laying out every card.
        if hasattr(self, '_layout_timer'):
            self._layout_timer.start(55)

    def _elide_card(self, card):
        """Keep full copy and measure only once its card has real geometry."""
        try:
            label = card.contentLabel
            full = getattr(card, "_full_description", label.text())
            rendered = getattr(card, "_rendered_description", full)
            if label.text() != rendered:
                full = label.text()  # A live setting changed the description.
                card._full_description = full
            if label.text() != full:
                label.setText(full)
            card._rendered_description = full
            label.setToolTip(full)
            card.titleLabel.setToolTip(card.titleLabel.text())
            if card.width() < 320 or label.width() < 150:
                return  # Qt has not yet assigned final widths.
            needed = label.fontMetrics().boundingRect(
                0, 0, max(150, label.width() - 4), 600,
                Qt.TextFlag.TextWordWrap, full).height()
            heading_height = card.titleLabel.fontMetrics().boundingRect(
                0, 0, max(100, card.titleLabel.width()), 160,
                Qt.TextFlag.TextWordWrap, card.titleLabel.text()).height()
            extra_heading = max(0, heading_height - card.titleLabel.fontMetrics().height())
            height = max(96 if self.config.language == "ar" else 82,
                         min(180, needed + (70 if self.config.language == "ar" else 55) + extra_heading)) if full else 62
            if card.height() != height:
                card.setFixedHeight(height)
        except RuntimeError:  # Deferred page was destroyed.
            return

    def _refresh_descriptions(self):
        for card in self.findChildren(BaseSettingCard):
            if hasattr(card, "_full_description"):
                self._elide_card(card)

    def _adjust_control_widths(self):
        """Keep controls usable when the sidebar or window width changes."""
        nav = self.navigationInterface.width()
        free_width = self.width() - nav
        slider_width = max(100, min(160, (free_width - 390) // 2))
        for slider in self._responsive_sliders:
            if slider.width() != slider_width:
                slider.setFixedWidth(slider_width)
        for combo, normal_width in self._responsive_combos:
            combo.setFixedWidth(max(150, min(normal_width, free_width - 360)))
        if hasattr(self, "_hotkey_badge"):
            self._hotkey_badge.setVisible(free_width >= 670)
        self._queue_description_refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if self.config.language == "ar":
            self.titleBar.setGeometry(0, 0, self.width(), self.titleBar.height())
            self.titleBar.raise_()
        QTimer.singleShot(0, self._queue_description_refresh)
        QTimer.singleShot(250, self._refresh_descriptions)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "config") and self.config.language == "ar":
            # FluentWindow offsets its titlebar for a LEFT sidebar. RTL puts
            # the sidebar on the right, so use the full physical title width.
            self.titleBar.setGeometry(0, 0, self.width(), self.titleBar.height())
            self.titleBar.raise_()
        if hasattr(self, "_responsive_sliders"):
            self._adjust_control_widths()

    def _create_page_scaffold(self, title_text: str, subtitle_text: str):
        scroll = ScrollArea()
        # Avoid a 600ms 20+ repaint animation for every wheel notch.
        # Native Qt wheel scrolling also preserves high-resolution trackpad deltas.
        scroll.setSmoothMode(SmoothMode.NO_SMOOTH, Qt.Orientation.Vertical)
        scroll.verticalScrollBar().setSingleStep(32)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidgetResizable(True)

        view = QWidget()
        view.setStyleSheet("background: transparent;")
        scroll.setWidget(view)

        layout = QVBoxLayout(view)
        layout.setContentsMargins(24, 22, 24, 28)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = TitleLabel(title_text)
        title.setStyleSheet("font-size: 26px; font-weight: 600; color: #E6F7FF; background: transparent;")
        if self.config.language == "ar": title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)

        if subtitle_text:
            sub = CaptionLabel(subtitle_text)
            sub.setStyleSheet("font-size: 13px; color: #AAC1D5; background: transparent; margin-bottom: 4px;")
            sub.setWordWrap(True)
            if self.config.language == "ar": sub.setAlignment(Qt.AlignmentFlag.AlignLeft)
            sub.setMinimumWidth(0)
            sub.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            layout.addWidget(sub)

        return scroll, view, layout

    # =========================================================================
    # Helpers for Setting Cards (With 24px Right Padding to Avoid Edge Crowding)
    # =========================================================================
    def _create_slider_card(self, icon, title, desc, min_v, max_v, cur_v, on_change, unit=""):
        card = SettingCard(icon, title, desc)
        slider = Slider(Qt.Orientation.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(int(cur_v))
        slider.setFixedWidth(160)
        slider.setAccessibleName(title)
        self._responsive_sliders.append(slider)

        val_lbl = CaptionLabel(f"{int(cur_v)}{unit}")
        val_lbl.setStyleSheet("""
            CaptionLabel {
                color: #38BDF8;
                font-weight: 600;
                min-width: 52px;
                background: transparent;
            }
            CaptionLabel:disabled {
                color: #64748B !important;
            }
        """)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_lbl.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        def on_val(v):
            val_lbl.setText(f"{v}{unit}")
            on_change(v)

        slider.valueChanged.connect(on_val)
        card.hBoxLayout.addWidget(slider)
        card.hBoxLayout.addSpacing(10)
        card.hBoxLayout.addWidget(val_lbl)
        card.hBoxLayout.addSpacing(24)  # Generous padding from right edge
        return card, slider, val_lbl

    def _create_combo_card(self, icon, title, desc, items, cur_idx, on_change, width=240):
        card = SettingCard(icon, title, desc)
        combo = MirrorComboBox()
        combo.addItems(items)
        if self.config.language == "ar":
            combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            combo.setStyleSheet(combo.styleSheet() +
                                "\nComboBox { padding: 5px 12px 6px 34px; text-align: right; }")
        combo.setCurrentIndex(cur_idx)
        combo.setFixedWidth(width)
        combo.setAccessibleName(title)
        self._responsive_combos.append((combo, width))
        combo.currentIndexChanged.connect(on_change)
        card.hBoxLayout.addWidget(combo)
        card.hBoxLayout.addSpacing(24)  # Generous padding from right edge
        return card, combo

    def _create_color_card(self, icon, title, desc, cur_hex, on_change):
        card = SettingCard(icon, title, desc)
        btn = FluentColorButton(QColor(cur_hex), self._t(title), self)
        btn.colorChanged.connect(on_change)
        card.hBoxLayout.addWidget(btn)
        card.hBoxLayout.addSpacing(24)  # Generous padding from right edge
        return card, btn


    def _create_master_card(self, parent_view, prefix="basic"):
        """Compact one-line status; recovery actions live in System & recovery."""
        card = CardWidget(parent_view)
        card.setObjectName("cursorStatusHero")
        card.setStyleSheet("CardWidget#cursorStatusHero {background:#25292F; border:1px solid #414852; border-radius:9px;}")
        card.setFixedHeight(56)
        line = QHBoxLayout(card)
        line.setContentsMargins(14, 8, 14, 8)
        line.setSpacing(12)
        dot = CaptionLabel("\u25cf", card)
        dot.setStyleSheet("color:#58DABF; font-size:15px; background:transparent;")
        line.addWidget(dot)
        title = StrongBodyLabel("FluidCursor active" if self.config.enabled else "FluidCursor paused", card)
        title.setStyleSheet("color:#F4F5F8; font-size:13px; font-weight:600; background:transparent;")
        line.addWidget(title)
        subtitle = CaptionLabel("", card)
        subtitle.setStyleSheet("color:#A6AFBD; font-size:11px; background:transparent;")
        line.addWidget(subtitle)
        line.addStretch(1)
        toggle = SwitchButton(card)
        toggle.setAccessibleName("Pause or resume FluidCursor")
        toggle.setChecked(self.config.enabled)
        toggle.checkedChanged.connect(self._toggle_master)
        line.addWidget(toggle)
        setattr(self, f"{prefix}_lbl_master_title", title)
        setattr(self, f"{prefix}_lbl_master_desc", subtitle)
        setattr(self, f"{prefix}_switch_master", toggle)
        setattr(self, f"{prefix}_status_dot", dot)
        self._sync_master_cards(self.config.enabled)
        return card

    # =========================================================================
    # 1. Basic Interface (Essential Landing Page - NO CLUTTER, EXCLUSIVE MASTER CARD)
    # =========================================================================
    def _create_fun_interface(self):
        scroll, view, layout = self._create_page_scaffold(
            "Fun lab", "One playful cursor experience at a time. Your regular setup is never overwritten.")
        self.fun_banner = CardWidget(view)
        self.fun_banner.setObjectName("funStatusBanner")
        banner_layout = QHBoxLayout(self.fun_banner)
        banner_layout.setContentsMargins(14, 10, 14, 10)
        banner_layout.setSpacing(14)
        banner_icon = IconWidget(FIF.GAME, self.fun_banner)
        banner_icon.setFixedSize(20, 20)
        banner_layout.addWidget(banner_icon)
        banner_text = QVBoxLayout()
        self.fun_status_title = StrongBodyLabel()
        self.fun_status_description = CaptionLabel()
        self.fun_status_description.setWordWrap(True)
        banner_text.addWidget(self.fun_status_title)
        banner_text.addWidget(self.fun_status_description)
        banner_layout.addLayout(banner_text, 1)
        self.fun_master = SwitchButton(self.fun_banner)
        self.fun_master.setAccessibleName("Enable exclusive Fun mode")
        self.fun_master.setToolTip("Fun overrides normal controls. Turn off to unlock them.")
        self.fun_master.setChecked(self.config.fun_enabled)
        self.fun_master.checkedChanged.connect(self._set_fun_enabled)
        banner_layout.addWidget(self.fun_master)
        layout.addWidget(self.fun_banner)
        selector = CardWidget(view)
        selector.setObjectName("funModeSelector")
        selector.setStyleSheet("CardWidget#funModeSelector {background: #24232D; border: 1px solid #464050; border-radius: 12px;}")
        selector_layout = QVBoxLayout(selector)
        selector_layout.setContentsMargins(18, 16, 18, 18)
        selector_layout.setSpacing(10)
        label = StrongBodyLabel("Choose your experience")
        label.setStyleSheet("font-size: 16px; color: #F7F5FF; background: transparent;")
        selector_layout.addWidget(label)
        hint = CaptionLabel("Select a mode below. Only your chosen mode runs.")
        hint.setStyleSheet("color: #B8B1CB; background: transparent;")
        selector_layout.addWidget(hint)
        self.fun_mode_group = QButtonGroup(self)
        self.fun_mode_group.setExclusive(True)
        self.fun_mode_buttons = {}
        choices = (("tile", "FOLLOWER TILE", "A tiny glassy companion", "#AD98FA"),
                   ("stardust", "STARDUST", "Gold dust that follows your path", "#F5C86D"),
                   ("chain", "LINKED CHAIN", "A swinging chain with real joints", "#AFC6EE"),
                   ("comet", "COMET", "An icy comet and glowing fragments", "#74E5F4"),
                   ("orbit", "ORBIT", "Tiny satellites circle your pointer", "#A0ACFF"),
                   ("yoyo", "BOUNCY YO-YO", "A tethered ball; click to launch it", "#FD9F77"),
                   ("ribbon", "SILK RIBBON", "A flowing silk strip with inertia", "#F4A0D4"),
                   ("spinner", "FIDGET SPINNER", "Move or click to spin; coast to a stop", "#75DFF2"))
        selector_grid = QGridLayout()
        selector_grid.setSpacing(10)
        selector_grid.setColumnStretch(0, 1)
        selector_grid.setColumnStretch(1, 1)
        selector_layout.addLayout(selector_grid)
        for index, (mode, title, desc, accent) in enumerate(choices):
            # Qt mirrors grid column zero under RTL: the first choice is top-right.
            # Keep that order; replace only QPushButton's broken mixed icon/text paint.
            button = FunModeButton(self._t(title), self._t(desc),
                                   self._fun_thumbnail(mode), self.config.language == "ar", selector)
            button.setStyleSheet(self._fun_button_style(accent))
            self.fun_mode_group.addButton(button, index)
            self.fun_mode_buttons[mode] = button
            selector_grid.addWidget(button, index // 2, index % 2)
            button.clicked.connect(lambda checked=False, i=index: self._set_fun_mode(i))
        self.fun_mode_buttons.get(self.config.fun_mode, self.fun_mode_buttons["chain"]).setChecked(True)
        layout.addWidget(selector)
        options = SettingCardGroup("Fine-tune your mode", view)
        self.fun_card_smooth, self.fun_slider_smooth, self.fun_lbl_smooth = self._create_slider_card(
            FIF.SPEED_HIGH, "Motion smoothness", "Low: responsive / High: gently floating. Independent of normal motion.",
            0, 100, self.config.fun_smoothness, self._set_fun_smoothness, "%")
        options.addSettingCard(self.fun_card_smooth)
        self.fun_card_distance, self.fun_slider_distance, _ = self._create_slider_card(
            FIF.MOVE, "Tile distance", "How far your companion follows behind the pointer.",
            14, 48, self.config.fun_tile_distance, self._set_fun_distance, " px")
        options.addSettingCard(self.fun_card_distance)
        self.fun_card_particles, self.fun_slider_particles, _ = self._create_slider_card(
            FIF.CLOUD, "Particle intensity", "Spark frequency; zero turns them off. Maximum 16.",
            0, 100, self.config.fun_particles, self._set_fun_particles, "%")
        options.addSettingCard(self.fun_card_particles)
        self.fun_card_chain, self.fun_slider_chain, _ = self._create_slider_card(
            FIF.LINK, "Chain length", "More connected links for a longer, swinging chain.",
            6, 32, min(32, self.config.fun_chain_length), self._set_fun_chain, " links")
        options.addSettingCard(self.fun_card_chain)
        self.fun_card_swing, self.fun_slider_swing, _ = self._create_slider_card(
            FIF.SPEED_HIGH, "Chain liveliness", "0: weighted and calm · 100: lively swinging.",
            0, 100, self.config.fun_chain_swing, self._set_fun_swing, "%")
        options.addSettingCard(self.fun_card_swing)
        self.fun_card_orbit, self.fun_slider_orbit, _ = self._create_slider_card(
            FIF.GAME, "Satellites", "Number of orbiting companions, from two to six.",
            2, 6, self.config.fun_orbit_count, self._set_fun_orbit, "")
        options.addSettingCard(self.fun_card_orbit)
        self.fun_card_yoyo, self.fun_slider_yoyo, _ = self._create_slider_card(
            FIF.LINK, "Yo-yo string length", "How far the yo-yo can swing from the pointer.",
            45, 120, self.config.fun_yoyo_length, self._set_fun_yoyo, " px")
        options.addSettingCard(self.fun_card_yoyo)
        self.fun_card_spinner, self.fun_slider_spinner, _ = self._create_slider_card(
            FIF.ROTATE, "Spin energy", "Movement and clicks spin the toy; it coasts to rest.",
            0, 100, self.config.fun_spinner_speed, self._set_fun_spinner, "%")
        options.addSettingCard(self.fun_card_spinner)
        self.fun_card_ribbon, self.fun_slider_ribbon, _ = self._create_slider_card(
            FIF.SPEED_HIGH, "Ribbon flow", "Lower: calmer silk. Higher: more lively motion.",
            0, 100, self.config.fun_ribbon_flow, self._set_fun_ribbon, "%")
        options.addSettingCard(self.fun_card_ribbon)
        layout.addWidget(options)
        self._refresh_fun_controls()
        return scroll

    def _fun_button_style(self, accent):
        alignment = "right" if self.config.language == "ar" else "left"
        return ("QPushButton#funModeChoice { text-align: " + alignment + "; padding: 8px 10px; "
                "font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; "
                "color: #DBDAE6; background: #302F39; border: 1px solid #484650; border-radius: 10px; }"
                "QPushButton#funModeChoice:hover { background: #3A3846; border-color: " + accent + "; }"
                "QPushButton#funModeChoice:checked { color: #FFFFFF; font-weight: 600; "
                "background: #343241; border: 2px solid " + accent + "; }"
                "QPushButton#funModeChoice:disabled { color: #777582; background: #292830; border-color: #34323D; }")
    def _fun_thumbnail(self, mode):
        pix=QPixmap(54,54)
        pix.fill(Qt.GlobalColor.transparent)
        painter=QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg={'tile':'#302649','stardust':'#574127',
            'chain':'#273448','comet':'#174453','orbit':'#292B50',
            'yoyo':'#52332D','ribbon':'#502949','spinner':'#1B424B'}[mode]
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(bg))
        painter.drawRoundedRect(1,1,52,52,12,12)
        if mode=='tile':
            painter.translate(27,27); painter.scale(1.35,1.35)
            FunArtwork.tile(painter)
        elif mode=='stardust':
            painter.translate(27,13); painter.scale(1.48,1.48)
            FunArtwork.star(painter)
        elif mode=='chain':
            points=[[41-i*4,9+i*5] for i in range(7)]
            FunArtwork.chain(painter,points,0,0)
        elif mode=='comet':
            painter.translate(42,27);painter.scale(1.28,1.28)
            FunArtwork.comet(painter)
        elif mode=='orbit':
            painter.translate(27,27)
            FunArtwork.orbit(painter,4,clock=0)
        elif mode=='yoyo':
            FunArtwork.yoyo(painter,(14,8),[37,38,0,0],0,0)
        elif mode=='ribbon':
            FunArtwork.ribbon(painter,[[44-i*1.5,12+i*2] for i in range(17)],0,0)
        elif mode=='spinner':
            painter.translate(27,27)
            FunArtwork.spinner(painter,32)
        painter.end()
        return QIcon(pix)

    def _create_basic_interface(self) -> QWidget:
        scroll, view, layout = self._create_page_scaffold(
            "Your cursor, your way",
            "Adjust the essentials here. Your changes take effect immediately."
        )

        # Compact Master Card (Exclusive to Basic page)
        master_card = self._create_master_card(view, prefix="basic")
        layout.addWidget(master_card)

        # Essential Controls Group
        group_ess = SettingCardGroup("Movement & feel", view)

        # 1. Smoothness
        card_smooth, self.b_slider_resp, self.b_lbl_resp = self._create_slider_card(
            FIF.SPEED_HIGH,
            "Movement smoothness",
            "Adjusts tracking responsiveness and fluid momentum",
            5, 100, self.config.responsiveness * 100,
            self._update_resp,
            "%"
        )
        group_ess.addSettingCard(card_smooth)

        # 2. Cursor Size
        card_size, self.b_slider_size, self.b_lbl_size = self._create_slider_card(
            FIF.ZOOM,
            "Cursor size",
            "Physical display size of the cursor pointer",
            18, 54, self.config.cursor_size,
            self._update_size,
            " px"
        )
        group_ess.addSettingCard(card_size)

        # 3. Click Compression Scale
        card_shrink, self.b_slider_shrink, self.b_lbl_shrink = self._create_slider_card(
            FIF.MOVE,
            "Click compression scale",
            "Dynamic scale shrink factor applied during mouse clicks",
            40, 95, self.config.shrink_factor * 100,
            self._update_shrink,
            "%"
        )
        group_ess.addSettingCard(card_shrink)

        # 4. Dynamic Cursor Tilt
        self.b_card_tilt = SwitchSettingCard(
            FIF.ROTATE,
            "Dynamic cursor tilt",
            "Smoothly tilts cursor along movement direction (defaults to velocity tilt). Fine-tune angle, deadzone, and decay in the Tilt page.",
            parent=group_ess
        )
        self.b_card_tilt.setChecked(self.config.tilt_enabled)
        self.b_card_tilt.checkedChanged.connect(self._update_tilt)
        group_ess.addSettingCard(self.b_card_tilt)

        # 5. Clone System Cursor
        self.b_card_clone = SwitchSettingCard(
            FIF.SYNC,
            "Clone active Windows cursor",
            "Uses your installed Windows cursor scheme with native hotspot alignment",
            parent=group_ess
        )
        self.b_card_clone.setChecked(self.config.use_system_cursor_clone)
        self.b_card_clone.checkedChanged.connect(self._toggle_clone)
        group_ess.addSettingCard(self.b_card_clone)

        layout.addWidget(group_ess)

        # Quick Toggles Group (Clean secondary essentials)
        group_quick = SettingCardGroup("Quick switches", view)

        # Snap on Click Accuracy
        self.b_card_snap = SwitchSettingCard(
            FIF.FINGERPRINT,
            "Snap to hardware position on click",
            "Instantly aligns visual cursor to click coordinate for 100% targeting accuracy",
            parent=group_quick
        )
        self.b_card_snap.setChecked(self.config.snap_on_click)
        self.b_card_snap.checkedChanged.connect(self._update_snap)
        group_quick.addSettingCard(self.b_card_snap)

        # Click Ripples
        self.b_card_ripples = SwitchSettingCard(
            FIF.RINGER,
            "Click shockwave ripples",
            "Spawns expanding radial shockwaves at click coordinates",
            parent=group_quick
        )
        self.b_card_ripples.setChecked(self.config.ripples_enabled)
        self.b_card_ripples.checkedChanged.connect(self._update_ripples)
        group_quick.addSettingCard(self.b_card_ripples)

        # Hide Windows System Cursor
        self.b_card_hide = SwitchSettingCard(
            FIF.HIDE,
            "Hide Windows system cursor",
            "Hides original Windows cursor so only the animated cursor is visible",
            parent=group_quick
        )
        self.b_card_hide.setChecked(self.config.hide_system_cursor)
        self.b_card_hide.checkedChanged.connect(self._update_hide_sys)
        group_quick.addSettingCard(self.b_card_hide)

        layout.addWidget(group_quick)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # 2. Motion Interface (Consolidated Tracking & Advanced Physics Simulation)
    # =========================================================================
    def _create_motion_interface(self) -> QWidget:
        scroll, view, layout = self._create_page_scaffold(
            "Motion & Physics",
            "Pointer responsiveness, tracking dynamics, and advanced physics simulation"
        )

        # Group 1: Pointer Dynamics
        group_motion = SettingCardGroup("Pointer Dynamics", view)

        # Smoothness Slider
        card_smooth, self.m_slider_resp, self.m_lbl_resp = self._create_slider_card(
            FIF.SPEED_HIGH,
            "Movement smoothness",
            "Adjusts cursor tracking responsiveness and fluid momentum",
            5, 100, self.config.responsiveness * 100,
            self._update_resp,
            "%"
        )
        group_motion.addSettingCard(card_smooth)

        # Snap on Click
        self.m_card_snap = SwitchSettingCard(
            FIF.FINGERPRINT,
            "Snap to hardware position on click",
            "Instantly aligns visual cursor to click coordinate for 100% targeting accuracy",
            parent=group_motion
        )
        self.m_card_snap.setChecked(self.config.snap_on_click)
        self.m_card_snap.checkedChanged.connect(self._update_snap)
        group_motion.addSettingCard(self.m_card_snap)

        # Drag Precision Boost
        self.card_boost = SwitchSettingCard(
            FIF.ACCEPT,
            "Improve click-and-drag accuracy",
            "Tracks more closely while selecting or dragging.",
            parent=group_motion
        )
        self.card_boost.setChecked(self.config.drag_boost)
        self.card_boost.checkedChanged.connect(self._update_boost)
        group_motion.addSettingCard(self.card_boost)

        layout.addWidget(group_motion)

        # Group 2: Advanced Physics Engine (Power-User Harmonic Models)
        group_adv = SettingCardGroup("Advanced Physics Engine", view)

        self.card_adv_master = SwitchSettingCard(
            FIF.DEVELOPER_TOOLS,
            "Enable advanced physics models",
            "Choose a specialized tracking model; standard smoothing is used when off.",
            parent=group_adv
        )
        self.card_adv_master.setChecked(self.config.enable_advanced_physics)
        self.card_adv_master.checkedChanged.connect(self._toggle_adv_physics)
        group_adv.addSettingCard(self.card_adv_master)

        algo_map = {"exponential": 0, "spring": 1, "smoothstep": 2, "predictive": 3, "drag": 4}
        self.card_algo, self.combo_algo = self._create_combo_card(
            FIF.SPEED_HIGH,
            "Physics algorithm",
            self._get_algo_description(self.config.smoothing_type),
            [
                "Standard smoothing",
                "Spring and damping",
                "Adaptive easing",
                "Predictive lead",
                "Momentum drag"
            ],
            algo_map.get(self.config.smoothing_type, 0),
            self._update_algo
        )
        group_adv.addSettingCard(self.card_algo)

        # Spring Tension Slider
        self.card_stiff, self.slider_stiff, self.lbl_stiff = self._create_slider_card(
            FIF.ALIGNMENT,
            "Spring tension / stiffness",
            "Controls spring response (50-600).",
            50, 600, self.config.spring_stiffness,
            self._update_stiff,
            ""
        )
        group_adv.addSettingCard(self.card_stiff)

        # Spring Damping Slider
        self.card_damp, self.slider_damp, self.lbl_damp = self._create_slider_card(
            FIF.TILES,
            "Spring damping / friction",
            "Reduces spring oscillation (8-60).",
            8, 60, self.config.spring_damping,
            self._update_damp,
            ""
        )
        group_adv.addSettingCard(self.card_damp)

        # Velocity Prediction Lead
        self.card_pred, self.slider_pred, self.lbl_pred = self._create_slider_card(
            FIF.DATE_TIME,
            "Velocity prediction lead",
            "Look-ahead duration (5-80 ms).",
            5, 80, self.config.prediction_factor * 1000,
            self._update_pred,
            " ms"
        )
        group_adv.addSettingCard(self.card_pred)

        # Kinematic Drag Friction
        self.card_drag, self.slider_drag, self.lbl_drag = self._create_slider_card(
            FIF.AIRPLANE,
            "Air drag friction",
            "Resistance to movement (5-45).",
            5, 45, self.config.drag_friction,
            self._update_drag,
            ""
        )
        group_adv.addSettingCard(self.card_drag)

        layout.addWidget(group_adv)

        # Compact, functional cross-page shortcut; never expand into blank space.
        tilt_hint = QFrame(view)
        tilt_hint.setObjectName('tiltNavigationHint')
        tilt_hint.setFixedHeight(66)
        tilt_hint.setStyleSheet('QFrame#tiltNavigationHint { background: #292C36; border: 1px solid #48465A; border-radius: 9px; }')
        hint_layout = QHBoxLayout(tilt_hint)
        hint_layout.setContentsMargins(18, 8, 16, 8)
        hint_layout.setSpacing(12)
        tilt_icon = IconWidget(FIF.ROTATE, tilt_hint)
        tilt_icon.setFixedSize(21, 21)
        hint_layout.addWidget(tilt_icon)
        hint_text = BodyLabel('Customize tilt and return.', tilt_hint)
        hint_text.setWordWrap(True)
        hint_text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        hint_text.setStyleSheet('color: #E4E7F4; font-size: 12px; background: transparent; border: none;')
        hint_layout.addWidget(hint_text, 1)
        tilt_link = QPushButton('Open Tilt  \u2192', tilt_hint)
        tilt_link.setCursor(Qt.CursorShape.PointingHandCursor)
        tilt_link.setAccessibleName('Open tilt and rotation settings')
        tilt_link.setStyleSheet('QPushButton {color: #D5C6FF; background: #343044; border: 1px solid #62567E; border-radius: 6px; padding: 7px 10px; font-weight: 600;} QPushButton:hover {background: #493B63;} QPushButton:pressed {background: #312942;}')
        tilt_link.clicked.connect(lambda: self.switchTo(self.tilt_interface))
        hint_layout.addWidget(tilt_link)
        layout.addWidget(tilt_hint)
        self._advanced_group = group_adv

        self._refresh_advanced_sliders_state()
        layout.addStretch(1)
        return scroll

    # =========================================================================
    # 3. Dedicated Tilt Interface (All Tilt options nested and greyed out if disabled)
    # =========================================================================
    def _create_tilt_interface(self) -> QWidget:
        scroll, view, layout = self._create_page_scaffold(
            "Tilt Dynamics",
            "Configure movement lean, rotational inertia physics, slow-speed deadzone, and recovery timing"
        )

        # Master Tilt Enable Toggle Card (Top level on Tilt page)
        self.t_card_tilt = SwitchSettingCard(
            FIF.ROTATE,
            "Dynamic cursor tilt",
            "Enables smooth rotational dynamics while moving the mouse",
            parent=view
        )
        self.t_card_tilt.setChecked(self.config.tilt_enabled)
        self.t_card_tilt.checkedChanged.connect(self._update_tilt)
        layout.addWidget(self.t_card_tilt)

        # Nested Group: Tilt Configuration (All options nested under dynamic cursor tilt)
        self.group_tilt_options = SettingCardGroup("Tilt Configuration", view)

        # 1. Tilt Dynamics Mode
        tilt_idx = self._get_tilt_mode_index()
        self.t_card_tilt_mode, self.t_combo_tilt_mode = self._create_combo_card(
            FIF.TILES,
            "Tilt dynamics mode",
            "Choose sideways lean, motion-following, or opposing rotation",
            [
                "Velocity tilt",
                "Follow movement",
                "Oppose movement"
            ],
            tilt_idx,
            self._update_tilt_mode,
            width=280
        )
        self.group_tilt_options.addSettingCard(self.t_card_tilt_mode)

        # 2. Tilt Angle Multiplier Slider (0% to 100%)
        self.t_card_tstr, self.t_slider_tstr, self.t_lbl_tstr = self._create_slider_card(
            FIF.SCROLL,
            "Tilt angle multiplier",
            "0% disables rotation; 100% is full strength.",
            0, 100, min(100, max(0, self.config.tilt_strength * 100)),
            self._update_tstr,
            "%"
        )
        self.group_tilt_options.addSettingCard(self.t_card_tstr)

        # 3. Slow Movement Deadzone (Optimization setting to eliminate slow jitter)
        self.t_card_deadzone, self.t_slider_deadzone, self.t_lbl_deadzone = self._create_slider_card(
            FIF.FILTER,
            "Slow movement deadzone",
            "Ignore tiny movements to prevent twitching (0-120 px/s).",
            0, 120, int(self.config.tilt_deadzone),
            self._update_tilt_deadzone,
            " px/s"
        )
        self.group_tilt_options.addSettingCard(self.t_card_deadzone)

        # 4. Disable Return to Original Position (Never Return / Hold Indefinitely)
        self.t_card_tilt_never_return = SwitchSettingCard(
            FIF.PIN,
            "Keep the last tilt when stopped",
            "Keep the current angle until you move again",
            parent=self.group_tilt_options
        )
        self.t_card_tilt_never_return.setChecked(self.config.tilt_disable_return)
        self.t_card_tilt_never_return.checkedChanged.connect(self._update_tilt_never_return)
        self.group_tilt_options.addSettingCard(self.t_card_tilt_never_return)

        # 5. Delay Before Rotation Return (Hold Delay)
        self.t_card_tilt_delay = SwitchSettingCard(
            FIF.DATE_TIME,
            "Hold tilt before returning",
            "Wait briefly before returning to the original angle",
            parent=self.group_tilt_options
        )
        self.t_card_tilt_delay.setChecked(self.config.tilt_delay_enabled)
        self.t_card_tilt_delay.checkedChanged.connect(self._update_tilt_delay)
        self.group_tilt_options.addSettingCard(self.t_card_tilt_delay)

        # 6. Return Hold Delay Slider
        self.t_card_delay_dur, self.t_slider_delay_dur, self.t_lbl_delay_dur = self._create_slider_card(
            FIF.TILES,
            "Hold duration",
            "Delay before the cursor returns to neutral",
            50, 2000, int(self.config.tilt_return_delay * 1000),
            self._update_tilt_return_delay,
            " ms"
        )
        self.group_tilt_options.addSettingCard(self.t_card_delay_dur)

        # 7. Slow Rotation Return Switch
        self.t_card_tilt_decay = SwitchSettingCard(
            FIF.HISTORY,
            "Smooth return to neutral",
            "Ease back to the resting angle instead of snapping",
            parent=self.group_tilt_options
        )
        self.t_card_tilt_decay.setChecked(self.config.tilt_decay_enabled)
        self.t_card_tilt_decay.checkedChanged.connect(self._update_tilt_decay)
        self.group_tilt_options.addSettingCard(self.t_card_tilt_decay)

        # 8. Rotation Return Smoothness Slider
        self.t_card_decay_speed, self.t_slider_decay_speed, self.t_lbl_decay_speed = self._create_slider_card(
            FIF.SPEED_HIGH,
            "Return smoothing",
            "Choose how gradually the cursor returns",
            10, 100, int(self.config.tilt_decay_speed * 100),
            self._update_tilt_decay_speed,
            "%"
        )
        self.group_tilt_options.addSettingCard(self.t_card_decay_speed)

        layout.addWidget(self.group_tilt_options)

        # Initialize nested enablement state based on current tilt_enabled setting
        self._update_tilt_nested_state(self.config.tilt_enabled)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # 4. Appearance Interface (Themes, Colors, Sizing, Trails, and Precision Reticle)
    # =========================================================================
    def _create_appearance_interface(self) -> QWidget:
        scroll, view, layout = self._create_page_scaffold(
            "Cursor Appearance",
            "Personalize your cursor scheme, vector styling, colors, and visual enhancements"
        )

        # Group 1: Cursor Scheme & Source
        group_scheme = SettingCardGroup("Cursor Scheme & Source", view)

        self.a_card_roles = SwitchSettingCard(
            FIF.FINGERPRINT, "Match Windows cursor shapes",
            "Match text, link and resize shapes; other application cursors remain native.",
            parent=group_scheme)
        self.a_card_roles.setChecked(self.config.match_cursor_roles)
        self.a_card_roles.checkedChanged.connect(self._update_cursor_roles)
        group_scheme.addSettingCard(self.a_card_roles)

        self.a_card_clone = SwitchSettingCard(
            FIF.SYNC,
            "Clone active Windows cursor",
            "Uses your installed Windows cursor scheme with native hotspot alignment",
            parent=group_scheme
        )
        self.a_card_clone.setChecked(self.config.use_system_cursor_clone)
        self.a_card_clone.checkedChanged.connect(self._toggle_clone)
        group_scheme.addSettingCard(self.a_card_clone)

        theme_map = {"aero_modern": 0, "neon_glow": 1, "macos_fluid": 2, "cyber_arrow": 3, "minimal_dot": 4, "custom_arrow": 5}
        self.card_theme, self.combo_theme = self._create_combo_card(
            FIF.PALETTE,
            "Alternative vector theme",
            "Stylized procedural cursor styles (Inactive while system cloning is enabled)" if self.config.use_system_cursor_clone else "Stylized procedural cursor styles applied to custom pointer",
            ["Aero Modern", "Neon Glow", "macOS Fluid", "Cyber Arrow", "Minimalist Dot", "Custom Colors Arrow"],
            theme_map.get(self.config.cursor_theme, 0),
            self._update_theme
        )
        self.combo_theme.setEnabled(not self.config.use_system_cursor_clone)
        self.card_theme.setEnabled(not self.config.use_system_cursor_clone)
        group_scheme.addSettingCard(self.card_theme)

        layout.addWidget(group_scheme)

        # Group 2: Sizing & Palette
        group_size = SettingCardGroup("Dimensions & Color Palette", view)

        card_size, self.a_slider_size, self.a_lbl_size = self._create_slider_card(
            FIF.ZOOM,
            "Cursor size",
            "Physical display size of the cursor pointer",
            18, 54, self.config.cursor_size,
            self._update_size,
            " px"
        )
        group_size.addSettingCard(card_size)

        self.card_prim, self.btn_prim_color = self._create_color_card(
            FIF.BACKGROUND_FILL,
            "Primary fill color",
            "Fill color for Custom Colors Arrow only",
            self.config.primary_color,
            self._update_prim_color
        )
        self.card_prim.setEnabled(False)
        self.btn_prim_color.setEnabled(False)
        group_size.addSettingCard(self.card_prim)

        self.card_border, self.btn_border_color = self._create_color_card(
            FIF.BRUSH,
            "Accent border color",
            "Outline color for Custom Colors Arrow only",
            self.config.border_color,
            self._update_border_color
        )
        self.card_border.setEnabled(False)
        self.btn_border_color.setEnabled(False)
        group_size.addSettingCard(self.card_border)

        layout.addWidget(group_size)
        self._refresh_custom_palette()

        # Group 3: Visual Enhancements & Targeting (Cleanly consolidated here)
        group_effects = SettingCardGroup("Visual Enhancements & Targeting", view)

        # Motion Trails (Ghosting) - Moved cleanly to Appearance
        self.card_trails = SwitchSettingCard(
            FIF.PHOTO,
            "Motion trail ghosting",
            "Draws fading ghost echoes following fast cursor movements",
            parent=group_effects
        )
        self.card_trails.setChecked(self.config.trail_enabled)
        self.card_trails.checkedChanged.connect(self._update_trails)
        group_effects.addSettingCard(self.card_trails)

        # Display Precision Targeting Dot - Moved cleanly to Appearance
        self.card_dot = SwitchSettingCard(
            FIF.ASTERISK,
            "Display precision targeting dot",
            "Renders a tiny reticle dot at the exact physical mouse coordinate (OFF by default)",
            parent=group_effects
        )
        self.card_dot.setChecked(self.config.show_precision_dot)
        self.card_dot.checkedChanged.connect(self._update_dot)
        group_effects.addSettingCard(self.card_dot)

        self.card_outl = SwitchSettingCard(
            FIF.CHECKBOX,
            "Precision dot white outline",
            "High-contrast white outline ring ensuring clarity over dark & light content (OFF by default)",
            parent=group_effects
        )
        self.card_outl.setChecked(self.config.precision_dot_white_outline)
        self.card_outl.checkedChanged.connect(self._update_outl)
        self.card_outl.setEnabled(self.config.show_precision_dot)
        group_effects.addSettingCard(self.card_outl)

        layout.addWidget(group_effects)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # 5. Click Dynamics Interface (Compression and Visual Shockwaves)
    # =========================================================================
    def _create_click_interface(self) -> QWidget:
        scroll, view, layout = self._create_page_scaffold(
            "Click Dynamics",
            "Tactile click feedback, scale compression, and ripple shockwaves"
        )

        group_click = SettingCardGroup("Click Compression", view)

        # Shrink Factor Slider
        card_shrink, self.c_slider_shrink, self.c_lbl_shrink = self._create_slider_card(
            FIF.MOVE,
            "Click compression scale",
            "Scale compression factor applied dynamically when mouse buttons are pressed",
            40, 95, self.config.shrink_factor * 100,
            self._update_shrink,
            "%"
        )
        self.c_card_shrink = card_shrink
        group_click.addSettingCard(card_shrink)

        # Snap on click
        self.c_card_snap = SwitchSettingCard(
            FIF.FINGERPRINT,
            "Snap to hardware position on click",
            "Instantly aligns visual cursor to click coordinate for 100% targeting accuracy",
            parent=group_click
        )
        self.c_card_snap.setChecked(self.config.snap_on_click)
        self.c_card_snap.checkedChanged.connect(self._update_snap)
        group_click.addSettingCard(self.c_card_snap)

        layout.addWidget(group_click)

        # Group: Ripple Shockwaves
        group_ripple = SettingCardGroup("Visual Shockwaves", view)

        self.c_card_ripples = SwitchSettingCard(
            FIF.RINGER,
            "Click shockwave ripples",
            "Spawns expanding radial shockwaves at click coordinates",
            parent=group_ripple
        )
        self.c_card_ripples.setChecked(self.config.ripples_enabled)
        self.c_card_ripples.checkedChanged.connect(self._update_ripples)
        group_ripple.addSettingCard(self.c_card_ripples)

        self.c_card_rip_col, self.btn_rip_color = self._create_color_card(
            FIF.PALETTE,
            "Ripple accent color",
            "Color of the expanding shockwave ring",
            self.config.ripple_color,
            self._update_ripple_color
        )
        self.c_card_rip_col.setEnabled(self.config.ripples_enabled)
        self.btn_rip_color.setEnabled(self.config.ripples_enabled)
        group_ripple.addSettingCard(self.c_card_rip_col)

        layout.addWidget(group_ripple)

        layout.addStretch(1)
        return scroll

    # Compatibility alias if ever called directly
    def _create_advanced_interface(self) -> QWidget:
        return self.motion_interface

    # =========================================================================
    # 6. System Interface (Bottom of Sidebar)
    # =========================================================================
    def _create_system_interface(self) -> QWidget:
        scroll, view, layout = self._create_page_scaffold(
            "System Integration",
            "Operating system cursor management, emergency restoration, and process control"
        )

        # Group: Windows Integration
        group_win = SettingCardGroup("Windows Integration", view)

        self.s_card_hide = SwitchSettingCard(
            FIF.HIDE,
            "Hide original Windows cursor",
            "Replaces Windows system cursors with transparent masks while FluidCursor is running",
            parent=group_win
        )
        self.s_card_hide.setChecked(self.config.hide_system_cursor)
        self.s_card_hide.checkedChanged.connect(self._update_hide_sys)
        group_win.addSettingCard(self.s_card_hide)
        layout.addWidget(group_win)

        group_language = SettingCardGroup("Language & appearance", view)
        self.s_card_language, self.s_combo_language = self._create_combo_card(
            FIF.SETTING, "Interface language",
            "Choose the language for settings and the tray menu.",
            ["English", "العربية"], 1 if self.config.language == "ar" else 0,
            self._set_language, width=180)
        group_language.addSettingCard(self.s_card_language)
        choices = ("system", "dark", "light")
        self.s_card_ui_theme, self.s_combo_ui_theme = self._create_combo_card(
            FIF.PALETTE, "Application theme",
            "Choose a theme for settings and the tray menu.",
            ["Follow Windows theme", "Dark mode", "Light mode"],
            choices.index(self.config.ui_theme), self._set_ui_theme, width=180)
        group_language.addSettingCard(self.s_card_ui_theme)
        layout.addWidget(group_language)

        group_keys = SettingCardGroup("Keyboard shortcut", view)
        self.s_card_hotkey, self.s_combo_hotkey = self._create_combo_card(
            FIF.SPEED_HIGH, "Toggle FluidCursor", "Choose a function key to pause or resume the cursor.",
            list(HOTKEY_CHOICES), HOTKEY_CHOICES.index(normalize_hotkey(self.config.toggle_hotkey)),
            self._set_toggle_hotkey, width=180)

        group_keys.addSettingCard(self.s_card_hotkey)
        layout.addWidget(group_keys)

        # Group: Performance & Memory Optimization
        group_perf = SettingCardGroup("Performance & memory", view)

        self.s_card_ram = SwitchSettingCard(
            FIF.SPEED_HIGH,
            "Release settings when closed",
            "Recreates the settings window on demand; initial reopening may take a moment.",
            parent=group_perf
        )
        self.s_card_ram.setChecked(getattr(self.config, "ram_optimization_mode", True))
        self.s_card_ram.checkedChanged.connect(self._on_ram_opt_toggle_requested)
        group_perf.addSettingCard(self.s_card_ram)

        self.card_flush_ram = PushSettingCard(
            "Trim",
            FIF.DELETE,
            "Trim settings UI memory",
            "A temporary memory trim for this settings window only.",
            parent=group_perf
        )
        self.card_flush_ram.clicked.connect(self._manual_flush_ram)
        group_perf.addSettingCard(self.card_flush_ram)

        layout.addWidget(group_perf)

        group_rec = SettingCardGroup("Emergency & Recovery", view)

        self.card_restore = PushSettingCard(
            "Restore",
            FIF.SYNC,
            "Restore default Windows cursor",
            "Force reset all 13 Windows system cursors to Windows defaults",
            parent=group_rec
        )
        self.card_restore.clicked.connect(self._restore_sys_cursor)
        group_rec.addSettingCard(self.card_restore)

        self.card_exit = PushSettingCard(
            "Exit",
            FIF.CLOSE,
            "Exit FluidCursor",
            "Restores system cursors and safely shuts down the application",
            parent=group_rec
        )
        self.card_exit.clicked.connect(self._exit_app)
        group_rec.addSettingCard(self.card_exit)

        layout.addWidget(group_rec)
        layout.addStretch(1)
        return scroll

    # =========================================================================
    # Logic & State Synchronization
    # =========================================================================
    def _set_language(self, index):
        language = 'ar' if index == 1 else 'en'
        if self.config.language == language:
            return
        self.config.language = language
        self._save_timer.stop()
        self.config.save()
        if self.on_config_changed:
            self.on_config_changed()
        if self.on_language_changed:
            QTimer.singleShot(0, self.on_language_changed)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if language == 'ar' else Qt.LayoutDirection.LeftToRight)
            self.setWindowTitle(self._t('FluidCursor Settings'))

    def _set_ui_theme(self, index):
        choices = ("system", "dark", "light")
        value = choices[index] if 0 <= index < len(choices) else "system"
        if self.config.ui_theme == value: return
        self.config.ui_theme = value
        self._save_timer.stop(); self.config.save()
        if self.on_config_changed: self.on_config_changed()
        if self.on_language_changed: QTimer.singleShot(0, self.on_language_changed)
        else:
            self._active_theme = interface_theme(value)
            self._light_theme = self._active_theme == "light"
            setTheme(Theme.LIGHT if self._light_theme else Theme.DARK)
            self._apply_palette(self)

    def _set_toggle_hotkey(self, index):
        self.config.toggle_hotkey = HOTKEY_CHOICES[index] if 0 <= index < len(HOTKEY_CHOICES) else "F9"
        self._sync_master_cards(self.config.enabled)
        self._notify()

    def _get_tilt_mode_index(self) -> int:
        if self.config.tilt_mode == "physics_forward":
            return 1
        elif self.config.tilt_mode in ("physics_opposing", "physics"):
            return 2
        return 0

    def _get_algo_description(self, algo_type: str) -> str:
        descriptions = {
            "exponential": "Adaptive exponential lerp for silky smooth motion.",
            "spring": "Simulates 2nd-order harmonic spring-damper physics with organic mass & bounce.",
            "smoothstep": "Cubic ease on micro-movements with instant acceleration on high-speed sweeps.",
            "predictive": "Extrapolates mouse velocity forward to eliminate perceived display latency.",
            "drag": "Simulates physical cursor mass with air resistance friction."
        }
        return self._t(descriptions.get(algo_type, descriptions["exponential"]))

    def _apply_badge_style(self, badge_label, is_enabled: bool):
        if is_enabled:
            badge_label.setText(self._t("Active"))
            badge_label.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.15);
                border: 1px solid rgba(56, 189, 248, 0.4);
                padding: 4px 10px;
                border-radius: 6px;
                color: #38BDF8;
                font-weight: 600;
                font-size: 12px;
            """)
        else:
            badge_label.setText(self._t("Paused"))
            badge_label.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.4);
                padding: 4px 10px;
                border-radius: 6px;
                color: #EF4444;
                font-weight: 600;
                font-size: 12px;
            """)

    def _sync_master_cards(self, is_enabled: bool):
        title = self._t("FluidCursor active" if is_enabled else "FluidCursor paused")
        desc = f"{normalize_hotkey(self.config.toggle_hotkey)}: {self._t('pause / resume')}"

        for prefix in ["basic", "motion", "tilt"]:
            lbl_t = getattr(self, f"{prefix}_lbl_master_title", None)
            lbl_d = getattr(self, f"{prefix}_lbl_master_desc", None)
            lbl_b = getattr(self, f"{prefix}_lbl_status_badge", None)
            sw = getattr(self, f"{prefix}_switch_master", None)

            if lbl_t:
                lbl_t.setText(title)
            if lbl_d:
                lbl_d.setText(desc)
            if lbl_b:
                self._apply_badge_style(lbl_b, is_enabled)
            dot = getattr(self, f"{prefix}_status_dot", None)
            if dot:
                dot.setStyleSheet("color:#58DABF; background:transparent; font-size:15px;" if is_enabled else
                                  "color:#E3B66A; background:transparent; font-size:15px;")
            if sw and sw.isChecked() != is_enabled:
                sw.blockSignals(True)
                sw.setChecked(is_enabled)
                sw.blockSignals(False)

    def _toggle_master(self, checked: bool):
        self.config.enabled = checked
        if not checked and self.cursor_mgr:
            self.cursor_mgr.restore_system_cursor()
        self._sync_master_cards(checked)
        self._notify()

    def update_enabled_state(self, is_enabled: bool):
        """Synchronizes GUI master switch with external state changes (F9 hotkey or tray)."""
        self.config.enabled = is_enabled
        self._sync_master_cards(is_enabled)
        self._update_fun_status()

    def _update_cursor_roles(self, checked: bool):
        self.config.match_cursor_roles = checked
        self._notify()

    def _toggle_clone(self, checked: bool):
        self.config.use_system_cursor_clone = checked

        # Sync both clone switches
        for card_name in ["b_card_clone", "a_card_clone"]:
            c = getattr(self, card_name, None)
            if c and c.isChecked() != checked:
                c.blockSignals(True)
                c.setChecked(checked)
                c.blockSignals(False)

        # Grey out or enable vector theme and color pickers
        if hasattr(self, "card_theme"):
            self.card_theme.setEnabled(not checked)
            if checked:
                self.card_theme.setContent(self._t("Stylized procedural cursor styles (Inactive while system cloning is enabled)"))
            else:
                self.card_theme.setContent(self._t("Stylized procedural cursor styles applied to custom pointer"))
        if hasattr(self, "combo_theme"):
            self.combo_theme.setEnabled(not checked)

        if hasattr(self, "card_prim"):
            self._refresh_custom_palette()

        self._notify()

    def _update_tilt_mode(self, idx: int):
        modes = ["velocity", "physics_forward", "physics_opposing"]
        self.config.tilt_mode = modes[idx] if idx < len(modes) else "velocity"

        if hasattr(self, "t_combo_tilt_mode") and self.t_combo_tilt_mode.currentIndex() != idx:
            self.t_combo_tilt_mode.blockSignals(True)
            self.t_combo_tilt_mode.setCurrentIndex(idx)
            self.t_combo_tilt_mode.blockSignals(False)

        self._notify()

    def _refresh_custom_palette(self):
        """The saved palette belongs exclusively to Custom Colors Arrow."""
        editable = (not self.config.use_system_cursor_clone
                    and self.config.cursor_theme == "custom_arrow")
        for name in ("card_prim", "btn_prim_color", "card_border", "btn_border_color"):
            control = getattr(self, name, None)
            if control is not None:
                control.setEnabled(editable)
        for name in ("card_prim", "card_border"):
            card = getattr(self, name, None)
            if card is not None:
                card.setToolTip(self._t("Select Custom Colors Arrow and disable cloning to edit its palette") if not editable else "")

    def _update_theme(self, idx: int):
        themes = ["aero_modern", "neon_glow", "macos_fluid", "cyber_arrow", "minimal_dot", "custom_arrow"]
        self.config.cursor_theme = themes[idx]
        self._refresh_custom_palette()
        self._notify()

    def _update_size(self, val: int):
        self.config.cursor_size = val
        for sld_name, lbl_name in [("b_slider_size", "b_lbl_size"), ("a_slider_size", "a_lbl_size")]:
            sld = getattr(self, sld_name, None)
            lbl = getattr(self, lbl_name, None)
            if sld and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
            if lbl:
                lbl.setText(f"{val} px")

        self._notify()

    def _update_resp(self, val: int):
        self.config.responsiveness = val / 100.0
        for sld_name, lbl_name in [("b_slider_resp", "b_lbl_resp"), ("m_slider_resp", "m_lbl_resp")]:
            sld = getattr(self, sld_name, None)
            lbl = getattr(self, lbl_name, None)
            if sld and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
            if lbl:
                lbl.setText(f"{val}%")
        self._notify()

    def _update_shrink(self, val: int):
        self.config.shrink_factor = val / 100.0
        for sld_name, lbl_name in [("b_slider_shrink", "b_lbl_shrink"), ("c_slider_shrink", "c_lbl_shrink")]:
            sld = getattr(self, sld_name, None)
            lbl = getattr(self, lbl_name, None)
            if sld and sld.value() != val:
                sld.blockSignals(True)
                sld.setValue(val)
                sld.blockSignals(False)
            if lbl:
                lbl.setText(f"{val}%")
        self._notify()

    def _update_snap(self, val: bool):
        self.config.snap_on_click = val
        for card_name in ["b_card_snap", "m_card_snap", "c_card_snap"]:
            c = getattr(self, card_name, None)
            if c and c.isChecked() != val:
                c.blockSignals(True)
                c.setChecked(val)
                c.blockSignals(False)
        self._notify()

    def _update_ripples(self, val: bool):
        self.config.ripples_enabled = val
        for card_name in ["b_card_ripples", "c_card_ripples"]:
            c = getattr(self, card_name, None)
            if c and c.isChecked() != val:
                c.blockSignals(True)
                c.setChecked(val)
                c.blockSignals(False)
        if hasattr(self, "c_card_rip_col"):
            self.c_card_rip_col.setEnabled(val)
        if hasattr(self, "btn_rip_color"):
            self.btn_rip_color.setEnabled(val)
        self._notify()

    def _update_tilt_nested_state(self, enabled: bool):
        if hasattr(self, "group_tilt_options"):
            self.group_tilt_options.setEnabled(enabled)
        if enabled:
            never_ret = getattr(self.config, "tilt_disable_return", False)
            if hasattr(self, "t_card_tilt_never_return"):
                self.t_card_tilt_never_return.setEnabled(True)

            delay_active = not never_ret
            decay_active = not never_ret

            if hasattr(self, "t_card_tilt_delay"):
                self.t_card_tilt_delay.setEnabled(delay_active)
            if hasattr(self, "t_card_delay_dur"):
                self.t_card_delay_dur.setEnabled(delay_active and self.config.tilt_delay_enabled)
            if hasattr(self, "t_slider_delay_dur"):
                self.t_slider_delay_dur.setEnabled(delay_active and self.config.tilt_delay_enabled)

            if hasattr(self, "t_card_tilt_decay"):
                self.t_card_tilt_decay.setEnabled(decay_active)
            if hasattr(self, "t_card_decay_speed"):
                self.t_card_decay_speed.setEnabled(decay_active and self.config.tilt_decay_enabled)
            if hasattr(self, "t_slider_decay_speed"):
                self.t_slider_decay_speed.setEnabled(decay_active and self.config.tilt_decay_enabled)

    def _update_tilt_never_return(self, val: bool):
        self.config.tilt_disable_return = val
        c = getattr(self, "t_card_tilt_never_return", None)
        if c and c.isChecked() != val:
            c.blockSignals(True)
            c.setChecked(val)
            c.blockSignals(False)
        self._update_tilt_nested_state(self.config.tilt_enabled)
        self._notify()

    def _update_tilt(self, val: bool):
        self.config.tilt_enabled = val
        for card_name in ["b_card_tilt", "t_card_tilt"]:
            c = getattr(self, card_name, None)
            if c and c.isChecked() != val:
                c.blockSignals(True)
                c.setChecked(val)
                c.blockSignals(False)
        self._update_tilt_nested_state(val)
        self._notify()

    def _update_tstr(self, val: int):
        self.config.tilt_strength = max(0, min(100, val)) / 100.0
        sld = getattr(self, "t_slider_tstr", None)
        lbl = getattr(self, "t_lbl_tstr", None)
        if sld and sld.value() != val:
            sld.blockSignals(True)
            sld.setValue(val)
            sld.blockSignals(False)
        if lbl:
            lbl.setText(f"{val}%")
        self._notify()

    def _update_tilt_deadzone(self, val: int):
        self.config.tilt_deadzone = float(val)
        sld = getattr(self, "t_slider_deadzone", None)
        lbl = getattr(self, "t_lbl_deadzone", None)
        if sld and sld.value() != val:
            sld.blockSignals(True)
            sld.setValue(val)
            sld.blockSignals(False)
        if lbl:
            lbl.setText(f"{val} px/s")
        self._notify()

    def _update_tilt_decay(self, val: bool):
        self.config.tilt_decay_enabled = val
        c = getattr(self, "t_card_tilt_decay", None)
        if c and c.isChecked() != val:
            c.blockSignals(True)
            c.setChecked(val)
            c.blockSignals(False)

        self._update_tilt_nested_state(self.config.tilt_enabled)
        self._notify()

    def _update_tilt_decay_speed(self, val: int):
        self.config.tilt_decay_speed = val / 100.0
        sld = getattr(self, "t_slider_decay_speed", None)
        lbl = getattr(self, "t_lbl_decay_speed", None)
        if sld and sld.value() != val:
            sld.blockSignals(True)
            sld.setValue(val)
            sld.blockSignals(False)
        if lbl:
            lbl.setText(f"{val}%")
        self._notify()

    def _update_tilt_delay(self, val: bool):
        self.config.tilt_delay_enabled = val
        c = getattr(self, "t_card_tilt_delay", None)
        if c and c.isChecked() != val:
            c.blockSignals(True)
            c.setChecked(val)
            c.blockSignals(False)

        self._update_tilt_nested_state(self.config.tilt_enabled)
        self._notify()

    def _update_tilt_return_delay(self, val: int):
        self.config.tilt_return_delay = val / 1000.0
        sld = getattr(self, "t_slider_delay_dur", None)
        lbl = getattr(self, "t_lbl_delay_dur", None)
        if sld and sld.value() != val:
            sld.blockSignals(True)
            sld.setValue(val)
            sld.blockSignals(False)
        if lbl:
            lbl.setText(f"{val} ms")
        self._notify()

    def _update_prim_color(self, color: QColor):
        self.config.primary_color = color.name()
        self._notify()

    def _update_border_color(self, color: QColor):
        self.config.border_color = color.name()
        self._notify()

    def _update_ripple_color(self, color: QColor):
        self.config.ripple_color = color.name()
        self._notify()

    def _update_trails(self, val: bool):
        self.config.trail_enabled = val
        self._notify()

    def _toggle_adv_physics(self, checked: bool):
        self.config.enable_advanced_physics = checked
        self._refresh_advanced_sliders_state()
        self._notify()

    def _refresh_advanced_sliders_state(self):
        adv = self.config.enable_advanced_physics
        if hasattr(self, "card_algo"):
            self.card_algo.setEnabled(adv)
        if hasattr(self, "combo_algo"):
            self.combo_algo.setEnabled(adv)
        if hasattr(self, "card_boost"):
            # Drag precision is available with the standard physics engine too.
            self.card_boost.setEnabled(True)

        algo = self.config.smoothing_type
        is_spring = adv and (algo == "spring")
        is_pred = adv and (algo == "predictive")
        is_drag = adv and (algo == "drag")

        if hasattr(self, "card_stiff"):
            self.card_stiff.setEnabled(is_spring)
        if hasattr(self, "slider_stiff"):
            self.slider_stiff.setEnabled(is_spring)

        if hasattr(self, "card_damp"):
            self.card_damp.setEnabled(is_spring)
        if hasattr(self, "slider_damp"):
            self.slider_damp.setEnabled(is_spring)

        if hasattr(self, "card_pred"):
            self.card_pred.setEnabled(is_pred)
        if hasattr(self, "slider_pred"):
            self.slider_pred.setEnabled(is_pred)

        if hasattr(self, "card_drag"):
            self.card_drag.setEnabled(is_drag)
        if hasattr(self, "slider_drag"):
            self.slider_drag.setEnabled(is_drag)

        # Progressive disclosure: show only controls that affect the chosen model.
        # This also avoids long pages full of unusable, disabled sliders.
        for name, visible in (
            ('card_algo', adv), ('card_stiff', is_spring),
            ('card_damp', is_spring), ('card_pred', is_pred),
            ('card_drag', is_drag),
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setVisible(bool(visible))
        group = getattr(self, '_advanced_group', None)
        if group is not None:
            group.adjustSize()
            if group.parentWidget() and group.parentWidget().layout():
                group.parentWidget().layout().invalidate()
            self._queue_description_refresh()

    def _update_algo(self, idx: int):
        algos = ["exponential", "spring", "smoothstep", "predictive", "drag"]
        self.config.smoothing_type = algos[idx]
        self.card_algo.setContent(self._get_algo_description(self.config.smoothing_type))
        self._refresh_advanced_sliders_state()
        self._notify()

    def _update_stiff(self, val: int):
        self.config.spring_stiffness = float(val)
        self._notify()

    def _update_damp(self, val: int):
        self.config.spring_damping = float(val)
        self._notify()

    def _update_pred(self, val: int):
        self.config.prediction_factor = val / 1000.0
        self._notify()

    def _update_drag(self, val: int):
        self.config.drag_friction = float(val)
        self._notify()

    def _update_boost(self, val: bool):
        self.config.drag_boost = val
        self._notify()

    def _update_dot(self, val: bool):
        self.config.show_precision_dot = val
        if hasattr(self, "card_outl"):
            self.card_outl.setEnabled(val)
        self._notify()

    def _update_outl(self, val: bool):
        self.config.precision_dot_white_outline = val
        self._notify()

    def _update_hide_sys(self, val: bool):
        self.config.hide_system_cursor = val
        for card_name in ["b_card_hide", "s_card_hide"]:
            c = getattr(self, card_name, None)
            if c and c.isChecked() != val:
                c.blockSignals(True)
                c.setChecked(val)
                c.blockSignals(False)

        if self.cursor_mgr:
            if val and self.config.enabled:
                self.cursor_mgr.hide_system_cursor()
            else:
                self.cursor_mgr.restore_system_cursor()

        self._notify()

    def _restore_sys_cursor(self):
        # Pause first: otherwise the overlay hides the restored cursor next frame.
        self.config.enabled = False
        self._sync_master_cards(False)
        if self.cursor_mgr:
            self.cursor_mgr.restore_system_cursor()
        self._notify()
        InfoBar.success(
            title=self._t("System Cursor Restored"),
            content=self._t("Standard Windows cursor has been restored."),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self
        )

    def _exit_app(self):
        if hasattr(self, "_save_timer"):
            self._save_timer.stop()
        self.config.save()
        if self.cursor_mgr:
            self.cursor_mgr.restore_system_cursor()
        exit_callback = getattr(self, 'on_exit_callback', None)
        if exit_callback:
            exit_callback()
        QApplication.instance().quit()

    def _apply_fun_exclusivity(self):
        """Lock overridden pages while Fun runs; never lock emergency recovery."""
        active = bool(self.config.fun_enabled)
        if active and self.stackedWidget.currentWidget() not in (self.fun_interface, self.sys_interface):
            self.stackedWidget.setCurrentWidget(self.fun_interface)
        for page in (self.basic_interface, self.app_interface, self.motion_interface,
                     self.click_interface, self.tilt_interface):
            page.setEnabled(not active)
            nav = self.navigationInterface.widget(page.objectName())
            if nav is not None:
                nav.setEnabled(not active)
                nav.setToolTip(self._t("Unavailable while Fun mode is enabled") if active else "")
        self.s_card_hide.setEnabled(not active)
        self.s_card_hide.setToolTip(self._t("Fun temporarily controls cursor visibility") if active else "")
        if hasattr(self, "fun_banner"):
            selected = {"tile": "Follower tile", "stardust": "Stardust",
                         "chain": "Linked chain", "comet": "Comet", "orbit": "Orbit",
                         "yoyo": "Bouncy yo-yo", "ribbon": "Silk ribbon",
                         "spinner": "Fidget spinner"}.get(
                self.config.fun_mode, "Fun")
            running = active and self.config.enabled
            self.fun_status_title.setText(
                (self._t("Fun on:") + " " + self._t(selected)) if running else
                self._t("Fun selected - cursor paused") if active else
                self._t("Fun mode is off"))
            self.fun_status_description.setText(
                self._t("Standard settings are locked until Fun is turned off.")
                if active else self._t("Normal cursor settings are available."))
            color = "#7C6AF2" if active else "#2E746E"
            self.fun_banner.setStyleSheet(
                "CardWidget#funStatusBanner { background: " + ("#29263D" if active else "#203332") +
                "; border: 1px solid " + color + "; border-radius: 12px; }")
            self.fun_status_title.setStyleSheet("color: " + ("#D9CDFF" if active else "#91E5D0") +
                                                "; font-size: 14px; font-weight: 700;")
            self.fun_status_description.setStyleSheet("color: #D6D1E4; font-size: 12px;")
            self._apply_palette(self.fun_banner)

    def _refresh_fun_controls(self):
        if not hasattr(self, "fun_card_smooth"):
            return
        mode = self.config.fun_mode
        enabled = bool(self.config.fun_enabled)
        self.fun_card_smooth.setEnabled(enabled)
        for card, relevant in (
                               (self.fun_card_distance, mode == "tile"),
                               (self.fun_card_particles, mode in ("stardust", "comet")),
                               (self.fun_card_chain, mode == "chain"),
                               (self.fun_card_swing, mode == "chain"),
                               (self.fun_card_orbit, mode == "orbit"),
                               (self.fun_card_yoyo, mode == "yoyo"),
                               (self.fun_card_spinner, mode == "spinner"),
                               (self.fun_card_ribbon, mode == "ribbon")):
            card.setVisible(relevant)
            card.setEnabled(enabled)
        for choice, button in self.fun_mode_buttons.items():
            button.setChecked(choice == mode)
        self._queue_description_refresh()
        self._update_fun_status()

    def _update_fun_status(self):
        if hasattr(self, "fun_banner"):
            self._apply_fun_exclusivity()

    def _set_fun_enabled(self, value):
        self.config.fun_enabled = bool(value)
        self._refresh_fun_controls()
        self._apply_fun_exclusivity()
        self._notify()

    def _set_fun_mode(self, index):
        self.config.fun_mode = MODES[max(0, min(len(MODES)-1, index))]
        self._refresh_fun_controls()
        self._notify()

    def _set_fun_smoothness(self, value):
        self.config.fun_smoothness = int(value)
        self._notify()

    def _set_fun_distance(self, value):
        self.config.fun_tile_distance = int(value)
        self._notify()

    def _set_fun_particles(self, value):
        self.config.fun_particles = int(value)
        self._notify()

    def _set_fun_chain(self, value):
        self.config.fun_chain_length = int(value)
        self._notify()

    def _set_fun_swing(self, value):
        self.config.fun_chain_swing = int(value)
        self._notify()

    def _set_fun_orbit(self, value):
        self.config.fun_orbit_count = int(value)
        self._notify()

    def _set_fun_yoyo(self, value):
        self.config.fun_yoyo_length = int(value)
        self._notify()

    def _set_fun_spinner(self, value):
        self.config.fun_spinner_speed = int(value)
        self._notify()

    def _set_fun_ribbon(self, value):
        self.config.fun_ribbon_flow = int(value)
        self._notify()

    def _notify(self):
        # Debounce disk write by 350ms so scrubbing sliders does not freeze the UI thread
        if hasattr(self, "_save_timer"):
            self._save_timer.start(350)
        else:
            self.config.save()
        if self.on_config_changed:
            self.on_config_changed()

    def _on_ram_opt_toggle_requested(self, val: bool):
        if not val:
            # User wants to disable RAM optimization -> warn them!
            dialog = MessageBox(
                self._t("Keep settings in memory?"),
                self._t("Keeping the settings window in memory makes reopening faster, but uses more memory while it is hidden.") + "\n\n" +
                self._t("Release it when closing instead? You can change this anytime."),
                self
            )
            dialog.yesButton.setText(self._t("Keep in memory"))
            dialog.cancelButton.setText(self._t("Release on close"))
            if dialog.exec():
                self.config.ram_optimization_mode = False
                self._notify()
            else:
                if hasattr(self.s_card_ram, "switchButton"):
                    self.s_card_ram.switchButton.blockSignals(True)
                else:
                    self.s_card_ram.blockSignals(True)
                self.s_card_ram.setChecked(True)
                if hasattr(self.s_card_ram, "switchButton"):
                    self.s_card_ram.switchButton.blockSignals(False)
                else:
                    self.s_card_ram.blockSignals(False)
        else:
            self.config.ram_optimization_mode = True
            self._notify()

    def _manual_flush_ram(self):
        self._trim_process_memory()
        current_mb = self.get_current_ram_mb()
        memory_text = f"{current_mb:.1f} MB" if current_mb > 0 else "unavailable"
        InfoBar.success(
            title=self._t("Settings memory trimmed"),
            content=f"{self._t('Settings window working set:')} {memory_text}",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    @staticmethod
    def get_current_ram_mb() -> float:
        import ctypes
        from ctypes import wintypes
        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        try:
            current_process = ctypes.windll.kernel32.GetCurrentProcess
            current_process.restype = wintypes.HANDLE
            current_process.argtypes = []
            get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
            get_memory.restype = wintypes.BOOL
            get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            if not get_memory(current_process(), ctypes.byref(pmc), pmc.cb):
                return 0.0  # Caller reports unavailable, not zero memory use.
            return pmc.WorkingSetSize / (1024 * 1024)
        except Exception:
            return 0.0

    @staticmethod
    def _trim_process_memory():
        import gc
        import ctypes
        gc.collect()
        try:
            h = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.EmptyWorkingSet(h)
        except Exception:
            pass

    def closeEvent(self, event):
        if hasattr(self, "_save_timer"):
            self._save_timer.stop()
        self.config.save()
        event.ignore()
        if getattr(self.config, "ram_optimization_mode", True):
            self.hide()
            cb = getattr(self, "on_destroy_callback", None)
            self.deleteLater()
            if cb:
                cb()
            QTimer.singleShot(60, self._trim_process_memory)
        else:
            self.hide()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized() and getattr(self.config, "ram_optimization_mode", True):
                if hasattr(self, "_save_timer"):
                    self._save_timer.stop()
                self.config.save()
                self.hide()
                cb = getattr(self, "on_destroy_callback", None)
                self.deleteLater()
                if cb:
                    cb()
                QTimer.singleShot(60, self._trim_process_memory)
                return
        super().changeEvent(event)
