from core.config_manager import load_all_config, build_vlan_to_kms_map, get_single_section
from services.helpers_service import get_port_by_desc
from services.parsing_service import parse_show_interfaces_status
from services.ssh_service import SSHService, run_ios_commands


class AgentKmsService:
    def _get_runtime(self):
        _, kms_switch, _, kms_stations, _ = load_all_config()
        kms_info = get_single_section(kms_switch, "KMS_SWITCH")
        if not kms_info:
            return {}, {}, [], {}, []

        plane_ports = [p.strip() for p in kms_info.get("kms_ports", "").split(",") if p.strip()]
        vlan_to_station = build_vlan_to_kms_map(kms_stations)

        output, error = SSHService.execute_command(
            kms_info["hostname"],
            kms_info["username"],
            kms_info["password"],
            "show interfaces status",
        )
        if error:
            return kms_info, {}, plane_ports, vlan_to_station, []

        int_kms_dec: dict[str, str] = {}
        rows: list[dict] = []

        for item in parse_show_interfaces_status(output):
            if item["interface"] not in plane_ports:
                continue
            if "KMS" in item["description"] or "env" in item["description"]:
                continue

            int_kms_dec[item["interface"]] = item["description"]
            station_name = vlan_to_station.get(item["vlan"], "Free to connect")
            status = "connected" if item["vlan"] in vlan_to_station else "free"

            rows.append(
                {
                    "interface": item["interface"],
                    "description": item["description"],
                    "vlan": item["vlan"],
                    "station_name": station_name,
                    "status": status,
                }
            )

        return kms_info, int_kms_dec, plane_ports, vlan_to_station, rows

    def _build_dry_run_rows_from_config(self):
        _, kms_switch, _, kms_stations, _ = load_all_config()
        kms_info = get_single_section(kms_switch, "KMS_SWITCH")
        plane_ports = [p.strip() for p in kms_info.get("kms_ports", "").split(",") if p.strip()] if kms_info else []
        vlan_to_station = build_vlan_to_kms_map(kms_stations)

        rows = []
        station_values = list(vlan_to_station.values())

        for idx, port in enumerate(plane_ports):
            rows.append(
                {
                    "interface": port,
                    "description": port,
                    "vlan": "999",
                    "station_name": station_values[idx % len(station_values)] if station_values else "Dry Run",
                    "status": "dry-run",
                }
            )

        return rows

    def get_rows(self):
        _, _, _, _, rows = self._get_runtime()
        if rows:
            return rows
        return self._build_dry_run_rows_from_config()

    def get_options(self):
        _, _, _, vlan_to_station, rows = self._get_runtime()

        if rows:
            used_vlans = {row["vlan"] for row in rows if row["status"] == "connected"}
            free_stations = [name for vlan, name in vlan_to_station.items() if vlan not in used_vlans]
            planes = [row["description"] for row in rows]
            return {
                "planes": planes,
                "stations": sorted(free_stations),
            }

        dry_rows = self._build_dry_run_rows_from_config()
        return {
            "planes": [row["description"] for row in dry_rows],
            "stations": sorted(list(vlan_to_station.values())),
        }

    def connect_station(self, plane_description: str, station_name: str):
        kms_info, int_kms_dec, _, vlan_to_station, rows = self._get_runtime()

        if not rows:
            dry_rows = self._build_dry_run_rows_from_config()
            plane_names = [row["description"] for row in dry_rows]
            station_names = list(vlan_to_station.values())

            if plane_description not in plane_names:
                return {"success": False, "message": f"Plane {plane_description} not found"}
            if station_name not in station_names:
                return {"success": False, "message": f"Station {station_name} not found"}

            return {
                "success": True,
                "message": f"DRY RUN: would connect {station_name} to {plane_description}",
            }

        interface = get_port_by_desc(int_kms_dec, plane_description)
        target_vlan = get_port_by_desc(vlan_to_station, station_name)

        if not interface:
            return {"success": False, "message": f"Plane {plane_description} not found"}
        if not target_vlan:
            return {"success": False, "message": f"Station {station_name} not found"}

        for row in rows:
            if row["station_name"] == station_name and row["status"] == "connected":
                return {"success": False, "message": f"{station_name} already in use"}

        current_row = next((row for row in rows if row["description"] == plane_description), None)
        if not current_row:
            return {"success": False, "message": f"Plane {plane_description} not found in current KMS rows"}

        if current_row["vlan"] != "999":
            return {"success": False, "message": f"{plane_description} already in use"}

        commands = [
            "enable",
            "configure terminal",
            f"interface range {interface}",
            "switchport mode access",
            f"switchport access vlan {target_vlan}",
            "no shutdown",
            "exit",
            "exit",
            "write memory",
            "exit",
        ]

        output, error = run_ios_commands(
            kms_info["hostname"],
            kms_info["username"],
            kms_info["password"],
            commands,
        )

        if error:
            return {"success": False, "message": error, "output": output}

        return {
            "success": True,
            "message": f"{station_name} connected successfully to {plane_description}",
            "interface": interface,
            "vlan": target_vlan,
            "output": output,
        }

    def disconnect_station(self, plane_description: str):
        kms_info, int_kms_dec, _, _, rows = self._get_runtime()

        if not rows:
            dry_rows = self._build_dry_run_rows_from_config()
            plane_names = [row["description"] for row in dry_rows]

            if plane_description not in plane_names:
                return {"success": False, "message": f"Plane {plane_description} not found"}

            return {
                "success": True,
                "message": f"DRY RUN: would disconnect service from {plane_description}",
            }

        interface = get_port_by_desc(int_kms_dec, plane_description)
        if not interface:
            return {"success": False, "message": f"Plane {plane_description} not found"}

        current_row = next((row for row in rows if row["description"] == plane_description), None)
        if not current_row:
            return {"success": False, "message": f"Plane {plane_description} not found in current KMS rows"}

        if current_row["status"] != "connected":
            return {"success": False, "message": f"{plane_description} is already free"}

        commands = [
            "enable",
            "configure terminal",
            f"interface range {interface}",
            "switchport mode access",
            "switchport access vlan 999",
            "shutdown",
            "exit",
            "exit",
            "write memory",
            "exit",
        ]

        output, error = run_ios_commands(
            kms_info["hostname"],
            kms_info["username"],
            kms_info["password"],
            commands,
        )

        if error:
            return {"success": False, "message": error, "output": output}

        return {
            "success": True,
            "message": f"Disconnected service from {plane_description}",
            "interface": interface,
            "output": output,
        }