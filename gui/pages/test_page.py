from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def build_test_page(window) -> QWidget:
    t = window._t
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)

    group = QGroupBox(t("translation_test"))
    group_layout = QVBoxLayout(group)
    hint = QLabel(t("translation_test_hint"))
    hint.setObjectName("mutedText")
    hint.setWordWrap(True)

    window.test_input = QTextEdit()
    window.test_input.setAcceptRichText(False)
    window.test_input.setPlaceholderText(t("translation_test_placeholder"))
    window.test_output = QPlainTextEdit()
    window.test_output.setReadOnly(True)

    buttons = QHBoxLayout()
    window.test_button = QPushButton(t("translation_test"))
    window.test_button.setObjectName("primaryButton")
    window.test_button.clicked.connect(window.test_translation)
    buttons.addWidget(window.test_button)
    buttons.addStretch()

    group_layout.addWidget(hint)
    group_layout.addWidget(window.test_input, 1)
    group_layout.addLayout(buttons)
    group_layout.addWidget(window.test_output, 1)
    layout.addWidget(group, 1)
    return page
