import configparser
import os
import sys
from typing import Optional


def get_base_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_PATH = get_base_path()
CONFIG_DIR = os.path.join(BASE_PATH, "config")

CONFIG_FILE = os.path.join(CONFIG_DIR, "agent.ini")
LOCAL_RUNTIME = os.path.join(CONFIG_DIR, "local_runtime.ini")


def _read_config_file(path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if os.path.exists(path):
        config.read(path, encoding="utf-8")
    return config


def load_agent_config() -> configparser.ConfigParser:
    return _read_config_file(CONFIG_FILE)


def save_agent_config(config: configparser.ConfigParser) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        config.write(f)


def load_local_runtime() -> configparser.ConfigParser:
    return _read_config_file(LOCAL_RUNTIME)


def load_general_settings() -> dict:
    config = load_local_runtime()
    return {
        "keys_dir": config.get("general", "keys_dir", fallback=""),
        "bridge_export_path": config.get("general", "bridge_export_path", fallback=""),
        "bridge_smb_username": config.get("general", "bridge_smb_username", fallback=""),
        "bridge_smb_password": config.get("general", "bridge_smb_password", fallback=""),
        "local_export_root": config.get("general", "local_export_root", fallback=""),
        "dry_run": config.getboolean("general", "dry_run", fallback=False),
    }


def load_components() -> list[dict]:
    config = load_local_runtime()
    components: list[dict] = []

    for section in config.sections():
        if section.startswith("COMPONENT_"):
            components.append(
                {
                    "section_name": section,
                    "name": config[section].get("name", ""),
                    "maintenance_host": config[section].get("maintenance_host", ""),
                    "direct_host": config[section].get("direct_host", ""),
                    "username": config[section].get("username", ""),
                    "port": config[section].get("port", "22"),
                    "default_key": config[section].get("default_key", ""),
                }
            )

    return components


def load_kms_stations() -> list[dict]:
    config = load_local_runtime()
    stations: list[dict] = []

    for section in config.sections():
        if section.startswith("KMS_Station_"):
            stations.append(
                {
                    "section_name": section,
                    "name": config[section].get("name", ""),
                    "host": config[section].get("host", "") or config[section].get("ip", ""),
                    "ip": config[section].get("ip", ""),
                    "vlan": config[section].get("vlan", ""),
                    "os_type": config[section].get("os_type", "windows"),
                    "username": config[section].get("username", ""),
                    "password": config[section].get("password", ""),
                    "copy_root": config[section].get("copy_root", r"C:\Temp\copy_jobs"),
                }
            )

    return stations


def load_available_keys() -> list[str]:
    settings = load_general_settings()
    keys_dir = settings.get("keys_dir", "")
    if not keys_dir or not os.path.isdir(keys_dir):
        return []

    return sorted(
        [
            f for f in os.listdir(keys_dir)
            if os.path.isfile(os.path.join(keys_dir, f))
        ]
    )


def get_component_by_name(components: list[dict], target_name: str) -> Optional[dict]:
    for component in components:
        if component.get("name") == target_name:
            return component
    return None


def get_kms_station_by_name(kms_stations: list[dict], target_name: str) -> Optional[dict]:
    for station in kms_stations:
        if station.get("name") == target_name:
            return station
    return None


def get_single_section(config_dict: dict, section_prefix: str) -> dict:
    for key, value in config_dict.items():
        if key.startswith(section_prefix):
            return value
    return {}


def find_ate_by_name(ate_list: list[dict], target_name: str) -> Optional[dict]:
    for item in ate_list:
        if item.get("name") == target_name:
            return item
    return None


def load_all_config(config_file: str = LOCAL_RUNTIME):
    config = _read_config_file(config_file)

    ate_switches_list = []
    kms_switch = {}
    dl_switch = {}
    kms_stations = []
    env_state = []
    tod_switch = {}
    tod_envs = []

    for section in config.sections():
        if section.startswith("ate_switch_"):
            ate_switches_list.append(
                {
                    "section_name": section,
                    "name": config[section].get("name", ""),
                    "ip": config[section].get("ip", ""),
                    "username": config[section].get("username", ""),
                    "password": config[section].get("password", ""),
                    "ate_dl_port": config[section].get("ate_dl_port", ""),
                    "ate_core_port": config[section].get("ate_core_port", ""),
                    "ges_ports": config[section].get("ges_ports", ""),
                    "dl_gr_sw_port": config[section].get("dl_gr_sw_port", ""),
                }
            )

        elif section.startswith("KMS_SWITCH"):
            kms_switch[section] = {
                "section_name": section,
                "hostname": config[section].get("hostname", ""),
                "username": config[section].get("username", ""),
                "password": config[section].get("password", ""),
                "kms_ports": config[section].get("kms_ports", ""),
            }

        elif section.startswith("DL_SWITCH"):
            dl_switch[section] = {
                "section_name": section,
                "hostname": config[section].get("hostname", ""),
                "username": config[section].get("username", ""),
                "password": config[section].get("password", ""),
                "dl_ports": config[section].get("dl_ports", ""),
            }

        elif section.startswith("TOD_ATE_SWITCH"):
            tod_switch[section] = {
                "section_name": section,
                "hostname": config[section].get("hostname", ""),
                "username": config[section].get("username", ""),
                "password": config[section].get("password", ""),
                "tod_vlan": config[section].get("tod_vlan", ""),
            }

        elif section.startswith("TOD_ENV_"):
            tod_envs.append(
                {
                    "section_name": section,
                    "name": config[section].get("name", ""),
                    "ip_policy_command": config[section].get("ip_policy_command", ""),
                }
            )

        elif section.startswith("KMS_Station_"):
            kms_stations.append(
                {
                    "section_name": section,
                    "name": config[section].get("name", ""),
                    "vlan": config[section].get("vlan", ""),
                    "host": config[section].get("host", ""),
                    "ip": config[section].get("ip", ""),
                    "os_type": config[section].get("os_type", "windows"),
                    "username": config[section].get("username", ""),
                    "password": config[section].get("password", ""),
                    "copy_root": config[section].get("copy_root", r"C:\Temp\copy_jobs"),
                }
            )

        elif section.startswith("state_env_"):
            item = {
                "section_name": section,
                "env_name": config[section].get("env_name", ""),
            }
            for key, value in config[section].items():
                if key != "env_name":
                    item[key] = value
            env_state.append(item)

    return ate_switches_list, kms_switch, dl_switch, kms_stations, env_state, tod_switch, tod_envs


def build_vlan_to_kms_map(kms_stations: list[dict]) -> dict[str, str]:
    vlan_map: dict[str, str] = {}
    for kms in kms_stations:
        vlan = str(kms.get("vlan", "")).strip()
        name = str(kms.get("name", "")).strip()
        if vlan and name:
            vlan_map[vlan] = name
    return vlan_map


def build_vlan_to_env_map(env_states: list[dict]) -> dict[str, str]:
    vlan_map: dict[str, str] = {}
    for env in env_states:
        env_name = env.get("env_name", "")
        if not env_name or env_name == "default":
            continue

        for key, value in env.items():
            if key.startswith("state_") and isinstance(value, str):
                vlan_list = value.replace(" ", "").split(",")
                for vlan in vlan_list:
                    if vlan:
                        vlan_map[vlan] = env_name
    return vlan_map


def get_env_names(env_list: list[dict]) -> list[str]:
    env_names = []
    for env in env_list:
        env_name = env.get("env_name", "")
        if env_name and env_name != "default":
            env_names.append(env_name)
    return env_names


def get_env_state_by_name(env_state: list[dict], name: str) -> list[str]:
    for env in env_state:
        if env.get("env_name") == name:
            return [key for key in env.keys() if key.startswith("state_")]
    return []