from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox

from core.config_manager import load_agent_config, save_agent_config


class ConfigPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        cfg = load_agent_config()

        self.server_input = QLineEdit(cfg.get("server", "url", fallback="http://localhost:8000"))
        self.agent_id_input = QLineEdit(cfg.get("server", "agent_id", fallback="agent-1"))
        self.token_input = QLineEdit(cfg.get("server", "token", fallback="12345"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["local", "server"])
        self.mode_combo.setCurrentText(cfg.get("server", "mode", fallback="local"))

        layout.addWidget(QLabel("Server URL"))
        layout.addWidget(self.server_input)

        layout.addWidget(QLabel("Agent ID"))
        layout.addWidget(self.agent_id_input)

        layout.addWidget(QLabel("Token"))
        layout.addWidget(self.token_input)

        layout.addWidget(QLabel("Mode"))
        layout.addWidget(self.mode_combo)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

    def save(self):
        cfg = load_agent_config()

        if "server" not in cfg:
            cfg["server"] = {}

        cfg["server"]["url"] = self.server_input.text().strip()
        cfg["server"]["agent_id"] = self.agent_id_input.text().strip()
        cfg["server"]["token"] = self.token_input.text().strip()
        cfg["server"]["mode"] = self.mode_combo.currentText().strip()

        save_agent_config(cfg)
        QMessageBox.information(self, "Saved", "Agent config saved successfully.")