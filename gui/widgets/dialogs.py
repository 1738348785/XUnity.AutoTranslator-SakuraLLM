from PySide6.QtWidgets import QInputDialog, QLabel, QMessageBox, QWidget


_DIALOG_QSS = """
QMessageBox, QInputDialog {
    background-color: #25252b;
}
QMessageBox QWidget, QInputDialog QWidget {
    color: #e4e4ea;
    background-color: #25252b;
}
QMessageBox QLabel {
    color: #dddde6;
    min-width: 0;
    max-width: 220px;
}
QInputDialog QLabel {
    color: #dddde6;
    min-width: 0;
}
QMessageBox QPushButton, QInputDialog QPushButton {
    background-color: #33333a;
    border: 1px solid #484853;
    border-radius: 10px;
    color: #f0f0f4;
    min-width: 88px;
    padding: 8px 14px;
}
QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {
    background-color: #3a3a43;
}
QMessageBox QLineEdit, QInputDialog QLineEdit, QInputDialog QComboBox, QInputDialog QListView {
    background-color: #2e2e35;
    border: 1px solid #4a4a54;
    border-radius: 10px;
    color: #f0f0f4;
    padding: 8px 10px;
    selection-background-color: #ff96d3;
}
"""


def dialog_stylesheet() -> str:
    return _DIALOG_QSS


def style_dialog(dialog, parent: QWidget, ui_text: dict) -> None:
    dialog.setWindowIcon(parent.windowIcon())
    dialog.setStyleSheet(_DIALOG_QSS)
    if isinstance(dialog, QInputDialog):
        dialog.setOkButtonText(ui_text["dialog_ok"])
        dialog.setCancelButtonText(ui_text["dialog_cancel"])
        dialog.adjustSize()
        return

    for label in dialog.findChildren(QLabel):
        label.setWordWrap(True)
    dialog.adjustSize()

    button_text_map = {
        QMessageBox.StandardButton.Ok: ui_text["dialog_ok"],
        QMessageBox.StandardButton.Cancel: ui_text["dialog_cancel"],
        QMessageBox.StandardButton.Yes: ui_text["dialog_yes"],
        QMessageBox.StandardButton.No: ui_text["dialog_no"],
    }
    for button_flag, text in button_text_map.items():
        button = dialog.button(button_flag)
        if button is not None:
            button.setText(text)


def message_box(
    parent: QWidget,
    ui_text: dict,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
) -> QMessageBox.StandardButton:
    dialog = QMessageBox(parent)
    dialog.setIcon(icon)
    dialog.setWindowTitle(title)
    dialog.setText(text)
    dialog.setStandardButtons(buttons)
    dialog.setDefaultButton(default_button)
    style_dialog(dialog, parent, ui_text)
    return QMessageBox.StandardButton(dialog.exec())


def show_warning(parent: QWidget, ui_text: dict, title: str, text: str) -> None:
    message_box(parent, ui_text, QMessageBox.Icon.Warning, title, text)


def show_information(parent: QWidget, ui_text: dict, title: str, text: str) -> None:
    message_box(parent, ui_text, QMessageBox.Icon.Information, title, text)


def show_critical(parent: QWidget, ui_text: dict, title: str, text: str) -> None:
    message_box(parent, ui_text, QMessageBox.Icon.Critical, title, text)


def ask_yes_no(parent: QWidget, ui_text: dict, title: str, text: str) -> bool:
    result = message_box(
        parent,
        ui_text,
        QMessageBox.Icon.Question,
        title,
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def prompt_text(
    parent: QWidget,
    ui_text: dict,
    title: str,
    label: str,
    text: str = "",
) -> tuple[str, bool]:
    dialog = QInputDialog(parent)
    dialog.setInputMode(QInputDialog.InputMode.TextInput)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(text)
    style_dialog(dialog, parent, ui_text)
    accepted = bool(dialog.exec())
    return dialog.textValue(), accepted
