from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.wheel_ignore import WheelIgnoreComboBox

from sakura_llm.config import DEFAULT_SYSTEM_PROMPT


def build_prompt_page(window) -> QWidget:
    t = window._t
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)

    prompt_group = QGroupBox(t("system_prompt"))
    prompt_layout = QVBoxLayout(prompt_group)
    prompt_bar = QHBoxLayout()
    window.prompt_preset_combo = WheelIgnoreComboBox()
    window._refresh_prompt_preset_combo()
    window.prompt_preset_combo.currentIndexChanged.connect(window._preview_prompt_preset)
    window.prompt_apply_button = QPushButton(t("apply_preset"))
    window.prompt_apply_button.clicked.connect(window.apply_prompt_preset)
    window.prompt_save_button = QPushButton(t("save_custom_preset"))
    window.prompt_save_button.setObjectName("ghostButton")
    window.prompt_save_button.clicked.connect(window.save_custom_prompt_preset)
    window.prompt_rename_button = QPushButton(t("rename_custom_preset"))
    window.prompt_rename_button.setObjectName("ghostButton")
    window.prompt_rename_button.clicked.connect(window.rename_custom_prompt_preset)
    window.prompt_delete_button = QPushButton(t("delete_custom_preset"))
    window.prompt_delete_button.setObjectName("ghostButton")
    window.prompt_delete_button.clicked.connect(window.delete_custom_prompt_preset)
    prompt_bar.addWidget(QLabel(t("prompt_preset")))
    prompt_bar.addWidget(window.prompt_preset_combo)
    window.prompt_preset_status = QLabel(t("preset_status_applied"))
    window.prompt_preset_status.setObjectName("presetStatusApplied")
    prompt_bar.addWidget(window.prompt_apply_button)
    prompt_bar.addWidget(window.prompt_preset_status)
    prompt_bar.addWidget(window.prompt_save_button)
    prompt_bar.addWidget(window.prompt_rename_button)
    prompt_bar.addWidget(window.prompt_delete_button)
    prompt_bar.addStretch()

    window.system_prompt_edit = QPlainTextEdit()
    window.system_prompt_edit.setPlaceholderText(DEFAULT_SYSTEM_PROMPT)
    window.system_prompt_edit.setMaximumBlockCount(1000)
    window.system_prompt_edit.setMinimumHeight(260)

    prompt_layout.addLayout(prompt_bar)
    prompt_layout.addWidget(window.system_prompt_edit)
    layout.addWidget(prompt_group, 1)

    headers_group = QGroupBox(t("custom_headers"))
    headers_layout = QVBoxLayout(headers_group)
    headers_hint = QLabel(t("custom_headers_hint"))
    headers_hint.setObjectName("mutedText")
    headers_hint.setWordWrap(True)
    window.custom_headers_edit = QPlainTextEdit()
    window.custom_headers_edit.setPlaceholderText('{\n  "x-custom-header": "value"\n}')
    window.custom_headers_edit.setMaximumBlockCount(200)
    window.custom_headers_edit.setMinimumHeight(160)
    headers_layout.addWidget(headers_hint)
    headers_layout.addWidget(window.custom_headers_edit)
    window.headers_error_label = QLabel("")
    window.headers_error_label.setWordWrap(True)
    headers_layout.addWidget(window.headers_error_label)
    layout.addWidget(headers_group)

    btn_bar = QHBoxLayout()
    btn_bar.addStretch()
    
    window.save_button_prompt = QPushButton(t("save_config"))
    window.save_button_prompt.setObjectName("primaryButton")
    window.save_button_prompt.clicked.connect(window.save_config)
    window.save_button_prompt.setFixedWidth(130)
    btn_bar.addWidget(window.save_button_prompt)
    layout.addLayout(btn_bar)

    window.system_prompt_edit.textChanged.connect(window._mark_prompt_modified)
    window.system_prompt_edit.textChanged.connect(window._mark_config_modified)
    window.custom_headers_edit.textChanged.connect(window._mark_config_modified)
    window.custom_headers_edit.textChanged.connect(window._validate_custom_headers)
    window.prompt_preset_combo.currentIndexChanged.connect(window._mark_config_modified)

    return window._wrap_scroll_page(content)
