import sys
from gevent import monkey
monkey.patch_all(thread=False)

import warnings
warnings.filterwarnings(
    "ignore",
    message=r".*doesn't match a supported version.*",
)

import signal
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    # Restore default handler for SIGINT (Ctrl+C) so the application terminates
    # immediately and cleanly without raising Python KeyboardInterrupt tracebacks.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    window = MainWindow()
    if not window.windowIcon().isNull():
        app.setWindowIcon(window.windowIcon())
    window.show()
    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
