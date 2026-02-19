import os
import pathlib
from cluster_control.checks.node_connectivity_check import NodeConnectivityCheck

ANSIBLE_INVENTORY = os.getenv("ANSIBLE_INVENTORY", "")
HEALTH_CHECK_LIST = [NodeConnectivityCheck()]

def get_dhcp_config_path():
    """Get the path to the static DHCP configuration file."""
    return os.getenv("STATIC_DHCP_CONFIG", "/etc/dnsmasq.d/static_dhcp.conf")

def get_dnsmasq_config_path():
    """Get the path to the dnsmasq configuration file."""
    return os.getenv("DNSMASQ_CONFIG", "/etc/dnsmasq.conf")

def get_available_ips_path():
    """Get the path to the runtime available IPs file."""
    return pathlib.Path("/run/cluster-control/available_ips.txt")
