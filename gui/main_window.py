from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.app_state import app_state
from gui.pages.dashboard_page import DashboardPage
from gui.pages.file_copy_page import FileCopyPage
from gui.pages.kms_page import KmsPage
from gui.pages.datalink_page import DataLinkPage
from gui.pages.logs_page import LogsPage
from gui.theme import DARK_STYLE
from services.server_sync_service import AgentServerSyncService
from gui.pages.tod_page import TodPage

BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.server_sync = AgentServerSyncService()

        self.setWindowTitle("Gronich Agent")
        self.resize(1450, 900)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        sidebar = self._build_sidebar()
        content = self._build_content()

        body.addWidget(sidebar, 1)
        body.addWidget(content, 5)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_server_status)
        self.status_timer.start(10000)

        self.refresh_server_status()

        self.job_timer = QTimer(self)
        self.job_timer.timeout.connect(self.run_job_poll)
        self.job_timer.start(5000)
    
    def run_job_poll(self):
        self.server_sync.execute_pending_job()
    
    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("HeaderFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        logo_label = QLabel()
        if LOGO_PATH.exists():
            pixmap = QPixmap(str(LOGO_PATH))
            logo_label.setPixmap(
                pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            logo_label.setText("No Logo")
        logo_label.setFixedSize(72, 72)
        logo_label.setAlignment(Qt.AlignCenter)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title = QLabel("Gronich Agent")
        title.setObjectName("TitleLabel")

        subtitle = QLabel("Local control console for File Copy, KMS and Data-Link")
        subtitle.setObjectName("SubTitleLabel")

        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        self.mode_badge = QLabel("LOCAL MODE")
        self.mode_badge.setObjectName("ModeBadge")
        self.mode_badge.setAlignment(Qt.AlignCenter)
        self.mode_badge.setFixedHeight(34)
        self.mode_badge.setMinimumWidth(150)

        layout.addWidget(logo_label)
        layout.addLayout(title_col)
        layout.addStretch()
        layout.addWidget(self.mode_badge, alignment=Qt.AlignRight | Qt.AlignVCenter)

        return frame

    def _build_sidebar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("SidebarFrame")
        frame.setMinimumWidth(250)
        frame.setMaximumWidth(300)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        nav_title = QLabel("Navigation")
        nav_title.setObjectName("SectionTitle")
        layout.addWidget(nav_title)

        self.stack = QStackedWidget()

        self.pages = [
            ("Dashboard", DashboardPage()),
            ("File Copy", FileCopyPage()),
            ("KMS", KmsPage()),
            ("Data-Link", DataLinkPage()),
            ("TOD-SIL", TodPage()),
            ("Logs", LogsPage()),
        ]

        for index, (name, page) in enumerate(self.pages):
            btn = QPushButton(name)
            btn.setObjectName("NavButton")
            btn.clicked.connect(lambda checked=False, idx=index: self.stack.setCurrentIndex(idx))
            layout.addWidget(btn)

        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        footer = QLabel("Made by Avichai Avicii Dahan")
        footer.setObjectName("SubTitleLabel")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        return frame

    def _build_content(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ContentFrame")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addWidget(self.stack)

        for _, page in self.pages:
            self.stack.addWidget(page)

        return frame

    def refresh_server_status(self):
        self.server_sync.ping_server()

        if app_state.current_mode == "SERVER" and app_state.server_online:
            self.mode_badge.setText("SERVER MODE")
        else:
            self.mode_badge.setText("LOCAL MODE")