from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget


class WindowResizer(QObject):
    """无边框窗口 8 方向边缘调整大小。
    install() 后向 QApplication 注册全局事件过滤器。"""

    def __init__(self, window: QMainWindow, margin: int = 6):
        super().__init__(window)
        self.window = window
        self.margin = margin
        self._resize_edges = Qt.Edge(0)
        self._resize_start_global = QPoint()
        self._resize_start_geom: QRect | None = None
        self._override_cursor_active = False

    def install(self) -> None:
        self._enable_mouse_tracking_recursive(self.window)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def uninstall(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

    def refresh_mouse_tracking(self) -> None:
        """Re-enable mouse tracking on any newly created child widgets."""
        self._enable_mouse_tracking_recursive(self.window)

    def _enable_mouse_tracking_recursive(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        for child in widget.findChildren(QWidget):
            child.setMouseTracking(True)

    def eventFilter(self, obj, event):
        if not isinstance(obj, QWidget) or obj.window() is not self.window:
            return super().eventFilter(obj, event)
        etype = event.type()

        if etype == QEvent.Type.MouseMove:
            if self._resize_edges:
                self._perform_resize(event.globalPosition().toPoint())
                return True
            if not self.window.isMaximized() and not self.window.isFullScreen():
                self._apply_hover_cursor(self._edges_at(event.globalPosition().toPoint()))
            else:
                self._clear_override_cursor()
        elif etype == QEvent.Type.MouseButtonPress:
            if (
                event.button() == Qt.MouseButton.LeftButton
                and not self.window.isMaximized()
                and not self.window.isFullScreen()
            ):
                edges = self._edges_at(event.globalPosition().toPoint())
                if edges:
                    self._resize_edges = edges
                    self._resize_start_global = event.globalPosition().toPoint()
                    self._resize_start_geom = QRect(self.window.geometry())
                    return True
        elif etype == QEvent.Type.MouseButtonRelease:
            if self._resize_edges and event.button() == Qt.MouseButton.LeftButton:
                self._resize_edges = Qt.Edge(0)
                self._resize_start_geom = None
                self._clear_override_cursor()
                return True
        elif etype == QEvent.Type.Leave and not self._resize_edges:
            self._clear_override_cursor()

        return super().eventFilter(obj, event)

    def _edges_at(self, global_pos: QPoint) -> Qt.Edge:
        local = self.window.mapFromGlobal(global_pos)
        rect = self.window.rect()
        if not rect.contains(local):
            return Qt.Edge(0)
        m = self.margin
        edges = Qt.Edge(0)
        if local.x() < m:
            edges |= Qt.Edge.LeftEdge
        elif local.x() >= rect.width() - m:
            edges |= Qt.Edge.RightEdge
        if local.y() < m:
            edges |= Qt.Edge.TopEdge
        elif local.y() >= rect.height() - m:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _cursor_for_edges(self, edges: Qt.Edge):
        L = Qt.Edge.LeftEdge
        R = Qt.Edge.RightEdge
        T = Qt.Edge.TopEdge
        B = Qt.Edge.BottomEdge
        if edges == (L | T) or edges == (R | B):
            return Qt.CursorShape.SizeFDiagCursor
        if edges == (R | T) or edges == (L | B):
            return Qt.CursorShape.SizeBDiagCursor
        if edges == L or edges == R:
            return Qt.CursorShape.SizeHorCursor
        if edges == T or edges == B:
            return Qt.CursorShape.SizeVerCursor
        return None

    def _apply_hover_cursor(self, edges: Qt.Edge) -> None:
        shape = self._cursor_for_edges(edges)
        if shape is None:
            self._clear_override_cursor()
            return
        cursor = QCursor(shape)
        if self._override_cursor_active:
            QApplication.changeOverrideCursor(cursor)
        else:
            QApplication.setOverrideCursor(cursor)
            self._override_cursor_active = True

    def _clear_override_cursor(self) -> None:
        if self._override_cursor_active:
            QApplication.restoreOverrideCursor()
            self._override_cursor_active = False

    def _perform_resize(self, global_pos: QPoint) -> None:
        if self._resize_start_geom is None:
            return
        delta = global_pos - self._resize_start_global
        geom = self._resize_start_geom
        new = QRect(geom)
        min_w = max(self.window.minimumWidth(), 1)
        min_h = max(self.window.minimumHeight(), 1)

        if self._resize_edges & Qt.Edge.LeftEdge:
            new.setLeft(min(geom.left() + delta.x(), geom.right() - min_w + 1))
        if self._resize_edges & Qt.Edge.RightEdge:
            new.setRight(max(geom.right() + delta.x(), geom.left() + min_w - 1))
        if self._resize_edges & Qt.Edge.TopEdge:
            new.setTop(min(geom.top() + delta.y(), geom.bottom() - min_h + 1))
        if self._resize_edges & Qt.Edge.BottomEdge:
            new.setBottom(max(geom.bottom() + delta.y(), geom.top() + min_h - 1))

        self.window.setGeometry(new)
