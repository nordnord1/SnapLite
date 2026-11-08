from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QFont,
    QPixmap,
    QKeySequence,
    QShortcut,
    QPainterPath,
    QIcon,
)
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QFrame,
    QColorDialog,
    QFileDialog,
    QInputDialog,
    QToolTip,
)

from src.annotations import AnnotationItem
from src.capture import apply_blur_region, save_and_copy_pixmap, save_pixmap_to_disk
from src.icons import get_icon
from src.i18n import tr


TOOL_DEFINITIONS = [
    ("select", "select", "tool_select"),
    ("rect", "rect", "tool_rect"),
    ("ellipse", "ellipse", "tool_ellipse"),
    ("line", "line", "tool_line"),
    ("arrow", "arrow", "tool_arrow"),
    ("pen", "pen", "tool_pen"),
    ("highlighter", "highlighter", "tool_highlighter"),
    ("text", "text", "tool_text"),
    ("callout", "callout", "tool_callout"),
    ("step", "step", "tool_step"),
    ("blur", "blur", "tool_blur"),
    ("pixelate", "pixelate", "tool_pixelate"),
]

QUICK_COLORS = [
    "#FF3B30", "#FF9500", "#FFCC00", "#34C759",
    "#0A84FF", "#5E5CE6", "#BF5AF2", "#FF2D55",
    "#FFFFFF", "#1C1C1E",
]


