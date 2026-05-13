from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout


def create_summary_card(title: str, on_click: Optional[Callable[[], None]] = None):
    frame = QFrame()
    frame.setObjectName("summaryCard")
    if on_click is not None:
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.mousePressEvent = lambda e: on_click()

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(6)

    title_label = QLabel(title)
    title_label.setObjectName("summaryTitle")
    value_label = QLabel("-")
    value_label.setObjectName("summaryValue")
    value_label.setWordWrap(True)

    layout.addWidget(title_label)
    layout.addWidget(value_label)
    value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return frame, value_label
