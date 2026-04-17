import json
import sys
from pathlib import Path

import requests
from PySide6.QtCore import QLocale, QPoint, QSize, QThread, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QPainter, QPen, QTextCharFormat, QTextCursor
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
    QInputDialog,
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


def get_app_resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir.joinpath(*parts)


UI_TEXT = {
    "zh_CN": {
        "page_launch_title": "启动器",
        "page_launch_desc": "启动本地翻译服务，并查看当前运行状态。",
        "page_settings_title": "配置中心",
        "page_settings_desc": "编辑连接参数、模型参数和兼容设置。",
        "page_prompt_title": "提示词与请求头",
        "page_prompt_desc": "管理系统提示词、预设和额外请求头。",
        "page_test_title": "测试翻译",
        "page_test_desc": "直接调用本地 /translate 接口做端到端验证。",
        "page_log_title": "运行日志",
        "page_log_desc": "查看服务日志、错误信息和翻译输出。",
        "brand_subtitle": "本地翻译启动器",
        "nav_launch": "启动",
        "nav_settings": "配置",
        "nav_prompt": "提示词",
        "nav_test": "测试",
        "nav_log": "日志",
        "sidebar_about": "兼容 XUnity.AutoTranslator\n支持本地 Flask / gevent 服务",
        "quick_log": "运行日志",
        "save_config": "保存配置",
        "import_config": "导入配置",
        "export_config": "导出配置",
        "reset_defaults": "恢复默认",
        "local_service_title": "本地翻译服务",
        "local_service_desc": "保持与 XUnity.AutoTranslator 的本地 HTTP 调用方式兼容，快速启动、停止并检查当前配置摘要。",
        "config_center": "配置中心",
        "translation_test": "翻译测试",
        "start_service": "启动服务",
        "stop_service": "停止服务",
        "quick_status": "快速状态",
        "idle": "待机",
        "quick_status_desc": "点击右侧主按钮即可启动或停止本地服务。",
        "current_model": "当前模型",
        "reasoning_effort": "深度思考",
        "upstream_url": "上游地址",
        "request_timeout": "请求超时",
        "param_temperature": "温度 (temperature)",
        "param_top_p": "Top-P 采样 (top_p)",
        "param_max_tokens": "最大生成长度 (max_tokens)",
        "param_frequency_penalty": "频率惩罚 (frequency_penalty)",
        "param_repeat_count": "重复检测阈值 (repeat_count)",
        "param_max_retries": "最大重试次数 (max_retries)",
        "param_max_concurrency": "最大并发数 (max_concurrency)",
        "usage_tips": "使用提示",
        "usage_tips_desc": "首次使用建议先在“配置中心”填写 Base URL、模型名和端口；如果要调整提示词或额外请求体字段，可在“提示词”页继续设置。",
        "quick_steps": "快速流程",
        "quick_steps_desc": "1. 填写连接参数\n2. 选择深度思考与模型参数\n3. 保存配置\n4. 启动服务\n5. 到测试页验证输出",
        "connection_settings": "连接配置",
        "default": "默认",
        "model_name": "模型名",
        "listen_port": "监听端口",
        "timeout_seconds": "超时(秒)",
        "newline_mode": "换行模式",
        "reasoning_effort_hint": "会写入请求体中的 reasoning_effort；默认表示不额外传这个字段。",
        "model_parameters": "模型参数",
        "compatibility_notes": "兼容性说明",
        "compatibility_notes_desc": "本地接口仍保持 http://127.0.0.1:<端口>/translate 形式。若修改监听端口，请同步更新 XUnity.AutoTranslator 的 Custom.Url。",
        "system_prompt": "系统提示词",
        "apply_preset": "应用预设",
        "save_custom_preset": "保存自定义预设",
        "rename_custom_preset": "重命名自定义预设",
        "delete_custom_preset": "删除自定义预设",
        "prompt_preset": "提示词预设",
        "ui_language": "界面语言",
        "language_auto": "跟随系统",
        "custom_headers": "自定义请求头(JSON)",
        "custom_headers_hint": "用于补充额外请求头。reasoning_effort 已提供单独菜单，一般不需要再手写在这里。",
        "translation_test_hint": "输入文本后会直接请求本地 /translate 接口，用于验证 GUI → 本地服务 → 上游 API 整条链路。",
        "translation_test_placeholder": "输入测试文本",
        "clear_logs": "清空日志",
        "tray_show_window": "显示窗口",
        "tray_hide_window": "隐藏窗口",
        "tray_exit": "退出",
        "not_set": "未设置",
        "seconds_suffix": " 秒",
        "running": "运行中",
        "local_url": "本地地址: {url}",
        "local_url_invalid": "本地地址: 配置无效",
        "preset_applied": "已应用提示词预设: {name}",
        "notice": "提示",
        "system_prompt_required": "系统提示词不能为空。",
        "save_custom_prompt_title": "保存自定义提示词",
        "preset_name_prompt": "请输入预设名称：",
        "preset_name_required": "预设名称不能为空。",
        "builtin_preset_reserved": "该名称已被内置预设占用，请换一个名称。",
        "overwrite_confirmation": "覆盖确认",
        "custom_preset_exists": "自定义预设“{name}”已存在，是否覆盖？",
        "custom_preset_saved": "已保存自定义提示词预设: {name}",
        "builtin_preset_rename_blocked": "当前选择的是内置预设，不能重命名。",
        "rename_custom_prompt_title": "重命名自定义提示词",
        "new_preset_name_prompt": "请输入新的预设名称：",
        "custom_preset_renamed": "已重命名自定义提示词预设: {old_name} -> {new_name}",
        "builtin_preset_delete_blocked": "当前选择的是内置预设，不能删除。",
        "delete_confirmation": "删除确认",
        "custom_preset_delete_confirm": "确定删除自定义预设“{name}”吗？",
        "custom_preset_deleted": "已删除自定义提示词预设: {name}",
        "custom_headers_invalid": "自定义请求头不是有效 JSON：{msg}",
        "custom_headers_must_be_object": "自定义请求头必须是 JSON 对象。",
        "status_not_started": "状态: 未启动",
        "status_running": "状态: 运行中",
        "status_starting": "状态: 启动中",
        "status_stopping": "状态: 停止中",
        "base_url_and_model_required": "Base URL 和 模型名不能为空。",
        "config_saved": "配置已保存",
        "import_failed": "导入失败",
        "config_imported": "已导入配置: {file_path}",
        "export_failed": "导出失败",
        "config_exported": "已导出配置: {file_path}",
        "config_restored": "已恢复默认配置",
        "port_in_use": "端口占用",
        "port_in_use_message": "127.0.0.1:{port} 已被占用。",
        "port_in_use_log": "端口已占用: {port}",
        "enter_test_text_first": "请先输入测试文本。",
        "requesting": "请求中...",
        "service_started_success": "服务启动成功",
        "service_started_balloon": "本地翻译服务已启动。",
        "service_error": "服务错误",
        "minimized_to_tray": "程序已最小化到托盘。",
        "json_file_filter": "JSON Files (*.json)",
        "builtin_sakura_preset": "sakura预设",
        "dialog_ok": "确定",
        "dialog_cancel": "取消",
        "dialog_yes": "是",
        "dialog_no": "否",
    },
    "en": {
        "page_launch_title": "Launcher",
        "page_launch_desc": "Start the local translation service and view the current status.",
        "page_settings_title": "Settings",
        "page_settings_desc": "Edit connection parameters, model parameters, and compatibility settings.",
        "page_prompt_title": "Prompts & Headers",
        "page_prompt_desc": "Manage system prompts, presets, and extra request headers.",
        "page_test_title": "Translation Test",
        "page_test_desc": "Call the local /translate endpoint directly for end-to-end validation.",
        "page_log_title": "Logs",
        "page_log_desc": "View service logs, errors, and translation output.",
        "brand_subtitle": "Local Translator Launcher",
        "nav_launch": "Launch",
        "nav_settings": "Settings",
        "nav_prompt": "Prompts",
        "nav_test": "Test",
        "nav_log": "Logs",
        "sidebar_about": "Compatible with XUnity.AutoTranslator\nSupports local Flask / gevent service",
        "quick_log": "Logs",
        "save_config": "Save Config",
        "import_config": "Import Config",
        "export_config": "Export Config",
        "reset_defaults": "Reset Defaults",
        "local_service_title": "Local Translation Service",
        "local_service_desc": "Keep the local HTTP workflow compatible with XUnity.AutoTranslator. Start, stop, and inspect the current configuration summary quickly.",
        "config_center": "Settings",
        "translation_test": "Translation Test",
        "start_service": "Start Service",
        "stop_service": "Stop Service",
        "quick_status": "Quick Status",
        "idle": "Idle",
        "quick_status_desc": "Use the main buttons on the right to start or stop the local service.",
        "current_model": "Current Model",
        "reasoning_effort": "Reasoning Effort",
        "upstream_url": "Upstream URL",
        "request_timeout": "Request Timeout",
        "param_temperature": "Temperature",
        "param_top_p": "Top-P Sampling",
        "param_max_tokens": "Max Tokens",
        "param_frequency_penalty": "Frequency Penalty",
        "param_repeat_count": "Repeat Detection Threshold",
        "param_max_retries": "Max Retries",
        "param_max_concurrency": "Max Concurrency",
        "usage_tips": "Usage Tips",
        "usage_tips_desc": "For first-time use, fill in Base URL, model name, and port in Settings first. If you need to adjust prompts or extra request fields, continue in the Prompts page.",
        "quick_steps": "Quick Steps",
        "quick_steps_desc": "1. Fill in connection parameters\n2. Choose reasoning effort and model parameters\n3. Save the configuration\n4. Start the service\n5. Validate output in the test page",
        "connection_settings": "Connection Settings",
        "default": "Default",
        "model_name": "Model Name",
        "listen_port": "Listen Port",
        "timeout_seconds": "Timeout (s)",
        "newline_mode": "Newline Mode",
        "reasoning_effort_hint": "This writes reasoning_effort into the request body. Default means the field is omitted.",
        "model_parameters": "Model Parameters",
        "compatibility_notes": "Compatibility Notes",
        "compatibility_notes_desc": "The local endpoint remains in the form http://127.0.0.1:<port>/translate. If you change the listen port, update XUnity.AutoTranslator Custom.Url as well.",
        "system_prompt": "System Prompt",
        "apply_preset": "Apply Preset",
        "save_custom_preset": "Save Custom Preset",
        "rename_custom_preset": "Rename Custom Preset",
        "delete_custom_preset": "Delete Custom Preset",
        "prompt_preset": "Prompt Preset",
        "ui_language": "UI Language",
        "language_auto": "Auto",
        "custom_headers": "Custom Headers (JSON)",
        "custom_headers_hint": "Use this to add extra request headers. reasoning_effort already has a dedicated control, so you usually do not need to write it here.",
        "translation_test_hint": "After entering text, the GUI calls the local /translate endpoint directly to verify the full chain: GUI -> local service -> upstream API.",
        "translation_test_placeholder": "Enter test text",
        "clear_logs": "Clear Logs",
        "tray_show_window": "Show Window",
        "tray_hide_window": "Hide Window",
        "tray_exit": "Exit",
        "not_set": "Not Set",
        "seconds_suffix": " s",
        "running": "Running",
        "local_url": "Local URL: {url}",
        "local_url_invalid": "Local URL: Invalid configuration",
        "preset_applied": "Applied prompt preset: {name}",
        "notice": "Notice",
        "system_prompt_required": "System prompt cannot be empty.",
        "save_custom_prompt_title": "Save Custom Prompt",
        "preset_name_prompt": "Enter a preset name:",
        "preset_name_required": "Preset name cannot be empty.",
        "builtin_preset_reserved": "This name is reserved by a built-in preset. Please choose another name.",
        "overwrite_confirmation": "Overwrite Confirmation",
        "custom_preset_exists": "Custom preset \"{name}\" already exists. Overwrite it?",
        "custom_preset_saved": "Saved custom prompt preset: {name}",
        "builtin_preset_rename_blocked": "The current selection is a built-in preset and cannot be renamed.",
        "rename_custom_prompt_title": "Rename Custom Prompt",
        "new_preset_name_prompt": "Enter a new preset name:",
        "custom_preset_renamed": "Renamed custom prompt preset: {old_name} -> {new_name}",
        "builtin_preset_delete_blocked": "The current selection is a built-in preset and cannot be deleted.",
        "delete_confirmation": "Delete Confirmation",
        "custom_preset_delete_confirm": "Delete custom preset \"{name}\"?",
        "custom_preset_deleted": "Deleted custom prompt preset: {name}",
        "custom_headers_invalid": "Custom headers are not valid JSON: {msg}",
        "custom_headers_must_be_object": "Custom headers must be a JSON object.",
        "status_not_started": "Status: Not Started",
        "status_running": "Status: Running",
        "status_starting": "Status: Starting",
        "status_stopping": "Status: Stopping",
        "base_url_and_model_required": "Base URL and model name cannot be empty.",
        "config_saved": "Configuration saved",
        "import_failed": "Import Failed",
        "config_imported": "Imported configuration: {file_path}",
        "export_failed": "Export Failed",
        "config_exported": "Exported configuration: {file_path}",
        "config_restored": "Default configuration restored",
        "port_in_use": "Port In Use",
        "port_in_use_message": "127.0.0.1:{port} is already in use.",
        "port_in_use_log": "Port already in use: {port}",
        "enter_test_text_first": "Please enter test text first.",
        "requesting": "Requesting...",
        "service_started_success": "Service started successfully",
        "service_started_balloon": "Local translation service started.",
        "service_error": "Service Error",
        "minimized_to_tray": "The app was minimized to the system tray.",
        "json_file_filter": "JSON Files (*.json)",
        "builtin_sakura_preset": "Sakura Default",
        "dialog_ok": "OK",
        "dialog_cancel": "Cancel",
        "dialog_yes": "Yes",
        "dialog_no": "No",
    },
}

