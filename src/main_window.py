import os
import ctypes
from pathlib import Path
from PyQt6.QtCore import (
    Qt,
    QSize,
    QRectF,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QLinearGradient,
    QPainterPath,
    QPixmap,
    QGuiApplication,
    QFontMetrics,
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QFileDialog,
    QSlider,
    QStackedWidget,
    QGridLayout,
    QButtonGroup,
    QColorDialog,
    QSizePolicy,
)
from src.overlay import TOOL_DEFINITIONS
from src.icons import get_icon
from src.i18n import tr, tr_btn
from src.autostart import is_autostart_enabled, set_autostart_enabled
from src import theme

user32 = ctypes.WinDLL("user32", use_last_error=True)
WM_NCLBUTTONDOWN = 0x00A1
HTCAPTION = 2

CRYPTO_ADDRESSES = [
    ("Ethereum (ETH)", "0x2168A8e00f503D61cDe7C878321531c17C9D6089", "#627EEA"),
    ("TON", "UQAZ2pLXFMrCS2DShL4i94VCXv76pRHgUU83cW56sv_CE9Ui", "#0098EA"),
    ("Tron (TRX / TRC-20)", "TQj86sAZqMg8NeYksT1ZCzKV4TCjtU2PUA", "#FF0013"),
    ("Bitcoin (BTC)", "bc1qcl7rmmc08pum6gljc45rq4004k5azktqp9lsge", "#F7931A"),
]


class SupportDialog(QDialog):
    def __init__(self, parent, lang: str = "ua"):
        super().__init__(parent)
        self.lang = lang
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(590, 434)

        p = theme.CURRENT
        av = QColor(p.accent_vivid)
        avc = (av.red(), av.green(), av.blue())
        base_bg = theme.rgba(p.base, 248)
        row_bg = theme.rgba(p.tint, 185)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("SupportModalCard")
        card.setStyleSheet(f"""
            QFrame#SupportModalCard {{
                background-color: {base_bg};
                border: 1px solid {theme.rgba(avc, 95)};
                border-radius: 16px;
            }}
            QFrame.CryptoRow {{
                background-color: {row_bg};
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 11px;
            }}
            QFrame.CryptoRow:hover {{
                border: 1px solid {theme.rgba(avc, 110)};
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: #F2F2F7;
                font-family: "Segoe UI", sans-serif;
            }}
            QPushButton.CopyCryptoBtn {{
                background-color: {theme.rgba(avc, 36)};
                border: 1px solid {theme.rgba(avc, 118)};
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                min-width: 118px;
            }}
            QPushButton.CopyCryptoBtn:hover {{
                background-color: {theme.rgba(avc, 74)};
                border-color: {p.accent_vivid};
            }}
            QPushButton.CopyCryptoBtn[copied="true"] {{
                background-color: rgba(52, 199, 89, 42);
                border: 1px solid rgba(52, 199, 89, 175);
                color: #FFFFFF;
            }}
            QPushButton#CloseSupportBtn {{
                background: transparent;
                border: none;
                border-radius: 7px;
                min-width: 28px; max-width: 28px;
                min-height: 28px; max-height: 28px;
            }}
            QPushButton#CloseSupportBtn:hover {{
                background-color: rgba(255, 255, 255, 24);
            }}
        """)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(11)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        heart_badge = QLabel()
        heart_badge.setFixedSize(38, 38)
        heart_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heart_badge.setStyleSheet(f"""
            background-color: {theme.rgba(avc, 36)};
            border: 1px solid {theme.rgba(avc, 105)};
            border-radius: 10px;
        """)
        heart_badge.setPixmap(get_icon("heart", p.accent_vivid, 18).pixmap(18, 18))

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title_lbl = QLabel(tr(lang, "support_title"))
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        sub_lbl = QLabel(tr(lang, "support_subtitle"))
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("font-size: 12px; color: rgba(235, 235, 245, 168);")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)

        close_btn = QPushButton()
        close_btn.setObjectName("CloseSupportBtn")
        close_btn.setIcon(get_icon("close", "#E5E5EA", 15))
        close_btn.setIconSize(QSize(15, 15))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)

        top_bar.addWidget(heart_badge, 0, Qt.AlignmentFlag.AlignTop)
        top_bar.addLayout(title_col, 1)
        top_bar.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top_bar)
        lay.addSpacing(4)

        for net_name, addr, badge_col in CRYPTO_ADDRESSES:
            row_frame = QFrame()
            row_frame.setProperty("class", "CryptoRow")
            r_lay = QHBoxLayout(row_frame)
            r_lay.setContentsMargins(14, 10, 14, 10)
            r_lay.setSpacing(12)

            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background-color: {badge_col}; border-radius: 5px;")

            info_col = QVBoxLayout()
            info_col.setSpacing(2)
            net_lbl = QLabel(net_name)
            net_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #FFFFFF;")
            addr_lbl = QLabel(addr)
            addr_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            addr_lbl.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 11px; color: rgba(235, 235, 245, 195);"
            )
            info_col.addWidget(net_lbl)
            info_col.addWidget(addr_lbl)

            copy_btn = QPushButton("  " + tr_btn(lang, "btn_copy_addr"))
            copy_btn.setProperty("class", "CopyCryptoBtn")
            copy_btn.setProperty("copied", "false")
            copy_btn.setIcon(get_icon("copy", "#FFFFFF", 14))
            copy_btn.setIconSize(QSize(14, 14))
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.clicked.connect(lambda checked=False, a=addr, b=copy_btn: self._copy_address(a, b))

            r_lay.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
            r_lay.addLayout(info_col, 1)
            r_lay.addWidget(copy_btn, 0, Qt.AlignmentFlag.AlignVCenter)
            lay.addWidget(row_frame)

        lay.addStretch()

        footer = QLabel("by nord")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("""
            color: rgba(255, 255, 255, 95);
            font-family: "Segoe UI Variable Display", "Segoe UI Light", "Segoe UI", sans-serif;
            font-size: 11px;
            font-weight: 300;
            letter-spacing: 2.8px;
        """)
        lay.addWidget(footer)

    def _copy_address(self, address: str, btn: QPushButton):
        QGuiApplication.clipboard().setText(address)
        btn.setProperty("copied", "true")
        btn.setIcon(get_icon("check", "#34C759", 14))
        btn.setText("  " + tr_btn(self.lang, "btn_copied_addr"))
        btn.style().unpolish(btn)
        btn.style().polish(btn)

        def _restore():
            try:
                btn.setProperty("copied", "false")
                btn.setIcon(get_icon("copy", "#FFFFFF", 14))
                btn.setText("  " + tr_btn(self.lang, "btn_copy_addr"))
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            except RuntimeError:
                pass

        QTimer.singleShot(1500, _restore)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 64:
            win_handle = self.windowHandle()
            if win_handle is not None and win_handle.startSystemMove():
                event.accept()
                return
            hwnd = int(self.winId())
            user32.ReleaseCapture()
            user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
            event.accept()


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = bool(checked)
        self._thumb_pos = 22.0 if self._checked else 2.0
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumb_pos", self)
        self._anim.setDuration(65)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    @pyqtProperty(float)
    def thumb_pos(self) -> float:
        return self._thumb_pos

    @thumb_pos.setter
    def thumb_pos(self, val: float):
        self._thumb_pos = val
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        self._checked = bool(checked)
        self._thumb_pos = 22.0 if self._checked else 2.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._anim.stop()
            self._anim.setStartValue(self._thumb_pos)
            self._anim.setEndValue(22.0 if self._checked else 2.0)
            self._anim.start()
            self.update()
            self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._checked:
            acc = QColor(theme.CURRENT.accent)
            lum = 0.299 * acc.red() + 0.587 * acc.green() + 0.114 * acc.blue()
            track_color = QColor(theme.CURRENT.accent_vivid) if lum < 52 else acc
            border_pen = QPen(QColor(theme.CURRENT.accent_vivid), 1)
        else:
            track_color = QColor(255, 255, 255, 36)
            border_pen = QPen(QColor(255, 255, 255, 24), 1)

        p.setPen(border_pen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0), 11.5, 11.5)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(self._thumb_pos, 2.0, 20.0, 20.0))
        p.end()


