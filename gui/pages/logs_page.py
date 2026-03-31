import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QFileDialog


class LogsPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)

        refresh_btn = QPushButton("Refresh Latest Log")
        refresh_btn.clicked.connect(self.load_latest_log)

        layout.addWidget(refresh_btn)
        layout.addWidget(self.logs)

    def load_latest_log(self):
        log_dir = "logs"
        if not os.path.isdir(log_dir):
            self.logs.setPlainText("No logs directory found.")
            return

        files = [
            os.path.join(log_dir, f)
            for f in os.listdir(log_dir)
            if f.endswith(".log")
        ]

        if not files:
            self.logs.setPlainText("No log files found.")
            return

        latest = max(files, key=os.path.getmtime)
        with open(latest, "r", encoding="utf-8", errors="ignore") as f:
            self.logs.setPlainText(f.read())