BUILTIN_PROMPT_PRESET_NAMES = {
    "sakura预设": "builtin_sakura_preset",
}

APP_VERSION = "v1.0.2"


def detect_ui_language() -> str:
    return "zh_CN" if QLocale.system().language() == QLocale.Language.Chinese else "en"


def resolve_ui_language(language_mode: str) -> str:
    return detect_ui_language() if language_mode == "auto" else language_mode


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
        started = False
        try:
            self.service.start()
            self.started_ok.emit()
            started = True
            self.service.serve_forever()
        except Exception as e:
            self.failed.emit(str(e))
            return
        finally:
            if started:
                self.stopped_ok.emit()

    def stop_service(self):
        if self.service:
            self.service.stop()


class TestTranslationThread(QThread):
    finished_ok = Signal(str)
    finished_err = Signal(str)

    def __init__(self, url: str, text: str, timeout: int):
        super().__init__()
        self.url = url
        self.text = text
        self.timeout = timeout

    def run(self):
        try:
            response = requests.get(
                self.url,
                params={"text": self.text},
                timeout=self.timeout,
            )
            if response.ok:
                self.finished_ok.emit(response.text)
            else:
                self.finished_ok.emit(f"HTTP {response.status_code}\n{response.text}")
        except Exception as e:
            self.finished_err.emit(str(e))


