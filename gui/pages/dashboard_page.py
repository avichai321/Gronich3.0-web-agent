from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton

from core.app_state import app_state
from core.config_manager import load_agent_config, load_general_settings
from services.kms_service import AgentKmsService
from services.datalink_service import AgentDataLinkService
from services.server_sync_service import AgentServerSyncService


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
        self.server_sync = AgentServerSyncService()

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
        
        top_row.addWidget(self.tod_card)
        top_row.addWidget(self.mode_card)
        top_row.addWidget(self.server_card)
        top_row.addWidget(self.kms_card)
        top_row.addWidget(self.dl_card)

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
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(15000)

        self.refresh_data()

    def refresh_data(self):
        cfg = load_agent_config()
        general = load_general_settings()

        mode = app_state.current_mode
        server_url = cfg.get("server", "url", fallback="-")

        kms_rows = self.kms_service.get_rows()
        dl_rows = self.dl_service.get_rows()
        tod_status = self.dl_service.get_tod_status()

        kms_connected = sum(1 for row in kms_rows if row.get("status") == "connected")
        dl_active = sum(1 for row in dl_rows if row.get("environment") != "Free to connect")

        self.mode_card.set_value(mode)
        self.server_card.set_value(server_url)
        self.kms_card.set_value(str(kms_connected))
        self.dl_card.set_value(str(dl_active))
        self.tod_card.set_value(tod_status.get("env", "-"))

        self.status_label.setText(
            f"Keys Dir: {general.get('keys_dir', '')} | Bridge Export: {general.get('bridge_export_path', '')}"
        )

        self.details_label.setText(
            f"Server Online: {app_state.server_online} | "
            f"Last Register: {app_state.last_register} | "
            f"Last Heartbeat: {app_state.last_heartbeat} | "
            f"Last Error: {app_state.last_error or '-'}"
        )

    def handle_register(self):
        self.server_sync.register()
        self.refresh_data()

    def handle_heartbeat(self):
        self.server_sync.heartbeat()
        self.refresh_data()