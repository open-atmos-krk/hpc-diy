import pathlib
import subprocess
from fastapi import FastAPI
from pydantic import BaseModel
from cluster_control.utils.config import HEALTH_CHECK_LIST, STATIC_DHCP_CONFIG

app = FastAPI()

class Node(BaseModel):
    """Representation of a cluster node."""
    mac_address: str

@app.get("/health")
def health():
    """Run health checks and return their status."""
    status = {}
    for check in HEALTH_CHECK_LIST:
        status[check.get_name()] = "OK" if check.check() else "Failure!"
    return status

@app.post("/register/node")
def register_node(node: Node):
    """Register a new node by:
    - adding a static DHCP entry.
    """
    print(f"Got request from: {node.mac_address=}")
    # TODO: https://github.com/open-atmos-krk/hpc-diy/issues/34
    try:
        _add_static_dhcp_entry(node.mac_address)
        _restart_dnsmasq()
    except Exception as e:
        print(f"Could not process the request {node=}")
        print(f"Got an exception: {e!r}")
        return {"statuc_code": 500, "message": "Couldn't process the request"}
    return {"status_code": 200, "mac": node.mac_address}

def _add_static_dhcp_entry(mac: str):
    with pathlib.Path(STATIC_DHCP_CONFIG).open("a") as f:
        f.write(f"dhcp-host={mac},jetson01, 172.16.100.10\n")

def _restart_dnsmasq():
    result = subprocess.run(["sudo", "systemctl", "restart", "dnsmasq"], capture_output=True, text=True)
    if result.returncode == 0:
        print("dnsmasq restarted successfully")
    else:
        print(f"Failed to restart dnsmasq: {result.stderr}")
