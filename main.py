import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from core.logger import init_logger


def main():
    init_logger()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()