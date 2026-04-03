import json
import socket
from pathlib import Path

import requests
from PySide6.QtCore import QPoint, QSize, QThread, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor, QPainter, QPen, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sakura_llm.config import (
    AppConfig,
    ConfigStore,
    DEFAULT_SYSTEM_PROMPT,
    PROMPT_PRESETS,
    get_default_config_path,
)
from sakura_llm.logging_bridge import LogEntry, LoggerBridge
from sakura_llm.service import TranslationService


class MaximizeButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._maximized = False
        self.setFixedSize(36, 28)

    def set_maximized(self, maximized: bool):
        self._maximized = maximized
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor("#f5f5f7"), 1.4)
        painter.setPen(pen)
        if self._maximized:
            painter.drawRect(12, 9, 10, 8)
            painter.drawRect(15, 12, 10, 8)
        else:
            painter.drawRect(12, 10, 12, 9)
        painter.end()


class ServiceThread(QThread):
    log_received = Signal(str, str)
    started_ok = Signal()
    stopped_ok = Signal()
    failed = Signal(str)

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.service = None

    def _handle_log(self, entry: LogEntry):
        self.log_received.emit(entry.level, entry.message)

    def run(self):
        logger = LoggerBridge(self._handle_log)
        self.service = TranslationService(self.config, logger)
        try:
            self.service.start()
            self.started_ok.emit()
            self.service.serve_forever()
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            self.stopped_ok.emit()

    def stop_service(self):
        if self.service:
            self.service.stop()


