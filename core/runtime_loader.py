import configparser
import os


def load_runtime_config(path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if os.path.exists(path):
        config.read(path)
    return config


def load_general_settings(path: str) -> dict:
    config = load_runtime_config(path)
    return {
        "keys_dir": config.get("general", "keys_dir", fallback=""),
        "bridge_export_path": config.get("general", "bridge_export_path", fallback=""),
        "bridge_smb_username": config.get("general", "bridge_smb_username", fallback=""),
        "bridge_smb_password": config.get("general", "bridge_smb_password", fallback=""),
        "local_export_root": config.get("general", "local_export_root", fallback=""),
        "dry_run": config.getboolean("general", "dry_run", fallback=False),
    }


def load_components(path: str) -> list[dict]:
    config = load_runtime_config(path)
    components: list[dict] = []

    for section in config.sections():
        if section.startswith("COMPONENT_"):
            components.append(
                {
                    "name": config[section].get("name", ""),
                    "maintenance_host": config[section].get("maintenance_host", ""),
                    "direct_host": config[section].get("direct_host", ""),
                    "username": config[section].get("username", ""),
                    "port": config[section].get("port", ""),
                    "default_key": config[section].get("default_key", ""),
                }
            )
    return components


def load_kms_stations(path: str) -> list[dict]:
    config = load_runtime_config(path)
    stations: list[dict] = []

    for section in config.sections():
        if section.startswith("KMS_Station_"):
            stations.append(
                {
                    "name": config[section].get("name", ""),
                    "host": config[section].get("host", ""),
                    "ip": config[section].get("ip", ""),
                    "os_type": config[section].get("os_type", "windows"),
                    "username": config[section].get("username", ""),
                    "password": config[section].get("password", ""),
                    "copy_root": config[section].get("copy_root", r"C:\Temp\copy_jobs"),
                }
            )
    return stations


def load_available_keys(keys_dir: str) -> list[str]:
    if not keys_dir or not os.path.isdir(keys_dir):
        return []

    return sorted(
        [
            f
            for f in os.listdir(keys_dir)
            if os.path.isfile(os.path.join(keys_dir, f))
        ]
    )