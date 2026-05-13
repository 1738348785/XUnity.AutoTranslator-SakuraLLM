from dataclasses import dataclass
from typing import Any

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit, QSpinBox

from sakura_llm.config import AppConfig


@dataclass(frozen=True)
class FieldSpec:
    config_name: str   # AppConfig 字段名
    widget_attr: str   # MainWindow 上的控件属性名
    kind: str          # "text" | "spin" | "double_spin" | "combo_text" | "plain_text"


FIELD_SPECS: list[FieldSpec] = [
    FieldSpec("base_url",          "base_url_edit",          "text"),
    FieldSpec("api_key",           "api_key_edit",           "text"),
    FieldSpec("model_type",        "model_type_edit",        "text"),
    FieldSpec("listen_port",       "listen_port_spin",       "spin"),
    FieldSpec("request_timeout",   "timeout_spin",           "spin"),
    FieldSpec("newline_mode",      "newline_mode_combo",     "combo_text"),
    FieldSpec("temperature",       "temperature_spin",       "double_spin"),
    FieldSpec("top_p",             "top_p_spin",             "double_spin"),
    FieldSpec("max_tokens",        "max_tokens_spin",        "spin"),
    FieldSpec("frequency_penalty", "frequency_penalty_spin", "double_spin"),
    FieldSpec("repeat_count",      "repeat_count_spin",      "spin"),
    FieldSpec("max_retries",       "max_retries_spin",       "spin"),
    FieldSpec("max_concurrency",   "max_concurrency_spin",   "spin"),
    FieldSpec("system_prompt",     "system_prompt_edit",     "plain_text"),
]


def _get_widget(window, attr: str):
    return getattr(window, attr)


def get_widget_value(window, spec: FieldSpec) -> Any:
    widget = _get_widget(window, spec.widget_attr)
    kind = spec.kind
    if kind == "text":
        assert isinstance(widget, QLineEdit)
        return widget.text()
    if kind == "spin":
        assert isinstance(widget, QSpinBox)
        return widget.value()
    if kind == "double_spin":
        assert isinstance(widget, QDoubleSpinBox)
        return widget.value()
    if kind == "combo_text":
        assert isinstance(widget, QComboBox)
        return widget.currentText()
    if kind == "plain_text":
        assert isinstance(widget, QPlainTextEdit)
        return widget.toPlainText()
    raise ValueError(f"Unknown widget kind: {kind}")


def set_widget_value(window, spec: FieldSpec, value: Any) -> None:
    widget = _get_widget(window, spec.widget_attr)
    kind = spec.kind
    if kind == "text":
        widget.setText(str(value))
    elif kind in ("spin", "double_spin"):
        widget.setValue(value)
    elif kind == "combo_text":
        widget.setCurrentText(str(value))
    elif kind == "plain_text":
        widget.setPlainText(str(value))
    else:
        raise ValueError(f"Unknown widget kind: {kind}")


def load_from_config(window, config: AppConfig) -> None:
    """Populate widgets from AppConfig values for all simple fields."""
    for spec in FIELD_SPECS:
        set_widget_value(window, spec, getattr(config, spec.config_name))


def collect_to_dict(window) -> dict:
    """Collect widget values into a dict keyed by AppConfig field name."""
    return {spec.config_name: get_widget_value(window, spec) for spec in FIELD_SPECS}


def snapshot_widget_state(window) -> dict:
    """Snapshot all simple-field widget values for restore-after-rebuild."""
    return {spec.widget_attr: get_widget_value(window, spec) for spec in FIELD_SPECS}


def restore_widget_state(window, state: dict) -> None:
    """Restore widget values from a snapshot dict (keyed by widget_attr)."""
    for spec in FIELD_SPECS:
        if spec.widget_attr in state:
            set_widget_value(window, spec, state[spec.widget_attr])
