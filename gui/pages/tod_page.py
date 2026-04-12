from PySide6.QtCore import QTimer, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QTextEdit
)

from services.tod_service import AgentTodService
from gui.page_workers import TodLoadWorker, TodConnectWorker


class TodPage(QWidget):
    def __init__(self):
        super().__init__()

        self.service = AgentTodService()
        self._busy = False
        self._action_busy = False

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

        self.refresh_btn = QPushButton("Refresh")
        root.addWidget(self.refresh_btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        root.addWidget(self.output)

        self.connect_btn.clicked.connect(self.handle_connect)
        self.refresh_btn.clicked.connect(self.load_data_async)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data_async)
        self.timer.start(15000)

        QTimer.singleShot(250, self.load_data_async)

    def append_output(self, text: str):
        self.output.append(text)

    def set_controls_enabled(self, enabled: bool):
        self.connect_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)

    def load_data_async(self):
        if self._busy:
            return
        self._busy = True
        self.set_controls_enabled(False)

        self.load_thread = QThread()
        self.load_worker = TodLoadWorker(self.service)
        self.load_worker.moveToThread(self.load_thread)

        self.load_thread.started.connect(self.load_worker.run)
        self.load_worker.finished.connect(self._apply_loaded_data)
        self.load_worker.error.connect(self._on_load_error)

        self.load_worker.finished.connect(self.load_thread.quit)
        self.load_worker.error.connect(self.load_thread.quit)
        self.load_worker.finished.connect(self.load_worker.deleteLater)
        self.load_worker.error.connect(self.load_worker.deleteLater)
        self.load_thread.finished.connect(self.load_thread.deleteLater)

        self.load_thread.start()

    def _apply_loaded_data(self, payload: dict):
        self._busy = False
        self.set_controls_enabled(True)

        status = payload.get("status", {})
        envs = payload.get("envs", [])

        self.status_label.setText(f"Current: {status.get('env', '-')}")
        self.env_box.clear()
        self.env_box.addItems(envs)

    def _on_load_error(self, message: str):
        self._busy = False
        self.set_controls_enabled(True)
        self.append_output(f"Load error: {message}")

    def handle_connect(self):
        if self._action_busy:
            return

        env_name = self.env_box.currentText().strip()

        self._action_busy = True
        self.set_controls_enabled(False)

        self.action_thread = QThread()
        self.action_worker = TodConnectWorker(self.service, env_name)
        self.action_worker.moveToThread(self.action_thread)

        self.action_thread.started.connect(self.action_worker.run)
        self.action_worker.finished.connect(self._on_action_finished)
        self.action_worker.error.connect(self._on_action_error)

        self.action_worker.finished.connect(self.action_thread.quit)
        self.action_worker.error.connect(self.action_thread.quit)
        self.action_worker.finished.connect(self.action_worker.deleteLater)
        self.action_worker.error.connect(self.action_worker.deleteLater)
        self.action_thread.finished.connect(self.action_thread.deleteLater)

        self.action_thread.start()

    def _on_action_finished(self, result: dict):
        self._action_busy = False
        self.set_controls_enabled(True)

        self.append_output(result.get("message", "No response"))

        if result.get("success"):
            QMessageBox.information(self, "TOD-SIL", result.get("message", "Success"))
            self.load_data_async()
        else:
            QMessageBox.critical(self, "TOD-SIL", result.get("message", "Failed"))

    def _on_action_error(self, message: str):
        self._action_busy = False
        self.set_controls_enabled(True)
        self.append_output(f"Action error: {message}")
        QMessageBox.critical(self, "TOD-SIL", message)