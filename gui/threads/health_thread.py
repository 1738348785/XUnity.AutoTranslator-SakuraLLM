import requests
from PySide6.QtCore import QThread, Signal


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
