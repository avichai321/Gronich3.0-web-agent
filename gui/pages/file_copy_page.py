import os
import subprocess

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QMessageBox,
    QProgressBar,
    QFrame,
)

from services.file_copy_service import AgentFileCopyService
from gui.page_workers import (
    FileCopyConnectWorker,
    FileCopyBrowseWorker,
    FileCopyCopyWorker,
)


class StatCard(QFrame):
    def __init__(self, title: str, value: str):
        super().__init__()
        self.setObjectName("PanelCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("MutedText")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("PanelTitle")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class FileCopyPage(QWidget):
    MODE_TO_INTERNAL = {
        "Maintenance": "bridge",
        "Direct": "direct",
    }

    def __init__(self):
        super().__init__()

        self.service = AgentFileCopyService()
        self.current_items = []
        self.current_path = "."
        self.last_result_path = ""

        self._connect_busy = False
        self._browse_busy = False
        self._copy_busy = False

        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel("File Copy")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "Maintenance = copy through this KMS station. Direct = direct access from this machine."
        )
        subtitle.setObjectName("SubTitleLabel")
        root.addWidget(subtitle)

        stats_row = QHBoxLayout()
        root.addLayout(stats_row)

        self.mode_card = StatCard("Mode", "Maintenance")
        self.path_card = StatCard("Current Path", ".")
        self.items_card = StatCard("Visible Items", "0")
        self.dest_card = StatCard("Destination Mode", "smb")

        stats_row.addWidget(self.mode_card)
        stats_row.addWidget(self.path_card)
        stats_row.addWidget(self.items_card)
        stats_row.addWidget(self.dest_card)

        main_row = QHBoxLayout()
        root.addLayout(main_row, 1)

        left_panel = QFrame()
        left_panel.setObjectName("PanelCard")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        right_panel = QFrame()
        right_panel.setObjectName("PanelCard")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        main_row.addWidget(left_panel, 2)
        main_row.addWidget(right_panel, 3)

        left_title = QLabel("Session Settings")
        left_title.setObjectName("PanelTitle")
        left_layout.addWidget(left_title)

        self.component_combo = QComboBox()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Maintenance", "Direct"])
        self.mode_combo.setCurrentText("Maintenance")

        self.kms_combo = QComboBox()
        self.key_combo = QComboBox()

        self.dest_combo = QComboBox()
        self.dest_combo.addItems(["smb", "download"])

        left_layout.addWidget(QLabel("Component"))
        left_layout.addWidget(self.component_combo)

        left_layout.addWidget(QLabel("Connection Mode"))
        left_layout.addWidget(self.mode_combo)

        left_layout.addWidget(QLabel("KMS Station"))
        left_layout.addWidget(self.kms_combo)

        left_layout.addWidget(QLabel("Key"))
        left_layout.addWidget(self.key_combo)

        left_layout.addWidget(QLabel("Destination Mode"))
        left_layout.addWidget(self.dest_combo)

        self.mode_info = QLabel("Maintenance mode uses this KMS station for browse and copy.")
        self.mode_info.setObjectName("MutedText")
        left_layout.addWidget(self.mode_info)

        btn_row_top = QHBoxLayout()
        self.connect_btn = QPushButton("Connect and Browse")
        self.connect_btn.setObjectName("PrimaryButton")
        self.refresh_btn = QPushButton("Refresh")
        btn_row_top.addWidget(self.connect_btn)
        btn_row_top.addWidget(self.refresh_btn)
        left_layout.addLayout(btn_row_top)

        btn_row_bottom = QHBoxLayout()
        self.copy_btn = QPushButton("Copy Selected")
        self.copy_btn.setObjectName("PrimaryButton")
        self.root_btn = QPushButton("Root")
        self.up_btn = QPushButton("Up")
        btn_row_bottom.addWidget(self.copy_btn)
        btn_row_bottom.addWidget(self.root_btn)
        btn_row_bottom.addWidget(self.up_btn)
        left_layout.addLayout(btn_row_bottom)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        left_layout.addWidget(self.progress)

        self.status_badge = QLabel("Idle")
        self.status_badge.setObjectName("InfoBadge")
        self.status_badge.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_badge)

        left_layout.addStretch()

        right_title = QLabel("Remote Browser")
        right_title.setObjectName("PanelTitle")
        right_layout.addWidget(right_title)

        self.path_label = QLabel("Current path: .")
        self.path_label.setObjectName("MutedText")
        right_layout.addWidget(self.path_label)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.handle_open_item)
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        right_layout.addWidget(self.list_widget, 3)

        details_title = QLabel("Operation Output")
        details_title.setObjectName("PanelTitle")
        right_layout.addWidget(details_title)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        right_layout.addWidget(self.output, 2)

        self.connect_btn.clicked.connect(self.handle_connect)
        self.copy_btn.clicked.connect(self.handle_copy)
        self.refresh_btn.clicked.connect(self.handle_refresh)
        self.root_btn.clicked.connect(lambda: self.load_path("."))
        self.up_btn.clicked.connect(self.go_up)

        self.mode_combo.currentTextChanged.connect(self._toggle_kms_state)
        self.dest_combo.currentTextChanged.connect(self._update_cards)

        self.load_options()
        self._toggle_kms_state(self.mode_combo.currentText())
        self._update_cards()

    def append_output(self, text: str):
        self.output.append(text)

    def set_status(self, text: str, good: bool = False):
        self.status_badge.setText(text)
        self.status_badge.setObjectName("GoodBadge" if good else "InfoBadge")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def set_controls_enabled(self, enabled: bool):
        self.connect_btn.setEnabled(enabled and not self._connect_busy)
        self.refresh_btn.setEnabled(enabled and not self._browse_busy)
        self.copy_btn.setEnabled(enabled and not self._copy_busy)
        self.root_btn.setEnabled(enabled and not self._browse_busy)
        self.up_btn.setEnabled(enabled and not self._browse_busy)
        self.mode_combo.setEnabled(enabled and not self._connect_busy and not self._copy_busy)
        self.dest_combo.setEnabled(enabled and not self._copy_busy)
        self.component_combo.setEnabled(enabled and not self._connect_busy and not self._copy_busy)
        self.key_combo.setEnabled(enabled and not self._connect_busy and not self._copy_busy)

        is_maintenance = self.mode_combo.currentText().strip() == "Maintenance"
        self.kms_combo.setEnabled(enabled and is_maintenance and not self._connect_busy and not self._copy_busy)

    def _update_cards(self):
        self.mode_card.set_value(self.mode_combo.currentText())
        self.path_card.set_value(self.current_path)
        self.items_card.set_value(str(len(self.current_items)))
        self.dest_card.set_value(self.dest_combo.currentText())

    def load_options(self):
        data = self.service.get_options()

        self.component_combo.clear()
        for item in data.get("components", []):
            self.component_combo.addItem(item.get("name", ""))

        self.kms_combo.clear()
        for item in data.get("kms_stations", []):
            self.kms_combo.addItem(item.get("name", ""))

        self.key_combo.clear()
        for key_name in data.get("keys", []):
            self.key_combo.addItem(key_name)

    def _toggle_kms_state(self, display_mode: str):
        is_maintenance = display_mode == "Maintenance"

        if is_maintenance:
            self.mode_info.setText("Maintenance mode uses this KMS station for browse and copy.")
        else:
            self.mode_info.setText("Direct mode connects directly from this machine to the component.")

        self.set_controls_enabled(True)
        self._update_cards()

    def handle_connect(self):
        if self._connect_busy:
            return

        component_name = self.component_combo.currentText().strip()
        display_mode = self.mode_combo.currentText().strip()
        connection_mode = self.MODE_TO_INTERNAL[display_mode]
        kms_station_name = self.kms_combo.currentText().strip() if connection_mode == "bridge" else None
        key_name = self.key_combo.currentText().strip()

        self._connect_busy = True
        self.set_controls_enabled(False)
        self.progress.setValue(15)
        self.set_status("Connecting...")
        self.append_output(f"Connecting in {display_mode} mode...")

        self.connect_thread = QThread()
        self.connect_worker = FileCopyConnectWorker(
            self.service,
            component_name,
            connection_mode,
            kms_station_name,
            key_name,
        )
        self.connect_worker.moveToThread(self.connect_thread)

        self.connect_thread.started.connect(self.connect_worker.run)
        self.connect_worker.finished.connect(self._on_connect_finished)
        self.connect_worker.error.connect(self._on_connect_error)

        self.connect_worker.finished.connect(self.connect_thread.quit)
        self.connect_worker.error.connect(self.connect_thread.quit)
        self.connect_worker.finished.connect(self.connect_worker.deleteLater)
        self.connect_worker.error.connect(self.connect_worker.deleteLater)
        self.connect_thread.finished.connect(self.connect_thread.deleteLater)

        self.connect_thread.start()

    def _on_connect_finished(self, result: dict):
        self._connect_busy = False
        self.set_controls_enabled(True)

        if not result.get("success"):
            self.progress.setValue(0)
            self.set_status("Connect failed")
            QMessageBox.critical(self, "Connect Failed", result.get("message", "Unknown error"))
            self.append_output(result.get("message", "Connect failed"))
            return

        self.current_path = result.get("current_path", ".")
        self.path_label.setText(f"Current path: {self.current_path}")
        self.fill_items(result.get("items", []))
        self.progress.setValue(100)
        self.set_status("Connected", good=True)
        self.append_output(result.get("message", "Connected"))
        self._update_cards()

    def _on_connect_error(self, message: str):
        self._connect_busy = False
        self.set_controls_enabled(True)
        self.progress.setValue(0)
        self.set_status("Connect failed")
        self.append_output(f"Connect error: {message}")
        QMessageBox.critical(self, "Connect Failed", message)

    def fill_items(self, items: list[dict]):
        self.current_items = items
        self.list_widget.clear()

        for item in items:
            item_type = item.get("item_type", "raw")
            name = item.get("name", "")
            size = item.get("size")

            if item_type == "directory":
                label = f"[DIR] {name}"
            elif item_type == "file" and size is not None:
                label = f"{name} ({size} bytes)"
            else:
                label = name

            row = QListWidgetItem(label)
            row.setData(Qt.UserRole, item)

            if item_type == "directory":
                row.setForeground(QColor("#7dd3fc"))
            elif item_type == "file":
                row.setForeground(QColor("#e5e7eb"))
            elif item_type == "error":
                row.setForeground(QColor("#fca5a5"))
            else:
                row.setForeground(QColor("#cbd5e1"))

            self.list_widget.addItem(row)

        self._update_cards()

    def load_path(self, path: str):
        if self._browse_busy:
            return

        self._browse_busy = True
        self.set_controls_enabled(False)
        self.progress.setValue(25)
        self.set_status("Loading path...")
        self.current_path = path
        self.path_label.setText(f"Current path: {self.current_path}")

        self.browse_thread = QThread()
        self.browse_worker = FileCopyBrowseWorker(self.service, path)
        self.browse_worker.moveToThread(self.browse_thread)

        self.browse_thread.started.connect(self.browse_worker.run)
        self.browse_worker.finished.connect(self._on_browse_finished)
        self.browse_worker.error.connect(self._on_browse_error)

        self.browse_worker.finished.connect(self.browse_thread.quit)
        self.browse_worker.error.connect(self.browse_thread.quit)
        self.browse_worker.finished.connect(self.browse_worker.deleteLater)
        self.browse_worker.error.connect(self.browse_worker.deleteLater)
        self.browse_thread.finished.connect(self.browse_thread.deleteLater)

        self.browse_thread.start()

    def _on_browse_finished(self, items: list[dict]):
        self._browse_busy = False
        self.set_controls_enabled(True)
        self.fill_items(items)
        self.progress.setValue(100)
        self.set_status("Ready", good=True)
        self.append_output(f"Loaded path: {self.current_path}")

    def _on_browse_error(self, message: str):
        self._browse_busy = False
        self.set_controls_enabled(True)
        self.progress.setValue(0)
        self.set_status("Browse failed")
        self.append_output(f"Browse error: {message}")
        QMessageBox.critical(self, "Browse Failed", message)

    def handle_refresh(self):
        self.load_path(self.current_path)

    def handle_open_item(self, item: QListWidgetItem):
        payload = item.data(Qt.UserRole)
        if not payload:
            return

        if payload.get("item_type") == "directory":
            self.load_path(payload.get("path", "."))

    def go_up(self):
        if self.current_path in [".", "/"]:
            self.load_path(".")
            return

        parts = self.current_path.rstrip("/").split("/")
        new_path = "/".join(parts[:-1]) if len(parts) > 1 else "."
        if not new_path:
            new_path = "."
        self.load_path(new_path)

    def handle_copy(self):
        if self._copy_busy:
            return

        selected = self.list_widget.selectedItems()
        selected_paths = []

        for item in selected:
            payload = item.data(Qt.UserRole)
            if payload and payload.get("path"):
                selected_paths.append(payload["path"])

        if not selected_paths:
            QMessageBox.warning(self, "No selection", "Please select at least one file or folder.")
            return

        display_mode = self.mode_combo.currentText().strip()
        self.append_output(f"Starting copy in {display_mode} mode...")
        self.progress.setValue(40)
        self.set_status("Copying...")
        self._copy_busy = True
        self.set_controls_enabled(False)

        self.copy_thread = QThread()
        self.copy_worker = FileCopyCopyWorker(
            self.service,
            selected_paths,
            self.dest_combo.currentText().strip(),
        )
        self.copy_worker.moveToThread(self.copy_thread)

        self.copy_thread.started.connect(self.copy_worker.run)
        self.copy_worker.finished.connect(self._on_copy_finished)
        self.copy_worker.error.connect(self._on_copy_error)

        self.copy_worker.finished.connect(self.copy_thread.quit)
        self.copy_worker.error.connect(self.copy_thread.quit)
        self.copy_worker.finished.connect(self.copy_worker.deleteLater)
        self.copy_worker.error.connect(self.copy_worker.deleteLater)
        self.copy_thread.finished.connect(self.copy_thread.deleteLater)

        self.copy_thread.start()

    def _on_copy_finished(self, result: dict):
        self._copy_busy = False
        self.set_controls_enabled(True)

        if not result.get("success"):
            self.progress.setValue(0)
            self.set_status("Copy failed")
            QMessageBox.critical(self, "Copy Failed", result.get("message", "Unknown error"))
            self.append_output(result.get("message", "Copy failed"))
            return

        self.progress.setValue(100)
        self.set_status("Completed", good=True)
        self.append_output(result.get("message", "Copy completed"))

        dest = result.get("destination_path", "")
        self.last_result_path = dest
        if dest:
            self.append_output(f"Destination: {dest}")

            reply = QMessageBox.question(
                self,
                "Copy Completed",
                "Operation completed. Open containing folder?",
            )
            if reply == QMessageBox.Yes:
                self._open_path(dest)

    def _on_copy_error(self, message: str):
        self._copy_busy = False
        self.set_controls_enabled(True)
        self.progress.setValue(0)
        self.set_status("Copy failed")
        self.append_output(f"Copy error: {message}")
        QMessageBox.critical(self, "Copy Failed", message)

    def _open_path(self, path: str):
        try:
            if os.name == "nt":
                if path.lower().endswith(".zip") and os.path.exists(path):
                    subprocess.Popen(f'explorer /select,"{path}"')
                    return

                if os.path.exists(path):
                    subprocess.Popen(f'explorer "{path}"')
                    return

                parent_dir = os.path.dirname(path)
                if parent_dir and os.path.exists(parent_dir):
                    subprocess.Popen(f'explorer "{parent_dir}"')
            else:
                if os.path.exists(path):
                    subprocess.Popen(["xdg-open", path])
                    return

                parent_dir = os.path.dirname(path)
                if parent_dir and os.path.exists(parent_dir):
                    subprocess.Popen(["xdg-open", parent_dir])
        except Exception as exc:
            self.append_output(f"Failed to open path: {exc}")