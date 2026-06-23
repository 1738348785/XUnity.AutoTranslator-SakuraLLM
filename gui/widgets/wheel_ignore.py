from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class WheelIgnoreSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class WheelIgnoreDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class WheelIgnoreComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()
