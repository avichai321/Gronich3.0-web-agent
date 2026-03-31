from PySide6.QtCore import QTimer, QThread
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton

from core.app_state import app_state
from core.config_manager import load_agent_config, load_general_settings
from services.kms_service import AgentKmsService
from services.datalink_service import AgentDataLinkService
from services.tod_service import AgentTodService
from services.server_sync_service import AgentServerSyncService
from gui.workers import DashboardWorker


class InfoCard(QFrame):
    def __init__(self, title: str, value: str):
        super().__init__()
        self.setObjectName("InfoCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("CardValue")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        self.kms_service = AgentKmsService()
        self.dl_service = AgentDataLinkService()
        self.tod_service = AgentTodService()
        self.server_sync = AgentServerSyncService()
        self._busy = False

        root = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        top_row = QHBoxLayout()
        root.addLayout(top_row)

        self.mode_card = InfoCard("Mode", "-")
        self.server_card = InfoCard("Server URL", "-")
        self.kms_card = InfoCard("KMS Connected", "0")
        self.dl_card = InfoCard("DL Active", "0")
        self.tod_card = InfoCard("TOD-SIL", "-")

        top_row.addWidget(self.mode_card)
        top_row.addWidget(self.server_card)
        top_row.addWidget(self.kms_card)
        top_row.addWidget(self.dl_card)
        top_row.addWidget(self.tod_card)

        sync_row = QHBoxLayout()
        root.addLayout(sync_row)

        self.register_btn = QPushButton("Register Agent")
        self.register_btn.setObjectName("PrimaryButton")
        self.heartbeat_btn = QPushButton("Send Heartbeat")
        self.heartbeat_btn.setObjectName("PrimaryButton")

        sync_row.addWidget(self.register_btn)
        sync_row.addWidget(self.heartbeat_btn)
        sync_row.addStretch()

        self.status_label = QLabel("Loading...")
        self.status_label.setObjectName("SubTitleLabel")
        root.addWidget(self.status_label)

        self.details_label = QLabel("-")
        self.details_label.setObjectName("SubTitleLabel")
        root.addWidget(self.details_label)

        self.register_btn.clicked.connect(self.handle_register)
        self.heartbeat_btn.clicked.connect(self.handle_heartbeat)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data_async)
        self.timer.start(15000)

        QTimer.singleShot(300, self.refresh_data_async)

    def refresh_data_async(self):
        if self._busy:
            return
        self._busy = True

        self.thread = QThread()
        self.worker = DashboardWorker(
            self.kms_service,
            self.dl_service,
            self.tod_service,
            self.server_sync,
            load_agent_config,
            load_general_settings,
            app_state,
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._apply_data)
        self.worker.error.connect(self._on_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _apply_data(self, data: dict):
        self._busy = False

        self.mode_card.set_value(data["mode"])
        self.server_card.set_value(data["server_url"])
        self.kms_card.set_value(str(data["kms_connected"]))
        self.dl_card.set_value(str(data["dl_active"]))
        self.tod_card.set_value(data["tod_env"])

        self.status_label.setText(
            f"Keys Dir: {data['keys_dir']} | Bridge Export: {data['bridge_export_path']}"
        )

        self.details_label.setText(
            f"Server Online: {data['server_online']} | "
            f"Last Register: {data['last_register']} | "
            f"Last Heartbeat: {data['last_heartbeat']} | "
            f"Last Error: {data['last_error']} | "
            f"TOD Status: {data['tod_status']}"
        )

    def _on_error(self, message: str):
        self._busy = False
        self.details_label.setText(f"Dashboard error: {message}")

    def handle_register(self):
        self.server_sync.register()
        self.refresh_data_async()

    def handle_heartbeat(self):
        self.server_sync.heartbeat()
        self.refresh_data_async()