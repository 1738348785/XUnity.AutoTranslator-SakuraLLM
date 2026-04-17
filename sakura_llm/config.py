from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import os
import sys
import tempfile


DEFAULT_SYSTEM_PROMPT = """你是一个视觉小说翻译模型，可以通顺地使用给定的术语表以指定的风格将日文翻译成简体中文，并联系上下文正确使用人称代词，注意不要混淆使役态和被动态的主语和宾语，不要擅自添加原文中没有的特殊符号，也不要擅自增加或减少换行。"""

PROMPT_PRESETS = {
    "sakura预设": DEFAULT_SYSTEM_PROMPT,
}


@dataclass
class AppConfig:
    base_url: str = "http://127.0.0.1:8080"
    api_key: str = ""
    listen_port: int = 4000
    custom_headers: dict = field(default_factory=dict)
    model_type: str = "GalTransl-v4-4B-2601"
    request_timeout: int = 20
    max_concurrency: int = 2
    newline_mode: str = "escape"
    repeat_count: int = 8
    max_retries: int = 3
    temperature: float = 0.3
    max_tokens: int = 2048
    top_p: float = 0.8
    frequency_penalty: float = 0.0
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    prompt_presets: dict = field(default_factory=dict)
    ui_language: str = "auto"

    @property
    def translate_url(self) -> str:
        return f"http://127.0.0.1:{self.listen_port}/translate"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        defaults = cls().to_dict()
        values = {**defaults, **{k: v for k, v in (data or {}).items() if k in defaults}}
        if not isinstance(values.get("custom_headers"), dict):
            values["custom_headers"] = {}
        if not isinstance(values.get("system_prompt"), str) or not values.get("system_prompt", "").strip():
            values["system_prompt"] = DEFAULT_SYSTEM_PROMPT
        if not isinstance(values.get("prompt_presets"), dict):
            values["prompt_presets"] = {}
        else:
            values["prompt_presets"] = {
                str(k): str(v)
                for k, v in values["prompt_presets"].items()
                if str(k).strip() and str(v).strip()
            }
        if values.get("ui_language") not in {"auto", "zh_CN", "en"}:
            values["ui_language"] = "auto"
        return cls(**values)


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        with self.path.open("r", encoding="utf-8") as f:
            return AppConfig.from_dict(json.load(f))

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

def get_default_config_path() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "config.json"
