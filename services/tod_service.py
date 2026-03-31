from core.app_state import app_state
from core.api_client import ApiClient
from core.config_manager import load_agent_config
from services.ssh_service import SSHService, run_ios_commands


class AgentTodService:
    def __init__(self):
        self.api = ApiClient()

    def _is_server_mode(self):
        return app_state.current_mode == "SERVER" and app_state.server_online

    def _get_local_config(self):
        cfg = load_agent_config()

        tod_switch = cfg.get("TOD_ATE_SWITCH", {})
        tod_envs = cfg.get("TOD_ENVS", [])

        return tod_switch, tod_envs

    # =========================
    # STATUS
    # =========================
    def get_status(self):
        try:
            if self._is_server_mode():
                return self.api.get("/api/tod/status")

            return self._get_status_local()

        except Exception as e:
            return {"status": "error", "env": str(e)}

    def _get_status_local(self):
        cfg = load_agent_config()
        dry_run = cfg.get("general", {}).get("dry_run", False)

        if dry_run:
            return {"status": "dry-run", "env": "Dry Run ENV"}

        tod_switch, tod_envs = self._get_local_config()

        if not tod_switch:
            return {"status": "unknown", "env": "Not configured"}

        output, error = SSHService.execute_command(
            tod_switch["hostname"],
            tod_switch["username"],
            tod_switch["password"],
            f"show run interface vlan {tod_switch['tod_vlan']}",
        )

        if error:
            return {"status": "error", "env": "Unknown"}

        for env in tod_envs:
            if env["ip_policy_command"] in output:
                return {"status": "connected", "env": env["name"]}

        return {"status": "connected", "env": "Unknown"}

    # =========================
    # OPTIONS
    # =========================
    def get_env_options(self):
        try:
            if self._is_server_mode():
                return self.api.get("/api/tod/options")

            _, tod_envs = self._get_local_config()
            return [env["name"] for env in tod_envs]

        except Exception:
            return []

    # =========================
    # CONNECT
    # =========================
    def connect_env(self, env_name: str):
        try:
            if self._is_server_mode():
                return self.api.post("/api/tod/connect", {"env_name": env_name})

            return self._connect_env_local(env_name)

        except Exception as e:
            return {"success": False, "message": str(e)}

    def _connect_env_local(self, env_name: str):
        cfg = load_agent_config()
        dry_run = cfg.get("general", {}).get("dry_run", False)

        if dry_run:
            return {
                "success": True,
                "message": f"DRY RUN: would connect TOD to {env_name}",
            }

        tod_switch, tod_envs = self._get_local_config()

        target_env = next((e for e in tod_envs if e["name"] == env_name), None)

        if not target_env:
            return {"success": False, "message": "ENV not found"}

        commands = [
            "enable",
            "configure terminal",
            f"interface vlan {tod_switch['tod_vlan']}",
            target_env["ip_policy_command"],
            "no shutdown",
            "end",
            "write memory",
        ]

        output, error = run_ios_commands(
            tod_switch["hostname"],
            tod_switch["username"],
            tod_switch["password"],
            commands,
        )

        if error:
            return {"success": False, "message": error}

        return {
            "success": True,
            "message": f"Connected TOD to {env_name}",
        }