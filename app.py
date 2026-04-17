import sys
from gevent import monkey
monkey.patch_all()

import warnings
warnings.filterwarnings(
    "ignore",
    message=r".*doesn't match a supported version.*",
)

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    if not window.windowIcon().isNull():
        app.setWindowIcon(window.windowIcon())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
