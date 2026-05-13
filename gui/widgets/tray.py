from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


class TrayController(QObject):
    show_requested = Signal()
    hide_requested = Signal()
    exit_requested = Signal()
    activated = Signal(QSystemTrayIcon.ActivationReason)

    def __init__(self, parent: QWidget, ui_text: dict):
        super().__init__(parent)
        self.parent_widget = parent
        self.ui_text = ui_text
        self.tray_icon: QSystemTrayIcon | None = None

    def setup(self, icon: QIcon) -> bool:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return False

        self.tray_icon = QSystemTrayIcon(icon, self.parent_widget)
        menu = QMenu(self.parent_widget)

        show_action = QAction(self.ui_text["tray_show_window"], self.parent_widget)
        hide_action = QAction(self.ui_text["tray_hide_window"], self.parent_widget)
        exit_action = QAction(self.ui_text["tray_exit"], self.parent_widget)

        show_action.triggered.connect(self.show_requested)
        hide_action.triggered.connect(self.hide_requested)
        exit_action.triggered.connect(self.exit_requested)

        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()
        return True

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        self.activated.emit(reason)
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()

    def show_message(
        self,
        title: str,
        message: str,
        icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        ms: int = 2000,
    ) -> None:
        if self.tray_icon is not None:
            self.tray_icon.showMessage(title, message, icon_type, ms)

    def teardown(self) -> None:
        if self.tray_icon is not None:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()
            self.tray_icon = None

    def is_available(self) -> bool:
        return self.tray_icon is not None
