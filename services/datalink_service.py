from concurrent.futures import ThreadPoolExecutor, as_completed

from core.config_manager import load_all_config, build_vlan_to_env_map, get_env_names, get_env_state_by_name, get_single_section
from services.datalink_logic_service import (
    get_env_vlans_str_by_state,
    generate_vlan_config_dl_switch_between_envs,
    generate_vlan_config_dl_ate_port_switch_default,
    generate_vlan_config_dl_ate_gronich_port_switch_default,
    get_ate_station_for_plane,
)
from services.helpers_service import get_port_by_desc, expand_interface_name, identify_state_for_interface
from services.parsing_service import parse_show_interfaces_status, parse_show_run_interfaces
from services.ssh_service import SSHService, run_ios_commands, reset_interface_and_apply


class AgentDataLinkService:
    def _get_runtime(self):
        ate_switches, _, dl_switch, _, env_state ,_ ,_= load_all_config()
        dl_info = get_single_section(dl_switch, "DL_SWITCH")
        if not dl_info:
            return ate_switches, {}, env_state, [], {}, {}

        plane_dl_ports = [p.strip() for p in dl_info.get("dl_ports", "").split(",") if p.strip()]

        status_output, status_error = SSHService.execute_command(
            dl_info["hostname"],
            dl_info["username"],
            dl_info["password"],
            "show interfaces status",
        )
        run_output, run_error = SSHService.execute_command(
            dl_info["hostname"],
            dl_info["username"],
            dl_info["password"],
            "show run",
        )

        interface_desc_map: dict[str, str] = {}
        if not status_error:
            for item in parse_show_interfaces_status(status_output):
                if item["interface"] in plane_dl_ports:
                    if "KMS" in item["description"] or "env" in item["description"]:
                        continue
                    interface_desc_map[item["interface"]] = item["description"]

        parsed_run = parse_show_run_interfaces(run_output) if not run_error else {}
        return ate_switches, dl_info, env_state, plane_dl_ports, interface_desc_map, parsed_run

    def _build_dry_run_rows_from_config(self):
        _, _, dl_switch, _, env_state ,_ ,_= load_all_config()
        dl_info = get_single_section(dl_switch, "DL_SWITCH")
        plane_dl_ports = [p.strip() for p in dl_info.get("dl_ports", "").split(",") if p.strip()] if dl_info else []
        env_names = get_env_names(env_state)

        rows = []
        for port in plane_dl_ports:
            rows.append(
                {
                    "interface": port,
                    "description": port,
                    "vlans": [],
                    "environment": env_names[0] if env_names else "Dry Run",
                    "maintenance": "Dry Run",
                    "ate_state": "Dry Run",
                    "health": "dry-run",
                }
            )
        return rows

    def get_rows(self):
        ate_switches, dl_info, env_state, plane_dl_ports, interface_desc_map, parsed_run = self._get_runtime()
        del ate_switches, dl_info, plane_dl_ports

        vlan_to_env = build_vlan_to_env_map(env_state)
        rows = []

        for interface, desc in interface_desc_map.items():
            run_data = parsed_run.get(
                expand_interface_name(interface),
                parsed_run.get(interface, {"description": desc, "vlans": []}),
            )
            vlans = run_data.get("vlans", [])
            environment = "Free to connect"
            if vlans:
                environment = vlan_to_env.get(vlans[0], "Free to connect")

            maintenance = self.get_maintenance_by_plane(desc)
            ate_state = self.get_ate_state_by_plane(desc)
            health = "healthy" if environment != "Free to connect" else "free"

            if maintenance.startswith("Connected to"):
                health = "warning"
            if ate_state == "Unknown":
                health = "warning" if health != "free" else health

            rows.append(
                {
                    "interface": interface,
                    "description": desc,
                    "vlans": vlans,
                    "environment": environment,
                    "maintenance": maintenance,
                    "ate_state": ate_state,
                    "health": health,
                }
            )

        if rows:
            return rows

        return self._build_dry_run_rows_from_config()

    def get_options(self):
        rows = self.get_rows()
        _, _, _, _, env_state ,_ ,_= load_all_config()
        envs = get_env_names(env_state)
        state_map = {env: get_env_state_by_name(env_state, env) for env in envs}
        return {
            "planes": [row["description"] for row in rows],
            "envs": envs,
            "states_by_env": state_map,
        }

    def get_maintenance_by_plane(self, plane_description: str) -> str:
        _, kms_switch, _, kms_stations, _ ,_ ,_= load_all_config()
        kms_info = get_single_section(kms_switch, "KMS_SWITCH")
        if not kms_info:
            return "Dry Run"

        vlan_to_station = {v: n for v, n in [(s.get("vlan", ""), s.get("name", "")) for s in kms_stations] if v and n}

        output, error = SSHService.execute_command(
            kms_info["hostname"],
            kms_info["username"],
            kms_info["password"],
            "show interfaces status",
        )
        if error:
            return "Dry Run"

        for item in parse_show_interfaces_status(output):
            if item["description"] == plane_description:
                station = vlan_to_station.get(item["vlan"])
                if station:
                    return f"Connected to {station}"
                return "OFF"
        return "Unknown"

    def _get_interface_vlans(self, ip: str, username: str, password: str, target_interface: str) -> dict:
        output, error = SSHService.execute_command(ip, username, password, "show run")
        if error:
            return {"error": error}
        parsed = parse_show_run_interfaces(output)
        return parsed.get(target_interface) or parsed.get(expand_interface_name(target_interface)) or {
            "error": f"Interface {target_interface} not found"
        }

    def get_ate_state_by_plane(self, plane_description: str) -> str:
        ate_switches, _, _, _, env_state ,_ ,_= load_all_config()
        ate_station = get_ate_station_for_plane(ate_switches, plane_description)

        if ate_station is None:
            rows = self.get_rows_basic_without_recursive_checks()
            target = next((row for row in rows if row["description"] == plane_description), None)
            if not target:
                return "Dry Run"
            for env in env_state:
                matched = identify_state_for_interface(target["vlans"], env)
                if matched:
                    return matched
            return "Dry Run"

        ate_dl_int = self._get_interface_vlans(
            ate_station["ip"],
            ate_station["username"],
            ate_station["password"],
            expand_interface_name(ate_station["ate_dl_port"]),
        )
        if "error" in ate_dl_int:
            return "Dry Run"

        dl_vlan_list = ate_dl_int.get("vlans", [])
        for env in env_state:
            matched = identify_state_for_interface(dl_vlan_list, env)
            if matched:
                return matched
        return "Unknown"

    def get_rows_basic_without_recursive_checks(self):
        _, _, env_state, _, interface_desc_map, parsed_run = self._get_runtime()
        vlan_to_env = build_vlan_to_env_map(env_state)
        rows = []
        for interface, desc in interface_desc_map.items():
            run_data = parsed_run.get(
                expand_interface_name(interface),
                parsed_run.get(interface, {"description": desc, "vlans": []}),
            )
            vlans = run_data.get("vlans", [])
            environment = vlan_to_env.get(vlans[0], "Free to connect") if vlans else "Free to connect"
            rows.append(
                {
                    "interface": interface,
                    "description": desc,
                    "vlans": vlans,
                    "environment": environment,
                    "maintenance": "Unknown",
                    "ate_state": "Unknown",
                    "health": "healthy" if environment != "Free to connect" else "free",
                }
            )
        return rows

    def connect_env(self, plane_description: str, env_name: str, state_name: str):
        ate_switches, dl_info, env_state, _, interface_desc_map, _ = self._get_runtime()

        if not interface_desc_map:
            dry_rows = self._build_dry_run_rows_from_config()
            plane_names = [row["description"] for row in dry_rows]
            if plane_description not in plane_names:
                return {"success": False, "message": f"Plane {plane_description} not found on DL switch"}

            return {
                "success": True,
                "message": f"DRY RUN: would connect {plane_description} to {env_name} with {state_name}",
            }

        dl_sw_gr_port = get_port_by_desc(interface_desc_map, plane_description)
        if not dl_sw_gr_port:
            return {"success": False, "message": f"Plane {plane_description} not found on DL switch"}

        str_default_vlan = get_env_vlans_str_by_state(env_state, state_name, "default")
        ate_station = get_ate_station_for_plane(ate_switches, plane_description)

        try:
            command_change_ate_dl_vlans = generate_vlan_config_dl_ate_port_switch_default("default", state_name, env_state)
            command_change_ate_dl_gronich_vlans = generate_vlan_config_dl_ate_gronich_port_switch_default("default", state_name, env_state)
            commands_gr_enter = generate_vlan_config_dl_switch_between_envs("default", env_name, state_name, env_state)
        except Exception as exc:
            return {"success": False, "message": str(exc)}

        command_remove_trunk_dl = [f"switchport trunk allowed vlan remove {str_default_vlan}", "no shutdown"]
        command_add_trunk_dl = [f"switchport trunk allowed vlan add {str_default_vlan}", "no shutdown"]
        command_add_acl_to_l1 = ["ip access-group permit_remote_dc in", "no shutdown"]
        command_add_acl_to_ges_local = ["ip access-group deny_remote_dc in", "no shutdown"]
        shut_command = ["shutdown"]
        no_shut_command = ["no shutdown"]

        tasks = []

        if ate_station is None:
            tasks.append(
                (reset_interface_and_apply, (dl_info["hostname"], dl_info["username"], dl_info["password"], dl_sw_gr_port, commands_gr_enter, False))
            )
        else:
            if env_name in ["DC", "L1"]:
                tasks.extend(
                    [
                        (reset_interface_and_apply, (dl_info["hostname"], dl_info["username"], dl_info["password"], dl_sw_gr_port, commands_gr_enter, True)),
                        (reset_interface_and_apply, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["dl_gr_sw_port"], command_change_ate_dl_gronich_vlans, True)),
                        (self._run_interface_commands, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ate_core_port"], command_add_trunk_dl)),
                        (self._run_interface_commands, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ate_core_port"], command_add_acl_to_l1)),
                        (reset_interface_and_apply, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ate_dl_port"], command_change_ate_dl_vlans, False)),
                        (self._run_interface_commands, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ges_ports"], shut_command)),
                        (self._configure_vlan_interfaces, (ate_station["ip"], ate_station["username"], ate_station["password"], str_default_vlan, False)),
                    ]
                )
            elif env_name == "Ges_local":
                tasks.extend(
                    [
                        (reset_interface_and_apply, (dl_info["hostname"], dl_info["username"], dl_info["password"], dl_sw_gr_port, commands_gr_enter, True)),
                        (reset_interface_and_apply, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ate_dl_port"], command_change_ate_dl_vlans, False)),
                        (self._run_interface_commands, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ate_core_port"], command_add_trunk_dl)),
                        (self._run_interface_commands, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ate_core_port"], command_add_acl_to_ges_local)),
                        (reset_interface_and_apply, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["dl_gr_sw_port"], command_change_ate_dl_gronich_vlans, True)),
                        (self._configure_vlan_interfaces, (ate_station["ip"], ate_station["username"], ate_station["password"], str_default_vlan, False)),
                        (self._run_interface_commands, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ges_ports"], no_shut_command)),
                    ]
                )
            else:
                tasks.extend(
                    [
                        (self._run_interface_commands, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ate_core_port"], command_remove_trunk_dl)),
                        (self._run_interface_commands, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ges_ports"], shut_command)),
                        (reset_interface_and_apply, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["ate_dl_port"], command_change_ate_dl_vlans, False)),
                        (reset_interface_and_apply, (dl_info["hostname"], dl_info["username"], dl_info["password"], dl_sw_gr_port, commands_gr_enter, False)),
                        (reset_interface_and_apply, (ate_station["ip"], ate_station["username"], ate_station["password"], ate_station["dl_gr_sw_port"], command_change_ate_dl_gronich_vlans, False)),
                        (self._configure_vlan_interfaces, (ate_station["ip"], ate_station["username"], ate_station["password"], str_default_vlan, True)),
                    ]
                )

        results = []
        with ThreadPoolExecutor(max_workers=min(8, len(tasks) or 1)) as executor:
            futures = [executor.submit(func, *args) for func, args in tasks]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append((False, str(exc)))

        failed = [r for r in results if isinstance(r, tuple) and r and r[0] is False]
        if failed:
            return {"success": False, "message": "One or more DL actions failed", "results": results}

        return {
            "success": True,
            "message": f"Connected {plane_description} to {env_name} with {state_name}",
            "results": results,
        }

    def _run_interface_commands(self, hostname: str, username: str, password: str, interface: str, commands: list[str]):
        command_seq = [
            "enable",
            "configure terminal",
            f"interface range {interface}",
            *commands,
            "exit",
            "exit",
            "write memory",
            "exit",
        ]
        output, error = run_ios_commands(hostname, username, password, command_seq)
        if error:
            return False, error
        return True, output

    def _configure_vlan_interfaces(self, ip: str, username: str, password: str, vlans_string: str, shutdown: bool = True):
        try:
            action = "shutdown" if shutdown else "no shutdown"
            vlan_list = [v.strip() for v in vlans_string.split(",")] if "," in vlans_string else [vlans_string.strip()]
            command_seq = ["enable", "configure terminal"]
            for vlan in vlan_list:
                command_seq.append(f"interface vlan {vlan}")
                command_seq.append(action)
            command_seq.extend(["end", "write memory", "exit"])
            output, error = run_ios_commands(ip, username, password, command_seq)
            if error:
                return False, error
            return True, output
        except Exception as exc:
            return False, str(exc)