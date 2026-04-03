from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class LogEntry:
    level: str
    message: str


class LoggerBridge:
    def __init__(self, sink: Optional[Callable[[LogEntry], None]] = None):
        self.sink = sink

    def _emit(self, level: str, message: str) -> None:
        entry = LogEntry(level=level, message=message)
        print(f"[{level}] {message}")
        if self.sink:
            self.sink(entry)

    def info(self, message: str) -> None:
        self._emit("INFO", message)

    def warn(self, message: str) -> None:
        self._emit("WARN", message)

    def error(self, message: str) -> None:
        self._emit("ERROR", message)
