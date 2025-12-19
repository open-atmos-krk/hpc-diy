import os
from cluster_control.checks.node_connectivity_check import NodeConnectivityCheck

STATIC_DHCP_CONFIG = os.getenv("STATIC_DHCP_CONFIG", "/etc/dnsmasq.d/static_dhcp.conf")
ANSIBLE_INVENTORY = os.getenv("ANSIBLE_INVENTORY", "")
HEALTH_CHECK_LIST = [NodeConnectivityCheck()]