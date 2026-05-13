from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def build_log_page(window) -> QWidget:
    t = window._t
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)

    group = QGroupBox(t("page_log_title"))
    group_layout = QVBoxLayout(group)
    buttons = QHBoxLayout()
    window.clear_log_button = QPushButton(t("clear_logs"))
    window.clear_log_button.clicked.connect(window.clear_logs)
    buttons.addWidget(window.clear_log_button)
    buttons.addStretch()

    window.log_output = QTextEdit()
    window.log_output.setReadOnly(True)
    window.log_output.document().setMaximumBlockCount(5000)

    group_layout.addLayout(buttons)
    group_layout.addWidget(window.log_output, 1)
    layout.addWidget(group, 1)
    return page
