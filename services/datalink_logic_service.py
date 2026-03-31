from core.config_manager import find_ate_by_name


def get_env_vlans_str_by_state(env_states: list[dict], state_label: str, env_label: str) -> str:
    for env in env_states:
        env_name = env.get("env_name")
        if env_name == env_label:
            for key, value in env.items():
                if key == state_label:
                    if isinstance(value, list):
                        return ",".join(str(v) for v in value)
                    if isinstance(value, str):
                        return value
    return ""


def generate_vlan_config_dl_switch_between_envs(source_env_name: str, target_env_name: str, state_key: str, ate_states: list[dict]) -> list[str]:
    source_env = None
    target_env = None

    for env in ate_states:
        if env.get("env_name") == source_env_name:
            source_env = env
        elif env.get("env_name") == target_env_name:
            target_env = env

    if not source_env or not target_env:
        raise ValueError("One or both environments not found")

    default_vlans = source_env.get(state_key, "")
    target_vlans = target_env.get(state_key, "")

    if "," not in default_vlans and "," not in target_vlans:
        return [
            "switchport mode access",
            f"switchport access vlan {target_vlans.strip()}",
            "spanning-tree portfast",
            "no shutdown",
        ]

    default_list = [v.strip() for v in default_vlans.split(",") if v.strip()]
    target_list = [v.strip() for v in target_vlans.split(",") if v.strip()]

    if len(default_list) != len(target_list):
        raise ValueError(f"VLAN count mismatch between environments for state: {state_key}")

    commands = [
        "switchport mode trunk",
        "switchport trunk native vlan 999",
        "spanning-tree bpdufilter enable",
        "no shutdown",
    ]
    for src, dst in zip(default_list, target_list):
        if src != dst:
            commands.append(f"switchport vlan mapping {src} {dst}")
    return commands


def generate_vlan_config_dl_ate_port_switch_default(source_env_name: str, state_key: str, ate_states: list[dict]) -> list[str]:
    source_env = None
    for env in ate_states:
        if env.get("env_name") == source_env_name:
            source_env = env

    if not source_env:
        raise ValueError("Environment not found")

    default_vlans = source_env.get(state_key, "")
    if "," not in default_vlans:
        return [
            "switchport mode access",
            f"switchport access vlan {default_vlans.strip()}",
            "speed 100",
            "duplex full",
            "spanning-tree portfast",
            "no shutdown",
        ]

    return [
        "switchport mode trunk",
        f"switchport trunk allowed vlan {default_vlans.strip()}",
        "speed 100",
        "duplex full",
        "no shutdown",
    ]


def generate_vlan_config_dl_ate_gronich_port_switch_default(source_env_name: str, state_key: str, ate_states: list[dict]) -> list[str]:
    source_env = None
    for env in ate_states:
        if env.get("env_name") == source_env_name:
            source_env = env

    if not source_env:
        raise ValueError("Environment not found")

    default_vlans = source_env.get(state_key, "")
    if "," not in default_vlans:
        return [
            "switchport mode access",
            f"switchport access vlan {default_vlans.strip()}",
            "spanning-tree portfast",
            "no shutdown",
        ]

    return [
        "switchport mode trunk",
        f"switchport trunk allowed vlan {default_vlans.strip()}",
        "no shutdown",
    ]


def get_ate_station_for_plane(ate_switches: list[dict], plane_description: str) -> dict | None:
    return find_ate_by_name(ate_switches, plane_description)