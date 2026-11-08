import os
import sys
import gc
from pathlib import Path

os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from src.config import ConfigManager
from src.hotkeys import GlobalHotkeyManager
from src.capture import grab_virtual_screen, save_and_copy_pixmap
from src.overlay import SnippingOverlay
from src.main_window import MainSettingsWindow
from src.toast import CaptureToast
from src.icons import get_icon
from src.i18n import tr


def get_app_icon(accent_hex: str = "#2563EB") -> QIcon:
    base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    ico_path = base_dir / "icon.ico"
    if ico_path.exists():
        icon = QIcon(str(ico_path))
        if not icon.isNull():
            return icon
    return create_tray_icon(accent_hex)


def create_tray_icon(accent_hex: str = "#2563EB") -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(accent_hex))
    p.drawRoundedRect(6, 6, 52, 52, 14, 14)

    p.setPen(QColor("#FFFFFF"))
    p.setBrush(Qt.BrushStyle.NoBrush)
    pen = p.pen()
    pen.setWidth(4)
    p.setPen(pen)
    p.drawRoundedRect(18, 18, 28, 28, 5, 5)
    p.end()
    return QIcon(pix)


class SnapLiteController:
    def __init__(self, app: QApplication):
        self.app = app
        self.config = ConfigManager("config.json")
        self.active_overlay: SnippingOverlay | None = None
        self.active_toast: CaptureToast | None = None
        self._tray_notified_once = False

        app_icon = get_app_icon(self.config.get("appearance", "accent_color", "#2563EB"))
        self.app.setWindowIcon(app_icon)

        self.hotkey_manager = GlobalHotkeyManager()
        self.hotkey_manager.region_triggered.connect(self.trigger_region_capture)
        self.hotkey_manager.fullscreen_triggered.connect(self.trigger_fullscreen_capture)
        self.register_hotkeys()

        self.tray = QSystemTrayIcon(
            create_tray_icon(self.config.get("appearance", "accent_color", "#2563EB")),
            self.app,
        )
        self._build_tray_menu()
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self.main_window = MainSettingsWindow(self.config, self.hotkey_manager)
        self.main_window.setWindowIcon(app_icon)
        self.main_window.region_capture_requested.connect(self.trigger_region_capture)
        self.main_window.fullscreen_capture_requested.connect(self.trigger_fullscreen_capture)
        self.main_window.hotkeys_updated.connect(self.register_hotkeys)
        self.main_window.accent_changed.connect(self._on_accent_changed)
        self.main_window.language_changed.connect(self._on_language_changed)
        self.main_window.minimized_to_tray.connect(self._on_minimized_to_tray)

    def _lang(self) -> str:
        return self.config.get("language", default="ua")

    def _on_accent_changed(self, accent_hex: str):
        self.tray.setIcon(create_tray_icon(accent_hex))

    def _on_language_changed(self, _lang_code: str):
        self._build_tray_menu()

    def _on_minimized_to_tray(self):
        if not self._tray_notified_once:
            self._tray_notified_once = True
            L = self._lang()
            self.tray.showMessage(
                tr(L, "tray_bg_title"),
                tr(L, "tray_bg_msg"),
                QSystemTrayIcon.MessageIcon.Information,
                2200,
            )

    def _build_tray_menu(self):
        L = self._lang()
        self.tray.setToolTip(tr(L, "tray_tooltip"))
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1C1D21;
                color: #F2F2F7;
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 5px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 18);
                margin: 4px 6px;
            }
        """)
        act_open = QAction(get_icon("sliders", "#F2F2F7", 16), tr(L, "tray_open"), menu)
        act_open.triggered.connect(self.show_main_window)

        act_region = QAction(get_icon("select", "#F2F2F7", 16), tr(L, "tray_region"), menu)
        act_region.triggered.connect(self.trigger_region_capture)

        act_full = QAction(get_icon("monitor", "#F2F2F7", 16), tr(L, "tray_full"), menu)
        act_full.triggered.connect(self.trigger_fullscreen_capture)

        act_quit = QAction(get_icon("close", "#FF453A", 16), tr(L, "tray_quit"), menu)
        act_quit.triggered.connect(self.quit_app)

        menu.addAction(act_open)
        menu.addSeparator()
        menu.addAction(act_region)
        menu.addAction(act_full)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if self.main_window.isVisible() and not self.main_window.isMinimized():
                self.main_window.hide()
            else:
                self.show_main_window()

    def show_main_window(self):
        self.main_window.setWindowState(
            self.main_window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive
        )
        self.main_window.showNormal()
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def register_hotkeys(self):
        reg_hk = self.config.get("hotkeys", "region_capture", "Ctrl+PrintScreen")
        full_hk = self.config.get("hotkeys", "fullscreen_capture", "PrintScreen")
        self.hotkey_manager.register_all(reg_hk, full_hk)

    def _dismiss_active_toast(self):
        toast = self.active_toast
        self.active_toast = None
        if toast is not None:
            try:
                toast.close()
            except RuntimeError:
                pass

    def _on_toast_destroyed(self, *_args):
        self.active_toast = None

    def trigger_region_capture(self):
        if self.active_overlay is not None:
            try:
                if self.active_overlay.isVisible():
                    return
            except RuntimeError:
                self.active_overlay = None

        self._dismiss_active_toast()

        if self.main_window.isVisible():
            self.main_window.hide()
            QTimer.singleShot(140, self._open_overlay)
        else:
            self._open_overlay()

    def _open_overlay(self):
        pixmap, geom = grab_virtual_screen()
        self.active_overlay = SnippingOverlay(pixmap, geom, self.config)
        self.active_overlay.capture_completed.connect(self._on_capture_completed)
        self.active_overlay.overlay_closed.connect(self._on_overlay_closed)
        self.active_overlay.destroyed.connect(self._on_overlay_closed)
        self.active_overlay.show()
        self.active_overlay.activateWindow()

    def trigger_fullscreen_capture(self):
        if self.active_overlay is not None:
            try:
                if self.active_overlay.isVisible():
                    return
            except RuntimeError:
                self.active_overlay = None

        self._dismiss_active_toast()

        pixmap, _ = grab_virtual_screen()
        res = save_and_copy_pixmap(pixmap, self.config, is_fullscreen=True)
        self._on_capture_completed(pixmap, res)

    def _on_capture_completed(self, pixmap: QPixmap, result: dict):
        self._dismiss_active_toast()
        toast = CaptureToast(pixmap, result, self.config)
        toast.closed.connect(self._on_toast_destroyed)
        toast.destroyed.connect(self._on_toast_destroyed)
        self.active_toast = toast
        toast.show()

    def _on_overlay_closed(self, *_args):
        self.active_overlay = None
        gc.collect()

    def quit_app(self):
        self._dismiss_active_toast()
        self.hotkey_manager.unregister_all()
        self.tray.hide()
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("SnapLite")

    controller = SnapLiteController(app)
    controller.show_main_window()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
