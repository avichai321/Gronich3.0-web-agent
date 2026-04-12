from PySide6.QtCore import QTimer, QThread
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QTextEdit
)

from services.datalink_service import AgentDataLinkService
from gui.page_workers import DlLoadWorker, DlConnectWorker


class DataLinkPage(QWidget):
    def __init__(self):
        super().__init__()
        self.service = AgentDataLinkService()
        self.current_options = {}
        self._busy = False
        self._action_busy = False

        root = QVBoxLayout(self)

        title = QLabel("Data-Link")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Interface", "Description", "VLANs", "Environment", "Maintenance", "ATE State", "Health"]
        )
        root.addWidget(self.table, 3)

        controls = QHBoxLayout()
        root.addLayout(controls)

        left = QVBoxLayout()
        right = QVBoxLayout()
        controls.addLayout(left, 2)
        controls.addLayout(right, 1)

        self.plane_box = QComboBox()
        self.env_box = QComboBox()
        self.state_box = QComboBox()

        left.addWidget(QLabel("Plane / Interface"))
        left.addWidget(self.plane_box)

        left.addWidget(QLabel("Environment"))
        left.addWidget(self.env_box)

        left.addWidget(QLabel("ATE Desired State"))
        left.addWidget(self.state_box)

        self.execute_btn = QPushButton("Execute")
        self.execute_btn.setObjectName("PrimaryButton")
        left.addWidget(self.execute_btn)

        self.refresh_btn = QPushButton("Refresh")
        right.addWidget(self.refresh_btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        root.addWidget(self.output, 1)

        self.env_box.currentTextChanged.connect(self.handle_env_change)
        self.execute_btn.clicked.connect(self.handle_execute)
        self.refresh_btn.clicked.connect(self.load_data_async)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data_async)
        self.timer.start(15000)

        QTimer.singleShot(250, self.load_data_async)

    def append_output(self, text: str):
        self.output.append(text)

    def set_controls_enabled(self, enabled: bool):
        self.execute_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)

    def load_data_async(self):
        if self._busy:
            return
        self._busy = True
        self.set_controls_enabled(False)

        self.load_thread = QThread()
        self.load_worker = DlLoadWorker(self.service)
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

        rows = payload.get("rows", [])
        opts = payload.get("options", {})
        self.current_options = opts

        self.table.setRowCount(0)
        self.plane_box.clear()
        self.env_box.clear()
        self.state_box.clear()

        self.plane_box.addItems(opts.get("planes", []))
        self.env_box.addItems(opts.get("envs", []))

        first_env = self.env_box.currentText().strip()
        self.state_box.addItems(opts.get("states_by_env", {}).get(first_env, []))

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                row["interface"],
                row["description"],
                ",".join(row["vlans"]),
                row["environment"],
                row["maintenance"],
                row["ate_state"],
                row["health"],
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if col == 6:
                    health = str(value).lower()
                    if health == "healthy":
                        item.setBackground(QColor("#12311d"))
                    elif health in ["warning", "dry-run"]:
                        item.setBackground(QColor("#4a3b12"))
                    elif health == "free":
                        item.setBackground(QColor("#1e293b"))
                    else:
                        item.setBackground(QColor("#4c1d1d"))

                self.table.setItem(i, col, item)

        self.table.resizeColumnsToContents()

    def _on_load_error(self, message: str):
        self._busy = False
        self.set_controls_enabled(True)
        self.append_output(f"Load error: {message}")

    def handle_env_change(self, env_name: str):
        self.state_box.clear()
        self.state_box.addItems(self.current_options.get("states_by_env", {}).get(env_name, []))

    def handle_execute(self):
        if self._action_busy:
            return

        plane = self.plane_box.currentText().strip()
        env_name = self.env_box.currentText().strip()
        state_name = self.state_box.currentText().strip()

        self._action_busy = True
        self.set_controls_enabled(False)

        self.action_thread = QThread()
        self.action_worker = DlConnectWorker(self.service, plane, env_name, state_name)
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
            QMessageBox.information(self, "Data-Link", result.get("message", "Success"))
            self.load_data_async()
        else:
            QMessageBox.critical(self, "Data-Link", result.get("message", "Failed"))

    def _on_action_error(self, message: str):
        self._action_busy = False
        self.set_controls_enabled(True)
        self.append_output(f"Action error: {message}")
        QMessageBox.critical(self, "Data-Link", message)