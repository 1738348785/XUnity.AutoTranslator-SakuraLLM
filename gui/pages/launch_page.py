from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def build_launch_page(window) -> QWidget:
    t = window._t
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)

    top_row = QHBoxLayout()
    top_row.setSpacing(16)

    hero_card = QFrame()
    hero_card.setObjectName("heroCard")
    hero_layout = QVBoxLayout(hero_card)
    hero_layout.setContentsMargins(28, 28, 28, 28)
    hero_layout.setSpacing(20)

    title = QLabel(t("local_service_title"))
    title.setObjectName("sectionTitle")
    desc = QLabel(t("local_service_desc"))
    desc.setObjectName("mutedText")
    desc.setWordWrap(True)
    desc.setMinimumWidth(300)
    desc.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)

    hero_layout.addWidget(title)
    hero_layout.addWidget(desc)
    hero_layout.addStretch()

    quick_row = QHBoxLayout()
    quick_row.setSpacing(12)
    settings_jump = QPushButton(t("config_center"))
    settings_jump.setObjectName("ghostButton")
    settings_jump.setMinimumHeight(44)
    settings_jump.clicked.connect(lambda: window._switch_page(1))
    test_jump = QPushButton(t("translation_test"))
    test_jump.setObjectName("ghostButton")
    test_jump.setMinimumHeight(44)
    test_jump.clicked.connect(lambda: window._switch_page(3))
    quick_row.addWidget(settings_jump)
    quick_row.addWidget(test_jump)
    quick_row.addStretch()
    hero_layout.addLayout(quick_row)

    top_row.addWidget(hero_card, 5)

    control_card = QFrame()
    control_card.setObjectName("heroCard")
    control_layout = QVBoxLayout(control_card)
    control_layout.setContentsMargins(28, 28, 28, 28)
    control_layout.setSpacing(20)

    status_hbox = QHBoxLayout()
    status_label_title = QLabel(t("quick_status"))
    status_label_title.setObjectName("summaryTitle")
    status_hbox.addWidget(status_label_title)
    status_hbox.addStretch()

    window.launch_status_value = QLabel(t("idle"))
    window.launch_status_value.setObjectName("heroStatus")
    window.launch_status_value.setMinimumWidth(150)
    window.launch_status_value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    control_layout.addLayout(status_hbox)
    control_layout.addWidget(window.launch_status_value)
    control_layout.addStretch()

    btn_row = QHBoxLayout()
    btn_row.setSpacing(12)
    window.start_button = QPushButton(t("start_service"))
    window.start_button.setObjectName("primaryButton")
    window.start_button.setMinimumHeight(44)
    window.stop_button = QPushButton(t("stop_service"))
    window.stop_button.setObjectName("dangerButton")
    window.stop_button.setMinimumHeight(44)
    window.start_button.clicked.connect(window.start_service)
    window.stop_button.clicked.connect(window.stop_service)

    btn_row.addWidget(window.stop_button, 1)
    btn_row.addWidget(window.start_button, 1)

    control_layout.addLayout(btn_row)

    top_row.addWidget(control_card, 4)

    layout.addLayout(top_row)

    summary_grid = QGridLayout()
    summary_grid.setHorizontalSpacing(16)
    summary_grid.setVerticalSpacing(16)
    summary_grid.setColumnStretch(0, 1)
    summary_grid.setColumnStretch(1, 1)

    model_card, window.launch_model_value = window._create_summary_card(t("current_model"), 1)
    reasoning_card, window.launch_reasoning_value = window._create_summary_card(t("reasoning_effort"), 2)
    base_url_card, window.launch_base_url_value = window._create_summary_card(t("upstream_url"), 1)
    timeout_card, window.launch_timeout_value = window._create_summary_card(t("request_timeout"), 1)

    summary_grid.addWidget(model_card, 0, 0)
    summary_grid.addWidget(reasoning_card, 0, 1)
    summary_grid.addWidget(base_url_card, 1, 0)
    summary_grid.addWidget(timeout_card, 1, 1)
    layout.addLayout(summary_grid)

    bottom_row = QHBoxLayout()
    bottom_row.setSpacing(16)

    hints_group = QGroupBox(t("usage_tips"))
    hint_layout = QVBoxLayout(hints_group)
    hint = QLabel(t("usage_tips_desc"))
    hint.setWordWrap(True)
    hint.setMargin(3)
    hint.setObjectName("mutedText")
    hint_layout.addWidget(hint)

    steps_group = QGroupBox(t("quick_steps"))
    steps_layout = QVBoxLayout(steps_group)
    steps = QLabel(t("quick_steps_desc"))
    steps.setWordWrap(True)
    steps.setMargin(3)
    steps.setObjectName("mutedText")
    steps_layout.addWidget(steps)

    bottom_row.addWidget(hints_group, 5)
    bottom_row.addWidget(steps_group, 4)
    layout.addLayout(bottom_row)
    layout.addStretch(1)
    return window._wrap_scroll_page(page)
