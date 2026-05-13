import sys
from pathlib import Path


APP_VERSION = "v1.0.6"


def get_app_resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir.joinpath(*parts)