class ClickableTile(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon_name: str, title: str, subtitle: str, hotkey: str):
        super().__init__()
        self.setProperty("role", "ActionTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(106)

        v = QVBoxLayout(self)
        v.setContentsMargins(18, 13, 18, 13)
        v.setSpacing(3)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        self.icon_badge = QLabel()
        self.icon_badge.setFixedSize(34, 34)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_badge.setProperty("role", "TileIcon")
        self._icon_name = icon_name
        self.icon_badge.setPixmap(get_icon(icon_name, "#FFFFFF", 18).pixmap(18, 18))

        self.chip = QLabel(hotkey)
        self.chip.setProperty("role", "Chip")

        top.addWidget(self.icon_badge)
        top.addStretch()
        top.addWidget(self.chip)
        v.addLayout(top)
        v.addStretch()

        self.t_lbl = QLabel(title)
        self.t_lbl.setProperty("role", "TileTitle")
        self.s_lbl = QLabel(subtitle)
        self.s_lbl.setProperty("role", "Muted")
        self.s_lbl.setWordWrap(True)
        v.addWidget(self.t_lbl)
        v.addWidget(self.s_lbl)

    def update_icon_contrast(self, fg_hex: str):
        self.icon_badge.setPixmap(get_icon(self._icon_name, fg_hex, 18).pixmap(18, 18))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()


class HotkeyRecorderButton(QPushButton):
    hotkey_changed = pyqtSignal(str)

    def __init__(self, current_hotkey: str, hotkey_manager, config):
        super().__init__(current_hotkey)
        self.current_hotkey = current_hotkey
        self.hotkey_manager = hotkey_manager
        self.config = config
        self.setProperty("role", "HotkeyField")
        self.setProperty("recording", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._toggle_recording)

    def _toggle_recording(self):
        if self.property("recording") == "true":
            self.cancel_if_recording()
            return
        lang = self.config.get("language", default="ua")
        self.setProperty("recording", "true")
        self.setText(tr_btn(lang, "hk_press"))
        self.style().unpolish(self)
        self.style().polish(self)
        if self.hotkey_manager is not None:
            self.hotkey_manager.begin_capture(self._on_captured)

    def cancel_if_recording(self):
        if self.property("recording") == "true":
            if self.hotkey_manager is not None:
                self.hotkey_manager.cancel_capture()
            self._on_captured(None)

    def _on_captured(self, combo: str | None):
        self.setProperty("recording", "false")
        if combo:
            self.current_hotkey = combo
            self.setText(combo)
            self.hotkey_changed.emit(combo)
        else:
            self.setText(self.current_hotkey)
        self.style().unpolish(self)
        self.style().polish(self)


class MainSettingsWindow(QMainWindow):
    region_capture_requested = pyqtSignal()
    fullscreen_capture_requested = pyqtSignal()
    hotkeys_updated = pyqtSignal()
    accent_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    minimized_to_tray = pyqtSignal()

    WIN_W = 880
    WIN_H = 616
    SIDEBAR_W = 248

    def __init__(self, config, hotkey_manager=None):
        super().__init__()
        self.config = config
        self.hotkey_manager = hotkey_manager

        self._bg_pil = None
        self._bg_blurred_pixmap: QPixmap | None = None
        self._cached_frame: QPixmap | None = None

        self.setWindowTitle("SnapLite")
        self.setFixedSize(self.WIN_W, self.WIN_H)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._root = QWidget(self)
        self.setCentralWidget(self._root)

        main_h = QHBoxLayout(self._root)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        self.sidebar = self._build_sidebar()
        main_h.addWidget(self.sidebar)

        right_panel = QWidget()
        right_v = QVBoxLayout(right_panel)
        right_v.setContentsMargins(28, 18, 28, 20)
        right_v.setSpacing(10)

        right_v.addLayout(self._build_top_bar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_page_capture())
        self.pages.addWidget(self._build_page_tools())
        self.pages.addWidget(self._build_page_appearance())
        right_v.addWidget(self.pages, 1)

        main_h.addWidget(right_panel, 1)

        self._reload_background_and_theme()
        self.retranslate_ui()
        self._center_on_screen()

    def _center_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            x = avail.x() + (avail.width() - self.WIN_W) // 2
            y = avail.y() + (avail.height() - self.WIN_H) // 2
            self.move(x, y)

    def _lang(self) -> str:
        return self.config.get("language", default="ua")

    def _cancel_hotkey_recordings(self):
        self.btn_hk_region.cancel_if_recording()
        self.btn_hk_full.cancel_if_recording()

    def _switch_page(self, idx: int):
        self._cancel_hotkey_recordings()
        self.pages.setCurrentIndex(idx)
        keys = ["page_capture", "page_tools", "page_appearance"]
        self.page_title_lbl.setText(tr(self._lang(), keys[idx]))

    def _open_support_dialog(self):
        self._cancel_hotkey_recordings()
        dlg = SupportDialog(self, self._lang())
        dlg.exec()

    def _build_sidebar(self) -> QFrame:
        sb = QFrame()
        sb.setObjectName("Sidebar")
        sb.setFixedWidth(self.SIDEBAR_W)
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(16, 22, 16, 18)
        lay.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(4, 0, 4, 0)
        brand_row.setSpacing(11)
        self.logo_lbl = QLabel()
        self.logo_lbl.setFixedSize(36, 36)
        self.logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_lbl.setProperty("role", "TileIcon")
        self.logo_lbl.setPixmap(get_icon("select", "#FFFFFF", 18).pixmap(18, 18))

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        app_lbl = QLabel("SnapLite")
        app_lbl.setProperty("role", "AppName")
        sub_lbl = QLabel("Screen Utility")
        sub_lbl.setProperty("role", "Muted")
        brand_col.addWidget(app_lbl)
        brand_col.addWidget(sub_lbl)

        brand_row.addWidget(self.logo_lbl)
        brand_row.addLayout(brand_col)
        brand_row.addStretch()
        lay.addLayout(brand_row)
        lay.addSpacing(18)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []

        nav_items = [
            ("select", "nav_capture", 0),
            ("sliders", "nav_tools", 1),
            ("palette", "nav_appearance", 2),
        ]
        for idx, (icon_name, tr_key, page_idx) in enumerate(nav_items):
            btn = QPushButton()
            btn.setProperty("role", "Nav")
            btn.setProperty("tr_key", tr_key)
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.setIcon(get_icon(icon_name, "#F2F2F7", 17))
            btn.setIconSize(QSize(17, 17))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, p=page_idx: self._switch_page(p))
            self.nav_group.addButton(btn, page_idx)
            self.nav_buttons.append(btn)
            lay.addWidget(btn)

        lay.addStretch()

        by_nord_lbl = QLabel("by nord")
        by_nord_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        by_nord_lbl.setStyleSheet("""
            color: rgba(255, 255, 255, 98);
            font-family: "Segoe UI Variable Display", "Segoe UI Light", "Segoe UI", sans-serif;
            font-size: 11px;
            font-style: normal;
            font-weight: 300;
            letter-spacing: 2.8px;
            padding-bottom: 4px;
        """)
        lay.addWidget(by_nord_lbl)
        lay.addSpacing(2)

        self.btn_support = QPushButton()
        self.btn_support.setProperty("role", "SupportBtn")
        self.btn_support.setIcon(get_icon("heart", theme.CURRENT.accent_vivid, 16))
        self.btn_support.setIconSize(QSize(16, 16))
        self.btn_support.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_support.clicked.connect(self._open_support_dialog)
        lay.addWidget(self.btn_support)
        lay.addSpacing(6)

        status_card = QFrame()
        status_card.setProperty("role", "Card")
        sc_lay = QVBoxLayout(status_card)
        sc_lay.setContentsMargins(13, 10, 13, 10)
        sc_lay.setSpacing(2)
        self.st_title = QLabel()
        self.st_title.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.st_sub = QLabel()
        self.st_sub.setProperty("role", "Muted")
        sc_lay.addWidget(self.st_title)
        sc_lay.addWidget(self.st_sub)
        lay.addWidget(status_card)

        return sb

    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 4)
        self.page_title_lbl = QLabel()
        self.page_title_lbl.setProperty("role", "PageTitle")
        bar.addWidget(self.page_title_lbl)
        bar.addStretch()

        self.btn_min = QPushButton()
        self.btn_min.setProperty("role", "WinBtn")
        self.btn_min.setIcon(get_icon("minimize", "#E5E5EA", 15))
        self.btn_min.setIconSize(QSize(15, 15))
        self.btn_min.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_min.clicked.connect(self._minimize_to_tray)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("WinClose")
        self.btn_close.setProperty("role", "WinBtn")
        self.btn_close.setIcon(get_icon("close", "#E5E5EA", 15))
        self.btn_close.setIconSize(QSize(15, 15))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self._minimize_to_tray)

        bar.addWidget(self.btn_min)
        bar.addWidget(self.btn_close)
        return bar

    def _minimize_to_tray(self):
        self._cancel_hotkey_recordings()
        self.config.flush()
        self.hide()
        self.minimized_to_tray.emit()

    def _build_page_capture(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 2, 0, 0)
        lay.setSpacing(8)

        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(14)

        self.tile_region = ClickableTile(
            icon_name="select",
            title="",
            subtitle="",
            hotkey=self.config.get("hotkeys", "region_capture", "Ctrl+PrintScreen"),
        )
        self.tile_region.clicked.connect(self.region_capture_requested.emit)

        self.tile_full = ClickableTile(
            icon_name="monitor",
            title="",
            subtitle="",
            hotkey=self.config.get("hotkeys", "fullscreen_capture", "PrintScreen"),
        )
        self.tile_full.clicked.connect(self.fullscreen_capture_requested.emit)

        tiles_row.addWidget(self.tile_region, 1)
        tiles_row.addWidget(self.tile_full, 1)
        lay.addLayout(tiles_row)

        self.sec_hk_lbl = self._section_label("")
        lay.addWidget(self.sec_hk_lbl)

        hk_card = self._create_card()
        hk_lay = QVBoxLayout(hk_card)
        hk_lay.setContentsMargins(16, 4, 16, 4)
        hk_lay.setSpacing(0)

        self.btn_hk_region = HotkeyRecorderButton(
            self.config.get("hotkeys", "region_capture", "Ctrl+PrintScreen"),
            self.hotkey_manager,
            self.config,
        )
        self.btn_hk_region.hotkey_changed.connect(self._on_region_hk_changed)
        row_w, self.lbl_hk_region = self._row("keyboard", "", self.btn_hk_region, height=44)
        hk_lay.addWidget(row_w)
        hk_lay.addWidget(self._divider())

        self.btn_hk_full = HotkeyRecorderButton(
            self.config.get("hotkeys", "fullscreen_capture", "PrintScreen"),
            self.hotkey_manager,
            self.config,
        )
        self.btn_hk_full.hotkey_changed.connect(self._on_full_hk_changed)
        row_w, self.lbl_hk_full = self._row("monitor", "", self.btn_hk_full, height=44)
        hk_lay.addWidget(row_w)
        lay.addWidget(hk_card)

        self.sec_save_lbl = self._section_label("")
        lay.addWidget(self.sec_save_lbl)

        sv_card = self._create_card()
        sv_lay = QVBoxLayout(sv_card)
        sv_lay.setContentsMargins(16, 4, 16, 4)
        sv_lay.setSpacing(0)

        self.sw_clip = ToggleSwitch(self.config.get("capture", "copy_to_clipboard", True))
        self.sw_clip.toggled.connect(lambda v: self.config.set("capture", "copy_to_clipboard", v))
        row_w, self.lbl_row_clip = self._row("copy", "", self.sw_clip, height=43)
        sv_lay.addWidget(row_w)
        sv_lay.addWidget(self._divider())

        self.sw_autosave = ToggleSwitch(self.config.get("capture", "auto_save_fullscreen", True))
        self.sw_autosave.toggled.connect(lambda v: self.config.set("capture", "auto_save_fullscreen", v))
        row_w, self.lbl_row_autosave = self._row("save", "", self.sw_autosave, height=43)
        sv_lay.addWidget(row_w)
        sv_lay.addWidget(self._divider())

        folder_right = QWidget()
        fr_lay = QHBoxLayout(folder_right)
        fr_lay.setContentsMargins(0, 0, 0, 0)
        fr_lay.setSpacing(10)
        self.lbl_dir = QLabel()
        self.lbl_dir.setProperty("role", "Muted")
        self._update_dir_label(self.config.get("capture", "save_directory", ""))
        self.btn_dir = QPushButton()
        self.btn_dir.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_dir.setIcon(get_icon("folder", "#F2F2F7", 15))
        self.btn_dir.setIconSize(QSize(15, 15))
        self.btn_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dir.clicked.connect(self._choose_directory)
        fr_lay.addWidget(self.lbl_dir)
        fr_lay.addWidget(self.btn_dir)
        row_w, self.lbl_row_folder = self._row("folder", "", folder_right, height=44)
        sv_lay.addWidget(row_w)
        sv_lay.addWidget(self._divider())

        self.sw_autostart = ToggleSwitch(is_autostart_enabled())
        self.sw_autostart.toggled.connect(set_autostart_enabled)
        row_w, self.lbl_row_autostart = self._row("sliders", "", self.sw_autostart, height=43)
        sv_lay.addWidget(row_w)
        sv_lay.addWidget(self._divider())

        lang_seg = QFrame()
        lang_seg.setProperty("role", "Segmented")
        ls_lay = QHBoxLayout(lang_seg)
        ls_lay.setContentsMargins(3, 3, 3, 3)
        ls_lay.setSpacing(3)

        self.lang_group = QButtonGroup(self)
        self.lang_group.setExclusive(True)
        cur_lang = self._lang()
        for code, title in (("ua", "UA"), ("en", "EN"), ("ru", "RU")):
            b = QPushButton(title)
            b.setProperty("role", "Segment")
            b.setCheckable(True)
            b.setChecked(cur_lang == code)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda checked=False, c=code: self._set_language(c))
            self.lang_group.addButton(b)
            ls_lay.addWidget(b)

        row_w, self.lbl_row_lang = self._row("keyboard", "", lang_seg, height=44)
        sv_lay.addWidget(row_w)

        lay.addWidget(sv_card)
        lay.addStretch()
        return page

    def _build_page_tools(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 2, 0, 0)
        lay.setSpacing(10)

        self.sec_ov_lbl = self._section_label("")
        lay.addWidget(self.sec_ov_lbl)

        ov_card = self._create_card()
        ov_lay = QVBoxLayout(ov_card)
        ov_lay.setContentsMargins(16, 6, 16, 6)
        ov_lay.setSpacing(0)

        self.sw_mag = ToggleSwitch(self.config.get("capture", "show_magnifier", True))
        self.sw_mag.toggled.connect(lambda v: self.config.set("capture", "show_magnifier", v))
        row_w, self.lbl_row_mag = self._row("magnifier", "", self.sw_mag)
        ov_lay.addWidget(row_w)
        ov_lay.addWidget(self._divider())

        ov_dim_right = QWidget()
        odr_lay = QHBoxLayout(ov_dim_right)
        odr_lay.setContentsMargins(0, 0, 0, 0)
        odr_lay.setSpacing(10)
        init_dim = int(self.config.get("capture", "dim_opacity", 110))
        self.lbl_ov_dim_val = QLabel(f"{round(init_dim * 100 / 255)}%")
        self.lbl_ov_dim_val.setProperty("role", "Muted")
        self.lbl_ov_dim_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_ov_dim_val.setFixedWidth(38)
        self.slider_dim = QSlider(Qt.Orientation.Horizontal)
        self.slider_dim.setRange(0, 200)
        self.slider_dim.setFixedWidth(175)
        self.slider_dim.setValue(init_dim)
        self.slider_dim.valueChanged.connect(self._on_ov_dim_changed)
        odr_lay.addWidget(self.lbl_ov_dim_val)
        odr_lay.addWidget(self.slider_dim)
        row_w, self.lbl_row_dim = self._row("sliders", "", ov_dim_right)
        ov_lay.addWidget(row_w)
        ov_lay.addWidget(self._divider())

        seg_frame = QFrame()
        seg_frame.setProperty("role", "Segmented")
        seg_lay = QHBoxLayout(seg_frame)
        seg_lay.setContentsMargins(3, 3, 3, 3)
        seg_lay.setSpacing(3)

        self.btn_pos_top = QPushButton()
        self.btn_pos_top.setProperty("role", "Segment")
        self.btn_pos_top.setCheckable(True)
        self.btn_pos_sel = QPushButton()
        self.btn_pos_sel.setProperty("role", "Segment")
        self.btn_pos_sel.setCheckable(True)

        cur_pos = self.config.get("toolbar", "position", "top")
        self.btn_pos_top.setChecked(cur_pos == "top")
        self.btn_pos_sel.setChecked(cur_pos != "top")

        pos_group = QButtonGroup(self)
        pos_group.setExclusive(True)
        pos_group.addButton(self.btn_pos_top)
        pos_group.addButton(self.btn_pos_sel)
        self.btn_pos_top.clicked.connect(lambda: self.config.set("toolbar", "position", "top"))
        self.btn_pos_sel.clicked.connect(lambda: self.config.set("toolbar", "position", "selection"))

        seg_lay.addWidget(self.btn_pos_top)
        seg_lay.addWidget(self.btn_pos_sel)
        row_w, self.lbl_row_pos = self._row("select", "", seg_frame)
        ov_lay.addWidget(row_w)
        lay.addWidget(ov_card)

        self.sec_tools_lbl = self._section_label("")
        lay.addWidget(self.sec_tools_lbl)

        tools_card = self._create_card()
        grid = QGridLayout(tools_card)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setSpacing(8)

        visible = set(self.config.get("toolbar", "visible_tools", [t[0] for t in TOOL_DEFINITIONS]))
        self.tool_chip_buttons: dict[str, QPushButton] = {}

        for idx, (tid, icon_name, tr_key) in enumerate(TOOL_DEFINITIONS):
            chip = QPushButton()
            chip.setProperty("role", "ToolChip")
            chip.setProperty("tr_key", tr_key)
            chip.setCheckable(True)
            chip.setChecked(tid in visible or tid == "select")
            chip.setIcon(get_icon(icon_name, "#F2F2F7", 16))
            chip.setIconSize(QSize(16, 16))
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            if tid == "select":
                chip.setEnabled(False)
            chip.toggled.connect(self._save_visible_tools)
            self.tool_chip_buttons[tid] = chip
            grid.addWidget(chip, idx // 3, idx % 3)

        lay.addWidget(tools_card)
        lay.addStretch()
        return page

    def _build_page_appearance(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 2, 0, 0)
        lay.setSpacing(10)

        self.sec_bg_lbl = self._section_label("")
        lay.addWidget(self.sec_bg_lbl)

        bg_card = self._create_card()
        bg_lay = QVBoxLayout(bg_card)
        bg_lay.setContentsMargins(16, 8, 16, 8)
        bg_lay.setSpacing(0)

        photo_right = QWidget()
        pr_lay = QHBoxLayout(photo_right)
        pr_lay.setContentsMargins(0, 0, 0, 0)
        pr_lay.setSpacing(8)

        self.lbl_bg_name = QLabel()
        self.lbl_bg_name.setProperty("role", "Muted")

        self.btn_pick_bg = QPushButton()
        self.btn_pick_bg.setProperty("role", "Primary")
        self.btn_pick_bg.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_pick_bg.setIcon(get_icon("image", "#FFFFFF", 15))
        self.btn_pick_bg.setIconSize(QSize(15, 15))
        self.btn_pick_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick_bg.clicked.connect(self._pick_background_photo)

        self.btn_clear_bg = QPushButton()
        self.btn_clear_bg.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_clear_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_bg.clicked.connect(self._clear_background_photo)

        pr_lay.addWidget(self.lbl_bg_name)
        pr_lay.addWidget(self.btn_pick_bg)
        pr_lay.addWidget(self.btn_clear_bg)
        row_w, self.lbl_row_bg_img = self._row("image", "", photo_right, height=48)
        bg_lay.addWidget(row_w)
        bg_lay.addWidget(self._divider())

        blur_right = QWidget()
        br_lay = QHBoxLayout(blur_right)
        br_lay.setContentsMargins(0, 0, 0, 0)
        br_lay.setSpacing(10)
        self.lbl_blur_val = QLabel(f"{self.config.get('appearance', 'background_blur', 18)} px")
        self.lbl_blur_val.setProperty("role", "Muted")
        self.lbl_blur_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_blur_val.setFixedWidth(44)
        self.slider_bg_blur = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_blur.setRange(0, 40)
        self.slider_bg_blur.setFixedWidth(185)
        self.slider_bg_blur.setValue(int(self.config.get("appearance", "background_blur", 18)))
        self.slider_bg_blur.valueChanged.connect(self._on_bg_blur_changed)
        br_lay.addWidget(self.lbl_blur_val)
        br_lay.addWidget(self.slider_bg_blur)
        row_w, self.lbl_row_bg_blur = self._row("blur", "", blur_right)
        bg_lay.addWidget(row_w)
        bg_lay.addWidget(self._divider())

        dim_right = QWidget()
        dr_lay = QHBoxLayout(dim_right)
        dr_lay.setContentsMargins(0, 0, 0, 0)
        dr_lay.setSpacing(10)
        self.lbl_bg_dim_val = QLabel(f"{self.config.get('appearance', 'background_dim', 45)}%")
        self.lbl_bg_dim_val.setProperty("role", "Muted")
        self.lbl_bg_dim_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_bg_dim_val.setFixedWidth(44)
        self.slider_bg_dim = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_dim.setRange(10, 88)
        self.slider_bg_dim.setFixedWidth(185)
        self.slider_bg_dim.setValue(int(self.config.get("appearance", "background_dim", 45)))
        self.slider_bg_dim.valueChanged.connect(self._on_bg_dim_changed)
        dr_lay.addWidget(self.lbl_bg_dim_val)
        dr_lay.addWidget(self.slider_bg_dim)
        row_w, self.lbl_row_bg_dim = self._row("sliders", "", dim_right)
        bg_lay.addWidget(row_w)

        lay.addWidget(bg_card)

        self.sec_pal_lbl = self._section_label("")
        lay.addWidget(self.sec_pal_lbl)

        col_card = self._create_card()
        col_lay = QVBoxLayout(col_card)
        col_lay.setContentsMargins(16, 8, 16, 8)
        col_lay.setSpacing(0)

        self.sw_adaptive = ToggleSwitch(self.config.get("appearance", "adaptive_colors", True))
        self.sw_adaptive.toggled.connect(self._on_adaptive_toggled)
        row_w, self.lbl_row_adaptive = self._row("palette", "", self.sw_adaptive, height=48)
        col_lay.addWidget(row_w)
        col_lay.addWidget(self._divider())

        accent_right = QWidget()
        ar_lay = QHBoxLayout(accent_right)
        ar_lay.setContentsMargins(0, 0, 0, 0)
        ar_lay.setSpacing(10)

        self.accent_preview_bar = QFrame()
        self.accent_preview_bar.setFixedSize(46, 24)

        self.lbl_accent_hex = QLabel()
        self.lbl_accent_hex.setProperty("role", "Muted")
        self.lbl_accent_hex.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")

        self.btn_custom_col = QPushButton()
        self.btn_custom_col.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_custom_col.setIcon(get_icon("palette", "#F2F2F7", 15))
        self.btn_custom_col.setIconSize(QSize(15, 15))
        self.btn_custom_col.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom_col.clicked.connect(self._pick_custom_accent)

        ar_lay.addWidget(self.accent_preview_bar)
        ar_lay.addWidget(self.lbl_accent_hex)
        ar_lay.addWidget(self.btn_custom_col)

        row_w, self.lbl_row_accent = self._row("sliders", "", accent_right, height=48)
        col_lay.addWidget(row_w)
        lay.addWidget(col_card)
        lay.addStretch()
        return page

    def _set_language(self, lang_code: str):
        self.config.set("language", lang_code)
        self.retranslate_ui()
        self.language_changed.emit(lang_code)

    def retranslate_ui(self):
        L = self._lang()
        page_keys = ["page_capture", "page_tools", "page_appearance"]
        self.page_title_lbl.setText(tr(L, page_keys[self.pages.currentIndex()]))

        for btn in self.nav_buttons:
            btn.setText("  " + tr_btn(L, btn.property("tr_key")))

        self.btn_support.setText("  " + tr_btn(L, "support_us"))
        self.st_title.setText(tr(L, "status_title"))
        self.st_sub.setText(tr(L, "status_sub"))
        self.btn_min.setToolTip(tr(L, "tooltip_min"))
        self.btn_close.setToolTip(tr(L, "tooltip_close"))

        self.tile_region.t_lbl.setText(tr(L, "tile_region_title"))
        self.tile_region.s_lbl.setText(tr(L, "tile_region_sub"))
        self.tile_full.t_lbl.setText(tr(L, "tile_full_title"))
        self.tile_full.s_lbl.setText(tr(L, "tile_full_sub"))

        self.sec_hk_lbl.setText(tr(L, "sec_hotkeys"))
        self.lbl_hk_region.setText(tr(L, "row_hk_region"))
        self.lbl_hk_full.setText(tr(L, "row_hk_full"))
        if self.btn_hk_region.property("recording") == "true":
            self.btn_hk_region.setText(tr_btn(L, "hk_press"))
        if self.btn_hk_full.property("recording") == "true":
            self.btn_hk_full.setText(tr_btn(L, "hk_press"))

        self.sec_save_lbl.setText(tr(L, "sec_save_system"))
        self.lbl_row_clip.setText(tr(L, "row_clip"))
        self.lbl_row_autosave.setText(tr(L, "row_autosave"))
        self.lbl_row_folder.setText(tr(L, "row_folder"))
        self.btn_dir.setText(tr_btn(L, "btn_change_folder"))
        self._update_dir_label(self.config.get("capture", "save_directory", ""))
        self.lbl_row_autostart.setText(tr(L, "row_autostart"))
        self.lbl_row_lang.setText(tr(L, "row_language"))

        self.sec_ov_lbl.setText(tr(L, "sec_overlay_behavior"))
        self.lbl_row_mag.setText(tr(L, "row_magnifier"))
        self.lbl_row_dim.setText(tr(L, "row_dim"))
        self.lbl_row_pos.setText(tr(L, "row_toolbar_pos"))
        self.btn_pos_top.setText(tr_btn(L, "pos_top"))
        self.btn_pos_sel.setText(tr_btn(L, "pos_sel"))
        self.sec_tools_lbl.setText(tr(L, "sec_active_tools"))

        for chip in self.tool_chip_buttons.values():
            chip.setText("  " + tr_btn(L, chip.property("tr_key")))

        self.sec_bg_lbl.setText(tr(L, "sec_bg_photo"))
        self.lbl_row_bg_img.setText(tr(L, "row_bg_img"))
        self._update_bg_label(self.config.get("appearance", "background_image", ""))
        self.btn_pick_bg.setText(tr_btn(L, "btn_pick_photo"))
        self.btn_clear_bg.setText(tr_btn(L, "btn_reset"))
        self.lbl_row_bg_blur.setText(tr(L, "row_bg_blur"))
        self.lbl_row_bg_dim.setText(tr(L, "row_bg_dim"))

        self.sec_pal_lbl.setText(tr(L, "sec_palette"))
        self.lbl_row_adaptive.setText(tr(L, "row_adaptive"))
        self.lbl_row_accent.setText(tr(L, "row_accent"))
        self.btn_custom_col.setText(tr_btn(L, "btn_pick_color"))

    def _row(self, icon_name: str, text: str, right_widget: QWidget, height: int = 46) -> tuple[QWidget, QLabel]:
        row = QWidget()
        row.setMinimumHeight(height)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 5, 0, 5)
        lay.setSpacing(12)

        ic = QLabel()
        ic.setFixedSize(30, 30)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setProperty("role", "RowIcon")
        ic.setPixmap(get_icon(icon_name, "#E5E5EA", 16).pixmap(16, 16))

        lbl = QLabel(text)
        lbl.setProperty("role", "RowTitle")
        lbl.setWordWrap(True)

        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(lbl, 1, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(right_widget, 0, Qt.AlignmentFlag.AlignVCenter)
        return row, lbl

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("role", "Section")
        return lbl

    def _create_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "Card")
        return card

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFixedHeight(1)
        line.setProperty("role", "Divider")
        return line

    def _elide_middle(self, widget: QLabel, text: str, max_px: int) -> str:
        fm = QFontMetrics(widget.font())
        return fm.elidedText(text, Qt.TextElideMode.ElideMiddle, max_px)

    def _update_dir_label(self, full_path: str):
        self.lbl_dir.setText(self._elide_middle(self.lbl_dir, full_path, 205))
        self.lbl_dir.setToolTip(full_path)

    def _update_bg_label(self, bg_path: str):
        if bg_path and os.path.exists(bg_path):
            name = Path(bg_path).name
            self.lbl_bg_name.setText(self._elide_middle(self.lbl_bg_name, name, 138))
            self.lbl_bg_name.setToolTip(bg_path)
        else:
            default_txt = tr(self._lang(), "bg_default")
            self.lbl_bg_name.setText(self._elide_middle(self.lbl_bg_name, default_txt, 138))
            self.lbl_bg_name.setToolTip("")

    def _rebuild_cached_frame(self):
        frame = QPixmap(self.WIN_W, self.WIN_H)
        frame.fill(Qt.GlobalColor.transparent)

        p = QPainter(frame)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.WIN_W - 1.0, self.WIN_H - 1.0)

        clip = QPainterPath()
        clip.addRoundedRect(rect, 14, 14)
        p.setClipPath(clip)

        if self._bg_blurred_pixmap is not None and not self._bg_blurred_pixmap.isNull():
            p.drawPixmap(0, 0, self.WIN_W, self.WIN_H, self._bg_blurred_pixmap)
            dim_pct = int(self.config.get("appearance", "background_dim", 45))
            alpha = int(255 * (dim_pct / 100.0))
            t = theme.CURRENT.base
            p.fillRect(0, 0, self.WIN_W, self.WIN_H, QColor(t[0], t[1], t[2], alpha))
        else:
            grad = QLinearGradient(0, 0, self.WIN_W, self.WIN_H)
            b = theme.CURRENT.base
            t = theme.CURRENT.tint
            grad.setColorAt(0.0, QColor(t[0], t[1], t[2]))
            grad.setColorAt(1.0, QColor(b[0], b[1], b[2]))
            p.fillRect(0, 0, self.WIN_W, self.WIN_H, grad)

        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 38), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 14, 14)
        p.end()

        self._cached_frame = frame
        self.update()

    def _reload_background_and_theme(self):
        bg_path = self.config.get("appearance", "background_image", "")
        blur_r = int(self.config.get("appearance", "background_blur", 18))
        adaptive = bool(self.config.get("appearance", "adaptive_colors", True))
        manual_acc = self.config.get("appearance", "manual_accent", theme.DEFAULT_ACCENT)

        if bg_path and os.path.exists(bg_path):
            self._bg_pil = theme.load_fitted(bg_path, (self.WIN_W, self.WIN_H))
        else:
            self._bg_pil = None
        self._update_bg_label(bg_path)

        if self._bg_pil is not None:
            self._bg_blurred_pixmap = theme.blurred_pixmap(self._bg_pil, blur_r)
            if adaptive:
                pal = theme.extract_palette(self._bg_pil)
            else:
                extracted = theme.extract_palette(self._bg_pil)
                pal = theme.palette_from_accent(manual_acc, extracted.tint)
        else:
            self._bg_blurred_pixmap = None
            pal = theme.palette_from_accent(manual_acc)

        theme.CURRENT = pal
        self.config.set("appearance", "accent_color", pal.accent)
        self.setStyleSheet(theme.build_qss(pal))

        self.logo_lbl.setPixmap(get_icon("select", pal.on_accent, 18).pixmap(18, 18))
        self.tile_region.update_icon_contrast(pal.on_accent)
        self.tile_full.update_icon_contrast(pal.on_accent)
        self.btn_pick_bg.setIcon(get_icon("image", pal.on_accent, 15))
        self.btn_support.setIcon(get_icon("heart", pal.accent_vivid, 16))

        self.accent_preview_bar.setStyleSheet(
            f"background-color: {pal.accent}; border: 1px solid rgba(255,255,255,95); border-radius: 6px;"
        )
        self.lbl_accent_hex.setText(pal.accent.upper())

        self.accent_changed.emit(pal.accent)
        self._rebuild_cached_frame()

    def _pick_background_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr(self._lang(), "row_bg_img"),
            str(Path.home() / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if file_path:
            self.config.set("appearance", "background_image", file_path)
            self._reload_background_and_theme()

    def _clear_background_photo(self):
        self.config.set("appearance", "background_image", "")
        self._reload_background_and_theme()

    def _on_ov_dim_changed(self, val: int):
        self.lbl_ov_dim_val.setText(f"{round(val * 100 / 255)}%")
        self.config.set("capture", "dim_opacity", val, debounce=True)

    def _on_bg_blur_changed(self, val: int):
        self.lbl_blur_val.setText(f"{val} px")
        self.config.set("appearance", "background_blur", val, debounce=True)
        if self._bg_pil is not None:
            self._bg_blurred_pixmap = theme.blurred_pixmap(self._bg_pil, val)
            self._rebuild_cached_frame()

    def _on_bg_dim_changed(self, val: int):
        self.lbl_bg_dim_val.setText(f"{val}%")
        self.config.set("appearance", "background_dim", val, debounce=True)
        self._rebuild_cached_frame()

    def _on_adaptive_toggled(self, checked: bool):
        self.config.set("appearance", "adaptive_colors", checked)
        self._reload_background_and_theme()

    def _set_manual_accent(self, hex_color: str):
        self.sw_adaptive.setChecked(False)
        self.config.set("appearance", "adaptive_colors", False, save=False)
        self.config.set("appearance", "manual_accent", hex_color)
        self._reload_background_and_theme()

    def _pick_custom_accent(self):
        col = QColorDialog.getColor(QColor(theme.CURRENT.accent), self, tr(self._lang(), "row_accent"))
        if col.isValid():
            self._set_manual_accent(col.name())

    def _on_region_hk_changed(self, combo: str):
        self.config.set("hotkeys", "region_capture", combo)
        self.tile_region.chip.setText(combo)
        self.hotkeys_updated.emit()

    def _on_full_hk_changed(self, combo: str):
        self.config.set("hotkeys", "fullscreen_capture", combo)
        self.tile_full.chip.setText(combo)
        self.hotkeys_updated.emit()

    def _choose_directory(self):
        cur = self.config.get("capture", "save_directory", "")
        folder = QFileDialog.getExistingDirectory(self, tr(self._lang(), "row_folder"), cur)
        if folder:
            self.config.set("capture", "save_directory", folder)
            self._update_dir_label(folder)

    def _save_visible_tools(self):
        selected = [tid for tid, btn in self.tool_chip_buttons.items() if btn.isChecked()]
        self.config.set("toolbar", "visible_tools", selected)

    def paintEvent(self, event):
        if self._cached_frame is not None:
            p = QPainter(self)
            p.drawPixmap(0, 0, self._cached_frame)
            p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            if pos.y() < 60 or pos.x() < self.SIDEBAR_W:
                win_handle = self.windowHandle()
                if win_handle is not None and win_handle.startSystemMove():
                    event.accept()
                    return
                hwnd = int(self.winId())
                user32.ReleaseCapture()
                user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
                event.accept()

    def closeEvent(self, event):
        event.ignore()
        self._minimize_to_tray()
