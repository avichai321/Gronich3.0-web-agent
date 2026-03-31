from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QTextEdit
)

from services.kms_service import AgentKmsService


class KmsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.service = AgentKmsService()

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
        self.refresh_btn.clicked.connect(self.load_data)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.timer.start(12000)

        self.load_data()

    def append_output(self, text: str):
        self.output.append(text)

    def load_data(self):
        self.table.setRowCount(0)
        self.plane_box.clear()
        self.station_box.clear()

        rows = self.service.get_rows()
        opts = self.service.get_options()

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

    def handle_connect(self):
        plane = self.plane_box.currentText().strip()
        station = self.station_box.currentText().strip()

        result = self.service.connect_station(plane, station)
        self.append_output(result.get("message", "No response"))

        if result.get("success"):
            QMessageBox.information(self, "KMS", result.get("message", "Success"))
            self.load_data()
        else:
            QMessageBox.critical(self, "KMS", result.get("message", "Failed"))

    def handle_disconnect(self):
        plane = self.plane_box.currentText().strip()

        result = self.service.disconnect_station(plane)
        self.append_output(result.get("message", "No response"))

        if result.get("success"):
            QMessageBox.information(self, "KMS", result.get("message", "Success"))
            self.load_data()
        else:
            QMessageBox.critical(self, "KMS", result.get("message", "Failed"))