from typing import Union
from pydantic import BaseModel
from fastapi import FastAPI
from cluster_control.utils.config import STATIC_DHCP_CONFIG, HEALTH_CHECK_LIST
import subprocess
import os

app = FastAPI()

class Node(BaseModel):
    mac_address: str

@app.get("/health")
def health():
    status = {}
    for check in HEALTH_CHECK_LIST:
        status[check.get_name()] = "OK" if check.check() else "Failure!"
    return status

@app.post("/register/node")
def register_node(node: Node):
    print(f"Got request from: {node.mac_address=}")
    # TODO: https://github.com/open-atmos-krk/hpc-diy/issues/34
    try:
        add_static_dhcp_entry(node.mac_address)
        restart_dnsmasq()
    except Exception as e:
        print(f"Could not process the request {node=}")
        print(f"Got an exception: {repr(e)}")
        return {"statuc_code": 500, "message": "Couldn't process the request"}
    return {"status_code": 200, "mac": node.mac_address}

def add_static_dhcp_entry(mac: str):
    with open(STATIC_DHCP_CONFIG, "a") as f:
        f.write(f"dhcp-host={mac},jetson01, 172.16.100.10\n")

def restart_dnsmasq():
    result = subprocess.run(
        ["sudo", "systemctl", "restart", "dnsmasq"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("dnsmasq restarted successfully")
    else:
        print(f"Failed to restart dnsmasq: {result.stderr}")
