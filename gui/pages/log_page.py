from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
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
    buttons.setSpacing(10)
    window.clear_log_button = QPushButton(t("clear_logs"))
    window.clear_log_button.clicked.connect(window.clear_logs)
    window.copy_log_button = QPushButton(t("copy_logs"))
    window.copy_log_button.setObjectName("ghostButton")
    window.copy_log_button.clicked.connect(window.copy_logs)
    
    window.log_filter_edit = QLineEdit()
    window.log_filter_edit.setPlaceholderText(t("log_filter_placeholder"))
    window.log_filter_edit.textChanged.connect(window._refresh_log_output)
    window.log_filter_edit.setFixedWidth(200)
    
    buttons.addWidget(window.clear_log_button)
    buttons.addWidget(window.copy_log_button)
    buttons.addStretch()
    buttons.addWidget(window.log_filter_edit)

    window.log_output = QTextEdit()
    window.log_output.setReadOnly(True)
    window.log_output.document().setMaximumBlockCount(5000)

    group_layout.addLayout(buttons)
    group_layout.addWidget(window.log_output, 1)
    layout.addWidget(group, 1)
    return page
