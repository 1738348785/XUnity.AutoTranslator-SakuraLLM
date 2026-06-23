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

    dual_layout = QHBoxLayout()
    dual_layout.setSpacing(16)

    left_box = QVBoxLayout()
    left_box.setSpacing(8)
    left_label = QLabel(t("test_input_label"))
    left_label.setObjectName("summaryTitle")
    window.test_input = QTextEdit()
    window.test_input.setAcceptRichText(False)
    window.test_input.setPlaceholderText(t("translation_test_placeholder"))
    left_box.addWidget(left_label)
    left_box.addWidget(window.test_input, 1)

    right_box = QVBoxLayout()
    right_box.setSpacing(8)
    right_label = QLabel(t("test_output_label"))
    right_label.setObjectName("summaryTitle")
    window.test_output = QPlainTextEdit()
    window.test_output.setReadOnly(True)
    right_box.addWidget(right_label)
    right_box.addWidget(window.test_output, 1)

    dual_layout.addLayout(left_box, 1)
    dual_layout.addLayout(right_box, 1)

    buttons = QHBoxLayout()
    window.test_button = QPushButton(t("translation_test"))
    window.test_button.setObjectName("primaryButton")
    window.test_button.clicked.connect(window.test_translation)
    buttons.addWidget(window.test_button)
    buttons.addStretch()

    group_layout.addWidget(hint)
    group_layout.addLayout(dual_layout, 1)
    group_layout.addLayout(buttons)
    layout.addWidget(group, 1)
    return page
