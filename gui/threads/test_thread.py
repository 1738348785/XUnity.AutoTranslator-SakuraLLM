import requests
from PySide6.QtCore import QThread, Signal


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
