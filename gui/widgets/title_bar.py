from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class MaximizeButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._maximized = False
        self.setFixedSize(36, 28)

    def set_maximized(self, maximized: bool):
        self._maximized = maximized
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor("#f5f5f7"), 1.4)
        painter.setPen(pen)
        if self._maximized:
            painter.drawRect(12, 9, 10, 8)
            painter.drawRect(15, 12, 10, 8)
        else:
            painter.drawRect(12, 10, 12, 9)
        painter.end()


class TitleBar(QFrame):
    minimize_requested = Signal()
    maximize_toggle_requested = Signal()
    close_requested = Signal()
    drag_started = Signal(QPoint)
    drag_moved = Signal(QPoint)
    drag_released = Signal()
    double_clicked = Signal()

    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(46)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 8, 6)
        layout.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("windowTitleLabel")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("windowSubtitleLabel")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        layout.addLayout(title_box)
        layout.addStretch()

        title_actions = QHBoxLayout()
        title_actions.setSpacing(6)

        self.min_button = QPushButton("—")
        self.min_button.setObjectName("titleButton")
        self.min_button.setFixedSize(36, 28)
        self.min_button.clicked.connect(self.minimize_requested)

        self.max_button = MaximizeButton()
        self.max_button.setObjectName("titleButton")
        self.max_button.clicked.connect(self.maximize_toggle_requested)

        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("closeTitleButton")
        self.close_button.setFixedSize(36, 28)
        self.close_button.clicked.connect(self.close_requested)

        title_actions.addWidget(self.min_button)
        title_actions.addWidget(self.max_button)
        title_actions.addWidget(self.close_button)
        layout.addLayout(title_actions)

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)

    def set_maximized(self, maximized: bool) -> None:
        self.max_button.set_maximized(maximized)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_started.emit(event.globalPosition().toPoint())
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        self.drag_moved.emit(event.globalPosition().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_released.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
        else:
            event.ignore()
