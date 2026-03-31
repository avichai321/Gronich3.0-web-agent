def get_port_by_desc(dict_ports: dict[str, str], val: str) -> str | None:
    for key, value in dict_ports.items():
        if value == val:
            return key
    return None


def expand_interface_name(short_name: str) -> str:
    original = short_name
    short_name = short_name.lower()
    mapping = {
        "gi": "GigabitEthernet",
        "fa": "FastEthernet",
        "te": "TenGigabitEthernet",
        "po": "Port-channel",
        "lo": "Loopback",
    }
    for short, full in mapping.items():
        if short_name.startswith(short):
            return original.replace(original[: len(short)], full, 1)
    return original


def identify_state_for_interface(interface_vlans: list[str], env_dict: dict) -> str | None:
    interface_vlans_sorted = sorted(interface_vlans)
    for key, value in env_dict.items():
        if key.startswith("state_") and isinstance(value, str):
            state_vlans = value.replace(" ", "").split(",")
            if sorted(state_vlans) == interface_vlans_sorted:
                return key
    return None