class MainWindow(QMainWindow):
    PAGE_META = [
        ("启动器", "启动本地翻译服务，并查看当前运行状态。"),
        ("配置中心", "编辑连接参数、模型参数和兼容设置。"),
        ("提示词与请求头", "管理系统提示词、预设和额外请求头。"),
        ("测试翻译", "直接调用本地 /translate 接口做端到端验证。"),
        ("运行日志", "查看服务日志、错误信息和翻译输出。"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XUnity.AutoTranslator-SakuraLLM GUI")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(1260, 860)
        self.setMinimumSize(1100, 760)

        self._drag_active = False
        self._drag_pos = QPoint()
        self._window_pos = QPoint()

        self.config_store = ConfigStore(get_default_config_path())
        self.config = self.config_store.load()
        self.service_thread = None
        self.minimize_to_tray = True
        self.force_exit = False
        self.nav_buttons = []

        self._build_ui()
        self._apply_styles()
        self._create_tray_icon()
        self._load_config_to_form()
        self._set_idle_state()
        self._switch_page(0)
        self._sync_titlebar_buttons()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("appRoot")

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_title_bar())

        shell = QHBoxLayout()
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        shell.addWidget(self._build_sidebar())

        main_panel = QWidget()
        main_panel.setObjectName("mainPanel")
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        main_layout.addWidget(self._build_header_bar())

        self.page_stack = QStackedWidget()
        self.page_stack.addWidget(self._build_launch_page())
        self.page_stack.addWidget(self._build_settings_page())
        self.page_stack.addWidget(self._build_prompt_page())
        self.page_stack.addWidget(self._build_test_page())
        self.page_stack.addWidget(self._build_log_page())
        main_layout.addWidget(self.page_stack, 1)

        shell.addWidget(main_panel, 1)
        root.addLayout(shell, 1)
        self.setCentralWidget(central)

        self.base_url_edit.textChanged.connect(self._sync_overview)
        self.model_type_edit.textChanged.connect(self._sync_overview)
        self.listen_port_spin.valueChanged.connect(self._sync_overview)
        self.timeout_spin.valueChanged.connect(self._sync_overview)
        self.reasoning_effort_combo.currentIndexChanged.connect(self._sync_overview)

    def _build_title_bar(self):
        self.title_bar = QFrame()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(46)
        self.title_bar.mousePressEvent = self._titlebar_mouse_press
        self.title_bar.mouseMoveEvent = self._titlebar_mouse_move
        self.title_bar.mouseReleaseEvent = self._titlebar_mouse_release
        self.title_bar.mouseDoubleClickEvent = self._titlebar_mouse_double_click

        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(14, 6, 8, 6)
        layout.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self.window_title_label = QLabel("XUnity.AutoTranslator-SakuraLLM GUI")
        self.window_title_label.setObjectName("windowTitleLabel")
        self.window_subtitle_label = QLabel("XUnity AutoTranslator Local Bridge")
        self.window_subtitle_label.setObjectName("windowSubtitleLabel")
        title_box.addWidget(self.window_title_label)
        title_box.addWidget(self.window_subtitle_label)
        layout.addLayout(title_box)
        layout.addStretch()

        title_actions = QHBoxLayout()
        title_actions.setSpacing(6)

        self.min_button = QPushButton("—")
        self.min_button.setObjectName("titleButton")
        self.min_button.setFixedSize(36, 28)
        self.min_button.clicked.connect(self._minimize_window)

        self.max_button = MaximizeButton()
        self.max_button.setObjectName("titleButton")
        self.max_button.clicked.connect(self._toggle_maximize_restore)

        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("closeTitleButton")
        self.close_button.setFixedSize(36, 28)
        self.close_button.clicked.connect(self._close_from_titlebar)

        title_actions.addWidget(self.min_button)
        title_actions.addWidget(self.max_button)
        title_actions.addWidget(self.close_button)
        layout.addLayout(title_actions)
        return self.title_bar

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 22, 18, 22)
        layout.setSpacing(12)

        brand = QLabel("SakuraLLM")
        brand.setObjectName("brandTitle")
        subtitle = QLabel("本地翻译启动器")
        subtitle.setObjectName("brandSubtitle")
        version = QLabel("Launcher UI")
        version.setObjectName("accentBadge")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addWidget(version)
        layout.addSpacing(14)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("启动", QStyle.StandardPixmap.SP_MediaPlay, 0),
            ("配置", QStyle.StandardPixmap.SP_FileDialogDetailedView, 1),
            ("提示词", QStyle.StandardPixmap.SP_FileDialogContentsView, 2),
            ("测试", QStyle.StandardPixmap.SP_DialogApplyButton, 3),
            ("日志", QStyle.StandardPixmap.SP_FileDialogInfoView, 4),
        ]
        for text, icon_type, index in nav_items:
            button = QPushButton(text)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setIcon(self.style().standardIcon(icon_type))
            button.setIconSize(QSize(20, 20))
            button.setMinimumHeight(52)
            button.clicked.connect(lambda checked, idx=index: self._switch_page(idx))
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()

        about = QLabel("兼容 XUnity.AutoTranslator\n支持本地 Flask / gevent 服务")
        about.setObjectName("sidebarFooter")
        about.setWordWrap(True)
        layout.addWidget(about)
        return sidebar

    def _build_header_bar(self):
        card = QFrame()
        card.setObjectName("headerCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(22)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        self.page_title_label = QLabel()
        self.page_title_label.setObjectName("pageTitle")
        self.page_desc_label = QLabel()
        self.page_desc_label.setObjectName("pageSubtitle")
        self.page_desc_label.setWordWrap(True)
        title_box.addWidget(self.page_title_label)
        title_box.addWidget(self.page_desc_label)
        layout.addLayout(title_box, 1)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(spacer)

        self.quick_log_button = QPushButton("运行日志")
        self.quick_log_button.setObjectName("ghostButton")
        self.quick_log_button.clicked.connect(lambda: self._switch_page(4))
        layout.addWidget(self.quick_log_button, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        right_box = QVBoxLayout()
        right_box.setSpacing(10)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.save_button = QPushButton("保存配置")
        self.import_button = QPushButton("导入配置")
        self.export_button = QPushButton("导出配置")
        self.reset_button = QPushButton("恢复默认")
        self.save_button.clicked.connect(self.save_config)
        self.import_button.clicked.connect(self.import_config)
        self.export_button.clicked.connect(self.export_config)
        self.reset_button.clicked.connect(self.reset_defaults)
        action_row.addWidget(self.save_button)
        action_row.addWidget(self.import_button)
        action_row.addWidget(self.export_button)
        action_row.addWidget(self.reset_button)

        info_row = QHBoxLayout()
        info_row.setSpacing(10)
        self.status_label = QLabel()
        self.status_label.setObjectName("statusPill")
        self.url_label = QLabel()
        self.url_label.setObjectName("urlValue")
        info_row.addWidget(self.status_label)
        info_row.addWidget(self.url_label)
        info_row.addStretch()

        right_box.addLayout(action_row)
        right_box.addLayout(info_row)
        layout.addLayout(right_box)
        return card

    def _build_launch_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        hero_card = QFrame()
        hero_card.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(16)

        title = QLabel("本地翻译服务")
        title.setObjectName("sectionTitle")
        desc = QLabel("保持与 XUnity.AutoTranslator 的本地 HTTP 调用方式兼容，快速启动、停止并检查当前配置摘要。")
        desc.setObjectName("mutedText")
        desc.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(desc)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)

        settings_jump = QPushButton("配置中心")
        settings_jump.setObjectName("ghostButton")
        settings_jump.clicked.connect(lambda: self._switch_page(1))
        test_jump = QPushButton("翻译测试")
        test_jump.setObjectName("ghostButton")
        test_jump.clicked.connect(lambda: self._switch_page(3))

        self.start_button = QPushButton("启动服务")
        self.start_button.setObjectName("primaryButton")
        self.stop_button = QPushButton("停止服务")
        self.stop_button.setObjectName("dangerButton")
        self.start_button.clicked.connect(self.start_service)
        self.stop_button.clicked.connect(self.stop_service)

        quick_row.addWidget(settings_jump)
        quick_row.addWidget(test_jump)
        quick_row.addStretch()
        quick_row.addWidget(self.stop_button)
        quick_row.addWidget(self.start_button)
        hero_layout.addLayout(quick_row)

        top_row.addWidget(hero_card, 3)

        side_card = QFrame()
        side_card.setObjectName("summaryCard")
        side_layout = QVBoxLayout(side_card)
        side_layout.setContentsMargins(18, 18, 18, 18)
        side_layout.setSpacing(10)
        side_title = QLabel("快速状态")
        side_title.setObjectName("summaryTitle")
        self.launch_status_value = QLabel("待机")
        self.launch_status_value.setObjectName("heroStatus")
        side_desc = QLabel("点击右侧主按钮即可启动或停止本地服务。")
        side_desc.setObjectName("mutedText")
        side_desc.setWordWrap(True)
        side_layout.addWidget(side_title)
        side_layout.addWidget(self.launch_status_value)
        side_layout.addWidget(side_desc)
        side_layout.addStretch()

        top_row.addWidget(side_card, 1)
        layout.addLayout(top_row)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(14)
        summary_grid.setVerticalSpacing(14)

        model_card, self.launch_model_value = self._create_summary_card("当前模型")
        reasoning_card, self.launch_reasoning_value = self._create_summary_card("深度思考")
        base_url_card, self.launch_base_url_value = self._create_summary_card("上游地址")
        timeout_card, self.launch_timeout_value = self._create_summary_card("请求超时")

        summary_grid.addWidget(model_card, 0, 0)
        summary_grid.addWidget(reasoning_card, 0, 1)
        summary_grid.addWidget(base_url_card, 1, 0)
        summary_grid.addWidget(timeout_card, 1, 1)
        layout.addLayout(summary_grid)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        hints_group = QGroupBox("使用提示")
        hint_layout = QVBoxLayout(hints_group)
        hint = QLabel(
            "首次使用建议先在“配置中心”填写 Base URL、模型名和端口；如果要调整提示词或额外请求体字段，可在“提示词”页继续设置。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("mutedText")
        hint_layout.addWidget(hint)

        steps_group = QGroupBox("快速流程")
        steps_layout = QVBoxLayout(steps_group)
        steps = QLabel("1. 填写连接参数\n2. 选择深度思考与模型参数\n3. 保存配置\n4. 启动服务\n5. 到测试页验证输出")
        steps.setObjectName("mutedText")
        steps_layout.addWidget(steps)

        bottom_row.addWidget(hints_group, 2)
        bottom_row.addWidget(steps_group, 1)
        layout.addLayout(bottom_row)
        layout.addStretch(1)
        return page

    def _build_settings_page(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        connection_group = QGroupBox("连接配置")
        connection_form = QFormLayout(connection_group)
        self.base_url_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.model_type_edit = QLineEdit()
        self.listen_port_spin = QSpinBox()
        self.listen_port_spin.setRange(1, 65535)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 600)
        self.newline_mode_combo = QComboBox()
        self.newline_mode_combo.addItems(["escape", "keep", "split_lines"])
        self.reasoning_effort_combo = QComboBox()
        self.reasoning_effort_combo.addItem("默认", "")
        self.reasoning_effort_combo.addItem("low", "low")
        self.reasoning_effort_combo.addItem("medium", "medium")
        self.reasoning_effort_combo.addItem("high", "high")

        connection_form.addRow("Base URL", self.base_url_edit)
        connection_form.addRow("API Key", self.api_key_edit)
        connection_form.addRow("模型名", self.model_type_edit)
        connection_form.addRow("监听端口", self.listen_port_spin)
        connection_form.addRow("超时(秒)", self.timeout_spin)
        connection_form.addRow("换行模式", self.newline_mode_combo)
        connection_form.addRow("深度思考", self.reasoning_effort_combo)

        thinking_hint = QLabel("会写入请求体中的 reasoning_effort；默认表示不额外传这个字段。")
        thinking_hint.setObjectName("mutedText")
        thinking_hint.setWordWrap(True)
        connection_form.addRow("", thinking_hint)

        model_group = QGroupBox("模型参数")
        model_form = QFormLayout(model_group)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.05)
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 32768)
        self.frequency_penalty_spin = QDoubleSpinBox()
        self.frequency_penalty_spin.setRange(0.0, 2.0)
        self.frequency_penalty_spin.setSingleStep(0.05)
        self.repeat_count_spin = QSpinBox()
        self.repeat_count_spin.setRange(1, 100)
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 20)

        model_form.addRow("temperature", self.temperature_spin)
        model_form.addRow("top_p", self.top_p_spin)
        model_form.addRow("max_tokens", self.max_tokens_spin)
        model_form.addRow("frequency_penalty", self.frequency_penalty_spin)
        model_form.addRow("repeat_count", self.repeat_count_spin)
        model_form.addRow("max_retries", self.max_retries_spin)

        top_row.addWidget(connection_group, 1)
        top_row.addWidget(model_group, 1)
        layout.addLayout(top_row)

        compatibility_group = QGroupBox("兼容性说明")
        compatibility_layout = QVBoxLayout(compatibility_group)
        compatibility_text = QLabel(
            "本地接口仍保持 http://127.0.0.1:<端口>/translate 形式。若修改监听端口，请同步更新 XUnity.AutoTranslator 的 Custom.Url。"
        )
        compatibility_text.setObjectName("mutedText")
        compatibility_text.setWordWrap(True)
        compatibility_layout.addWidget(compatibility_text)
        layout.addWidget(compatibility_group)
        layout.addStretch(1)
        return self._wrap_scroll_page(content)

    def _build_prompt_page(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        prompt_group = QGroupBox("系统提示词")
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_bar = QHBoxLayout()
        self.prompt_preset_combo = QComboBox()
        self.prompt_preset_combo.addItems(PROMPT_PRESETS.keys())
        self.prompt_apply_button = QPushButton("应用预设")
        self.prompt_apply_button.clicked.connect(self.apply_prompt_preset)
        prompt_bar.addWidget(QLabel("提示词预设"))
        prompt_bar.addWidget(self.prompt_preset_combo)
        prompt_bar.addWidget(self.prompt_apply_button)
        prompt_bar.addStretch()

        self.system_prompt_edit = QPlainTextEdit()
        self.system_prompt_edit.setPlaceholderText(DEFAULT_SYSTEM_PROMPT)
        self.system_prompt_edit.setMaximumBlockCount(1000)
        self.system_prompt_edit.setMinimumHeight(260)

        prompt_layout.addLayout(prompt_bar)
        prompt_layout.addWidget(self.system_prompt_edit)
        layout.addWidget(prompt_group, 1)

        headers_group = QGroupBox("自定义请求头(JSON)")
        headers_layout = QVBoxLayout(headers_group)
        headers_hint = QLabel("用于补充额外请求头。reasoning_effort 已提供单独菜单，一般不需要再手写在这里。")
        headers_hint.setObjectName("mutedText")
        headers_hint.setWordWrap(True)
        self.custom_headers_edit = QPlainTextEdit()
        self.custom_headers_edit.setPlaceholderText('{\n  "x-custom-header": "value"\n}')
        self.custom_headers_edit.setMaximumBlockCount(200)
        self.custom_headers_edit.setMinimumHeight(160)
        headers_layout.addWidget(headers_hint)
        headers_layout.addWidget(self.custom_headers_edit)
        layout.addWidget(headers_group)

        return self._wrap_scroll_page(content)

    def _build_test_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        group = QGroupBox("测试翻译")
        group_layout = QVBoxLayout(group)
        hint = QLabel("输入文本后会直接请求本地 /translate 接口，用于验证 GUI → 本地服务 → 上游 API 整条链路。")
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)

        self.test_input = QTextEdit()
        self.test_input.setAcceptRichText(False)
        self.test_input.setPlaceholderText("输入测试文本")
        self.test_output = QPlainTextEdit()
        self.test_output.setReadOnly(True)

        buttons = QHBoxLayout()
        self.test_button = QPushButton("测试翻译")
        self.test_button.setObjectName("primaryButton")
        self.test_button.clicked.connect(self.test_translation)
        buttons.addWidget(self.test_button)
        buttons.addStretch()

        group_layout.addWidget(hint)
        group_layout.addWidget(self.test_input, 1)
        group_layout.addLayout(buttons)
        group_layout.addWidget(self.test_output, 1)
        layout.addWidget(group, 1)
        return page

    def _build_log_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        group = QGroupBox("运行日志")
        group_layout = QVBoxLayout(group)
        buttons = QHBoxLayout()
        self.clear_log_button = QPushButton("清空日志")
        self.clear_log_button.clicked.connect(self.clear_logs)
        buttons.addWidget(self.clear_log_button)
        buttons.addStretch()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        group_layout.addLayout(buttons)
        group_layout.addWidget(self.log_output, 1)
        layout.addWidget(group, 1)
        return page

    def _wrap_scroll_page(self, content: QWidget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll

    def _create_summary_card(self, title: str):
        frame = QFrame()
        frame.setObjectName("summaryCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")
        value_label = QLabel("-")
        value_label.setObjectName("summaryValue")
        value_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return frame, value_label

    def _switch_page(self, index: int):
        self.page_stack.setCurrentIndex(index)
        title, desc = self.PAGE_META[index]
        self.page_title_label.setText(title)
        self.page_desc_label.setText(desc)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #1b1b1f;
                color: #f5f5f7;
            }
            QWidget#appRoot, QWidget#mainPanel {
                background-color: #1b1b1f;
            }
            QFrame#titleBar {
                background-color: #111115;
                border-bottom: 1px solid #2e2e37;
            }
            QLabel#windowTitleLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#windowSubtitleLabel {
                color: #9999a7;
                font-size: 11px;
            }
            QPushButton#titleButton, QPushButton#closeTitleButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                color: #f5f5f7;
                font-size: 14px;
                font-weight: 700;
                padding: 2px 4px;
            }
            QPushButton#titleButton:hover {
                background-color: #30303a;
            }
            QPushButton#closeTitleButton:hover {
                background-color: #cf5f91;
                color: #ffffff;
            }
            QFrame#sidebar {
                background-color: #202024;
                border-right: 1px solid #34343c;
            }
            QLabel#brandTitle {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#brandSubtitle, QLabel#sidebarFooter, QLabel#mutedText {
                color: #a9a9b4;
                font-size: 13px;
            }
            QLabel#accentBadge {
                color: #ffafe0;
                background-color: #342636;
                border: 1px solid #7d5770;
                border-radius: 12px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#navButton {
                background: transparent;
                border: none;
                border-radius: 14px;
                color: #c8c8d2;
                text-align: left;
                padding: 14px 16px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton#navButton:hover {
                background-color: #2d2d33;
                color: #ffffff;
            }
            QPushButton#navButton:checked {
                background-color: #34343d;
                color: #ff9ad6;
                border-left: 4px solid #ff8fd1;
                padding-left: 12px;
            }
            QPushButton#ghostButton {
                background-color: #2c2c33;
                border: 1px solid #43434f;
                color: #f4f4f7;
            }
            QPushButton#ghostButton:hover {
                background-color: #383842;
                border-color: #575765;
            }
            QFrame#headerCard, QFrame#heroCard, QFrame#summaryCard, QGroupBox {
                background-color: #25252b;
                border: 1px solid #373740;
                border-radius: 18px;
            }
            QLabel#pageTitle {
                color: #ffffff;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#pageSubtitle {
                color: #a9a9b4;
                font-size: 13px;
            }
            QLabel#statusPill {
                background-color: #312533;
                border: 1px solid #7f4e6d;
                border-radius: 12px;
                color: #ff9ad6;
                padding: 6px 12px;
                font-weight: 700;
            }
            QLabel#urlValue {
                color: #e0e0e5;
                font-size: 13px;
            }
            QLabel#sectionTitle {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#summaryTitle {
                color: #a9a9b4;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#heroStatus {
                color: #ffafe0;
                font-size: 30px;
                font-weight: 800;
            }
            QLabel#summaryValue {
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton {
                background-color: #33333a;
                border: 1px solid #484853;
                border-radius: 12px;
                color: #f7f7fa;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3a3a43;
            }
            QPushButton:disabled {
                background-color: #2a2a2f;
                border-color: #35353a;
                color: #7f7f89;
            }
            QPushButton#primaryButton {
                background-color: #f5a0d9;
                border: none;
                color: #2f1c2e;
                padding: 12px 22px;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton#primaryButton:hover {
                background-color: #ffb0e1;
            }
            QPushButton#dangerButton {
                background-color: #2d242d;
                border: 1px solid #80506f;
                color: #ffd8ec;
            }
            QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #2e2e35;
                border: 1px solid #4a4a54;
                border-radius: 12px;
                color: #f7f7fa;
                padding: 10px 12px;
                selection-background-color: #ff96d3;
            }
            QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #ff96d3;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QGroupBox {
                margin-top: 14px;
                padding-top: 10px;
                font-size: 14px;
                font-weight: 700;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #ffffff;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #232329;
                width: 12px;
                margin: 2px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #53535f;
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
        )

    def _titlebar_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint()
            self._window_pos = self.frameGeometry().topLeft()
            event.accept()
        else:
            event.ignore()

    def _titlebar_mouse_move(self, event):
        if self._drag_active and not self.isMaximized():
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self._window_pos + delta)
            event.accept()
        else:
            event.ignore()

    def _titlebar_mouse_release(self, event):
        self._drag_active = False
        event.accept()

    def _titlebar_mouse_double_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize_restore()
            event.accept()
        else:
            event.ignore()

    def _minimize_window(self):
        self.showMinimized()
        self._sync_titlebar_buttons()

    def _toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_titlebar_buttons()

    def _close_from_titlebar(self):
        self.close()

    def _sync_titlebar_buttons(self):
        self.max_button.set_maximized(self.isMaximized())

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            self._sync_titlebar_buttons()
        super().changeEvent(event)

    def _create_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        icon = self.windowIcon()
        if icon.isNull():
            icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
            self.setWindowIcon(icon)

        self.tray_icon = QSystemTrayIcon(icon, self)
        menu = QMenu(self)

        show_action = QAction("显示窗口", self)
        hide_action = QAction("隐藏窗口", self)
        exit_action = QAction("退出", self)

        show_action.triggered.connect(self._show_from_tray)
        hide_action.triggered.connect(self.hide)
        exit_action.triggered.connect(self._exit_from_tray)

        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._handle_tray_activation)
        self.tray_icon.show()

    def _handle_tray_activation(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.raise_()
        self.activateWindow()
        self._sync_titlebar_buttons()

    def _exit_from_tray(self):
        self.force_exit = True
        self.close()

    def _set_reasoning_effort(self, value: str):
        normalized = str(value or "").strip().lower()
        index = self.reasoning_effort_combo.findData(normalized if normalized in {"low", "medium", "high"} else "")
        if index >= 0:
            self.reasoning_effort_combo.setCurrentIndex(index)

    def _current_reasoning_effort(self) -> str:
        value = self.reasoning_effort_combo.currentData()
        return str(value).strip() if value else ""

    def _sync_overview(self):
        model = self.model_type_edit.text().strip() or "未设置"
        base_url = self.base_url_edit.text().strip() or "未设置"
        timeout = f"{self.timeout_spin.value()} 秒"
        reasoning = self._current_reasoning_effort() or "默认"

        self.launch_model_value.setText(model)
        self.launch_base_url_value.setText(base_url)
        self.launch_timeout_value.setText(timeout)
        self.launch_reasoning_value.setText(reasoning)
        self.launch_status_value.setText("运行中" if self._is_service_running() else "待机")

        if not self._is_service_running():
            try:
                self.url_label.setText(f"本地地址: {self._collect_config_from_form().translate_url}")
            except ValueError:
                self.url_label.setText("本地地址: 配置无效")

    def _load_config_to_form(self):
        cfg = self.config
        self.base_url_edit.setText(cfg.base_url)
        self.api_key_edit.setText(cfg.api_key)
        self.model_type_edit.setText(cfg.model_type)
        self.listen_port_spin.setValue(cfg.listen_port)
        self.timeout_spin.setValue(cfg.request_timeout)
        self.newline_mode_combo.setCurrentText(cfg.newline_mode)
        self.temperature_spin.setValue(cfg.temperature)
        self.top_p_spin.setValue(cfg.top_p)
        self.max_tokens_spin.setValue(cfg.max_tokens)
        self.frequency_penalty_spin.setValue(cfg.frequency_penalty)
        self.repeat_count_spin.setValue(cfg.repeat_count)
        self.max_retries_spin.setValue(cfg.max_retries)

        headers = dict(cfg.custom_headers or {})
        self._set_reasoning_effort(headers.pop("reasoning_effort", ""))
        self.custom_headers_edit.setPlainText(json.dumps(headers, ensure_ascii=False, indent=2) if headers else "{}")
        self.system_prompt_edit.setPlainText(cfg.system_prompt)
        self.url_label.setText(f"本地地址: {cfg.translate_url}")
        self._sync_overview()

    def apply_prompt_preset(self):
        preset_name = self.prompt_preset_combo.currentText()
        prompt = PROMPT_PRESETS.get(preset_name, DEFAULT_SYSTEM_PROMPT)
        self.system_prompt_edit.setPlainText(prompt)
        self.append_log("INFO", f"已应用提示词预设: {preset_name}")

    def _parse_custom_headers(self) -> dict:
        raw = self.custom_headers_edit.toPlainText().strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"自定义请求头不是有效 JSON：{e.msg}")
        if not isinstance(data, dict):
            raise ValueError("自定义请求头必须是 JSON 对象。")
        return {str(k): str(v) for k, v in data.items()}

    def _collect_config_from_form(self) -> AppConfig:
        headers = self._parse_custom_headers()
        reasoning_effort = self._current_reasoning_effort()
        headers.pop("reasoning_effort", None)
        if reasoning_effort:
            headers["reasoning_effort"] = reasoning_effort

        return AppConfig(
            base_url=self.base_url_edit.text().strip(),
            api_key=self.api_key_edit.text().strip(),
            listen_port=self.listen_port_spin.value(),
            custom_headers=headers,
            model_type=self.model_type_edit.text().strip(),
            request_timeout=self.timeout_spin.value(),
            newline_mode=self.newline_mode_combo.currentText(),
            repeat_count=self.repeat_count_spin.value(),
            max_retries=self.max_retries_spin.value(),
            temperature=self.temperature_spin.value(),
            max_tokens=self.max_tokens_spin.value(),
            top_p=self.top_p_spin.value(),
            frequency_penalty=self.frequency_penalty_spin.value(),
            system_prompt=self.system_prompt_edit.toPlainText().strip(),
        )

    def _is_port_available(self, port: int) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False
        finally:
            sock.close()

    def _is_service_running(self) -> bool:
        return self.service_thread is not None and self.service_thread.isRunning()

    def _set_idle_state(self):
        self.status_label.setText("状态: 未启动")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._sync_overview()

    def _set_running_state(self):
        self.status_label.setText("状态: 运行中")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.url_label.setText(f"本地地址: {self.config.translate_url}")
        self._sync_overview()

    def _set_starting_state(self):
        self.status_label.setText("状态: 启动中")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def _set_stopping_state(self):
        self.status_label.setText("状态: 停止中")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def append_log(self, level: str, message: str):
        color = {
            "INFO": QColor("#dcdcdc"),
            "WARN": QColor("#f1c40f"),
            "ERROR": QColor("#ff6b6b"),
        }.get(level, QColor("#dcdcdc"))
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"[{level}] {message}\n", fmt)
        self.log_output.setTextCursor(cursor)
        self.log_output.ensureCursorVisible()

    def save_config(self):
        try:
            config = self._collect_config_from_form()
        except ValueError as e:
            QMessageBox.warning(self, "提示", str(e))
            return False

        if not config.base_url or not config.model_type:
            QMessageBox.warning(self, "提示", "Base URL 和 模型名不能为空。")
            return False
        if not config.system_prompt.strip():
            QMessageBox.warning(self, "提示", "系统提示词不能为空。")
            return False

        self.config = config
        self.config_store.save(config)
        if self._is_service_running():
            self._set_running_state()
        else:
            self._set_idle_state()
        self.append_log("INFO", "配置已保存")
        return True

    def import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入配置", str(Path.cwd()), "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                imported = AppConfig.from_dict(json.load(f))
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))
            return
        self.config = imported
        self._load_config_to_form()
        self._set_idle_state() if not self._is_service_running() else self._set_running_state()
        self.append_log("INFO", f"已导入配置: {file_path}")

    def export_config(self):
        try:
            config = self._collect_config_from_form()
        except ValueError as e:
            QMessageBox.warning(self, "提示", str(e))
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出配置", str(Path.cwd() / "config-export.json"), "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
            return
        self.append_log("INFO", f"已导出配置: {file_path}")

    def reset_defaults(self):
        self.config = AppConfig()
        self._load_config_to_form()
        self._set_idle_state()
        self.append_log("INFO", "已恢复默认配置")

    def start_service(self):
        if self._is_service_running():
            return
        if not self.save_config():
            return
        if not self._is_port_available(self.config.listen_port):
            QMessageBox.warning(self, "端口占用", f"127.0.0.1:{self.config.listen_port} 已被占用。")
            self.append_log("ERROR", f"端口已占用: {self.config.listen_port}")
            return

        self.service_thread = ServiceThread(self.config)
        self.service_thread.log_received.connect(self.append_log)
        self.service_thread.started_ok.connect(self._on_service_started)
        self.service_thread.stopped_ok.connect(self._on_service_stopped)
        self.service_thread.failed.connect(self._handle_service_error)

        self._set_starting_state()
        self.service_thread.start()

    def stop_service(self):
        if not self._is_service_running():
            self._set_idle_state()
            return
        self._set_stopping_state()
        self.service_thread.stop_service()
        self.service_thread.wait(3000)

    def test_translation(self):
        text = self.test_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请先输入测试文本。")
            return
        self.test_button.setEnabled(False)
        self.test_output.setPlainText("请求中...")
        try:
            config = self._collect_config_from_form()
            response = requests.get(
                config.translate_url,
                params={"text": text},
                timeout=config.request_timeout,
            )
            if response.ok:
                self.test_output.setPlainText(response.text)
            else:
                self.test_output.setPlainText(f"HTTP {response.status_code}\n{response.text}")
        except Exception as e:
            self.test_output.setPlainText(str(e))
        finally:
            self.test_button.setEnabled(True)

    def clear_logs(self):
        self.log_output.clear()

    def _on_service_started(self):
        self._set_running_state()
        self.append_log("INFO", "服务启动成功")
        if self.tray_icon:
            self.tray_icon.showMessage("SakuraLLM GUI", "本地翻译服务已启动。", QSystemTrayIcon.MessageIcon.Information, 2000)

    def _on_service_stopped(self):
        self._set_idle_state()
        if self.service_thread is not None:
            self.service_thread.deleteLater()
            self.service_thread = None

    def _handle_service_error(self, message: str):
        self.append_log("ERROR", message)
        QMessageBox.critical(self, "服务错误", message)
        self._set_idle_state()

    def closeEvent(self, event: QCloseEvent):
        if self.minimize_to_tray and not self.force_exit and self.tray_icon is not None:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("SakuraLLM GUI", "程序已最小化到托盘。", QSystemTrayIcon.MessageIcon.Information, 2000)
            return
        self.stop_service()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        super().closeEvent(event)
