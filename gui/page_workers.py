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