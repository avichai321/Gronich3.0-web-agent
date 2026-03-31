from datetime import datetime
import requests

from core.app_state import app_state
from core.config_manager import load_agent_config
from core.logger import log
from services.file_copy_service import AgentFileCopyService


class AgentServerSyncService:
    def __init__(self):
        self.config = load_agent_config()

    def reload_config(self):
        self.config = load_agent_config()

    def _get_server_settings(self):
        self.reload_config()
        return {
            "url": self.config.get("server", "url", fallback="").rstrip("/"),
            "agent_id": self.config.get("server", "agent_id", fallback="agent-1"),
            "token": self.config.get("server", "token", fallback=""),
            "mode": self.config.get("server", "mode", fallback="local").lower(),
        }

    def ping_server(self) -> bool:
        settings = self._get_server_settings()
        server_url = settings["url"]

        app_state.server_url = server_url
        app_state.agent_id = settings["agent_id"]

        if settings["mode"] != "server":
            app_state.current_mode = "LOCAL"
            app_state.server_online = False
            return False

        if not server_url:
            app_state.current_mode = "LOCAL"
            app_state.server_online = False
            app_state.last_error = "Server URL is empty"
            return False

        try:
            res = requests.get(f"{server_url}/", timeout=5)
            if res.ok:
                app_state.server_online = True
                app_state.current_mode = "SERVER"
                app_state.last_error = ""
                return True

            app_state.server_online = False
            app_state.current_mode = "LOCAL"
            app_state.last_error = f"Server ping failed with HTTP {res.status_code}"
            return False

        except Exception as exc:
            app_state.server_online = False
            app_state.current_mode = "LOCAL"
            app_state.last_error = str(exc)
            return False

    def register(self) -> bool:
        settings = self._get_server_settings()
        server_url = settings["url"]

        if not self.ping_server():
            return False

        payload = {
            "agent_id": settings["agent_id"],
            "hostname": settings["agent_id"],
            "version": "1.0.0",
            "os_type": "windows",
            "token": settings["token"],
        }

        try:
            res = requests.post(f"{server_url}/api/agents/register", json=payload, timeout=8)
            if res.ok:
                app_state.last_register = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log(f"Agent registered successfully: {settings['agent_id']}")
                return True

            app_state.last_error = f"Register failed with HTTP {res.status_code}"
            log(app_state.last_error)
            return False

        except Exception as exc:
            app_state.last_error = str(exc)
            log(f"Register exception: {exc}")
            return False

    def heartbeat(self) -> bool:
        settings = self._get_server_settings()
        server_url = settings["url"]

        if not self.ping_server():
            return False

        payload = {
            "agent_id": settings["agent_id"],
            "status": "idle" if app_state.current_job in [None, "-", ""] else "busy",
            "current_job_id": None if app_state.current_job in [None, "-", ""] else app_state.current_job,
            "mode": app_state.current_mode,
        }

        try:
            res = requests.post(f"{server_url}/api/agents/heartbeat", json=payload, timeout=8)
            if res.ok:
                app_state.last_heartbeat = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log(f"Heartbeat sent successfully: {settings['agent_id']}")
                return True

            app_state.last_error = f"Heartbeat failed with HTTP {res.status_code}"
            log(app_state.last_error)
            return False

        except Exception as exc:
            app_state.last_error = str(exc)
            log(f"Heartbeat exception: {exc}")
            return False

    def poll_next_job(self) -> dict | None:
        settings = self._get_server_settings()
        server_url = settings["url"]
        agent_id = settings["agent_id"]

        if not self.ping_server():
            return None

        try:
            res = requests.get(f"{server_url}/api/agent-jobs/next/{agent_id}", timeout=8)
            if not res.ok:
                return None

            data = res.json()
            return data.get("job")
        except Exception as exc:
            app_state.last_error = str(exc)
            return None

    def submit_job_result(self, job_id: str, status: str, result: dict | None = None, message: str | None = None) -> bool:
        settings = self._get_server_settings()
        server_url = settings["url"]

        try:
            res = requests.post(
                f"{server_url}/api/agent-jobs/{job_id}/result",
                json={
                    "status": status,
                    "result": result or {},
                    "message": message,
                },
                timeout=10,
            )
            return res.ok
        except Exception as exc:
            app_state.last_error = str(exc)
            return False

    def execute_pending_job(self):
        job = self.poll_next_job()
        if not job:
            return

        app_state.current_job = job.get("job_id", "-")

        try:
            if job["job_type"] == "file_copy_browse":
                payload = job["payload"]
                svc = AgentFileCopyService()

                session = svc.create_session(
                    component_name=payload["component_name"],
                    connection_mode=payload["connection_mode"],
                    kms_station_name=payload.get("kms_station_name"),
                    key_name=payload["key_name"],
                    override_host=payload.get("override_host"),
                    override_user=payload.get("override_user"),
                    override_port=payload.get("override_port"),
                )

                if not session.get("success"):
                    self.submit_job_result(
                        job["job_id"],
                        "failed",
                        result={},
                        message=session.get("message", "Create session failed"),
                    )
                    return

                items = svc.list_remote_items(payload.get("path", "."))
                self.submit_job_result(
                    job["job_id"],
                    "completed",
                    result={"items": items},
                    message="Browse completed successfully",
                )
                return

            if job["job_type"] == "file_copy_copy":
                payload = job["payload"]
                svc = AgentFileCopyService()

                session = svc.create_session(
                    component_name=payload["component_name"],
                    connection_mode=payload["connection_mode"],
                    kms_station_name=payload.get("kms_station_name"),
                    key_name=payload["key_name"],
                    override_host=payload.get("override_host"),
                    override_user=payload.get("override_user"),
                    override_port=payload.get("override_port"),
                )

                if not session.get("success"):
                    self.submit_job_result(
                        job["job_id"],
                        "failed",
                        result={},
                        message=session.get("message", "Create session failed"),
                    )
                    return

                result = svc.start_copy(
                    selected_paths=payload.get("selected_paths", []),
                    destination_mode=payload.get("destination_mode", "smb"),
                    override_export_path=payload.get("override_export_path"),
                    override_smb_username=payload.get("override_smb_username"),
                    override_smb_password=payload.get("override_smb_password"),
                )

                self.submit_job_result(
                    job["job_id"],
                    "completed" if result.get("success") else "failed",
                    result=result,
                    message=result.get("message", "Copy finished"),
                )
                return

            self.submit_job_result(
                job["job_id"],
                "failed",
                result={},
                message=f"Unsupported job type: {job['job_type']}",
            )

        except Exception as exc:
            self.submit_job_result(job["job_id"], "failed", result={}, message=str(exc))
        finally:
            app_state.current_job = "-"
            self.heartbeat()