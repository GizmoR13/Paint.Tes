from __future__ import annotations

from PIL import Image, ImageDraw, ImageQt
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from .document import Document
from .imageops import selection_mask


def pixmap(image):
    return QPixmap.fromImage(ImageQt.ImageQt(image).copy())


class Canvas(QGraphicsView):
    changed = Signal()
    tool_requested = Signal(str)
    position_changed = Signal(str)

    def __init__(self, document: Document):
        super().__init__()
        self.document = document
        self.tool = "hand"
        self.color = (90, 55, 30, 255)
        self.brush_size = 16
        self._start = None
        self._points = []
        self._polygon = []
        self._stroke_base = None
        self._last = None
        self._zoom = 1.0
        scene = QGraphicsScene(self)
        self.setScene(scene)
        tile = QPixmap(24, 24)
        tile.fill(QColor("#c9bba9"))
        painter = QPainter(tile)
        painter.fillRect(0, 0, 12, 12, QColor("#e7ddcf"))
        painter.fillRect(12, 12, 12, 12, QColor("#e7ddcf"))
        painter.end()
        scene.setBackgroundBrush(QBrush(tile))
        self.item = QGraphicsPixmapItem()
        scene.addItem(self.item)
        self.mask_item = QGraphicsPixmapItem()
        self.mask_item.setZValue(1)
        scene.addItem(self.mask_item)
        self.outline = QGraphicsPathItem()
        pen = QPen(QColor("#f1bd72"), 1.5, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self.outline.setPen(pen)
        self.outline.setZValue(2)
        scene.addItem(self.outline)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setTool("hand")
        self.refresh()

    def refresh(self):
        self.item.setPixmap(pixmap(self.document.image))
        self.scene().setSceneRect(0, 0, self.document.image.width, self.document.image.height)
        self.show_mask()
        self.changed.emit()

    def show_mask(self):
        if self.document.mask and self.document.mask.getbbox():
            overlay = Image.new("RGBA", self.document.image.size, (215, 144, 55, 0))
            overlay.putalpha(self.document.mask.point(lambda a: a * 70 // 255))
            self.mask_item.setPixmap(pixmap(overlay))
        else:
            self.mask_item.setPixmap(QPixmap())

    def fit(self):
        self.fitInView(self.item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()

    def actual_size(self):
        self.resetTransform()
        self._zoom = 1.0

    def setTool(self, tool):
        self.tool = tool
        self._polygon.clear()
        self.outline.setPath(QPainterPath())
        self.setDragMode(
            QGraphicsView.DragMode.ScrollHandDrag
            if tool == "hand"
            else QGraphicsView.DragMode.NoDrag
        )
        self.setCursor(
            Qt.CursorShape.OpenHandCursor if tool == "hand" else Qt.CursorShape.CrossCursor
        )

    def point(self, event):
        pos = self.mapToScene(event.position().toPoint())
        return (
            max(0, min(self.document.image.width - 1, int(pos.x()))),
            max(0, min(self.document.image.height - 1, int(pos.y()))),
        )

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            target = self.transform().m11() * factor
            if 0.025 <= target <= 32:
                self.scale(factor, factor)
                self._zoom = target
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if self.tool == "hand" or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        point = self.point(event)
        if self.tool == "polygon":
            self._polygon.append(point)
            path = QPainterPath(QPointF(*self._polygon[0]))
            for p in self._polygon[1:]:
                path.lineTo(*p)
            self.outline.setPath(path)
            return
        self._start = point
        self._points = [point]
        self._last = point
        if self.tool in ("brush", "eraser"):
            self._stroke_base = self.document.image.copy()
            self.paint_segment(point, point)

    def paint_segment(self, start, end):
        color = self.color if self.tool == "brush" else (0, 0, 0, 0)
        result = self.document.image.copy()
        draw = ImageDraw.Draw(result)
        draw.line([start, end], fill=color, width=self.brush_size)
        radius = self.brush_size / 2
        for x, y in (start, end):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        if self.document.mask and self.document.mask.getbbox():
            result = Image.composite(result, self.document.image, self.document.mask)
        self.document.image = result
        self.item.setPixmap(pixmap(result))

    def mouseMoveEvent(self, event):
        point = self.point(event)
        self.position_changed.emit(
            f"{point[0]}, {point[1]} px  ·  {self.transform().m11() * 100:.0f}%"
        )
        if self._start is None:
            return super().mouseMoveEvent(event)
        if self.tool in ("brush", "eraser"):
            self.paint_segment(self._last, point)
            self._last = point
            return
        path = QPainterPath()
        if self.tool == "lasso":
            self._points.append(point)
            path.moveTo(*self._points[0])
            for p in self._points[1:]:
                path.lineTo(*p)
        else:
            x0, y0 = self._start
            x1, y1 = point
            if self.tool == "ellipse":
                path.addEllipse(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            else:
                path.addRect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        self.outline.setPath(path)

    def mouseReleaseEvent(self, event):
        if self._start is None or event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        point = self.point(event)
        if self.tool in ("brush", "eraser"):
            final = self.document.image
            self.document.image = self._stroke_base
            self.document.apply(final)
            self._stroke_base = None
        elif self.tool == "lasso":
            self.document.mask = selection_mask(self.document.image.size, points=self._points)
        elif self.tool == "ellipse":
            mask = Image.new("L", self.document.image.size, 0)
            draw = ImageDraw.Draw(mask)
            x0, y0 = self._start
            x1, y1 = point
            draw.ellipse((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), fill=255)
            self.document.mask = mask
        else:
            self.document.mask = selection_mask(
                self.document.image.size, rectangle=(*self._start, *point)
            )
        self._start = None
        self.outline.setPath(QPainterPath())
        self.refresh()

    def keyPressEvent(self, event):
        tools = {
            Qt.Key.Key_H: "hand",
            Qt.Key.Key_S: "rectangle",
            Qt.Key.Key_E: "ellipse",
            Qt.Key.Key_L: "lasso",
            Qt.Key.Key_P: "polygon",
            Qt.Key.Key_B: "brush",
            Qt.Key.Key_R: "eraser",
        }
        if event.modifiers() == Qt.KeyboardModifier.NoModifier and event.key() in tools:
            self.tool_requested.emit(tools[event.key()])
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self._polygon.clear()
            self._start = None
            self.outline.setPath(QPainterPath())
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.tool == "polygon" and len(self._polygon) >= 3:
            self.document.mask = selection_mask(self.document.image.size, points=self._polygon)
            self._polygon.clear()
            self.outline.setPath(QPainterPath())
            self.refresh()
        else:
            super().mouseDoubleClickEvent(event)
