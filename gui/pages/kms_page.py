from PySide6.QtCore import QTimer, QThread
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QTextEdit
)

from services.kms_service import AgentKmsService
from gui.page_workers import KmsLoadWorker, KmsConnectWorker, KmsDisconnectWorker


class KmsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.service = AgentKmsService()
        self._busy = False
        self._action_busy = False

        root = QVBoxLayout(self)

        title = QLabel("KMS")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Interface", "Plane", "VLAN", "Station", "Status"])
        root.addWidget(self.table, 3)

        controls = QHBoxLayout()
        root.addLayout(controls)

        left = QVBoxLayout()
        right = QVBoxLayout()
        controls.addLayout(left, 2)
        controls.addLayout(right, 1)

        self.plane_box = QComboBox()
        self.station_box = QComboBox()
        self.station_box.setEnabled(False)

        left.addWidget(QLabel("Plane / Interface"))
        left.addWidget(self.plane_box)

        left.addWidget(QLabel("Station"))
        left.addWidget(self.station_box)

        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("PrimaryButton")
        self.disconnect_btn = QPushButton("Disconnect")
        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        left.addLayout(btn_row)

        self.refresh_btn = QPushButton("Refresh")
        right.addWidget(self.refresh_btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        root.addWidget(self.output, 1)

        self.connect_btn.clicked.connect(self.handle_connect)
        self.disconnect_btn.clicked.connect(self.handle_disconnect)
        self.refresh_btn.clicked.connect(self.load_data_async)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data_async)
        self.timer.start(12000)

        QTimer.singleShot(250, self.load_data_async)

    def append_output(self, text: str):
        self.output.append(text)

    def set_controls_enabled(self, enabled: bool):
        self.connect_btn.setEnabled(enabled)
        self.disconnect_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)

    def load_data_async(self):
        if self._busy:
            return
        self._busy = True
        self.set_controls_enabled(False)

        self.load_thread = QThread()
        self.load_worker = KmsLoadWorker(self.service)
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

        self.table.setRowCount(0)
        self.plane_box.clear()
        self.station_box.clear()

        self.plane_box.addItems(opts.get("planes", []))
        self.station_box.addItems(opts.get("stations", []))

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                row["interface"],
                row["description"],
                row["vlan"],
                row["station_name"],
                row["status"],
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if col == 4:
                    status = str(value).lower()
                    if status == "connected":
                        item.setBackground(QColor("#12311d"))
                    elif status in ["free", "dry-run"]:
                        item.setBackground(QColor("#1e293b"))
                    else:
                        item.setBackground(QColor("#4c1d1d"))

                self.table.setItem(i, col, item)

        self.table.resizeColumnsToContents()

    def _on_load_error(self, message: str):
        self._busy = False
        self.set_controls_enabled(True)
        self.append_output(f"Load error: {message}")

    def handle_connect(self):
        if self._action_busy:
            return

        plane = self.plane_box.currentText().strip()
        station = self.station_box.currentText().strip()

        self._action_busy = True
        self.set_controls_enabled(False)

        self.connect_thread = QThread()
        self.connect_worker = KmsConnectWorker(self.service, plane, station)
        self.connect_worker.moveToThread(self.connect_thread)

        self.connect_thread.started.connect(self.connect_worker.run)
        self.connect_worker.finished.connect(self._on_connect_finished)
        self.connect_worker.error.connect(self._on_action_error)

        self.connect_worker.finished.connect(self.connect_thread.quit)
        self.connect_worker.error.connect(self.connect_thread.quit)
        self.connect_worker.finished.connect(self.connect_worker.deleteLater)
        self.connect_worker.error.connect(self.connect_worker.deleteLater)
        self.connect_thread.finished.connect(self.connect_thread.deleteLater)

        self.connect_thread.start()

    def _on_connect_finished(self, result: dict):
        self._action_busy = False
        self.set_controls_enabled(True)
        self.append_output(result.get("message", "No response"))

        if result.get("success"):
            QMessageBox.information(self, "KMS", result.get("message", "Success"))
            self.load_data_async()
        else:
            QMessageBox.critical(self, "KMS", result.get("message", "Failed"))

    def handle_disconnect(self):
        if self._action_busy:
            return

        plane = self.plane_box.currentText().strip()

        self._action_busy = True
        self.set_controls_enabled(False)

        self.disconnect_thread = QThread()
        self.disconnect_worker = KmsDisconnectWorker(self.service, plane)
        self.disconnect_worker.moveToThread(self.disconnect_thread)

        self.disconnect_thread.started.connect(self.disconnect_worker.run)
        self.disconnect_worker.finished.connect(self._on_disconnect_finished)
        self.disconnect_worker.error.connect(self._on_action_error)

        self.disconnect_worker.finished.connect(self.disconnect_thread.quit)
        self.disconnect_worker.error.connect(self.disconnect_thread.quit)
        self.disconnect_worker.finished.connect(self.disconnect_worker.deleteLater)
        self.disconnect_worker.error.connect(self.disconnect_worker.deleteLater)
        self.disconnect_thread.finished.connect(self.disconnect_thread.deleteLater)

        self.disconnect_thread.start()

    def _on_disconnect_finished(self, result: dict):
        self._action_busy = False
        self.set_controls_enabled(True)
        self.append_output(result.get("message", "No response"))

        if result.get("success"):
            QMessageBox.information(self, "KMS", result.get("message", "Success"))
            self.load_data_async()
        else:
            QMessageBox.critical(self, "KMS", result.get("message", "Failed"))

    def _on_action_error(self, message: str):
        self._action_busy = False
        self.set_controls_enabled(True)
        self.append_output(f"Action error: {message}")
        QMessageBox.critical(self, "KMS", message)