class ColorPopover(QFrame):
    color_selected = pyqtSignal(QColor)
    more_colors_requested = pyqtSignal()

    def __init__(self, parent, current_color: QColor, lang: str = "ua"):
        super().__init__(parent)
        self.setObjectName("ColorPopover")
        self.setStyleSheet("""
            QFrame#ColorPopover {
                background-color: rgba(24, 25, 29, 248);
                border: 1px solid rgba(255, 255, 255, 42);
                border-radius: 10px;
            }
            QPushButton#MoreColorsBtn {
                background-color: rgba(255, 255, 255, 16);
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 6px;
                color: #F2F2F7;
                font-size: 11px;
                font-weight: 600;
                min-height: 26px;
                padding: 0 10px;
            }
            QPushButton#MoreColorsBtn:hover {
                background-color: rgba(255, 255, 255, 28);
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(6)
        for idx, hex_col in enumerate(QUICK_COLORS):
            swatch = QPushButton()
            swatch.setFixedSize(24, 24)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            is_cur = current_color.name().lower() == hex_col.lower()
            border = "2px solid #FFFFFF" if is_cur else "1px solid rgba(255,255,255,70)"
            swatch.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_col};
                    border: {border};
                    border-radius: 6px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    border: 2px solid #FFFFFF;
                }}
            """)
            swatch.clicked.connect(lambda checked=False, c=hex_col: self._choose(QColor(c)))
            grid.addWidget(swatch, idx // 5, idx % 5)

        lay.addLayout(grid)

        more_btn = QPushButton(tr(lang, "more_colors"))
        more_btn.setObjectName("MoreColorsBtn")
        more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        more_btn.clicked.connect(self.more_colors_requested.emit)
        lay.addWidget(more_btn)

        self.adjustSize()
        self.hide()

    def _choose(self, col: QColor):
        self.hide()
        self.color_selected.emit(col)


class FloatingSnipToolbar(QFrame):
    tool_selected = pyqtSignal(str)
    color_changed = pyqtSignal(QColor)
    color_button_clicked = pyqtSignal()
    undo_requested = pyqtSignal()
    save_requested = pyqtSignal()
    copy_requested = pyqtSignal()
    close_requested = pyqtSignal()
    magnifier_toggled = pyqtSignal(bool)

    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        lang = config.get("language", default="ua")
        self.current_tool = "select"
        self.current_color = QColor(config.get("toolbar", "default_color", "#FF3B30"))
        self.tool_buttons: dict[str, QPushButton] = {}

        self.setObjectName("FloatingToolbar")
        self.setStyleSheet("""
            QFrame#FloatingToolbar {
                background-color: rgba(24, 25, 29, 242);
                border: 1px solid rgba(255, 255, 255, 34);
                border-radius: 10px;
            }
            QPushButton.IconBtn {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 7px;
                min-width: 34px;
                max-width: 34px;
                min-height: 34px;
                max-height: 34px;
                padding: 0px;
            }
            QPushButton.IconBtn:hover {
                background-color: rgba(255, 255, 255, 22);
            }
            QPushButton.IconBtn[active="true"] {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 170);
            }
            QPushButton#PrimaryCopyBtn {
                background-color: #2563EB;
                border: 1px solid #3B82F6;
                border-radius: 7px;
                min-width: 34px;
                max-width: 34px;
                min-height: 34px;
                max-height: 34px;
                padding: 0px;
            }
            QPushButton#PrimaryCopyBtn:hover {
                background-color: #1D4ED8;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(4)

        grip = QPushButton()
        grip.setIcon(get_icon("grip", "#8E8E93", 18))
        grip.setIconSize(QSize(18, 18))
        grip.setFlat(True)
        grip.setFixedSize(20, 34)
        grip.setStyleSheet("background: transparent; border: none;")
        grip.setCursor(Qt.CursorShape.SizeAllCursor)
        grip.setToolTip(tr(lang, "drag_toolbar"))
        layout.addWidget(grip)

        visible_tools = set(config.get("toolbar", "visible_tools", [t[0] for t in TOOL_DEFINITIONS]))

        for tool_id, icon_name, tr_key in TOOL_DEFINITIONS:
            if tool_id not in visible_tools and tool_id != "select":
                continue
            btn = QPushButton()
            btn.setProperty("class", "IconBtn")
            btn.setProperty("active", "true" if tool_id == "select" else "false")
            btn.setIcon(get_icon(icon_name, "#F2F2F7", 18))
            btn.setIconSize(QSize(18, 18))
            btn.setToolTip(tr(lang, tr_key))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, tid=tool_id: self.select_tool(tid))
            layout.addWidget(btn)
            self.tool_buttons[tool_id] = btn

        layout.addWidget(self._vsep())

        self.color_btn = QPushButton()
        self.color_btn.setProperty("class", "IconBtn")
        self.color_btn.setToolTip(tr(lang, "color_tooltip"))
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_color_swatch()
        self.color_btn.clicked.connect(self.color_button_clicked.emit)
        layout.addWidget(self.color_btn)

        self.mag_btn = QPushButton()
        self.mag_btn.setProperty("class", "IconBtn")
        self.mag_btn.setIcon(get_icon("magnifier", "#F2F2F7", 18))
        self.mag_btn.setIconSize(QSize(18, 18))
        self.mag_btn.setProperty("active", "true" if config.get("capture", "show_magnifier", True) else "false")
        self.mag_btn.setToolTip(tr(lang, "mag_tooltip"))
        self.mag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mag_btn.clicked.connect(self._toggle_magnifier)
        layout.addWidget(self.mag_btn)

        undo_btn = QPushButton()
        undo_btn.setProperty("class", "IconBtn")
        undo_btn.setIcon(get_icon("undo", "#F2F2F7", 18))
        undo_btn.setIconSize(QSize(18, 18))
        undo_btn.setToolTip(tr(lang, "undo_tooltip"))
        undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        undo_btn.clicked.connect(self.undo_requested.emit)
        layout.addWidget(undo_btn)

        layout.addWidget(self._vsep())

        copy_btn = QPushButton()
        copy_btn.setObjectName("PrimaryCopyBtn")
        copy_btn.setIcon(get_icon("copy", "#FFFFFF", 18))
        copy_btn.setIconSize(QSize(18, 18))
        copy_btn.setToolTip(tr(lang, "copy_tooltip"))
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self.copy_requested.emit)
        layout.addWidget(copy_btn)

        save_btn = QPushButton()
        save_btn.setProperty("class", "IconBtn")
        save_btn.setIcon(get_icon("save", "#F2F2F7", 18))
        save_btn.setIconSize(QSize(18, 18))
        save_btn.setToolTip(tr(lang, "save_tooltip"))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_requested.emit)
        layout.addWidget(save_btn)

        layout.addWidget(self._vsep())

        close_btn = QPushButton()
        close_btn.setProperty("class", "IconBtn")
        close_btn.setIcon(get_icon("close", "#F2F2F7", 18))
        close_btn.setIconSize(QSize(18, 18))
        close_btn.setToolTip(tr(lang, "close_tooltip"))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_requested.emit)
        layout.addWidget(close_btn)

        self.adjustSize()
        self._drag_offset = None

    def _vsep(self) -> QFrame:
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(22)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 28); border: none;")
        return sep

    def set_color(self, col: QColor):
        self.current_color = col
        self.config.set("toolbar", "default_color", col.name())
        self._update_color_swatch()
        self.color_changed.emit(col)

    def _update_color_swatch(self):
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor(255, 255, 255, 210), 2))
        p.setBrush(self.current_color)
        p.drawRoundedRect(6, 6, 20, 20, 5, 5)
        p.end()
        pix.setDevicePixelRatio(2)
        self.color_btn.setIcon(QIcon(pix))
        self.color_btn.setIconSize(QSize(16, 16))

    def _toggle_magnifier(self):
        is_active = self.mag_btn.property("active") == "true"
        new_state = not is_active
        self.mag_btn.setProperty("active", "true" if new_state else "false")
        self.mag_btn.style().unpolish(self.mag_btn)
        self.mag_btn.style().polish(self.mag_btn)
        self.magnifier_toggled.emit(new_state)

    def select_tool(self, tool_id: str):
        self.current_tool = tool_id
        for tid, btn in self.tool_buttons.items():
            btn.setProperty("active", "true" if tid == tool_id else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.tool_selected.emit(tool_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None


class SnippingOverlay(QWidget):
    capture_completed = pyqtSignal(QPixmap, dict)
    overlay_closed = pyqtSignal()

    def __init__(self, screen_pixmap: QPixmap, geometry: QRect, config):
        super().__init__(None)
        self.screen_pixmap = screen_pixmap
        self.config = config
        self.lang = config.get("language", default="ua")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(geometry)

        self.selection_rect = QRect()
        self.is_selecting = False
        self.select_start = QPoint()

        self.current_tool = "select"
        self.current_color = QColor(config.get("toolbar", "default_color", "#FF3B30"))
        self.stroke_width = int(config.get("toolbar", "stroke_width", 3))
        self.blur_intensity = int(config.get("toolbar", "blur_intensity", 15))
        self.annotations: list[AnnotationItem] = []
        self.active_annotation: AnnotationItem | None = None
        self.step_counter = 1

        self.cursor_pos = QPoint(geometry.width() // 2, geometry.height() // 2)
        self.show_magnifier = bool(config.get("capture", "show_magnifier", True))

        self.toolbar = FloatingSnipToolbar(self, config)
        self._position_toolbar_top()

        self.color_popover = ColorPopover(self, self.current_color, self.lang)
        self.color_popover.color_selected.connect(self.toolbar.set_color)
        self.color_popover.more_colors_requested.connect(self._open_full_color_dialog)

        self.toolbar.tool_selected.connect(self._on_tool_selected)
        self.toolbar.color_changed.connect(self._on_color_changed)
        self.toolbar.color_button_clicked.connect(self._toggle_color_popover)
        self.toolbar.undo_requested.connect(self.undo_last)
        self.toolbar.save_requested.connect(self.save_to_file_dialog)
        self.toolbar.copy_requested.connect(self.finish_and_copy)
        self.toolbar.close_requested.connect(self.close)
        self.toolbar.magnifier_toggled.connect(self._on_magnifier_toggled)

        QShortcut(QKeySequence("Escape"), self, activated=self.close)
        QShortcut(QKeySequence("Return"), self, activated=self.finish_and_copy)
        QShortcut(QKeySequence("Enter"), self, activated=self.finish_and_copy)
        QShortcut(QKeySequence("Ctrl+C"), self, activated=self.finish_and_copy)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_to_file_dialog)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo_last)
        QShortcut(QKeySequence("Z"), self, activated=lambda: self.toolbar._toggle_magnifier())

    def _toggle_color_popover(self):
        if self.color_popover.isVisible():
            self.color_popover.hide()
            return
        btn_global = self.toolbar.color_btn.mapTo(self, QPoint(0, self.toolbar.color_btn.height() + 8))
        px = max(10, min(btn_global.x() - 40, self.width() - self.color_popover.width() - 10))
        py = btn_global.y()
        if py + self.color_popover.height() > self.height() - 10:
            py = self.toolbar.y() - self.color_popover.height() - 8
        self.color_popover.move(px, py)
        self.color_popover.raise_()
        self.color_popover.show()

    def _open_full_color_dialog(self):
        self.color_popover.hide()
        dlg = QColorDialog(self.current_color, self)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        if dlg.exec():
            col = dlg.selectedColor()
            if col.isValid():
                self.toolbar.set_color(col)

    def _ask_text_topmost(self, title: str, label: str) -> tuple[str, bool]:
        dlg = QInputDialog(self)
        dlg.setWindowTitle(title)
        dlg.setLabelText(label)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        dlg.setStyleSheet("""
            QInputDialog { background-color: #1C1D21; color: #F2F2F7; }
            QLabel { color: #F2F2F7; font-size: 13px; }
            QLineEdit {
                background-color: #26272B; color: #FFFFFF;
                border: 1px solid rgba(255,255,255,40); border-radius: 6px; padding: 6px;
            }
            QPushButton {
                background-color: #2563EB; color: #FFFFFF; border-radius: 6px;
                padding: 6px 14px; font-weight: 600;
            }
        """)
        ok = bool(dlg.exec())
        return dlg.textValue(), ok

    def _position_toolbar_top(self):
        primary = self.screen()
        avail = primary.geometry() if primary else self.rect()
        local_x = avail.x() - self.geometry().x() + (avail.width() - self.toolbar.width()) // 2
        local_y = avail.y() - self.geometry().y() + 12
        self.toolbar.move(max(10, local_x), max(10, local_y))

    def _on_tool_selected(self, tool_id: str):
        self.color_popover.hide()
        self.current_tool = tool_id
        if tool_id != "select" and self.selection_rect.isNull():
            self.selection_rect = QRect(0, 0, self.width(), self.height())
        self.update()

    def _on_color_changed(self, color: QColor):
        self.current_color = color

    def _on_magnifier_toggled(self, visible: bool):
        self.show_magnifier = visible
        self.update()

    def undo_last(self):
        if self.annotations:
            popped = self.annotations.pop()
            if popped.tool == "step":
                self.step_counter = max(1, self.step_counter - 1)
            self.update()
        elif not self.selection_rect.isNull():
            self.selection_rect = QRect()
            self.toolbar.select_tool("select")
            self._position_toolbar_top()
            self.update()

    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        if self.current_tool in ("blur", "pixelate"):
            self.blur_intensity = max(4, min(45, self.blur_intensity + delta * 2))
            QToolTip.showText(event.globalPosition().toPoint(), f"Blur: {self.blur_intensity}px", self)
        else:
            self.stroke_width = max(1, min(20, self.stroke_width + delta))
            QToolTip.showText(event.globalPosition().toPoint(), f"Size: {self.stroke_width}px", self)
        self.update()

    def mousePressEvent(self, event):
        if self.color_popover.isVisible():
            self.color_popover.hide()

        if event.button() == Qt.MouseButton.RightButton:
            if not self.selection_rect.isNull():
                self.selection_rect = QRect()
                self.annotations.clear()
                self.toolbar.select_tool("select")
                self._position_toolbar_top()
                self.update()
            else:
                self.close()
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position().toPoint()
        pos_f = event.position()

        if self.current_tool == "select":
            self.is_selecting = True
            self.select_start = pos
            self.selection_rect = QRect(pos, pos)
            self.update()
            return

        if self.current_tool == "text":
            text, ok = self._ask_text_topmost(tr(self.lang, "dlg_text_title"), tr(self.lang, "dlg_text_label"))
            if ok and text.strip():
                item = AnnotationItem(
                    tool="text",
                    color=self.current_color,
                    stroke_width=self.stroke_width,
                    start_pos=pos_f,
                    end_pos=pos_f,
                    text=text.strip(),
                )
                self.annotations.append(item)
                self.update()
            return

        if self.current_tool == "step":
            item = AnnotationItem(
                tool="step",
                color=self.current_color,
                stroke_width=self.stroke_width,
                start_pos=pos_f,
                end_pos=pos_f,
                step_number=self.step_counter,
            )
            self.step_counter += 1
            self.annotations.append(item)
            self.update()
            return

        self.active_annotation = AnnotationItem(
            tool=self.current_tool,
            color=self.current_color,
            stroke_width=self.stroke_width,
            start_pos=pos_f,
            end_pos=pos_f,
            points=[pos_f],
        )
        self.update()

    def mouseMoveEvent(self, event):
        self.cursor_pos = event.position().toPoint()
        pos_f = event.position()

        if self.is_selecting:
            self.selection_rect = QRect(self.select_start, self.cursor_pos).normalized()
            if self.config.get("toolbar", "position", "top") == "selection":
                self._dock_toolbar_below_selection()
        elif self.active_annotation is not None:
            self.active_annotation.end_pos = pos_f
            if self.active_annotation.tool in ("pen", "highlighter"):
                self.active_annotation.points.append(pos_f)
            elif self.active_annotation.tool in ("blur", "pixelate"):
                rect = self.active_annotation.bounding_rect().toRect()
                if rect.width() > 4 and rect.height() > 4:
                    self.active_annotation.cached_pixmap = apply_blur_region(
                        self.screen_pixmap,
                        rect,
                        intensity=self.blur_intensity,
                        pixelate=(self.active_annotation.tool == "pixelate"),
                    )

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self.is_selecting:
            self.is_selecting = False
            self.selection_rect = QRect(self.select_start, event.position().toPoint()).normalized()
            if self.selection_rect.width() < 5 or self.selection_rect.height() < 5:
                self.selection_rect = QRect()
            elif self.config.get("toolbar", "position", "top") == "selection":
                self._dock_toolbar_below_selection()
        elif self.active_annotation is not None:
            if self.active_annotation.tool == "callout":
                text, ok = self._ask_text_topmost(tr(self.lang, "dlg_callout_title"), tr(self.lang, "dlg_callout_label"))
                if ok and text.strip():
                    self.active_annotation.text = text.strip()
                    self.annotations.append(self.active_annotation)
            else:
                self.annotations.append(self.active_annotation)
            self.active_annotation = None

        self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.finish_and_copy()

    def _dock_toolbar_below_selection(self):
        if self.selection_rect.isNull():
            return
        cx = self.selection_rect.center().x() - self.toolbar.width() // 2
        x = max(12, min(cx, self.width() - self.toolbar.width() - 12))
        y = self.selection_rect.bottom() + 14
        if y + self.toolbar.height() > self.height() - 12:
            y = max(12, self.selection_rect.top() - self.toolbar.height() - 14)
        self.toolbar.move(x, y)

    def render_final_pixmap(self) -> QPixmap:
        canvas = self.screen_pixmap.copy()
        painter = QPainter(canvas)
        for item in self.annotations:
            item.draw(painter)
        painter.end()

        target_rect = self.selection_rect
        if target_rect.isNull() or target_rect.width() < 4 or target_rect.height() < 4:
            target_rect = QRect(0, 0, canvas.width(), canvas.height())

        return canvas.copy(target_rect)

    def finish_and_copy(self):
        final_pix = self.render_final_pixmap()
        res = save_and_copy_pixmap(final_pix, self.config, is_fullscreen=False)
        self.capture_completed.emit(final_pix, res)
        self.close()

    def save_to_file_dialog(self):
        final_pix = self.render_final_pixmap()
        default_dir = self.config.get("capture", "save_directory", "")
        self.hide()
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            tr(self.lang, "dlg_save_title"),
            f"{default_dir}/Snap.png",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)",
        )
        if file_path:
            saved = save_pixmap_to_disk(final_pix, self.config, custom_path=file_path)
            res = save_and_copy_pixmap(final_pix, self.config, is_fullscreen=False)
            res["saved_path"] = saved
            self.capture_completed.emit(final_pix, res)
        self.close()

    def closeEvent(self, event):
        self.annotations.clear()
        self.overlay_closed.emit()
        super().closeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.drawPixmap(0, 0, self.screen_pixmap)

        dim_alpha = int(self.config.get("capture", "dim_opacity", 110))
        if not self.selection_rect.isNull():
            path = QPainterPath()
            path.addRect(QRectF(self.rect()))
            path.addRect(QRectF(self.selection_rect))
            painter.fillPath(path, QColor(0, 0, 0, dim_alpha))

        for item in self.annotations:
            item.draw(painter)
        if self.active_annotation is not None:
            self.active_annotation.draw(painter)

        if not self.selection_rect.isNull():
            self._draw_selection_frame(painter, self.selection_rect)
            self._draw_handles(painter, self.selection_rect)
            self._draw_dimension_badge(painter, self.selection_rect)

        if (
            self.show_magnifier
            and not self.toolbar.geometry().contains(self.cursor_pos)
            and not (self.color_popover.isVisible() and self.color_popover.geometry().contains(self.cursor_pos))
        ):
            self._draw_reference_magnifier(painter, self.cursor_pos)

    def _draw_selection_frame(self, painter: QPainter, rect: QRect):
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 140), 2.5))
        painter.drawRect(rect)
        painter.setPen(QPen(QColor(255, 255, 255, 245), 1.5))
        painter.drawRect(rect)

    def _draw_handles(self, painter: QPainter, rect: QRect):
        pts = [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomLeft(),
            rect.bottomRight(),
            QPoint(rect.center().x(), rect.top()),
            QPoint(rect.center().x(), rect.bottom()),
            QPoint(rect.left(), rect.center().y()),
            QPoint(rect.right(), rect.center().y()),
        ]
        painter.setPen(QPen(QColor(24, 25, 29, 220), 1.2))
        painter.setBrush(QColor(255, 255, 255))
        for p in pts:
            painter.drawRect(QRect(p.x() - 4, p.y() - 4, 8, 8))

    def _draw_dimension_badge(self, painter: QPainter, rect: QRect):
        text = f"{rect.width()} × {rect.height()}"
        font = QFont("Consolas", 9, QFont.Weight.DemiBold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        bw = fm.horizontalAdvance(text) + 20
        bh = fm.height() + 10

        bx = rect.left()
        by = rect.bottom() + 12
        if by + bh > self.height() - 10:
            by = max(8, rect.top() - bh - 10)

        badge_rect = QRectF(bx, by, bw, bh)
        painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
        painter.setBrush(QColor(24, 25, 29, 232))
        painter.drawRoundedRect(badge_rect, 6, 6)

        painter.setPen(QColor("#E5E5EA"))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_reference_magnifier(self, painter: QPainter, pos: QPoint):
        grid_count = 15
        cell_size = 8
        diameter = grid_count * cell_size

        loupe_x = pos.x() + 26
        loupe_y = pos.y() + 26
        if loupe_x + diameter + 20 > self.width():
            loupe_x = pos.x() - diameter - 26
        if loupe_y + diameter + 48 > self.height():
            loupe_y = pos.y() - diameter - 48

        loupe_rect = QRectF(loupe_x, loupe_y, diameter, diameter)

        painter.save()
        clip_path = QPainterPath()
        clip_path.addEllipse(loupe_rect)
        painter.setClipPath(clip_path)

        half = grid_count // 2
        src_rect = QRect(pos.x() - half, pos.y() - half, grid_count, grid_count)
        painter.fillRect(loupe_rect, QColor(24, 25, 29))

        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(loupe_rect.toRect(), self.screen_pixmap, src_rect)

        grid_pen = QPen(QColor(0, 0, 0, 65), 1)
        painter.setPen(grid_pen)
        for i in range(1, grid_count):
            gx = loupe_x + i * cell_size
            gy = loupe_y + i * cell_size
            painter.drawLine(QPointF(gx, loupe_y), QPointF(gx, loupe_y + diameter))
            painter.drawLine(QPointF(loupe_x, gy), QPointF(loupe_x + diameter, gy))

        center_offset = half * cell_size
        cross_color = QColor(255, 255, 255, 28)
        painter.fillRect(QRectF(loupe_x + center_offset, loupe_y, cell_size, diameter), cross_color)
        painter.fillRect(QRectF(loupe_x, loupe_y + center_offset, diameter, cell_size), cross_color)

        center_box = QRectF(loupe_x + center_offset, loupe_y + center_offset, cell_size, cell_size)
        painter.setPen(QPen(QColor(0, 0, 0, 220), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(center_box)
        painter.setPen(QPen(QColor(255, 255, 255, 240), 1))
        painter.drawRect(center_box)
        painter.restore()

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 190), 3))
        painter.drawEllipse(loupe_rect)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
        painter.drawEllipse(loupe_rect)

        coord_text = f"X: {pos.x()} Y: {pos.y()}"
        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        pw = fm.horizontalAdvance(coord_text) + 18
        ph = fm.height() + 8
        px = loupe_x + (diameter - pw) / 2.0
        py = loupe_y + diameter + 8

        pill_rect = QRectF(px, py, pw, ph)
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.setBrush(QColor(24, 25, 28, 232))
        painter.drawRoundedRect(pill_rect, 5, 5)

        painter.setPen(QColor("#F2F2F7"))
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, coord_text)
        painter.restore()
