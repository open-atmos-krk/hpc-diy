import ipaddress
import re
import subprocess
from pathlib import Path
from cluster_control.utils.paths import get_available_ips_path, get_dnsmasq_config_path

IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def get_available_ips():
    conf_path = Path(get_dnsmasq_config_path())
    iface = _parse_interface(conf_path)
    if not iface:
        raise RuntimeError("no dnsmasq interface configured")

    network = _get_iface_network(iface)
    iface_ip = _get_iface_ip(iface)
    dhcp_ranges = _parse_dhcp_ranges(conf_path)
    excludes = [iface_ip]

    available = _collect_available_ips(network, dhcp_ranges, excludes)
    return available

def _run_ip_addr_show(iface: str) -> str:
    try:
        result = subprocess.run(
            ["ip", "-4", "-br", "addr", "show", "dev", iface],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stderr.strip() or "failed to run ip") from exc
    return result.stdout.strip()


def _get_iface_network(iface: str) -> ipaddress.IPv4Network:
    output = _run_ip_addr_show(iface)
    if not output:
        raise RuntimeError(f"no output for interface {iface}")
    # Example: "enp0s9 UP 172.16.0.1/24"
    for token in output.split():
        if "/" in token:
            try:
                ip_interface = ipaddress.ip_interface(token)
            except ValueError:
                continue
            if isinstance(ip_interface, ipaddress.IPv4Interface):
                return ip_interface.network
    raise RuntimeError(f"no IPv4 address found on {iface}")

def _get_iface_ip(iface: str) -> ipaddress.IPv4Address:
    output = _run_ip_addr_show(iface)
    for token in output.split():
        if "/" in token:
            try:
                ip_interface = ipaddress.ip_interface(token)
            except ValueError:
                continue
            if isinstance(ip_interface, ipaddress.IPv4Interface):
                return ip_interface.ip
    raise RuntimeError(f"no IPv4 address found on {iface}")

def _parse_dhcp_ranges(conf_path: Path):
    ranges = []
    try:
        content = conf_path.read_text(encoding="utf-8")
    except OSError:
        return ranges
    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line:
            continue
        if not line.startswith("dhcp-range"):
            continue
        ips = IPV4_RE.findall(line)
        if len(ips) < 2:
            continue
        try:
            start = ipaddress.IPv4Address(ips[0])
            end = ipaddress.IPv4Address(ips[1])
        except ipaddress.AddressValueError:
            continue
        if int(end) < int(start):
            start, end = end, start
        ranges.append((start, end))
    return ranges

def _parse_interface(conf_path: Path):
    try:
        content = conf_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for raw_line in content.splitlines():
        # remove commennts and whitespaces
        line = raw_line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line.startswith("interface"):
            continue
        # TODO: test both "interface=eth0" and "interface = eth0" formats
        key, value = line.split("=", 1)
        if key.strip() != "interface":
            continue
        return value.strip()
    return ""

def _iter_range(start: ipaddress.IPv4Address, end: ipaddress.IPv4Address):
    current = int(start)
    last = int(end)
    while current <= last:
        yield ipaddress.IPv4Address(current)
        current += 1

def _collect_available_ips(network: ipaddress.IPv4Network, dhcp_ranges, excludes):
    excluded = set(excludes)
    for start, end in dhcp_ranges:
        for ip in _iter_range(start, end):
            excluded.add(ip)

    available = []
    for ip in network.hosts():
        if ip in excluded:
            continue
        available.append(ip)
    return available

def _read_available_ips():
    available_ips_file = get_available_ips_path()
    if not available_ips_file.exists():
        return []
    lines = available_ips_file.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]

def write_available_ips(ips):
    content = "\n".join(ips)
    if content:
        content += "\n"
    get_available_ips_path().write_text(content, encoding="utf-8")

def pop_available_ip():
    ips = _read_available_ips()
    if not ips:
        raise RuntimeError("no available IPs left")
    ip = ips.pop(0)
    write_available_ips(ips)
    return ip
