from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QThread
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
from gui.pages.tod_page import TodPage
from gui.pages.logs_page import LogsPage
from gui.theme import DARK_STYLE
from gui.workers import ServerStatusWorker, JobPollWorker
from services.server_sync_service import AgentServerSyncService


def get_base_path() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_path()
LOGO_PATH = BASE_DIR / "assets" / "logo.png"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.server_sync = AgentServerSyncService()
        self._status_busy = False
        self._job_busy = False

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
        self.status_timer.timeout.connect(self.refresh_server_status_async)
        self.status_timer.start(10000)

        self.job_timer = QTimer(self)
        self.job_timer.timeout.connect(self.run_job_poll_async)
        self.job_timer.start(5000)

        self.refresh_server_status_async()

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

        subtitle = QLabel("Local control console for File Copy, KMS, Data-Link and TOD-SIL")
        subtitle.setObjectName("SubTitleLabel")

        self.agent_info = QLabel("Agent: - | Server: -")
        self.agent_info.setObjectName("SubTitleLabel")

        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        title_col.addWidget(self.agent_info)

        self.job_badge = QLabel("Idle")
        self.job_badge.setObjectName("ModeBadge")
        self.job_badge.setAlignment(Qt.AlignCenter)
        self.job_badge.setFixedHeight(34)
        self.job_badge.setMinimumWidth(150)

        self.mode_badge = QLabel("LOCAL MODE")
        self.mode_badge.setObjectName("ModeBadge")
        self.mode_badge.setAlignment(Qt.AlignCenter)
        self.mode_badge.setFixedHeight(34)
        self.mode_badge.setMinimumWidth(150)

        layout.addWidget(logo_label)
        layout.addLayout(title_col)
        layout.addStretch()
        layout.addWidget(self.job_badge, alignment=Qt.AlignRight | Qt.AlignVCenter)
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

    def refresh_server_status_async(self):
        if self._status_busy:
            return
        self._status_busy = True

        self.status_thread = QThread()
        self.status_worker = ServerStatusWorker(self.server_sync, app_state)
        self.status_worker.moveToThread(self.status_thread)

        self.status_thread.started.connect(self.status_worker.run)
        self.status_worker.finished.connect(self._apply_server_status)
        self.status_worker.error.connect(self._on_server_status_error)

        self.status_worker.finished.connect(self.status_thread.quit)
        self.status_worker.error.connect(self.status_thread.quit)
        self.status_worker.finished.connect(self.status_worker.deleteLater)
        self.status_worker.error.connect(self.status_worker.deleteLater)
        self.status_thread.finished.connect(self.status_thread.deleteLater)

        self.status_thread.start()

    def _apply_server_status(self, data: dict):
        self._status_busy = False

        self.agent_info.setText(f"Agent: {data['agent_id']} | Server: {data['server_url']}")
        self.mode_badge.setText("SERVER MODE" if data["mode"] == "SERVER" and data["server_online"] else "LOCAL MODE")

        current_job = data.get("current_job", "-")
        self.job_badge.setText(f"JOB: {current_job[:8]}" if current_job not in [None, "-", ""] else "Idle")

    def _on_server_status_error(self, _message: str):
        self._status_busy = False

    def run_job_poll_async(self):
        if self._job_busy:
            return
        self._job_busy = True

        self.job_thread = QThread()
        self.job_worker = JobPollWorker(self.server_sync)
        self.job_worker.moveToThread(self.job_thread)

        self.job_thread.started.connect(self.job_worker.run)
        self.job_worker.finished.connect(self._on_job_poll_done)
        self.job_worker.error.connect(self._on_job_poll_error)

        self.job_worker.finished.connect(self.job_thread.quit)
        self.job_worker.error.connect(self.job_thread.quit)
        self.job_worker.finished.connect(self.job_worker.deleteLater)
        self.job_worker.error.connect(self.job_worker.deleteLater)
        self.job_thread.finished.connect(self.job_thread.deleteLater)

        self.job_thread.start()

    def _on_job_poll_done(self):
        self._job_busy = False
        self.refresh_server_status_async()

    def _on_job_poll_error(self, _message: str):
        self._job_busy = False