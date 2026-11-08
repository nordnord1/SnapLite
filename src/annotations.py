import math
from dataclasses import dataclass, field
from typing import List, Optional
from PyQt6.QtCore import QPointF, QRectF, QRect, Qt
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
    QPainterPath,
    QFont,
    QPixmap,
    QPolygonF,
)


@dataclass
class AnnotationItem:
    tool: str
    color: QColor
    stroke_width: int = 3
    start_pos: QPointF = field(default_factory=QPointF)
    end_pos: QPointF = field(default_factory=QPointF)
    points: List[QPointF] = field(default_factory=list)
    text: str = ""
    step_number: int = 1
    cached_pixmap: Optional[QPixmap] = None
    cached_rect: Optional[QRect] = None

    def bounding_rect(self) -> QRectF:
        if self.tool in ("pen", "highlighter") and self.points:
            xs = [p.x() for p in self.points]
            ys = [p.y() for p in self.points]
            return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)).normalized()
        return QRectF(self.start_pos, self.end_pos).normalized()

    def draw(self, painter: QPainter):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self.tool in ("blur", "pixelate"):
            rect = self.bounding_rect().toRect()
            if self.cached_pixmap and not self.cached_pixmap.isNull():
                painter.drawPixmap(rect, self.cached_pixmap)
            pen = QPen(QColor(255, 255, 255, 90), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            painter.restore()
            return

        if self.tool == "highlighter":
            hl_color = QColor(self.color)
            hl_color.setAlpha(95)
            pen = QPen(
                hl_color,
                max(14, self.stroke_width * 5),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(pen)
            if len(self.points) > 1:
                path = QPainterPath(self.points[0])
                for pt in self.points[1:]:
                    path.lineTo(pt)
                painter.drawPath(path)
            painter.restore()
            return

        pen = QPen(
            self.color,
            self.stroke_width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.tool == "rect":
            painter.drawRect(self.bounding_rect())

        elif self.tool == "ellipse":
            painter.drawEllipse(self.bounding_rect())

        elif self.tool == "line":
            painter.drawLine(self.start_pos, self.end_pos)

        elif self.tool == "arrow":
            self._draw_arrow(painter, self.start_pos, self.end_pos)

        elif self.tool == "pen":
            if len(self.points) > 1:
                path = QPainterPath(self.points[0])
                for pt in self.points[1:]:
                    path.lineTo(pt)
                painter.drawPath(path)

        elif self.tool == "text":
            if self.text:
                font = QFont("Segoe UI", max(11, self.stroke_width * 4 + 4), QFont.Weight.DemiBold)
                painter.setFont(font)
                metrics = painter.fontMetrics()
                lines = self.text.split("\n")
                w = max(metrics.horizontalAdvance(line) for line in lines) + 16
                h = metrics.height() * len(lines) + 12
                bg_rect = QRectF(self.start_pos.x(), self.start_pos.y(), w, h)

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(20, 20, 24, 185))
                painter.drawRoundedRect(bg_rect, 6, 6)

                painter.setPen(self.color)
                painter.drawText(bg_rect.adjusted(8, 6, -8, -6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text)

        elif self.tool == "callout":
            label = self.text if self.text else "Коментар"
            font = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            lines = label.split("\n")
            w = max(metrics.horizontalAdvance(line) for line in lines) + 22
            h = metrics.height() * len(lines) + 16

            box_rect = QRectF(self.end_pos.x(), self.end_pos.y(), w, h)
            painter.setPen(QPen(self.color, 2))
            painter.setBrush(QColor(24, 24, 28, 235))

            center = box_rect.center()
            painter.drawLine(self.start_pos, center)
            painter.drawRoundedRect(box_rect, 8, 8)

            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(box_rect, Qt.AlignmentFlag.AlignCenter, label)

        elif self.tool == "step":
            radius = max(13, self.stroke_width * 3 + 5)
            center = self.start_pos
            circle_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

            painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
            painter.setBrush(QBrush(self.color))
            painter.drawEllipse(circle_rect)

            font = QFont("Segoe UI", int(radius * 0.78), QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, str(self.step_number))

        painter.restore()

    def _draw_arrow(self, painter: QPainter, p1: QPointF, p2: QPointF):
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length < 4:
            return

        angle = math.atan2(dy, dx)
        head_len = max(12, self.stroke_width * 4.2)
        head_angle = math.radians(28)

        shaft_end = QPointF(
            p2.x() - (head_len * 0.65) * math.cos(angle),
            p2.y() - (head_len * 0.65) * math.sin(angle),
        )
        painter.drawLine(p1, shaft_end)

        arrow_p1 = QPointF(
            p2.x() - head_len * math.cos(angle - head_angle),
            p2.y() - head_len * math.sin(angle - head_angle),
        )
        arrow_p2 = QPointF(
            p2.x() - head_len * math.cos(angle + head_angle),
            p2.y() - head_len * math.sin(angle + head_angle),
        )

        poly = QPolygonF([p2, arrow_p1, arrow_p2])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.color))
        painter.drawPolygon(poly)
