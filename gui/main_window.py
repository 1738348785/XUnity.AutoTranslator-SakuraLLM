import json
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QCloseEvent, QColor, QIcon, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from sakura_llm.config import (
    AppConfig,
    ConfigStore,
    CONFIG_PRESETS,
    DEFAULT_SYSTEM_PROMPT,
    PROMPT_PRESETS,
    get_default_config_path,
)

from . import form_binding
from .i18n import (
    BUILTIN_PROMPT_PRESET_NAMES,
    UI_TEXT,
    resolve_ui_language,
)
from .pages.launch_page import build_launch_page
from .pages.log_page import build_log_page
from .pages.prompt_page import build_prompt_page
from .pages.settings_page import build_settings_page
from .pages.test_page import build_test_page
from .resources import APP_VERSION, get_app_resource_path
from .threads.health_thread import HealthCheckThread
from .threads.service_thread import ServiceThread
from .threads.test_thread import TestTranslationThread
from .widgets import dialogs
from .widgets.resizable import WindowResizer
from .widgets.summary_card import create_summary_card
from .widgets.title_bar import TitleBar
from .widgets.tray import TrayController


class MainWindow(QMainWindow):
    PAGE_META_KEYS = [
        ("page_launch_title", "page_launch_desc"),
        ("page_settings_title", "page_settings_desc"),
        ("page_prompt_title", "page_prompt_desc"),
        ("page_test_title", "page_test_desc"),
        ("page_log_title", "page_log_desc"),
    ]

    _RESIZE_MARGIN = 6

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XUnity.AutoTranslator-SakuraLLM GUI")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(1260, 860)
        self.setMinimumSize(1100, 760)
        self._apply_window_icon()

        self._drag_active = False
        self._drag_pos = QPoint()
        self._window_pos = QPoint()

        self.config_store = ConfigStore(get_default_config_path())
        self.config = self.config_store.load()
        self.ui_language_mode = "auto"
        self.tray: TrayController | None = None
        self._rebuilding_ui = False
        self._update_language_state(self.config.ui_language)
        self.custom_prompt_presets = dict(self.config.prompt_presets or {})
        self.builtin_prompt_presets = dict(PROMPT_PRESETS)
        self.prompt_presets = dict(self.builtin_prompt_presets)
        self.prompt_presets.update(self.custom_prompt_presets)
        self.service_thread = None
        self.minimize_to_tray = True
        self.force_exit = False
        self.nav_buttons = []
        self.log_entries = []

        self._build_ui()
        self._apply_styles()
        self._create_tray_icon()
        self._load_config_to_form()
        self._set_idle_state()
        self._switch_page(0)
        self._sync_titlebar_buttons()
        self._install_resize_support()

    def _t(self, key: str, **kwargs) -> str:
        text = self.ui_text[key]
        return text.format(**kwargs) if kwargs else text

    def _display_prompt_preset_name(self, name: str) -> str:
        label_key = BUILTIN_PROMPT_PRESET_NAMES.get(name)
        return self._t(label_key) if label_key else name

    def _selected_prompt_preset_name(self) -> str:
        data = self.prompt_preset_combo.currentData()
        return str(data).strip() if data else self.prompt_preset_combo.currentText().strip()

    def _is_builtin_preset_name_reserved(self, name: str) -> bool:
        return name in self.builtin_prompt_presets or name in {
            self._display_prompt_preset_name(preset_name) for preset_name in self.builtin_prompt_presets
        }

    def _update_language_state(self, language_mode: str | None = None):
        self.ui_language_mode = language_mode or "auto"
        self.ui_language = resolve_ui_language(self.ui_language_mode)
        self.ui_text = UI_TEXT[self.ui_language]
        self.page_meta = [(self._t(title_key), self._t(desc_key)) for title_key, desc_key in self.PAGE_META_KEYS]

    def _current_ui_language_mode(self) -> str:
        if hasattr(self, "ui_language_combo"):
            value = self.ui_language_combo.currentData()
            if value:
                return str(value)
        return self.ui_language_mode

    def _populate_ui_language_combo(self, selected_mode: str | None = None):
        self.ui_language_combo.blockSignals(True)
        self.ui_language_combo.clear()
        self.ui_language_combo.addItem(self._t("language_auto"), "auto")
        self.ui_language_combo.addItem("简体中文", "zh_CN")
        self.ui_language_combo.addItem("English", "en")
        target_mode = selected_mode or self.ui_language_mode
        index = self.ui_language_combo.findData(target_mode)
        self.ui_language_combo.setCurrentIndex(index if index >= 0 else 0)
        self.ui_language_combo.blockSignals(False)

    def _snapshot_ui_state(self) -> dict:
        state = form_binding.snapshot_widget_state(self)
        state.update({
            "page_index": self.page_stack.currentIndex(),
            "reasoning_effort": self._current_reasoning_effort(),
            "thinking_mode": self._current_thinking_mode(),
            "custom_headers_text": self.custom_headers_edit.toPlainText(),
            "prompt_preset_name": self._selected_prompt_preset_name(),
            "custom_prompt_presets": dict(self.custom_prompt_presets),
            "ui_language_mode": self._current_ui_language_mode(),
            "test_input": self.test_input.toPlainText(),
            "test_output": self.test_output.toPlainText(),
            "log_output": self.log_output.toPlainText(),
        })
        return state

    def _restore_ui_state(self, state: dict):
        self.custom_prompt_presets = dict(state["custom_prompt_presets"])
        self._reload_prompt_presets()
        self._refresh_prompt_preset_combo(state["prompt_preset_name"])
        self._populate_ui_language_combo(state["ui_language_mode"])

        form_binding.restore_widget_state(self, state)
        self._set_reasoning_effort(state["reasoning_effort"])
        self._set_thinking_mode(state.get("thinking_mode", "disabled"))
        self.custom_headers_edit.setPlainText(state["custom_headers_text"])
        self.test_input.setPlainText(state["test_input"])
        self.test_output.setPlainText(state["test_output"])
        self.log_output.setPlainText(state["log_output"])
        self._sync_prompt_preset_selection(self.system_prompt_edit.toPlainText())

    def _rebuild_ui_for_language_change(self, language_mode: str, persist: bool = True):
        state = self._snapshot_ui_state()
        state["ui_language_mode"] = language_mode
        self.config.ui_language = language_mode
        self._update_language_state(language_mode)

        self._rebuilding_ui = True
        try:
            old_central = self.centralWidget()
            if old_central is not None:
                old_central.setParent(None)
                old_central.deleteLater()

            if self.tray is not None:
                self.tray.teardown()
                self.tray = None

            self.nav_buttons = []
            self._build_ui()
            self._apply_styles()
            self._create_tray_icon()
            self._load_config_to_form()
            self._restore_ui_state(state)
            self._switch_page(state["page_index"])
            if self._is_service_running():
                self._set_running_state()
            else:
                self._set_idle_state()
            self._sync_titlebar_buttons()
        finally:
            self._rebuilding_ui = False

        if persist:
            self.config_store.save(self.config)

    def _on_ui_language_changed(self):
        if self._rebuilding_ui:
            return
        language_mode = self._current_ui_language_mode()
        if language_mode == self.ui_language_mode:
            return
        self._rebuild_ui_for_language_change(language_mode)

    def _apply_window_icon(self):
        icon_path = get_app_resource_path("assets", "app.png")
        if not icon_path.exists():
            return
        icon = QIcon(str(icon_path))
        if icon.isNull():
            return
        self.setWindowIcon(icon)

    def _build_ui(self):
        self.nav_buttons = []
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
        self.page_stack.addWidget(build_launch_page(self))
        self.page_stack.addWidget(build_settings_page(self))
        self.page_stack.addWidget(build_prompt_page(self))
        self.page_stack.addWidget(build_test_page(self))
        self.page_stack.addWidget(build_log_page(self))
        main_layout.addWidget(self.page_stack, 1)

        shell.addWidget(main_panel, 1)
        root.addLayout(shell, 1)
        self.setCentralWidget(central)

        self.base_url_edit.textChanged.connect(self._sync_overview)
        self.model_type_edit.textChanged.connect(self._sync_overview)
        self.listen_port_spin.valueChanged.connect(self._sync_overview)
        self.timeout_spin.valueChanged.connect(self._sync_overview)
        self.reasoning_effort_combo.currentIndexChanged.connect(self._sync_overview)
        self.thinking_mode_combo.currentIndexChanged.connect(self._sync_overview)

    def _build_title_bar(self):
        self.title_bar = TitleBar(
            title="XUnity.AutoTranslator-SakuraLLM GUI",
            subtitle="XUnity AutoTranslator Local Bridge",
        )
        self.window_title_label = self.title_bar.title_label
        self.window_subtitle_label = self.title_bar.subtitle_label
        self.min_button = self.title_bar.min_button
        self.max_button = self.title_bar.max_button
        self.close_button = self.title_bar.close_button

        self.title_bar.minimize_requested.connect(self._minimize_window)
        self.title_bar.maximize_toggle_requested.connect(self._toggle_maximize_restore)
        self.title_bar.close_requested.connect(self._close_from_titlebar)
        self.title_bar.double_clicked.connect(self._toggle_maximize_restore)
        self.title_bar.drag_started.connect(self._on_titlebar_drag_started)
        self.title_bar.drag_moved.connect(self._on_titlebar_drag_moved)
        self.title_bar.drag_released.connect(self._on_titlebar_drag_released)
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
        subtitle = QLabel(self._t("brand_subtitle"))
        subtitle.setObjectName("brandSubtitle")
        version = QLabel(APP_VERSION)
        version.setObjectName("accentBadge")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addWidget(version)
        layout.addSpacing(14)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            (self._t("nav_launch"), "play.svg", 0),
            (self._t("nav_settings"), "settings.svg", 1),
            (self._t("nav_prompt"), "terminal.svg", 2),
            (self._t("nav_test"), "zap.svg", 3),
            (self._t("nav_log"), "list.svg", 4),
        ]
        for text, icon_name, index in nav_items:
            button = QPushButton(text)
            button.setObjectName("navButton")
            button.setCheckable(True)
            icon_path = str(get_app_resource_path("assets", "icons", icon_name))
            button.setIcon(QIcon(icon_path))
            button.setIconSize(QSize(20, 20))
            button.setMinimumHeight(52)
            button.clicked.connect(lambda checked, idx=index: self._switch_page(idx))
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()

        about = QLabel(self._t("sidebar_about"))
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

        self.status_label = QLabel()
        self.status_label.setObjectName("statusPill")
        self.status_label.setVisible(False)

        self.url_label = QLabel()
        self.url_label.setObjectName("urlValue")
        layout.addWidget(self.url_label)
        return card

    def _wrap_scroll_page(self, content: QWidget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll

    def _create_summary_card(self, title: str, target_page: int = -1):
        on_click = (lambda: self._switch_page(target_page)) if target_page >= 0 else None
        return create_summary_card(title, on_click)

    def _switch_page(self, index: int):
        self.page_stack.setCurrentIndex(index)
        
        title, desc = self.page_meta[index]
        self.page_title_label.setText(title)
        self.page_desc_label.setText(desc)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def _apply_styles(self):
        qss_path = get_app_resource_path("assets", "theme.qss")
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _dialog_stylesheet(self) -> str:
        return dialogs.dialog_stylesheet()

    def _style_dialog(self, dialog):
        dialogs.style_dialog(dialog, self, self.ui_text)

    def _message_box(
        self,
        icon: QMessageBox.Icon,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    ) -> QMessageBox.StandardButton:
        return dialogs.message_box(self, self.ui_text, icon, title, text, buttons, default_button)

    def _show_warning(self, title: str, text: str):
        dialogs.show_warning(self, self.ui_text, title, text)

    def _show_information(self, title: str, text: str):
        dialogs.show_information(self, self.ui_text, title, text)

    def _show_critical(self, title: str, text: str):
        dialogs.show_critical(self, self.ui_text, title, text)

    def _ask_yes_no(self, title: str, text: str) -> bool:
        return dialogs.ask_yes_no(self, self.ui_text, title, text)

    def _prompt_text(self, title: str, label: str, text: str = "") -> tuple[str, bool]:
        return dialogs.prompt_text(self, self.ui_text, title, label, text)

    def _install_resize_support(self):
        self._resizer = WindowResizer(self, margin=self._RESIZE_MARGIN)
        self._resizer.install()

    def _on_titlebar_drag_started(self, global_pos):
        if not self.isMaximized():
            self._drag_active = True
            self._drag_pos = global_pos
            self._window_pos = self.frameGeometry().topLeft()

    def _on_titlebar_drag_moved(self, global_pos):
        if self._drag_active and not self.isMaximized():
            delta = global_pos - self._drag_pos
            self.move(self._window_pos + delta)

    def _on_titlebar_drag_released(self):
        self._drag_active = False

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
            self.tray = None
            return

        icon = self.windowIcon()
        if icon.isNull():
            icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
            self.setWindowIcon(icon)

        self.tray = TrayController(self, self.ui_text)
        self.tray.show_requested.connect(self._show_from_tray)
        self.tray.hide_requested.connect(self.hide)
        self.tray.exit_requested.connect(self._exit_from_tray)
        if not self.tray.setup(icon):
            self.tray = None

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
        index = self.reasoning_effort_combo.findData(normalized if normalized in {"low", "medium", "high", "xhigh", "max"} else "")
        if index >= 0:
            self.reasoning_effort_combo.setCurrentIndex(index)

    def _current_reasoning_effort(self) -> str:
        value = self.reasoning_effort_combo.currentData()
        return str(value).strip() if value else ""

    def _set_thinking_mode(self, value: str):
        normalized = str(value or "").strip().lower()
        index = self.thinking_mode_combo.findData(normalized if normalized in {"enabled", "disabled"} else "disabled")
        if index >= 0:
            self.thinking_mode_combo.setCurrentIndex(index)

    def _current_thinking_mode(self) -> str:
        value = self.thinking_mode_combo.currentData()
        return str(value).strip() if value else "disabled"

    def _set_preset_status(self, label: QLabel, status: str):
        if status == "applied":
            label.setText(self._t("preset_status_applied"))
            label.setObjectName("presetStatusApplied")
        else:
            label.setText(self._t("preset_status_pending"))
            label.setObjectName("presetStatusPending")
        label.setStyleSheet(label.styleSheet())  # force QSS refresh

    def _mark_config_modified(self, *args):
        if getattr(self, "_is_loading_config", False):
            return
        self._set_preset_status(self.config_preset_status, "pending")

    def _mark_prompt_modified(self, *args):
        if getattr(self, "_is_loading_config", False):
            return
        self._set_preset_status(self.prompt_preset_status, "pending")

    def _preview_config_preset(self):
        preset_key = self.config_preset_combo.currentData()
        if not preset_key:
            return
        preset = CONFIG_PRESETS.get(preset_key)
        if not preset:
            return
        if "base_url" in preset:
            self.base_url_edit.setText(preset["base_url"])
        if "model_type" in preset:
            self.model_type_edit.setText(preset["model_type"])
        if "temperature" in preset:
            self.temperature_spin.setValue(preset["temperature"])
        if "top_p" in preset:
            self.top_p_spin.setValue(preset["top_p"])
        if "frequency_penalty" in preset:
            self.frequency_penalty_spin.setValue(preset["frequency_penalty"])
        if "thinking" in preset:
            self._set_thinking_mode(preset["thinking"])
        if "reasoning_effort" in preset:
            self._set_reasoning_effort(preset["reasoning_effort"])
        if "prompt_preset" in preset:
            prompt_name = preset["prompt_preset"]
            idx = self.prompt_preset_combo.findData(prompt_name)
            if idx >= 0:
                self.prompt_preset_combo.setCurrentIndex(idx)
        self._set_preset_status(self.config_preset_status, "pending")
        display_name = self.config_preset_combo.currentText()
        self.append_log("INFO", self._t("config_preset_applied", name=display_name))

    def _sync_overview(self):
        model = self.model_type_edit.text().strip() or self._t("not_set")
        base_url = self.base_url_edit.text().strip() or self._t("not_set")
        timeout = f"{self.timeout_spin.value()}{self._t('seconds_suffix')}"
        reasoning = self._current_reasoning_effort() or self._t("default")
        thinking = self._current_thinking_mode()
        if thinking == "enabled":
            reasoning = f"{self._t('thinking_enabled')} / {reasoning}"

        self.launch_model_value.setText(model)
        self.launch_base_url_value.setText(base_url)
        self.launch_timeout_value.setText(timeout)
        self.launch_reasoning_value.setText(reasoning)
        if hasattr(self, "launch_status_value") and self.launch_status_value is not None:
            self.launch_status_value.setText(self._t("running") if self._is_service_running() else self._t("idle"))

        if not self._is_service_running():
            try:
                self.url_label.setText(self._t("local_url", url=self._collect_config_from_form().translate_url))
            except ValueError:
                self.url_label.setText(self._t("local_url_invalid"))

    def _load_config_to_form(self):
        self._is_loading_config = True
        try:
            cfg = self.config
            self._update_language_state(cfg.ui_language)
            self.custom_prompt_presets = dict(cfg.prompt_presets or {})
            self._reload_prompt_presets()
            self._refresh_prompt_preset_combo()
            self._populate_ui_language_combo(cfg.ui_language)
            form_binding.load_from_config(self, cfg)

            headers = dict(cfg.custom_headers or {})
            self._set_thinking_mode(headers.pop("thinking", "disabled"))
            self._set_reasoning_effort(headers.pop("reasoning_effort", ""))
            self.custom_headers_edit.setPlainText(json.dumps(headers, ensure_ascii=False, indent=2) if headers else "{}")
            self._sync_prompt_preset_selection(cfg.system_prompt)
            self.url_label.setText(self._t("local_url", url=cfg.translate_url))
            self._sync_overview()
            self._set_preset_status(self.config_preset_status, "applied")
            self._set_preset_status(self.prompt_preset_status, "applied")
            self._validate_custom_headers()
        finally:
            self._is_loading_config = False

    def apply_prompt_preset(self):
        preset_name = self._selected_prompt_preset_name()
        prompt = self.prompt_presets.get(preset_name, DEFAULT_SYSTEM_PROMPT)
        self.system_prompt_edit.setPlainText(prompt)
        self._set_preset_status(self.prompt_preset_status, "pending")
        self.append_log("INFO", self._t("preset_applied", name=self._display_prompt_preset_name(preset_name)))

    def _preview_prompt_preset(self):
        preset_name = self._selected_prompt_preset_name()
        if preset_name in self.prompt_presets:
            self.system_prompt_edit.setPlainText(self.prompt_presets[preset_name])
        self._set_preset_status(self.prompt_preset_status, "pending")

    def _reload_prompt_presets(self):
        self.prompt_presets = dict(self.builtin_prompt_presets)
        self.prompt_presets.update(self.custom_prompt_presets)

    def _refresh_prompt_preset_combo(self, selected_name: str | None = None):
        current_name = selected_name or self._selected_prompt_preset_name()
        self.prompt_preset_combo.blockSignals(True)
        self.prompt_preset_combo.clear()
        for preset_name in self.prompt_presets:
            self.prompt_preset_combo.addItem(self._display_prompt_preset_name(preset_name), preset_name)
        if current_name in self.prompt_presets:
            index = self.prompt_preset_combo.findData(current_name)
            if index >= 0:
                self.prompt_preset_combo.setCurrentIndex(index)
        elif self.prompt_preset_combo.count():
            self.prompt_preset_combo.setCurrentIndex(0)
        self.prompt_preset_combo.blockSignals(False)

    def _sync_prompt_preset_selection(self, prompt: str):
        target = (prompt or "").strip()
        for name, preset in self.prompt_presets.items():
            if preset.strip() == target:
                index = self.prompt_preset_combo.findData(name)
                if index >= 0:
                    self.prompt_preset_combo.setCurrentIndex(index)
                return

    def _persist_custom_prompt_presets(self):
        self.config.prompt_presets = dict(self.custom_prompt_presets)
        self.config.ui_language = self._current_ui_language_mode()
        self.config_store.save(self.config)

    def save_custom_prompt_preset(self):
        prompt = self.system_prompt_edit.toPlainText().strip()
        if not prompt:
            self._show_warning(self._t("notice"), self._t("system_prompt_required"))
            return

        name, ok = self._prompt_text(self._t("save_custom_prompt_title"), self._t("preset_name_prompt"))
        if not ok:
            return
        name = name.strip()
        if not name:
            self._show_warning(self._t("notice"), self._t("preset_name_required"))
            return
        if self._is_builtin_preset_name_reserved(name):
            self._show_warning(self._t("notice"), self._t("builtin_preset_reserved"))
            return
        if name in self.custom_prompt_presets:
            if not self._ask_yes_no(self._t("overwrite_confirmation"), self._t("custom_preset_exists", name=name)):
                return

        self.custom_prompt_presets[name] = prompt
        self._persist_custom_prompt_presets()
        self._reload_prompt_presets()
        self._refresh_prompt_preset_combo(name)
        self.append_log("INFO", self._t("custom_preset_saved", name=name))

    def rename_custom_prompt_preset(self):
        old_name = self._selected_prompt_preset_name()
        if not old_name:
            return
        if old_name not in self.custom_prompt_presets:
            self._show_information(self._t("notice"), self._t("builtin_preset_rename_blocked"))
            return

        new_name, ok = self._prompt_text(self._t("rename_custom_prompt_title"), self._t("new_preset_name_prompt"), old_name)
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            self._show_warning(self._t("notice"), self._t("preset_name_required"))
            return
        if new_name == old_name:
            return
        if self._is_builtin_preset_name_reserved(new_name):
            self._show_warning(self._t("notice"), self._t("builtin_preset_reserved"))
            return
        if new_name in self.custom_prompt_presets:
            if not self._ask_yes_no(self._t("overwrite_confirmation"), self._t("custom_preset_exists", name=new_name)):
                return

        prompt = self.custom_prompt_presets.pop(old_name)
        self.custom_prompt_presets[new_name] = prompt
        self._persist_custom_prompt_presets()
        self._reload_prompt_presets()
        self._refresh_prompt_preset_combo(new_name)
        self.append_log("INFO", self._t("custom_preset_renamed", old_name=old_name, new_name=new_name))

    def delete_custom_prompt_preset(self):
        name = self._selected_prompt_preset_name()
        if not name:
            return
        if name not in self.custom_prompt_presets:
            self._show_information(self._t("notice"), self._t("builtin_preset_delete_blocked"))
            return

        if not self._ask_yes_no(self._t("delete_confirmation"), self._t("custom_preset_delete_confirm", name=name)):
            return

        self.custom_prompt_presets.pop(name, None)
        self._persist_custom_prompt_presets()
        self._reload_prompt_presets()
        self._refresh_prompt_preset_combo()
        self.append_log("INFO", self._t("custom_preset_deleted", name=name))

    def _parse_custom_headers(self) -> dict:
        raw = self.custom_headers_edit.toPlainText().strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(self._t("custom_headers_invalid", msg=e.msg))
        if not isinstance(data, dict):
            raise ValueError(self._t("custom_headers_must_be_object"))
        return {str(k): str(v) for k, v in data.items()}

    def _collect_config_from_form(self) -> AppConfig:
        headers = self._parse_custom_headers()
        reasoning_effort = self._current_reasoning_effort()
        headers.pop("reasoning_effort", None)
        if reasoning_effort:
            headers["reasoning_effort"] = reasoning_effort
        thinking_mode = self._current_thinking_mode()
        headers.pop("thinking", None)
        if thinking_mode == "enabled":
            headers["thinking"] = thinking_mode

        fields = form_binding.collect_to_dict(self)
        for key in ("base_url", "api_key", "model_type", "system_prompt"):
            fields[key] = fields[key].strip()

        return AppConfig(
            custom_headers=headers,
            prompt_presets=dict(self.custom_prompt_presets),
            ui_language=self._current_ui_language_mode(),
            **fields,
        )

    def _is_service_running(self) -> bool:
        return self.service_thread is not None and self.service_thread.isRunning()

    def _set_idle_state(self):
        self.status_label.setText(self._t("status_not_started"))
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._update_status_style("idle")
        self._sync_overview()

    def _set_running_state(self):
        self.status_label.setText(self._t("status_running"))
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.url_label.setText(self._t("local_url", url=self.config.translate_url))
        self._update_status_style("running")
        self._sync_overview()

    def _set_starting_state(self):
        self.status_label.setText(self._t("status_starting"))
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self._update_status_style("busy")

    def _set_stopping_state(self):
        self.status_label.setText(self._t("status_stopping"))
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self._update_status_style("busy")

    def append_log(self, level: str, message: str):
        entry = (level, message)
        self.log_entries.append(entry)
        if len(self.log_entries) > 5000:
            self.log_entries.pop(0)

        filter_text = ""
        if hasattr(self, "log_filter_edit") and self.log_filter_edit is not None:
            filter_text = self.log_filter_edit.text().strip().lower()

        if filter_text:
            if filter_text not in message.lower() and filter_text not in level.lower():
                return

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
            self._show_warning(self._t("notice"), str(e))
            return False

        if not config.base_url or not config.model_type:
            self._show_warning(self._t("notice"), self._t("base_url_and_model_required"))
            return False
        if not config.system_prompt.strip():
            self._show_warning(self._t("notice"), self._t("system_prompt_required"))
            return False

        self.config = config
        self.config_store.save(config)
        self._load_config_to_form()
        if self._is_service_running():
            self.service_thread.apply_runtime_config(config)
            self._set_running_state()
        else:
            self._set_idle_state()
        
        self._set_preset_status(self.config_preset_status, "applied")
        self._set_preset_status(self.prompt_preset_status, "applied")
        
        self.append_log("INFO", self._t("config_saved"))
        return True

    def import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self._t("import_config"), str(Path.cwd()), self._t("json_file_filter"))
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                imported = AppConfig.from_dict(json.load(f))
        except Exception as e:
            self._show_critical(self._t("import_failed"), str(e))
            return
        previous_language = self.ui_language
        self.config = imported
        self._load_config_to_form()
        if resolve_ui_language(self.config.ui_language) != previous_language:
            self._rebuild_ui_for_language_change(self.config.ui_language, persist=False)
        self._set_idle_state() if not self._is_service_running() else self._set_running_state()
        self.append_log("INFO", self._t("config_imported", file_path=file_path))

    def export_config(self):
        try:
            config = self._collect_config_from_form()
        except ValueError as e:
            self._show_warning(self._t("notice"), str(e))
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self._t("export_config"),
            str(Path.cwd() / "config-export.json"),
            self._t("json_file_filter"),
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._show_critical(self._t("export_failed"), str(e))
            return
        self.append_log("INFO", self._t("config_exported", file_path=file_path))

    def reset_defaults(self):
        previous_language = self.ui_language
        self.config = AppConfig()
        self._load_config_to_form()
        if resolve_ui_language(self.config.ui_language) != previous_language:
            self._rebuild_ui_for_language_change(self.config.ui_language, persist=False)
        self._set_idle_state()
        self.append_log("INFO", self._t("config_restored"))

    def start_service(self):
        if self._is_service_running():
            return
        if not self.save_config():
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
        if not self.service_thread.wait(3000):
            self.append_log("WARN", self._t("stop_force_terminated"))
            self.service_thread.terminate()
            self.service_thread.wait(1000)

    def test_translation(self):
        text = self.test_input.toPlainText().strip()
        if not text:
            self._show_information(self._t("notice"), self._t("enter_test_text_first"))
            return
        if getattr(self, "_test_thread", None) is not None and self._test_thread.isRunning():
            return
        self.test_button.setEnabled(False)
        self.test_output.setPlainText(self._t("requesting"))
        config = self._collect_config_from_form()
        self._test_thread = TestTranslationThread(
            config.translate_url, text, config.request_timeout
        )
        self._test_thread.finished_ok.connect(self._on_test_done)
        self._test_thread.finished_err.connect(self._on_test_done)
        self._test_thread.finished.connect(self._on_test_thread_finished)
        self._test_thread.start()

    def _on_test_done(self, message: str):
        self.test_output.setPlainText(message)

    def _on_test_thread_finished(self):
        self.test_button.setEnabled(True)
        if self._test_thread is not None:
            self._test_thread.deleteLater()
            self._test_thread = None

    def clear_logs(self):
        self.log_entries.clear()
        self.log_output.clear()

    def _on_service_started(self):
        self._set_running_state()
        self.append_log("INFO", self._t("service_started_success"))
        if self.tray is not None:
            self.tray.show_message("SakuraLLM GUI", self._t("service_started_balloon"))
        self._start_backend_health_check()

    def _start_backend_health_check(self):
        existing = getattr(self, "_health_thread", None)
        if existing is not None and existing.isRunning():
            return
        self._health_thread = HealthCheckThread(self.config.base_url, timeout=5)
        self._health_thread.ok.connect(
            lambda: self.append_log("INFO", self._t("backend_reachable", url=self.config.base_url))
        )
        self._health_thread.failed.connect(
            lambda msg: self.append_log("WARN", self._t("backend_unreachable", url=self.config.base_url, msg=msg))
        )
        self._health_thread.finished.connect(self._on_health_finished)
        self._health_thread.start()

    def _on_health_finished(self):
        if self._health_thread is not None:
            self._health_thread.deleteLater()
            self._health_thread = None

    def _on_service_stopped(self):
        self._set_idle_state()
        if self.service_thread is not None:
            self.service_thread.deleteLater()
            self.service_thread = None

    def _handle_service_error(self, message: str):
        self.append_log("ERROR", message)
        self._show_critical(self._t("service_error"), message)
        self._set_idle_state()

    def closeEvent(self, event: QCloseEvent):
        if self.minimize_to_tray and not self.force_exit and self.tray is not None:
            event.ignore()
            self.hide()
            self.tray.show_message("SakuraLLM GUI", self._t("minimized_to_tray"))
            return

        app = QApplication.instance()
        if app is not None and getattr(self, "_resizer", None) is not None:
            self._resizer.uninstall()

        self.stop_service()
        if self.service_thread is not None:
            self.service_thread.wait(2000)
        for attr in ("_test_thread", "_health_thread"):
            t = getattr(self, attr, None)
            if t is not None and t.isRunning():
                t.wait(1000)
        if self.tray is not None:
            self.tray.teardown()
            self.tray = None
            
        super().closeEvent(event)
        
        if app is not None:
            app.quit()

    def _update_status_style(self, state: str):
        self.status_label.setProperty("state", state)
        if hasattr(self, "launch_status_value") and self.launch_status_value is not None:
            self.launch_status_value.setProperty("state", state)
        
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        if hasattr(self, "launch_status_value") and self.launch_status_value is not None:
            self.launch_status_value.style().unpolish(self.launch_status_value)
            self.launch_status_value.style().polish(self.launch_status_value)

    def _refresh_log_output(self):
        self.log_output.clear()
        filter_text = self.log_filter_edit.text().strip().lower()
        
        self.log_output.blockSignals(True)
        cursor = self.log_output.textCursor()
        cursor.beginEditBlock()
        for level, message in self.log_entries:
            if filter_text and filter_text not in message.lower() and filter_text not in level.lower():
                continue
            color = {
                "INFO": QColor("#dcdcdc"),
                "WARN": QColor("#f1c40f"),
                "ERROR": QColor("#ff6b6b"),
            }.get(level, QColor("#dcdcdc"))
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            cursor.insertText(f"[{level}] {message}\n", fmt)
        cursor.endEditBlock()
        self.log_output.setTextCursor(cursor)
        self.log_output.ensureCursorVisible()
        self.log_output.blockSignals(False)

    def copy_logs(self):
        text = self.log_output.toPlainText()
        QApplication.clipboard().setText(text)
        self.append_log("INFO", self._t("logs_copied"))

    def _validate_custom_headers(self):
        if not hasattr(self, "custom_headers_edit") or not hasattr(self, "headers_error_label"):
            return
        raw = self.custom_headers_edit.toPlainText().strip()
        if not raw:
            self.headers_error_label.setText("")
            return
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                self.headers_error_label.setText(self._t("custom_headers_must_be_object"))
                self.headers_error_label.setStyleSheet("color: #ff6b6b; font-size: 13px; font-weight: 600; margin-top: 4px;")
            else:
                self.headers_error_label.setText(self._t("json_valid"))
                self.headers_error_label.setStyleSheet("color: #2ecc71; font-size: 13px; font-weight: 600; margin-top: 4px;")
        except json.JSONDecodeError as e:
            self.headers_error_label.setText(self._t("custom_headers_invalid", msg=e.msg))
            self.headers_error_label.setStyleSheet("color: #ff6b6b; font-size: 13px; font-weight: 600; margin-top: 4px;")
