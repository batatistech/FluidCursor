"""
Windows 11 Settings-Style Fluent Control Center for FluidCursor.
Built natively on FluentWindow with authentic Windows 11 sidebar navigation:
- Dedicated "Basic" landing page for all essential settings (no preview/sandbox box to prevent crashes)
- Compact Master Status Card on Basic page
- 3 Tilt dynamics modes: Velocity, Full Physics (Forward Inertia), Full Physics (Opposing Inertia)
- Tilt angle multiplier slider up to 500%
- Generous right padding (24px) preventing controls from crowding the card edge
- Clean Mica dark theme with zero black boxes behind labels
- Safe hide-to-tray on window close
- Comprehensive reactive greying out of sliders, combos, and color pickers when parent options are disabled
"""

import math
from PyQt6.QtCore import Qt, QTimer, QPointF, pyqtSignal, QEvent
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QApplication,
    QPushButton
)

from qfluentwidgets import (
    FluentWindow,
    NavigationItemPosition,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    SettingCard,
    PushSettingCard,
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
    FluentIcon as FIF,
    IconWidget,
    setTheme,
    Theme
)

from core.config import CursorConfig
from core.theme import CursorRenderer
from core.physics import CursorPhysics


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
        self.setStyleSheet("""
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
        """)

    def setColor(self, color: QColor):
        self.currentColor = color
        self._update_ui()

    def _show_color_dialog(self):
        try:
            dlg = ColorDialog(self.currentColor, self.dialogTitle, self.window())
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

    def __init__(self, config: CursorConfig, on_config_changed, cursor_mgr, cloner=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.on_config_changed = on_config_changed
        self.cursor_mgr = cursor_mgr
        self.cloner = cloner

        # Debounce timer for saving configuration to disk (prevents disk I/O lag while scrubbing sliders)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.config.save)

        setTheme(Theme.DARK)
        self.setWindowTitle("FluidCursor Settings")
        self.resize(960, 720)
        self.setMinimumSize(840, 600)

        # Clean top title bar: remove return button
        self.navigationInterface.setReturnButtonVisible(False)
        self.navigationInterface.setExpandWidth(220)

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

        # Expand sidebar by default for authentic Windows 11 Settings layout
        QTimer.singleShot(50, lambda: self.navigationInterface.panel.expand())

    def _init_sub_interfaces(self):
        # 1. Basic (Primary Landing Page with Essential Controls - No duplicate master cards)
        self.basic_interface = self._create_basic_interface()
        self.basic_interface.setObjectName("basicInterface")
        self.addSubInterface(self.basic_interface, FIF.HOME, "Basic")

        # 2. Motion & Physics (Consolidated motion dynamics and advanced physics simulation)
        self.motion_interface = self._create_motion_interface()
        self.motion_interface.setObjectName("motionInterface")
        self.addSubInterface(self.motion_interface, FIF.SPEED_HIGH, "Motion")

        # 3. Dedicated Tilt Dynamics Page
        self.tilt_interface = self._create_tilt_interface()
        self.tilt_interface.setObjectName("tiltInterface")
        self.addSubInterface(self.tilt_interface, FIF.ROTATE, "Tilt")

        # 4. Appearance & Visuals (Scheme, themes, color palette, motion trails, and reticle dot)
        self.app_interface = self._create_appearance_interface()
        self.app_interface.setObjectName("appearanceInterface")
        self.addSubInterface(self.app_interface, FIF.PALETTE, "Appearance")

        # 5. Click Dynamics (Tactile click feedback, scale compression, and shockwave ripples)
        self.click_interface = self._create_click_interface()
        self.click_interface.setObjectName("clickInterface")
        self.addSubInterface(self.click_interface, FIF.FINGERPRINT, "Click Dynamics")

        # Compatibility alias for power users / legacy tests
        self.adv_interface = self.motion_interface

        # 6. System (Bottom of Sidebar)
        self.sys_interface = self._create_system_interface()
        self.sys_interface.setObjectName("systemInterface")
        self.addSubInterface(self.sys_interface, FIF.SETTING, "System", NavigationItemPosition.BOTTOM)

    def _create_page_scaffold(self, title_text: str, subtitle_text: str):
        scroll = ScrollArea()
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidgetResizable(True)

        view = QWidget()
        view.setStyleSheet("background: transparent;")
        scroll.setWidget(view)

        layout = QVBoxLayout(view)
        layout.setContentsMargins(36, 24, 36, 28)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = TitleLabel(title_text)
        title.setStyleSheet("font-size: 26px; font-weight: 600; color: #FFFFFF; background: transparent;")
        layout.addWidget(title)

        if subtitle_text:
            sub = CaptionLabel(subtitle_text)
            sub.setStyleSheet("font-size: 13px; color: #9E9E9E; background: transparent; margin-bottom: 4px;")
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
        combo = ComboBox()
        combo.addItems(items)
        combo.setCurrentIndex(cur_idx)
        combo.setFixedWidth(width)
        combo.currentIndexChanged.connect(on_change)
        card.hBoxLayout.addWidget(combo)
        card.hBoxLayout.addSpacing(24)  # Generous padding from right edge
        return card, combo

    def _create_color_card(self, icon, title, desc, cur_hex, on_change):
        card = SettingCard(icon, title, desc)
        btn = FluentColorButton(QColor(cur_hex), title, self)
        btn.colorChanged.connect(on_change)
        card.hBoxLayout.addWidget(btn)
        card.hBoxLayout.addSpacing(24)  # Generous padding from right edge
        return card, btn

    def _create_master_card(self, parent_view, prefix="basic"):
        """Creates a clean, crash-proof master card with toggle, status, hotkey and actions."""
        card = CardWidget(parent_view)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Top row: Master switch, status, hotkey
        top_row = QHBoxLayout()
        icon_master = IconWidget(FIF.POWER_BUTTON)
        icon_master.setFixedSize(22, 22)
        top_row.addWidget(icon_master)

        txt_box = QVBoxLayout()
        lbl_title = StrongBodyLabel("FluidCursor Active" if self.config.enabled else "FluidCursor Paused")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #FFFFFF; background: transparent;")
        lbl_desc = CaptionLabel("Real-time physics tracking active" if self.config.enabled else "Standard Windows cursor active")
        lbl_desc.setStyleSheet("color: #9E9E9E; background: transparent;")
        txt_box.addWidget(lbl_title)
        txt_box.addWidget(lbl_desc)
        top_row.addLayout(txt_box)

        top_row.addStretch()

        # Status badge
        lbl_status = CaptionLabel("Active" if self.config.enabled else "Paused")
        self._apply_badge_style(lbl_status, self.config.enabled)
        top_row.addWidget(lbl_status)

        # Hotkey badge
        hotkey_badge = CaptionLabel("Hotkey: F9")
        hotkey_badge.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 4px 10px;
            border-radius: 6px;
            color: #CCCCCC;
            font-size: 12px;
            background: transparent;
        """)
        top_row.addWidget(hotkey_badge)

        # Master switch
        switch_master = SwitchButton()
        switch_master.setChecked(self.config.enabled)
        switch_master.checkedChanged.connect(self._toggle_master)
        top_row.addWidget(switch_master)

        layout.addLayout(top_row)

        # Action buttons row
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_restore = QPushButton("Restore system cursor")
        btn_restore.setIcon(FIF.SYNC.icon())
        btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 12px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.10);
            }
        """)
        btn_restore.clicked.connect(self._restore_sys_cursor)
        btn_box.addWidget(btn_restore)

        btn_exit = QPushButton("Exit program")
        btn_exit.setIcon(FIF.CLOSE.icon())
        btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exit.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 12px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.20);
                border-color: rgba(239, 68, 68, 0.50);
            }
        """)
        btn_exit.clicked.connect(self._exit_app)
        btn_box.addWidget(btn_exit)
        btn_box.addStretch()
        layout.addLayout(btn_box)

        setattr(self, f"{prefix}_lbl_master_title", lbl_title)
        setattr(self, f"{prefix}_lbl_master_desc", lbl_desc)
        setattr(self, f"{prefix}_lbl_status_badge", lbl_status)
        setattr(self, f"{prefix}_switch_master", switch_master)

        return card

    # =========================================================================
    # 1. Basic Interface (Essential Landing Page - NO CLUTTER, EXCLUSIVE MASTER CARD)
    # =========================================================================
    def _create_basic_interface(self) -> QWidget:
        scroll, view, layout = self._create_page_scaffold(
            "Basic Settings",
            "Essential controls for cursor motion, size, click compression, and physics tilt"
        )

        # Compact Master Card (Exclusive to Basic page)
        master_card = self._create_master_card(view, prefix="basic")
        layout.addWidget(master_card)

        # Essential Controls Group
        group_ess = SettingCardGroup("Core Controls", view)

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
            "Directly copies your installed Windows scheme (Point.er Black+) with exact native hotspots",
            parent=group_ess
        )
        self.b_card_clone.setChecked(self.config.use_system_cursor_clone)
        self.b_card_clone.checkedChanged.connect(self._toggle_clone)
        group_ess.addSettingCard(self.b_card_clone)

        layout.addWidget(group_ess)

        # Quick Toggles Group (Clean secondary essentials)
        group_quick = SettingCardGroup("Quick Toggles", view)

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
            "Click & drag precision boost",
            "Forces 100% responsiveness while clicking to eliminate float during text selection (OFF by default)",
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
            "Unlock Elastic Spring-Damper, Predictive Lead, SmoothStep, and Kinematic Drag engines (OFF by default)",
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
                "Adaptive Exponential (Standard)",
                "Elastic Spring-Damper (Harmonic)",
                "Dynamic SmoothStep (Sigmoid)",
                "Zero-Latency Predictive (Look-ahead)",
                "Kinematic Drag (Momentum)"
            ],
            algo_map.get(self.config.smoothing_type, 0),
            self._update_algo
        )
        group_adv.addSettingCard(self.card_algo)

        # Spring Tension Slider
        self.card_stiff, self.slider_stiff, self.lbl_stiff = self._create_slider_card(
            FIF.ALIGNMENT,
            "Spring tension / stiffness",
            "Harmonic oscillator spring stiffness (k = 50 to 600)",
            50, 600, self.config.spring_stiffness,
            self._update_stiff,
            ""
        )
        group_adv.addSettingCard(self.card_stiff)

        # Spring Damping Slider
        self.card_damp, self.slider_damp, self.lbl_damp = self._create_slider_card(
            FIF.TILES,
            "Spring damping / friction",
            "Spring oscillation damping factor (c = 8 to 60)",
            8, 60, self.config.spring_damping,
            self._update_damp,
            ""
        )
        group_adv.addSettingCard(self.card_damp)

        # Velocity Prediction Lead
        self.card_pred, self.slider_pred, self.lbl_pred = self._create_slider_card(
            FIF.DATE_TIME,
            "Velocity prediction lead",
            "Forward motion extrapolation lead time (5ms to 80ms)",
            5, 80, self.config.prediction_factor * 1000,
            self._update_pred,
            " ms"
        )
        group_adv.addSettingCard(self.card_pred)

        # Kinematic Drag Friction
        self.card_drag, self.slider_drag, self.lbl_drag = self._create_slider_card(
            FIF.AIRPLANE,
            "Air drag friction",
            "Kinematic air resistance drag coefficient (5 to 45)",
            5, 45, self.config.drag_friction,
            self._update_drag,
            ""
        )
        group_adv.addSettingCard(self.card_drag)

        layout.addWidget(group_adv)

        # Helpful shortcut note to dedicated Tilt tab
        tilt_note_card = CardWidget(view)
        tnc_layout = QHBoxLayout(tilt_note_card)
        tnc_layout.setContentsMargins(18, 14, 18, 14)
        icon_tilt = IconWidget(FIF.ROTATE)
        icon_tilt.setFixedSize(18, 18)
        tnc_layout.addWidget(icon_tilt)
        lbl_tnote = BodyLabel("Looking for Dynamic Tilt, Rotational Inertia, Deadzone, or Return delay? Visit the Tilt tab in the sidebar.")
        lbl_tnote.setStyleSheet("color: #94A3B8; font-size: 13px; background: transparent;")
        tnc_layout.addWidget(lbl_tnote)
        tnc_layout.addStretch()
        layout.addWidget(tilt_note_card)

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
            "Toggle between forward velocity lean and full 2D physical inertia",
            [
                "Velocity Tilt (Leans along movement)",
                "Full Physics - Forward Inertia (Down tilts down)",
                "Full Physics - Opposing Inertia (Down rotates up)"
            ],
            tilt_idx,
            self._update_tilt_mode,
            width=280
        )
        self.group_tilt_options.addSettingCard(self.t_card_tilt_mode)

        # 2. Tilt Angle Multiplier Slider (10% to 500%)
        self.t_card_tstr, self.t_slider_tstr, self.t_lbl_tstr = self._create_slider_card(
            FIF.SCROLL,
            "Tilt angle multiplier",
            "Deflection strength of the rotational tilt (10% to 500%)",
            10, 500, self.config.tilt_strength * 100,
            self._update_tstr,
            "%"
        )
        self.group_tilt_options.addSettingCard(self.t_card_tstr)

        # 3. Slow Movement Deadzone (Optimization setting to eliminate slow jitter)
        self.t_card_deadzone, self.t_slider_deadzone, self.t_lbl_deadzone = self._create_slider_card(
            FIF.FILTER,
            "Slow movement deadzone",
            "Prevents tilt jitter and directional twitching during slow or micro movements (0 to 120 px/s)",
            0, 120, int(self.config.tilt_deadzone),
            self._update_tilt_deadzone,
            " px/s"
        )
        self.group_tilt_options.addSettingCard(self.t_card_deadzone)

        # 4. Disable Return to Original Position (Never Return / Hold Indefinitely)
        self.t_card_tilt_never_return = SwitchSettingCard(
            FIF.PIN,
            "Disable cursor returning back to original position",
            "Holds tilted cursor orientation indefinitely after stopping rather than returning back to neutral",
            parent=self.group_tilt_options
        )
        self.t_card_tilt_never_return.setChecked(self.config.tilt_disable_return)
        self.t_card_tilt_never_return.checkedChanged.connect(self._update_tilt_never_return)
        self.group_tilt_options.addSettingCard(self.t_card_tilt_never_return)

        # 5. Delay Before Rotation Return (Hold Delay)
        self.t_card_tilt_delay = SwitchSettingCard(
            FIF.DATE_TIME,
            "Delay before rotation return",
            "Holds cursor tilt after stopping and returns only after a delay instead of correcting instantly",
            parent=self.group_tilt_options
        )
        self.t_card_tilt_delay.setChecked(self.config.tilt_delay_enabled)
        self.t_card_tilt_delay.checkedChanged.connect(self._update_tilt_delay)
        self.group_tilt_options.addSettingCard(self.t_card_tilt_delay)

        # 6. Return Hold Delay Slider
        self.t_card_delay_dur, self.t_slider_delay_dur, self.t_lbl_delay_dur = self._create_slider_card(
            FIF.TILES,
            "Return hold delay",
            "How long the cursor holds its angle before returning (50ms to 2000ms)",
            50, 2000, int(self.config.tilt_return_delay * 1000),
            self._update_tilt_return_delay,
            " ms"
        )
        self.group_tilt_options.addSettingCard(self.t_card_delay_dur)

        # 7. Slow Rotation Return Switch
        self.t_card_tilt_decay = SwitchSettingCard(
            FIF.HISTORY,
            "Slow rotation return",
            "Gradually returns cursor to resting angle instead of snapping back instantly",
            parent=self.group_tilt_options
        )
        self.t_card_tilt_decay.setChecked(self.config.tilt_decay_enabled)
        self.t_card_tilt_decay.checkedChanged.connect(self._update_tilt_decay)
        self.group_tilt_options.addSettingCard(self.t_card_tilt_decay)

        # 8. Rotation Return Smoothness Slider
        self.t_card_decay_speed, self.t_slider_decay_speed, self.t_lbl_decay_speed = self._create_slider_card(
            FIF.SPEED_HIGH,
            "Rotation return smoothness",
            "Smoothness and duration of rotation recovery (10% to 100%)",
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

        self.a_card_clone = SwitchSettingCard(
            FIF.SYNC,
            "Clone active Windows cursor",
            "Directly copies your installed Windows scheme (Point.er Black+) with exact native hotspots",
            parent=group_scheme
        )
        self.a_card_clone.setChecked(self.config.use_system_cursor_clone)
        self.a_card_clone.checkedChanged.connect(self._toggle_clone)
        group_scheme.addSettingCard(self.a_card_clone)

        theme_map = {"aero_modern": 0, "neon_glow": 1, "macos_fluid": 2, "cyber_arrow": 3, "minimal_dot": 4}
        self.card_theme, self.combo_theme = self._create_combo_card(
            FIF.PALETTE,
            "Alternative vector theme",
            "Stylized procedural cursor styles (Inactive while system cloning is enabled)" if self.config.use_system_cursor_clone else "Stylized procedural cursor styles applied to custom pointer",
            ["Aero Modern", "Neon Glow", "macOS Fluid", "Cyber Arrow", "Minimalist Dot"],
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
            "Main inner body color for vector themes (Inactive while system cloning is enabled)" if self.config.use_system_cursor_clone else "Main inner body color for vector themes",
            self.config.primary_color,
            self._update_prim_color
        )
        self.card_prim.setEnabled(not self.config.use_system_cursor_clone)
        self.btn_prim_color.setEnabled(not self.config.use_system_cursor_clone)
        group_size.addSettingCard(self.card_prim)

        self.card_border, self.btn_border_color = self._create_color_card(
            FIF.BRUSH,
            "Accent border color",
            "Outer stroke border color for vector themes (Inactive while system cloning is enabled)" if self.config.use_system_cursor_clone else "Outer stroke border color for vector themes",
            self.config.border_color,
            self._update_border_color
        )
        self.card_border.setEnabled(not self.config.use_system_cursor_clone)
        self.btn_border_color.setEnabled(not self.config.use_system_cursor_clone)
        group_size.addSettingCard(self.card_border)

        layout.addWidget(group_size)

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
        return descriptions.get(algo_type, descriptions["exponential"])

    def _apply_badge_style(self, badge_label, is_enabled: bool):
        if is_enabled:
            badge_label.setText("Active")
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
            badge_label.setText("Paused")
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
        title = "FluidCursor Active" if is_enabled else "FluidCursor Paused"
        desc = "Real-time physics tracking active" if is_enabled else "Standard Windows cursor active"

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
                self.card_theme.setContent("Stylized procedural cursor styles (Inactive while system cloning is enabled)")
            else:
                self.card_theme.setContent("Stylized procedural cursor styles applied to custom pointer")
        if hasattr(self, "combo_theme"):
            self.combo_theme.setEnabled(not checked)

        if hasattr(self, "card_prim"):
            self.card_prim.setEnabled(not checked)
        if hasattr(self, "btn_prim_color"):
            self.btn_prim_color.setEnabled(not checked)

        if hasattr(self, "card_border"):
            self.card_border.setEnabled(not checked)
        if hasattr(self, "btn_border_color"):
            self.btn_border_color.setEnabled(not checked)

        self._notify()

    def _update_tilt_mode(self, idx: int):
        modes = ["velocity", "physics_forward", "physics_opposing"]
        self.config.tilt_mode = modes[idx] if idx < len(modes) else "velocity"

        if hasattr(self, "t_combo_tilt_mode") and self.t_combo_tilt_mode.currentIndex() != idx:
            self.t_combo_tilt_mode.blockSignals(True)
            self.t_combo_tilt_mode.setCurrentIndex(idx)
            self.t_combo_tilt_mode.blockSignals(False)

        self._notify()

    def _update_theme(self, idx: int):
        themes = ["aero_modern", "neon_glow", "macos_fluid", "cyber_arrow", "minimal_dot"]
        self.config.cursor_theme = themes[idx]
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
        self.config.tilt_strength = val / 100.0
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
            self.card_boost.setEnabled(adv)

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
        if self.cursor_mgr:
            self.cursor_mgr.restore_system_cursor()
        InfoBar.success(
            title="System Cursor Restored",
            content="Standard Windows cursor has been restored.",
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
        QApplication.instance().quit()

    def _notify(self):
        # Debounce disk write by 350ms so scrubbing sliders does not freeze the UI thread
        if hasattr(self, "_save_timer"):
            self._save_timer.start(350)
        else:
            self.config.save()
        if self.on_config_changed:
            self.on_config_changed()

    def closeEvent(self, event):
        if hasattr(self, "_save_timer"):
            self._save_timer.stop()
        self.config.save()
        event.ignore()
        self.hide()