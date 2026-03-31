import os
import subprocess

from PySide6.QtCore import Qt
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
        self.kms_combo.setEnabled(is_maintenance)

        if is_maintenance:
            self.mode_info.setText("Maintenance mode uses this KMS station for browse and copy.")
        else:
            self.mode_info.setText("Direct mode connects directly from this machine to the component.")

        self._update_cards()

    def handle_connect(self):
        component_name = self.component_combo.currentText().strip()
        display_mode = self.mode_combo.currentText().strip()
        connection_mode = self.MODE_TO_INTERNAL[display_mode]
        kms_station_name = self.kms_combo.currentText().strip() if connection_mode == "bridge" else None
        key_name = self.key_combo.currentText().strip()

        self.progress.setValue(15)
        self.set_status("Connecting...")
        self.append_output(f"Connecting in {display_mode} mode...")

        result = self.service.create_session(
            component_name=component_name,
            connection_mode=connection_mode,
            kms_station_name=kms_station_name,
            key_name=key_name,
        )

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
        self.progress.setValue(25)
        self.set_status("Loading path...")
        self.current_path = path
        self.path_label.setText(f"Current path: {self.current_path}")
        items = self.service.list_remote_items(path)
        self.fill_items(items)
        self.progress.setValue(100)
        self.set_status("Ready", good=True)
        self.append_output(f"Loaded path: {path}")

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

        result = self.service.start_copy(
            selected_paths=selected_paths,
            destination_mode=self.dest_combo.currentText().strip(),
        )

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

    def _open_path(self, path: str):
        try:
            if path.lower().endswith(".zip") and os.path.exists(path):
                subprocess.Popen(f'explorer /select,"{path}"')
                return

            if os.path.exists(path):
                subprocess.Popen(f'explorer "{path}"')
                return

            parent_dir = os.path.dirname(path)
            if parent_dir and os.path.exists(parent_dir):
                subprocess.Popen(f'explorer "{parent_dir}"')
        except Exception as exc:
            self.append_output(f"Failed to open path: {exc}")