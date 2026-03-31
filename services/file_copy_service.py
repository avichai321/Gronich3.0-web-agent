import os
import posixpath
import shutil
import stat as statmod
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import paramiko

from core.config_manager import (
    get_component_by_name,
    get_kms_station_by_name,
    load_available_keys,
    load_components,
    load_general_settings,
    load_kms_stations,
)
from core.logger import log


class AgentFileCopyService:
    def __init__(self):
        self.current_session: dict | None = None

    def get_options(self) -> dict:
        return {
            "components": load_components(),
            "kms_stations": load_kms_stations(),
            "keys": load_available_keys(),
            "general": load_general_settings(),
        }

    def create_session(
        self,
        component_name: str,
        connection_mode: str,
        kms_station_name: str | None,
        key_name: str,
        override_host: str | None = None,
        override_user: str | None = None,
        override_port: int | None = None,
    ) -> dict:
        components = load_components()
        component = get_component_by_name(components, component_name)
        if not component:
            return {"success": False, "message": f"Component {component_name} not found"}

        settings = load_general_settings()
        keys_dir = settings.get("keys_dir", "")
        local_key_path = os.path.join(keys_dir, key_name)

        if not os.path.isfile(local_key_path):
            return {"success": False, "message": f"Key {key_name} not found in keys_dir"}

        resolved_host = override_host or (
            component.get("maintenance_host") if connection_mode == "bridge" else component.get("direct_host")
        )
        resolved_user = override_user or component.get("username", "")
        resolved_port = override_port or int(component.get("port") or 22)

        kms_station = None
        if connection_mode == "bridge":
            kms_station = get_kms_station_by_name(load_kms_stations(), kms_station_name or "")
            if not kms_station:
                return {"success": False, "message": "KMS station is required for bridge mode"}

        if not resolved_host:
            return {"success": False, "message": "Resolved host is empty"}
        if not resolved_user:
            return {"success": False, "message": "Resolved user is empty"}

        self.current_session = {
            "component_name": component_name,
            "component_host": resolved_host,
            "remote_user": resolved_user,
            "port": resolved_port,
            "connection_mode": connection_mode,
            "kms_station_name": kms_station_name,
            "kms_station": kms_station,
            "key_name": key_name,
            "local_key_path": local_key_path,
        }

        items = self.list_remote_items(".")
        return {
            "success": True,
            "message": "Connected successfully",
            "items": items,
            "current_path": ".",
        }

    def list_remote_items(self, path: str) -> list[dict]:
        if not self.current_session:
            return []

        if self.current_session["connection_mode"] == "bridge":
            return self._browse_local_bridge(path)

        return self._browse_direct(path)

    def _browse_direct(self, path: str) -> list[dict]:
        session = self.current_session
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            session["component_host"],
            username=session["remote_user"],
            key_filename=session["local_key_path"],
            look_for_keys=False,
            allow_agent=False,
            timeout=15,
            port=int(session["port"]),
        )

        try:
            command = f"ls -ltr {path or '.'}"
            _, stdout, stderr = client.exec_command(command, timeout=20)
            output = stdout.read().decode(errors="ignore").strip()
            error = stderr.read().decode(errors="ignore").strip()
        finally:
            client.close()

        combined = "\n".join([x for x in [output, error] if x]).strip()
        return self._parse_or_fallback(combined, path or ".")

    def _browse_local_bridge(self, path: str) -> list[dict]:
        session = self.current_session
        key_path = session["local_key_path"]
        host = session["component_host"]
        user = session["remote_user"]
        port = int(session["port"])
        remote_path = path or "."

        cmd = [
            "ssh",
            "-i", key_path,
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-p", str(port),
            f"{user}@{host}",
            f"ls -ltr {remote_path}",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        combined = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
        return self._parse_or_fallback(combined, remote_path)

    def start_copy(
        self,
        selected_paths: list[str],
        destination_mode: str = "smb",
        override_export_path: str | None = None,
        override_smb_username: str | None = None,
        override_smb_password: str | None = None,
    ) -> dict:
        if not self.current_session:
            return {"success": False, "message": "No active session"}

        if not selected_paths:
            return {"success": False, "message": "No selected paths"}

        settings = load_general_settings()
        component_host = self.current_session["component_host"]
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        try:
            if destination_mode == "download":
                temp_root = Path(tempfile.gettempdir()) / "gronich_agent_downloads" / component_host / timestamp
                temp_root.mkdir(parents=True, exist_ok=True)

                if self.current_session["connection_mode"] == "bridge":
                    self._copy_bridge_local(selected_paths, str(temp_root), use_smb=False)
                else:
                    self._copy_direct(selected_paths, str(temp_root))

                zip_path = self._prepare_download_bundle(str(temp_root))
                return {
                    "success": True,
                    "message": "Download ZIP is ready",
                    "destination_path": zip_path,
                    "download_file": zip_path,
                }

            export_root = override_export_path or settings.get("bridge_export_path") or settings.get("local_export_root", "")
            if not export_root:
                return {"success": False, "message": "No export path configured"}

            if self.current_session["connection_mode"] == "bridge":
                dest = os.path.join(export_root, component_host, timestamp)
                self._copy_bridge_local(
                    selected_paths,
                    dest,
                    use_smb=True,
                    smb_username=override_smb_username or settings.get("bridge_smb_username", ""),
                    smb_password=override_smb_password or settings.get("bridge_smb_password", ""),
                )
            else:
                dest = os.path.join(export_root, component_host, timestamp)
                self._copy_direct(selected_paths, dest)

            return {
                "success": True,
                "message": "Copy completed successfully",
                "destination_path": dest,
            }
        except Exception as exc:
            log(f"File copy failed: {exc}")
            return {"success": False, "message": str(exc)}

    def _copy_direct(self, selected_paths: list[str], destination_path: str) -> None:
        session = self.current_session
        os.makedirs(destination_path, exist_ok=True)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            session["component_host"],
            username=session["remote_user"],
            key_filename=session["local_key_path"],
            look_for_keys=False,
            allow_agent=False,
            timeout=15,
            port=int(session["port"]),
        )

        sftp = client.open_sftp()
        try:
            for src in selected_paths:
                src_name = posixpath.basename(src.rstrip("/")) or "root_item"
                local_target = os.path.join(destination_path, src_name)
                log(f"Downloading {src} -> {local_target}")
                self._download_recursive(sftp, src, local_target)
        finally:
            sftp.close()
            client.close()

    def _copy_bridge_local(
        self,
        selected_paths: list[str],
        destination_path: str,
        use_smb: bool = True,
        smb_username: str = "",
        smb_password: str = "",
    ) -> None:
        session = self.current_session
        os.makedirs(destination_path, exist_ok=True)

        if use_smb and destination_path.startswith("\\\\"):
            self._net_use_base_share(destination_path, smb_username, smb_password)
        else:
            os.makedirs(destination_path, exist_ok=True)

        for src in selected_paths:
            cmd = [
                "scp",
                "-r",
                "-i", session["local_key_path"],
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-P", str(session["port"]),
                f'{session["remote_user"]}@{session["component_host"]}:{src}',
                destination_path,
            ]

            log(f"Running SCP: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "SCP copy failed")

    def _net_use_base_share(self, destination_path: str, smb_username: str, smb_password: str) -> None:
        parts = destination_path.split("\\")
        if len(parts) < 4:
            return

        base_share = "\\".join(parts[:4])
        if not smb_username or not smb_password:
            return

        subprocess.run(
            ["cmd", "/c", "net", "use", base_share, smb_password, f"/user:{smb_username}"],
            capture_output=True,
            text=True,
            timeout=20,
        )

    def _download_recursive(self, sftp: paramiko.SFTPClient, remote_path: str, local_path: str) -> None:
        attrs = sftp.stat(remote_path)

        if statmod.S_ISDIR(attrs.st_mode):
            os.makedirs(local_path, exist_ok=True)
            for entry in sftp.listdir_attr(remote_path):
                child_remote = posixpath.join(remote_path, entry.filename)
                child_local = os.path.join(local_path, entry.filename)
                self._download_recursive(sftp, child_remote, child_local)
            return

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        sftp.get(remote_path, local_path)

    def _prepare_download_bundle(self, source_path: str) -> str:
        bundle_dir = Path(tempfile.gettempdir()) / "gronich_agent_zip"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        bundle_name = f"file_copy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        bundle_path = bundle_dir / bundle_name

        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_path):
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                    arcname = os.path.relpath(full_path, source_path)
                    zf.write(full_path, arcname)

        return str(bundle_path)

    def _parse_or_fallback(self, combined: str, current_path: str) -> list[dict]:
        if not combined:
            return [{"name": "Browse returned no output", "path": current_path, "item_type": "error", "size": None}]

        parsed = self._parse_ls_ltr_output(combined, current_path)
        if parsed:
            return parsed

        return [
            {"name": line, "path": current_path, "item_type": "raw", "size": None}
            for line in combined.splitlines()
            if line.strip()
        ]

    def _parse_ls_ltr_output(self, output: str, current_path: str) -> list[dict]:
        items = []

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("total "):
                continue

            parts = line.split()
            if len(parts) < 9:
                continue

            perms = parts[0]
            size = parts[4]
            name = " ".join(parts[8:])

            if not (perms.startswith("d") or perms.startswith("-") or perms.startswith("l")):
                continue

            item_type = "directory" if perms.startswith("d") else "file"

            if current_path in [".", "/"]:
                full_path = name
            else:
                full_path = f"{current_path.rstrip('/')}/{name}"

            items.append(
                {
                    "name": name,
                    "path": full_path,
                    "item_type": item_type,
                    "size": int(size) if size.isdigit() else None,
                }
            )

        return items