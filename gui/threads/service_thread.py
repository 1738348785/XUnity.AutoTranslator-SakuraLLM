from PySide6.QtCore import QThread, Signal

from sakura_llm.config import AppConfig
from sakura_llm.logging_bridge import LogEntry, LoggerBridge
from sakura_llm.service import TranslationService


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

    def apply_runtime_config(self, config: AppConfig) -> None:
        if self.service is not None:
            self.service.apply_runtime_config(config)
