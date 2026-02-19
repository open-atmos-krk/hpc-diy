import pathlib
import subprocess
from fastapi import FastAPI
from pydantic import BaseModel
from cluster_control.utils.paths import HEALTH_CHECK_LIST, get_available_ips_path, get_dhcp_config_path
from cluster_control.utils.network import get_available_ips, pop_available_ip, write_available_ips

_NODE_BASE_NAME = "jetson_"

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


@app.on_event("startup")
def _initialize():
    available_ips_file = get_available_ips_path()
    available_ips_file.parent.mkdir(parents=True, exist_ok=True)
    ips = [str(ip) for ip in get_available_ips()]
    write_available_ips(ips)

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
        return {"status_code": 500, "message": "Couldn't process the request"}
    return {"status_code": 200, "mac": node.mac_address}

def _add_static_dhcp_entry(mac: str):
    ip = pop_available_ip()
    with pathlib.Path(get_dhcp_config_path()).open("a") as f:
        name = _next_node_name()
        f.write(f"dhcp-host={mac},{name}, {ip}\n")

#TODO: names has to be turbo-static.
def _next_node_name():
    path = pathlib.Path(get_dhcp_config_path())
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return _NODE_BASE_NAME + '0'
    last_name = lines[-1].split(",")[1].strip()
    try:
        number = int(last_name[last_name.rfind("_")+1:]) + 1
    except ValueError as e:
        print(f"Unexpected node name format: {last_name!r}")
        raise RuntimeError(f"Unexpected node name format: {last_name!r}") from e
    return f"{_NODE_BASE_NAME}_{number}"

def _restart_dnsmasq():
    result = subprocess.run(["sudo", "systemctl", "restart", "dnsmasq"], capture_output=True, text=True)
    if result.returncode == 0:
        print("dnsmasq restarted successfully")
    else:
        print(f"Failed to restart dnsmasq: {result.stderr}")
