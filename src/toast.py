import os
import subprocess
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QFileDialog,
)
from src.icons import get_icon
from src.capture import save_pixmap_to_disk
from src.i18n import tr


class CaptureToast(QWidget):
    closed = pyqtSignal()

    def __init__(self, pixmap: QPixmap, result: dict, config):
        super().__init__(None)
        self.pixmap = pixmap
        self.result = result
        self.config = config
        self.saved_path = result.get("saved_path")
        lang = config.get("language", default="ua")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setFixedSize(330, 118)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("ToastCard")
        card.setStyleSheet("""
            QFrame#ToastCard {
                background-color: rgba(24, 25, 29, 245);
                border: 1px solid rgba(255, 255, 255, 26);
                border-radius: 12px;
            }
            QLabel {
                background: transparent;
                border: none;
                font-family: "Segoe UI", sans-serif;
            }
            QPushButton.ToastBtn {
                background-color: rgba(255, 255, 255, 16);
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 7px;
                color: #F2F2F7;
                font-size: 12px;
                font-weight: 600;
                min-height: 30px;
                padding: 0 12px;
            }
            QPushButton.ToastBtn:hover {
                background-color: rgba(255, 255, 255, 28);
            }
            QPushButton#CloseBtn {
                background: transparent;
                border: none;
                border-radius: 5px;
                min-width: 22px;
                max-width: 22px;
                min-height: 22px;
                max-height: 22px;
            }
            QPushButton#CloseBtn:hover {
                background-color: rgba(255, 255, 255, 20);
            }
        """)
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(56, 40)
        thumb_lbl.setStyleSheet("""
            background-color: #121316;
            border: 1px solid rgba(255, 255, 255, 25);
            border-radius: 5px;
        """)
        scaled = pixmap.scaled(
            54, 38,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_lbl.setPixmap(scaled)
        top_row.addWidget(thumb_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel(tr(lang, "toast_copied"))
        title.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600;")

        kb_size = result.get("size_kb", max(1, (pixmap.width() * pixmap.height()) // 3200))
        meta = QLabel(f"{pixmap.width()} × {pixmap.height()} px • {kb_size} KB")
        meta.setStyleSheet("color: #8E8E93; font-size: 11px;")

        text_col.addWidget(title)
        text_col.addWidget(meta)
        top_row.addLayout(text_col, 1)

        close_btn = QPushButton()
        close_btn.setObjectName("CloseBtn")
        close_btn.setIcon(get_icon("close", "#8E8E93", 14))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        top_row.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(top_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_open = QPushButton(tr(lang, "toast_open"))
        btn_open.setProperty("class", "ToastBtn")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.clicked.connect(self._on_open)

        btn_save_as = QPushButton(tr(lang, "toast_save_as"))
        btn_save_as.setProperty("class", "ToastBtn")
        btn_save_as.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_as.clicked.connect(self._on_save_as)

        btn_row.addWidget(btn_open)
        btn_row.addWidget(btn_save_as)
        layout.addLayout(btn_row)

        self._position_bottom_right()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(4800)

    def _position_bottom_right(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        x = avail.right() - self.width() - 18
        y = avail.bottom() - self.height() - 18
        self.move(x, y)

    def _on_open(self):
        self.timer.stop()
        if not self.saved_path or not os.path.exists(self.saved_path):
            self.saved_path = save_pixmap_to_disk(self.pixmap, self.config)
        try:
            os.startfile(self.saved_path)
        except Exception:
            subprocess.Popen(["explorer", "/select,", self.saved_path])
        self.close()

    def _on_save_as(self):
        self.timer.stop()
        lang = self.config.get("language", default="ua")
        default_dir = self.config.get("capture", "save_directory", "")
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            tr(lang, "dlg_save_title"),
            os.path.join(default_dir, "Snap.png"),
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)",
        )
        if file_path:
            save_pixmap_to_disk(self.pixmap, self.config, custom_path=file_path)
        self.close()

    def closeEvent(self, event):
        self.timer.stop()
        self.pixmap = None
        self.closed.emit()
        super().closeEvent(event)
