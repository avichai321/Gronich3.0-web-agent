from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QTextEdit
)

from services.tod_service import AgentTodService


class TodPage(QWidget):
    def __init__(self):
        super().__init__()

        self.service = AgentTodService()

        root = QVBoxLayout(self)

        title = QLabel("TOD-SIL")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        self.status_label = QLabel("Current: -")
        root.addWidget(self.status_label)

        self.env_box = QComboBox()
        root.addWidget(self.env_box)

        self.connect_btn = QPushButton("Connect TOD to ENV")
        root.addWidget(self.connect_btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        root.addWidget(self.output)

        self.connect_btn.clicked.connect(self.handle_connect)

        self.load_data()

    def append_output(self, text: str):
        self.output.append(text)

    def load_data(self):
        status = self.service.get_status()
        envs = self.service.get_env_options()

        self.status_label.setText(f"Current: {status.get('env', '-')}")
        self.env_box.clear()
        self.env_box.addItems(envs)

    def handle_connect(self):
        env_name = self.env_box.currentText().strip()
        result = self.service.connect_env(env_name)

        self.append_output(result.get("message", "No response"))

        if result.get("success"):
            QMessageBox.information(self, "TOD-SIL", result.get("message", "Success"))
            self.load_data()
        else:
            QMessageBox.critical(self, "TOD-SIL", result.get("message", "Failed"))