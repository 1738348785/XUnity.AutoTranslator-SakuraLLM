from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def build_settings_page(window) -> QWidget:
    t = window._t
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)

    preset_bar = QHBoxLayout()
    preset_bar.setSpacing(10)
    window.config_preset_combo = QComboBox()
    window.config_preset_combo.addItem(t("config_preset_sakura"), "sakura本地")
    window.config_preset_combo.addItem(t("config_preset_general"), "通用大模型")
    window.config_preset_combo.currentIndexChanged.connect(window._preview_config_preset)
    window.config_preset_status = QLabel(t("preset_status_applied"))
    window.config_preset_status.setObjectName("presetStatusApplied")
    preset_bar.addWidget(QLabel(t("config_preset")))
    preset_bar.addWidget(window.config_preset_combo)
    preset_bar.addWidget(window.config_preset_status)
    preset_bar.addStretch()
    layout.addLayout(preset_bar)

    top_row = QHBoxLayout()
    top_row.setSpacing(16)

    connection_group = QGroupBox(t("connection_settings"))
    connection_form = QFormLayout(connection_group)
    window.base_url_edit = QLineEdit()
    window.api_key_edit = QLineEdit()
    window.api_key_edit.setEchoMode(QLineEdit.Password)
    window.model_type_edit = QLineEdit()
    window.listen_port_spin = QSpinBox()
    window.listen_port_spin.setRange(1, 65535)
    window.timeout_spin = QSpinBox()
    window.timeout_spin.setRange(1, 600)
    window.newline_mode_combo = QComboBox()
    window.newline_mode_combo.addItems(["escape", "keep", "split_lines"])
    window.ui_language_combo = QComboBox()
    window._populate_ui_language_combo(window.ui_language_mode)
    window.ui_language_combo.currentIndexChanged.connect(window._on_ui_language_changed)
    window.reasoning_effort_combo = QComboBox()
    window.reasoning_effort_combo.addItem(t("default"), "")
    window.reasoning_effort_combo.addItem("low", "low")
    window.reasoning_effort_combo.addItem("medium", "medium")
    window.reasoning_effort_combo.addItem("high", "high")
    window.reasoning_effort_combo.addItem("xhigh", "xhigh")
    window.reasoning_effort_combo.addItem("max", "max")
    window.thinking_mode_combo = QComboBox()
    window.thinking_mode_combo.addItem(t("thinking_disabled"), "disabled")
    window.thinking_mode_combo.addItem(t("thinking_enabled"), "enabled")

    window.max_retries_spin = QSpinBox()
    window.max_retries_spin.setRange(1, 20)
    window.max_concurrency_spin = QSpinBox()
    window.max_concurrency_spin.setRange(1, 64)

    connection_form.addRow(t("ui_language"), window.ui_language_combo)
    connection_form.addRow("Base URL", window.base_url_edit)
    connection_form.addRow("API Key", window.api_key_edit)
    connection_form.addRow(t("model_name"), window.model_type_edit)
    connection_form.addRow(t("listen_port"), window.listen_port_spin)
    connection_form.addRow(t("timeout_seconds"), window.timeout_spin)
    connection_form.addRow(t("newline_mode"), window.newline_mode_combo)
    connection_form.addRow(t("param_max_retries"), window.max_retries_spin)
    connection_form.addRow(t("param_max_concurrency"), window.max_concurrency_spin)

    model_group = QGroupBox(t("model_parameters"))
    model_form = QFormLayout(model_group)

    window.temperature_spin = QDoubleSpinBox()
    window.temperature_spin.setRange(0.0, 2.0)
    window.temperature_spin.setSingleStep(0.05)
    window.top_p_spin = QDoubleSpinBox()
    window.top_p_spin.setRange(0.0, 1.0)
    window.top_p_spin.setSingleStep(0.05)
    window.max_tokens_spin = QSpinBox()
    window.max_tokens_spin.setRange(1, 32768)
    window.frequency_penalty_spin = QDoubleSpinBox()
    window.frequency_penalty_spin.setRange(0.0, 2.0)
    window.frequency_penalty_spin.setSingleStep(0.05)
    window.repeat_count_spin = QSpinBox()
    window.repeat_count_spin.setRange(1, 100)

    model_form.addRow(t("param_temperature"), window.temperature_spin)
    model_form.addRow(t("param_top_p"), window.top_p_spin)
    model_form.addRow(t("param_max_tokens"), window.max_tokens_spin)
    model_form.addRow(t("param_frequency_penalty"), window.frequency_penalty_spin)
    model_form.addRow(t("param_repeat_count"), window.repeat_count_spin)

    model_form.addRow(t("thinking_mode"), window.thinking_mode_combo)

    thinking_hint = QLabel(t("thinking_mode_hint"))
    thinking_hint.setObjectName("mutedText")
    thinking_hint.setWordWrap(True)
    model_form.addRow("", thinking_hint)

    model_form.addRow(t("reasoning_effort"), window.reasoning_effort_combo)

    reasoning_hint = QLabel(t("reasoning_effort_hint"))
    reasoning_hint.setObjectName("mutedText")
    reasoning_hint.setWordWrap(True)
    model_form.addRow("", reasoning_hint)

    top_row.addWidget(connection_group, 1)
    top_row.addWidget(model_group, 1)
    layout.addLayout(top_row)

    compatibility_group = QGroupBox(t("compatibility_notes"))
    compatibility_layout = QVBoxLayout(compatibility_group)
    compatibility_text = QLabel(t("compatibility_notes_desc"))
    compatibility_text.setObjectName("mutedText")
    compatibility_text.setWordWrap(True)
    compatibility_layout.addWidget(compatibility_text)
    layout.addWidget(compatibility_group)
    layout.addStretch(1)

    window.base_url_edit.textChanged.connect(window._mark_config_modified)
    window.api_key_edit.textChanged.connect(window._mark_config_modified)
    window.model_type_edit.textChanged.connect(window._mark_config_modified)
    window.listen_port_spin.valueChanged.connect(window._mark_config_modified)
    window.timeout_spin.valueChanged.connect(window._mark_config_modified)
    window.newline_mode_combo.currentIndexChanged.connect(window._mark_config_modified)
    window.max_retries_spin.valueChanged.connect(window._mark_config_modified)
    window.max_concurrency_spin.valueChanged.connect(window._mark_config_modified)
    window.temperature_spin.valueChanged.connect(window._mark_config_modified)
    window.top_p_spin.valueChanged.connect(window._mark_config_modified)
    window.max_tokens_spin.valueChanged.connect(window._mark_config_modified)
    window.frequency_penalty_spin.valueChanged.connect(window._mark_config_modified)
    window.repeat_count_spin.valueChanged.connect(window._mark_config_modified)
    window.thinking_mode_combo.currentIndexChanged.connect(window._mark_config_modified)
    window.reasoning_effort_combo.currentIndexChanged.connect(window._mark_config_modified)

    return window._wrap_scroll_page(content)
