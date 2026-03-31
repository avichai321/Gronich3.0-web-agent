from PySide6.QtCore import QObject, Signal, Slot


class DashboardWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, kms_service, dl_service, tod_service, server_sync, load_agent_config, load_general_settings, app_state):
        super().__init__()
        self.kms_service = kms_service
        self.dl_service = dl_service
        self.tod_service = tod_service
        self.server_sync = server_sync
        self.load_agent_config = load_agent_config
        self.load_general_settings = load_general_settings
        self.app_state = app_state

    @Slot()
    def run(self):
        try:
            cfg = self.load_agent_config()
            general = self.load_general_settings()

            kms_rows = self.kms_service.get_rows()
            dl_rows = self.dl_service.get_rows()
            tod_status = self.tod_service.get_status()

            result = {
                "mode": self.app_state.current_mode,
                "server_url": cfg.get("server", "url", fallback="-"),
                "keys_dir": general.get("keys_dir", ""),
                "bridge_export_path": general.get("bridge_export_path", ""),
                "kms_connected": sum(1 for row in kms_rows if row.get("status") == "connected"),
                "dl_active": sum(1 for row in dl_rows if row.get("environment") != "Free to connect"),
                "tod_env": tod_status.get("env", "-"),
                "tod_status": tod_status.get("status", "-"),
                "last_register": self.app_state.last_register,
                "last_heartbeat": self.app_state.last_heartbeat,
                "last_error": self.app_state.last_error or "-",
                "server_online": self.app_state.server_online,
            }
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class ServerStatusWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, server_sync, app_state):
        super().__init__()
        self.server_sync = server_sync
        self.app_state = app_state

    @Slot()
    def run(self):
        try:
            self.server_sync.ping_server()
            self.finished.emit(
                {
                    "mode": self.app_state.current_mode,
                    "server_online": self.app_state.server_online,
                    "agent_id": self.app_state.agent_id or "-",
                    "server_url": self.app_state.server_url or "-",
                    "current_job": self.app_state.current_job or "-",
                }
            )
        except Exception as exc:
            self.error.emit(str(exc))


class JobPollWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, server_sync):
        super().__init__()
        self.server_sync = server_sync

    @Slot()
    def run(self):
        try:
            self.server_sync.execute_pending_job()
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))