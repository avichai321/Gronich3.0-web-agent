from PySide6.QtCore import QObject, Signal, Slot


class KmsLoadWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service):
        super().__init__()
        self.service = service

    @Slot()
    def run(self):
        try:
            rows = self.service.get_rows()
            opts = self.service.get_options()
            self.finished.emit({"rows": rows, "options": opts})
        except Exception as exc:
            self.error.emit(str(exc))


class KmsConnectWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service, plane: str, station: str):
        super().__init__()
        self.service = service
        self.plane = plane
        self.station = station

    @Slot()
    def run(self):
        try:
            result = self.service.connect_station(self.plane, self.station)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class KmsDisconnectWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service, plane: str):
        super().__init__()
        self.service = service
        self.plane = plane

    @Slot()
    def run(self):
        try:
            result = self.service.disconnect_station(self.plane)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class DlLoadWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service):
        super().__init__()
        self.service = service

    @Slot()
    def run(self):
        try:
            rows = self.service.get_rows()
            opts = self.service.get_options()
            self.finished.emit({"rows": rows, "options": opts})
        except Exception as exc:
            self.error.emit(str(exc))


class DlConnectWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service, plane: str, env_name: str, state_name: str):
        super().__init__()
        self.service = service
        self.plane = plane
        self.env_name = env_name
        self.state_name = state_name

    @Slot()
    def run(self):
        try:
            result = self.service.connect_env(self.plane, self.env_name, self.state_name)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class TodLoadWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service):
        super().__init__()
        self.service = service

    @Slot()
    def run(self):
        try:
            status = self.service.get_status()
            envs = self.service.get_env_options()
            self.finished.emit({"status": status, "envs": envs})
        except Exception as exc:
            self.error.emit(str(exc))


class TodConnectWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service, env_name: str):
        super().__init__()
        self.service = service
        self.env_name = env_name

    @Slot()
    def run(self):
        try:
            result = self.service.connect_env(self.env_name)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

class FileCopyConnectWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service, component_name: str, connection_mode: str, kms_station_name: str | None, key_name: str):
        super().__init__()
        self.service = service
        self.component_name = component_name
        self.connection_mode = connection_mode
        self.kms_station_name = kms_station_name
        self.key_name = key_name

    @Slot()
    def run(self):
        try:
            result = self.service.create_session(
                component_name=self.component_name,
                connection_mode=self.connection_mode,
                kms_station_name=self.kms_station_name,
                key_name=self.key_name,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class FileCopyBrowseWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, service, path: str):
        super().__init__()
        self.service = service
        self.path = path

    @Slot()
    def run(self):
        try:
            items = self.service.list_remote_items(self.path)
            self.finished.emit(items)
        except Exception as exc:
            self.error.emit(str(exc))


class FileCopyCopyWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        service,
        selected_paths: list[str],
        destination_mode: str,
        override_export_path: str | None = None,
        override_smb_username: str | None = None,
        override_smb_password: str | None = None,
    ):
        super().__init__()
        self.service = service
        self.selected_paths = selected_paths
        self.destination_mode = destination_mode
        self.override_export_path = override_export_path
        self.override_smb_username = override_smb_username
        self.override_smb_password = override_smb_password

    @Slot()
    def run(self):
        try:
            result = self.service.start_copy(
                selected_paths=self.selected_paths,
                destination_mode=self.destination_mode,
                override_export_path=self.override_export_path,
                override_smb_username=self.override_smb_username,
                override_smb_password=self.override_smb_password,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))