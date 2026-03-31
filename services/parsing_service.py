import re


def parse_show_interfaces_status(output: str) -> list[dict]:
    rows: list[dict] = []
    for line in output.splitlines():
        if line.startswith("Port"):
            continue

        parts = line.split()
        if len(parts) >= 4 and (line.startswith("Gi") or line.startswith("Fa") or line.startswith("Te")):
            rows.append(
                {
                    "interface": parts[0],
                    "description": parts[1],
                    "vlan": parts[3],
                }
            )
    return rows


def parse_show_run_interfaces(output: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    interfaces = output.split("interface ")

    for block in interfaces[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue

        intf_name = lines[0].strip()
        if intf_name.startswith("Vlan"):
            continue

        intf_desc = ""
        vlans: set[str] = set()

        for line in lines:
            line = line.strip()

            if line.startswith("description"):
                intf_desc = line.replace("description", "").strip()

            match = re.search(r"switchport access vlan (\d+)", line)
            if match:
                vlans.add(match.group(1))

            match = re.search(r"switchport trunk allowed vlan (.+)", line)
            if match:
                vlan_part = match.group(1)
                for part in vlan_part.split(","):
                    if "-" in part:
                        start, end = map(int, part.split("-"))
                        vlans.update(str(v) for v in range(start, end + 1))
                    else:
                        val = part.strip()
                        if val:
                            vlans.add(val)

            match = re.search(r"switchport vlan mapping \d+\s+(\d+)", line)
            if match:
                vlans.add(match.group(1))

        if vlans or intf_desc:
            if intf_desc.startswith("env"):
                continue

            result[intf_name] = {
                "description": intf_desc,
                "vlans": list(sorted(vlans)),
            }

    return result