class HealthCheckThread(QThread):
    ok = Signal()
    failed = Signal(str)

    def __init__(self, base_url: str, timeout: int = 5):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def run(self):
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=self.timeout)
            if response.ok:
                self.ok.emit()
            else:
                self.failed.emit(f"HTTP {response.status_code}")
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    PAGE_META_KEYS = [
        ("page_launch_title", "page_launch_desc"),
        ("page_settings_title", "page_settings_desc"),
        ("page_prompt_title", "page_prompt_desc"),
        ("page_test_title", "page_test_desc"),
        ("page_log_title", "page_log_desc"),
    ]

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
        self.tray_icon = None
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

        self._build_ui()
        self._apply_styles()
        self._create_tray_icon()
        self._load_config_to_form()
        self._set_idle_state()
        self._switch_page(0)
        self._sync_titlebar_buttons()

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
        return {
            "page_index": self.page_stack.currentIndex(),
            "base_url": self.base_url_edit.text(),
            "api_key": self.api_key_edit.text(),
            "model_type": self.model_type_edit.text(),
            "listen_port": self.listen_port_spin.value(),
            "timeout": self.timeout_spin.value(),
            "newline_mode": self.newline_mode_combo.currentText(),
            "reasoning_effort": self._current_reasoning_effort(),
            "temperature": self.temperature_spin.value(),
            "top_p": self.top_p_spin.value(),
            "max_tokens": self.max_tokens_spin.value(),
            "frequency_penalty": self.frequency_penalty_spin.value(),
            "repeat_count": self.repeat_count_spin.value(),
            "max_retries": self.max_retries_spin.value(),
            "max_concurrency": self.max_concurrency_spin.value(),
            "custom_headers_text": self.custom_headers_edit.toPlainText(),
            "system_prompt": self.system_prompt_edit.toPlainText(),
            "prompt_preset_name": self._selected_prompt_preset_name(),
            "custom_prompt_presets": dict(self.custom_prompt_presets),
            "ui_language_mode": self._current_ui_language_mode(),
            "test_input": self.test_input.toPlainText(),
            "test_output": self.test_output.toPlainText(),
            "log_output": self.log_output.toPlainText(),
        }

    def _restore_ui_state(self, state: dict):
        self.custom_prompt_presets = dict(state["custom_prompt_presets"])
        self._reload_prompt_presets()
        self._refresh_prompt_preset_combo(state["prompt_preset_name"])
        self._populate_ui_language_combo(state["ui_language_mode"])

        self.base_url_edit.setText(state["base_url"])
        self.api_key_edit.setText(state["api_key"])
        self.model_type_edit.setText(state["model_type"])
        self.listen_port_spin.setValue(state["listen_port"])
        self.timeout_spin.setValue(state["timeout"])
        self.newline_mode_combo.setCurrentText(state["newline_mode"])
        self._set_reasoning_effort(state["reasoning_effort"])
        self.temperature_spin.setValue(state["temperature"])
        self.top_p_spin.setValue(state["top_p"])
        self.max_tokens_spin.setValue(state["max_tokens"])
        self.frequency_penalty_spin.setValue(state["frequency_penalty"])
        self.repeat_count_spin.setValue(state["repeat_count"])
        self.max_retries_spin.setValue(state["max_retries"])
        self.max_concurrency_spin.setValue(state.get("max_concurrency", 2))
        self.custom_headers_edit.setPlainText(state["custom_headers_text"])
        self.system_prompt_edit.setPlainText(state["system_prompt"])
        self.test_input.setPlainText(state["test_input"])
        self.test_output.setPlainText(state["test_output"])
        self.log_output.setPlainText(state["log_output"])
        self._sync_prompt_preset_selection(state["system_prompt"])

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

            if self.tray_icon is not None:
                self.tray_icon.hide()
                self.tray_icon.deleteLater()
                self.tray_icon = None

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
            (self._t("nav_launch"), QStyle.StandardPixmap.SP_MediaPlay, 0),
            (self._t("nav_settings"), QStyle.StandardPixmap.SP_FileDialogDetailedView, 1),
            (self._t("nav_prompt"), QStyle.StandardPixmap.SP_FileDialogContentsView, 2),
            (self._t("nav_test"), QStyle.StandardPixmap.SP_DialogApplyButton, 3),
            (self._t("nav_log"), QStyle.StandardPixmap.SP_FileDialogInfoView, 4),
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

        self.quick_log_button = QPushButton(self._t("quick_log"))
        self.quick_log_button.setObjectName("ghostButton")
        self.quick_log_button.clicked.connect(lambda: self._switch_page(4))
        layout.addWidget(self.quick_log_button, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        right_box = QVBoxLayout()
        right_box.setSpacing(10)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.save_button = QPushButton(self._t("save_config"))
        self.import_button = QPushButton(self._t("import_config"))
        self.export_button = QPushButton(self._t("export_config"))
        self.reset_button = QPushButton(self._t("reset_defaults"))
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

        title = QLabel(self._t("local_service_title"))
        title.setObjectName("sectionTitle")
        desc = QLabel(self._t("local_service_desc"))
        desc.setObjectName("mutedText")
        desc.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(desc)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)

        settings_jump = QPushButton(self._t("config_center"))
        settings_jump.setObjectName("ghostButton")
        settings_jump.clicked.connect(lambda: self._switch_page(1))
        test_jump = QPushButton(self._t("translation_test"))
        test_jump.setObjectName("ghostButton")
        test_jump.clicked.connect(lambda: self._switch_page(3))

        self.start_button = QPushButton(self._t("start_service"))
        self.start_button.setObjectName("primaryButton")
        self.stop_button = QPushButton(self._t("stop_service"))
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
        side_title = QLabel(self._t("quick_status"))
        side_title.setObjectName("summaryTitle")
        self.launch_status_value = QLabel(self._t("idle"))
        self.launch_status_value.setObjectName("heroStatus")
        side_desc = QLabel(self._t("quick_status_desc"))
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

        model_card, self.launch_model_value = self._create_summary_card(self._t("current_model"))
        reasoning_card, self.launch_reasoning_value = self._create_summary_card(self._t("reasoning_effort"))
        base_url_card, self.launch_base_url_value = self._create_summary_card(self._t("upstream_url"))
        timeout_card, self.launch_timeout_value = self._create_summary_card(self._t("request_timeout"))

        summary_grid.addWidget(model_card, 0, 0)
        summary_grid.addWidget(reasoning_card, 0, 1)
        summary_grid.addWidget(base_url_card, 1, 0)
        summary_grid.addWidget(timeout_card, 1, 1)
        layout.addLayout(summary_grid)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        hints_group = QGroupBox(self._t("usage_tips"))
        hint_layout = QVBoxLayout(hints_group)
        hint = QLabel(self._t("usage_tips_desc"))
        hint.setWordWrap(True)
        hint.setObjectName("mutedText")
        hint_layout.addWidget(hint)

        steps_group = QGroupBox(self._t("quick_steps"))
        steps_layout = QVBoxLayout(steps_group)
        steps = QLabel(self._t("quick_steps_desc"))
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

        connection_group = QGroupBox(self._t("connection_settings"))
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
        self.ui_language_combo = QComboBox()
        self._populate_ui_language_combo(self.ui_language_mode)
        self.ui_language_combo.currentIndexChanged.connect(self._on_ui_language_changed)
        self.reasoning_effort_combo = QComboBox()
        self.reasoning_effort_combo.addItem(self._t("default"), "")
        self.reasoning_effort_combo.addItem("low", "low")
        self.reasoning_effort_combo.addItem("medium", "medium")
        self.reasoning_effort_combo.addItem("high", "high")

        connection_form.addRow(self._t("ui_language"), self.ui_language_combo)
        connection_form.addRow("Base URL", self.base_url_edit)
        connection_form.addRow("API Key", self.api_key_edit)
        connection_form.addRow(self._t("model_name"), self.model_type_edit)
        connection_form.addRow(self._t("listen_port"), self.listen_port_spin)
        connection_form.addRow(self._t("timeout_seconds"), self.timeout_spin)
        connection_form.addRow(self._t("newline_mode"), self.newline_mode_combo)
        connection_form.addRow(self._t("reasoning_effort"), self.reasoning_effort_combo)

        thinking_hint = QLabel(self._t("reasoning_effort_hint"))
        thinking_hint.setObjectName("mutedText")
        thinking_hint.setWordWrap(True)
        connection_form.addRow("", thinking_hint)

        model_group = QGroupBox(self._t("model_parameters"))
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
        self.max_concurrency_spin = QSpinBox()
        self.max_concurrency_spin.setRange(1, 64)

        model_form.addRow(self._t("param_temperature"), self.temperature_spin)
        model_form.addRow(self._t("param_top_p"), self.top_p_spin)
        model_form.addRow(self._t("param_max_tokens"), self.max_tokens_spin)
        model_form.addRow(self._t("param_frequency_penalty"), self.frequency_penalty_spin)
        model_form.addRow(self._t("param_repeat_count"), self.repeat_count_spin)
        model_form.addRow(self._t("param_max_retries"), self.max_retries_spin)
        model_form.addRow(self._t("param_max_concurrency"), self.max_concurrency_spin)

        top_row.addWidget(connection_group, 1)
        top_row.addWidget(model_group, 1)
        layout.addLayout(top_row)

        compatibility_group = QGroupBox(self._t("compatibility_notes"))
        compatibility_layout = QVBoxLayout(compatibility_group)
        compatibility_text = QLabel(self._t("compatibility_notes_desc"))
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

        prompt_group = QGroupBox(self._t("system_prompt"))
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_bar = QHBoxLayout()
        self.prompt_preset_combo = QComboBox()
        self._refresh_prompt_preset_combo()
        self.prompt_apply_button = QPushButton(self._t("apply_preset"))
        self.prompt_apply_button.clicked.connect(self.apply_prompt_preset)
        self.prompt_save_button = QPushButton(self._t("save_custom_preset"))
        self.prompt_save_button.setObjectName("ghostButton")
        self.prompt_save_button.clicked.connect(self.save_custom_prompt_preset)
        self.prompt_rename_button = QPushButton(self._t("rename_custom_preset"))
        self.prompt_rename_button.setObjectName("ghostButton")
        self.prompt_rename_button.clicked.connect(self.rename_custom_prompt_preset)
        self.prompt_delete_button = QPushButton(self._t("delete_custom_preset"))
        self.prompt_delete_button.setObjectName("ghostButton")
        self.prompt_delete_button.clicked.connect(self.delete_custom_prompt_preset)
        prompt_bar.addWidget(QLabel(self._t("prompt_preset")))
        prompt_bar.addWidget(self.prompt_preset_combo)
        prompt_bar.addWidget(self.prompt_apply_button)
        prompt_bar.addWidget(self.prompt_save_button)
        prompt_bar.addWidget(self.prompt_rename_button)
        prompt_bar.addWidget(self.prompt_delete_button)
        prompt_bar.addStretch()

        self.system_prompt_edit = QPlainTextEdit()
        self.system_prompt_edit.setPlaceholderText(DEFAULT_SYSTEM_PROMPT)
        self.system_prompt_edit.setMaximumBlockCount(1000)
        self.system_prompt_edit.setMinimumHeight(260)

        prompt_layout.addLayout(prompt_bar)
        prompt_layout.addWidget(self.system_prompt_edit)
        layout.addWidget(prompt_group, 1)

        headers_group = QGroupBox(self._t("custom_headers"))
        headers_layout = QVBoxLayout(headers_group)
        headers_hint = QLabel(self._t("custom_headers_hint"))
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

        group = QGroupBox(self._t("translation_test"))
        group_layout = QVBoxLayout(group)
        hint = QLabel(self._t("translation_test_hint"))
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)

        self.test_input = QTextEdit()
        self.test_input.setAcceptRichText(False)
        self.test_input.setPlaceholderText(self._t("translation_test_placeholder"))
        self.test_output = QPlainTextEdit()
        self.test_output.setReadOnly(True)

        buttons = QHBoxLayout()
        self.test_button = QPushButton(self._t("translation_test"))
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

        group = QGroupBox(self._t("page_log_title"))
        group_layout = QVBoxLayout(group)
        buttons = QHBoxLayout()
        self.clear_log_button = QPushButton(self._t("clear_logs"))
        self.clear_log_button.clicked.connect(self.clear_logs)
        buttons.addWidget(self.clear_log_button)
        buttons.addStretch()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.document().setMaximumBlockCount(5000)

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
        title, desc = self.page_meta[index]
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
            QLabel {
                color: #ffffff;
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
                color: #ffffff;
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
            QComboBox QAbstractItemView {
                background-color: #2e2e35;
                border: 1px solid #4a4a54;
                color: #f7f7fa;
                selection-background-color: #ff96d3;
                selection-color: #ffffff;
                outline: 0;
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

    def _dialog_stylesheet(self) -> str:
        return """
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

    def _style_dialog(self, dialog):
        dialog.setWindowIcon(self.windowIcon())
        dialog.setStyleSheet(self._dialog_stylesheet())
        if isinstance(dialog, QInputDialog):
            dialog.setOkButtonText(self._t("dialog_ok"))
            dialog.setCancelButtonText(self._t("dialog_cancel"))
            dialog.adjustSize()
            return

        for label in dialog.findChildren(QLabel):
            label.setWordWrap(True)
        dialog.adjustSize()

        button_text_map = {
            QMessageBox.StandardButton.Ok: self._t("dialog_ok"),
            QMessageBox.StandardButton.Cancel: self._t("dialog_cancel"),
            QMessageBox.StandardButton.Yes: self._t("dialog_yes"),
            QMessageBox.StandardButton.No: self._t("dialog_no"),
        }
        for button_flag, text in button_text_map.items():
            button = dialog.button(button_flag)
            if button is not None:
                button.setText(text)

    def _message_box(
        self,
        icon: QMessageBox.Icon,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    ) -> QMessageBox.StandardButton:
        dialog = QMessageBox(self)
        dialog.setIcon(icon)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setStandardButtons(buttons)
        dialog.setDefaultButton(default_button)
        self._style_dialog(dialog)
        return QMessageBox.StandardButton(dialog.exec())

    def _show_warning(self, title: str, text: str):
        self._message_box(QMessageBox.Icon.Warning, title, text)

    def _show_information(self, title: str, text: str):
        self._message_box(QMessageBox.Icon.Information, title, text)

    def _show_critical(self, title: str, text: str):
        self._message_box(QMessageBox.Icon.Critical, title, text)

    def _ask_yes_no(self, title: str, text: str) -> bool:
        result = self._message_box(
            QMessageBox.Icon.Question,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _prompt_text(self, title: str, label: str, text: str = "") -> tuple[str, bool]:
        dialog = QInputDialog(self)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextValue(text)
        self._style_dialog(dialog)
        accepted = bool(dialog.exec())
        return dialog.textValue(), accepted

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

        show_action = QAction(self._t("tray_show_window"), self)
        hide_action = QAction(self._t("tray_hide_window"), self)
        exit_action = QAction(self._t("tray_exit"), self)

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
        model = self.model_type_edit.text().strip() or self._t("not_set")
        base_url = self.base_url_edit.text().strip() or self._t("not_set")
        timeout = f"{self.timeout_spin.value()}{self._t('seconds_suffix')}"
        reasoning = self._current_reasoning_effort() or self._t("default")

        self.launch_model_value.setText(model)
        self.launch_base_url_value.setText(base_url)
        self.launch_timeout_value.setText(timeout)
        self.launch_reasoning_value.setText(reasoning)
        self.launch_status_value.setText(self._t("running") if self._is_service_running() else self._t("idle"))

        if not self._is_service_running():
            try:
                self.url_label.setText(self._t("local_url", url=self._collect_config_from_form().translate_url))
            except ValueError:
                self.url_label.setText(self._t("local_url_invalid"))

    def _load_config_to_form(self):
        cfg = self.config
        self._update_language_state(cfg.ui_language)
        self.custom_prompt_presets = dict(cfg.prompt_presets or {})
        self._reload_prompt_presets()
        self._refresh_prompt_preset_combo()
        self._populate_ui_language_combo(cfg.ui_language)
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
        self.max_concurrency_spin.setValue(cfg.max_concurrency)

        headers = dict(cfg.custom_headers or {})
        self._set_reasoning_effort(headers.pop("reasoning_effort", ""))
        self.custom_headers_edit.setPlainText(json.dumps(headers, ensure_ascii=False, indent=2) if headers else "{}")
        self.system_prompt_edit.setPlainText(cfg.system_prompt)
        self._sync_prompt_preset_selection(cfg.system_prompt)
        self.url_label.setText(self._t("local_url", url=cfg.translate_url))
        self._sync_overview()

    def apply_prompt_preset(self):
        preset_name = self._selected_prompt_preset_name()
        prompt = self.prompt_presets.get(preset_name, DEFAULT_SYSTEM_PROMPT)
        self.system_prompt_edit.setPlainText(prompt)
        self.append_log("INFO", self._t("preset_applied", name=self._display_prompt_preset_name(preset_name)))

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
            max_concurrency=self.max_concurrency_spin.value(),
            temperature=self.temperature_spin.value(),
            max_tokens=self.max_tokens_spin.value(),
            top_p=self.top_p_spin.value(),
            frequency_penalty=self.frequency_penalty_spin.value(),
            system_prompt=self.system_prompt_edit.toPlainText().strip(),
            prompt_presets=dict(self.custom_prompt_presets),
            ui_language=self._current_ui_language_mode(),
        )

    def _is_service_running(self) -> bool:
        return self.service_thread is not None and self.service_thread.isRunning()

    def _set_idle_state(self):
        self.status_label.setText(self._t("status_not_started"))
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._sync_overview()

    def _set_running_state(self):
        self.status_label.setText(self._t("status_running"))
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.url_label.setText(self._t("local_url", url=self.config.translate_url))
        self._sync_overview()

    def _set_starting_state(self):
        self.status_label.setText(self._t("status_starting"))
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def _set_stopping_state(self):
        self.status_label.setText(self._t("status_stopping"))
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
        if self._is_service_running():
            self._set_running_state()
        else:
            self._set_idle_state()
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
            self.append_log("WARN", "服务线程在 3 秒内未能正常停止，强制终止")
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
        self.log_output.clear()

    def _on_service_started(self):
        self._set_running_state()
        self.append_log("INFO", self._t("service_started_success"))
        if self.tray_icon:
            self.tray_icon.showMessage("SakuraLLM GUI", self._t("service_started_balloon"), QSystemTrayIcon.MessageIcon.Information, 2000)
        self._start_backend_health_check()

    def _start_backend_health_check(self):
        existing = getattr(self, "_health_thread", None)
        if existing is not None and existing.isRunning():
            return
        self._health_thread = HealthCheckThread(self.config.base_url, timeout=5)
        self._health_thread.ok.connect(
            lambda: self.append_log("INFO", f"后端连通正常: {self.config.base_url}")
        )
        self._health_thread.failed.connect(
            lambda msg: self.append_log("WARN", f"后端不可达 ({self.config.base_url}): {msg}，翻译请求将会失败")
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
        if self.minimize_to_tray and not self.force_exit and self.tray_icon is not None:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("SakuraLLM GUI", self._t("minimized_to_tray"), QSystemTrayIcon.MessageIcon.Information, 2000)
            return
        self.stop_service()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        super().closeEvent(event)
