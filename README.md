<h1 style="text-align:center;">HPC DIY</h1>

This repository contains playbooks and services required to setup and manage our [DIY Supercomputer](https://open-atmos-krk.github.io/projects/hpc-diy)

## Ansible playbooks

### dnsmasq.yml
After you execute the playbook, you get:
- `systemd-resolved` disabled
- DNS server running (via dnsmasq) and configured in `/etc/resolv.conf`
- DHCP server running (via dnsmasq)
- internet access for clients using DHCP server

#### How do i run it?
```bash
sudo ansible-playbook -i localhost ansible/playbooks/dnsmasq.yml
```

### cluster_control.yml
After you execute the playbook, you get:
- [cluster_control](./cluster-control/README.md) service deployed on server using systemd-services (can be managed by [systemctl](https://documentation.suse.com/smart/systems-management/html/systemd-management/index.html))

#### How do i run it?
```bash
sudo ansible-playbook -i localhost ansible/playbooks/cluster_control.yml
```
