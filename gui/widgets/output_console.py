from PySide6.QtWidgets import QTextEdit


class OutputConsole(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

    def write_line(self, text: str):
        self.append(text)