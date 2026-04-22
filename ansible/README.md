# DIY HPC Cluster Setup

## Overview

This directory contains Ansible playbooks for setting up the cluster.


**inventories/inventory.ini** inventory file to be used for playbooks. The file has three groups
| Inventory group | Role |
| --- | --- |
| `local` | Controller or gateway host |
| `nodes` | Compute nodes |
| `slurm_hosts` | Combined group containing both `local` and `nodes` |

<b>IMPORTANT:</b> set (or replace) these to vars
 - `$ANSIBLE_USER` TODO
 - `$ANSIBLE_PK` TODO 

## Repository layout

- `inventory.ini`
  Cluster inventory and SSH settings.
- `playbooks/dnsmasq.yml`
  Configures the local host as a DHCP, DNS, and NAT gateway.
- `playbooks/cluster_control.yml`
  Installs the external `cluster_control` systemd service from the upstream repository.
- `playbooks/sync_users.yml`
  Replicates local user and group IDs from the controller to compute nodes.
- `playbooks/generate_munge_key.yml`
  Generates a shared MUNGE key on the controller.
- `playbooks/munge.yml`
  Installs MUNGE and distributes the shared key.
- `playbooks/chrony.yml`
  Enables time synchronization on all Slurm hosts.
- `playbooks/shared_storage.yml`
  Exports a local disk over NFS and mounts it on compute nodes.
- `playbooks/slurm.yml`
  Builds and installs Slurm packages on all cluster nodes.
- `playbooks/slurm_startup.yml`
  Installs `slurm.conf` and starts `slurmctld` and `slurmd`.

Several additional Slurm playbooks exist for older or more specialized build paths. This document uses the generic `playbooks/slurm.yml` route unless you have a reason to choose one of the legacy playbooks.

## Prerequisites

Before running any commands from **Procedure** section please make sure that you satisfy the following prerequisites

### Netplan config

Make sure that `/etc/netplan/*.yaml` config file contains entry for OUT interface with `dhcp4: true`

### Ansible 
Install **Ansible 2.15.x** or version compatible with worker's nodes Python version -- see [instructions](https://docs.ansible.com/projects/ansible/latest/installation_guide/installation_distros.html#installing-ansible-on-ubuntu)

<b>IMPORTANT</b>: your user has to have

### Inventory

`inventory.ini` expects SSH details from environment variables (or you can just replace these values in-place within the file):

```bash
export ANSIBLE_USER=your-admin-user
export ANSIBLE_PK=/path/to/private/key
```
- `ANSIBLE_USER` has to exist on worker nodes
- `ANSIBLE_PK` use [ssh-copy-id](https://man7.org/linux/man-pages/man1/ssh-copy-id.1.html) first to propagate key to nodes

Review `inventory.ini` before running anything. In particular:

- replace example node names if your cluster differs
- ensure controller and node hostnames resolve correctly

### Slurm controller naming must be consistent

`config/slurm.conf` currently contains:

```ini
SlurmctldHost=bowie
```

If the controller host is not actually named `bowie`, update `playbooks/slurm.conf` or ensure name resolution maps `bowie` to the controller.

## Procedure

### 1. Clone the repository

On the controller:

```bash
git clone https://github.com/open-atmos-krk/hpc-diy.git
cd ansible
```

Run all commands in this document from the repository root unless noted otherwise.

### 2. Configure & install dnsmasq

Review the variables in `playbooks/dnsmasq.yml` so they match expected values:

- `external_iface`
- `dhcp_iface`
- `dhcp_iface_ip`
- `dhcp_start`
- `dhcp_end`
- `dhcp_domain`

Then apply the playbook:

```bash
ansible-playbook -i localhost playbooks/dnsmasq.yml -K
```

### 3. Install the cluster control service

If you use the external cluster control service on the controller:

```bash
ansible-playbook -i localhost playbooks/cluster_control.yml -K
```

This installs packages, clones the upstream repository into `/opt/cluster_control`, and registers a `cluster_control` systemd unit.

### 4. Create service users on the controller

Create the Slurm service accounts locally on the controller before syncing them to the nodes:

```bash
sudo useradd -m -u 2000 -U -s /bin/bash slurm
sudo useradd -m -u 2001 -U -s /bin/bash munge
```

Create any additional cluster users you want replicated to the nodes before continuing.

### 5. Sync users and groups to compute nodes

`playbooks/sync_users.yml` copies user and group IDs from the controller to hosts in the `nodes` group.

Example:

```bash
ansible-playbook -i inventories/inventory.ini playbooks/sync_users.yml -K \
  -e 'sync_users=["munge","slurm"]'
```

<b>IMPORTANT</b>: any user that wants to schedule slurm jobs needs to be synced across the cluster. Add all the additional users to `["munge","slurm"]` list before running the playbook

Notes:

- the listed users must already exist on the controller
- primary groups are created automatically
- secondary groups are only synchronized when `sync_secondary_groups=true`

### 6. Generate a shared MUNGE key

Generate the key once on the controller:

```bash
ansible-playbook -i inventories/inventory.ini playbooks/generate_munge_key.yml
```

By default, the key is written to:

```text
$HOME/.munge/files/munge.key
```

### 7. Synchronize clocks

Install and configure Chrony on all Slurm hosts:

```bash
ansible-playbook -i inventories/inventory.ini playbooks/chrony.yml -K
```

Time synchronization should be in place before starting MUNGE and Slurm.

### 8. Install and configure MUNGE

Distribute the shared MUNGE key to all Slurm hosts:

```bash
ansible-playbook -i inventories/inventory.ini playbooks/munge.yml -K \
  -e "munge_key_src=$HOME/.munge/files/munge.key"
```

### 9. Export shared storage

`playbooks/shared_storage.yml`:

- mounts a local block device on the controller
- exports it over NFS
- mounts the export on each node

Review these variables first:

- `shared_disk_device`
- `shared_mount_path`
- `nfs_allowed_cidr`

Then run:

```bash
ansible-playbook -i inventories/inventory.ini playbooks/shared_storage.yml -K
```

The playbook expects the selected block device to already contain a filesystem.

### 10. Ensure host name resolution is correct

Before starting Slurm, verify that all nodes can resolve:

- the controller hostname used by `SlurmctldHost`
- every compute node listed in `playbooks/slurm.conf`

If required, add entries to `/etc/hosts` on the controller and nodes.

### 11. Build and install Slurm

This repository currently uses separate Slurm installation playbooks for the controller and worker nodes.

#### Controller node

Use `playbooks/slurm_local_ubuntu24.yml` on the controller host. This playbook is intended for the `local` inventory group and asserts that the target is Ubuntu 24.

```bash
ansible-playbook -i inventories/inventory.ini playbooks/slurm_local_ubuntu24.yml -K
```

It downloads Slurm source, builds Debian packages locally, and installs the controller-side packages including `slurmctld`.

#### Worker nodes

Use `playbooks/slurm_nodes_ubuntu18.yml` for the compute nodes. This playbook targets the `nodes` inventory group and asserts that each worker is Ubuntu 18.

```bash
ansible-playbook -i inventories/inventory.ini playbooks/slurm_nodes_ubuntu18.yml -K
```

It builds Slurm manually on each worker under `/mnt/cluster-workspace/builds/slurm/<hostname>`, installs `slurmd`, and writes a custom systemd unit for the manually installed daemon.

Run the controller playbook first, then the worker-node playbook.

### 12. Install `slurm.conf` and start services

After Slurm packages are installed, configure and start the daemons:

```bash
ansible-playbook -i inventories/inventory.ini playbooks/slurm_startup.yml -K
```

This:

- ensures MUNGE is started first
- installs `playbooks/slurm.conf` to `/etc/slurm/slurm.conf`
- enables `slurmctld` on the controller
- enables `slurmd` on compute nodes

## Verification

After deployment, verify the cluster from the controller.

### Check MUNGE

```bash
munge -n | unmunge
```

The decoded credential should report successful authentication.

### Check NFS mounts

```bash
mount | grep cluster-workspace
```

You should see the shared path mounted on the controller and nodes.

### Check Slurm services

```bash
systemctl status slurmctld
systemctl status slurmd
```

### Check Slurm node visibility

```bash
sinfo
scontrol show nodes
```

## Troubleshooting

### `sync_users.yml` fails for a user

Ensure the user exists locally on the controller and that `getent passwd <user>` returns a valid entry there.

### `munge.yml` cannot find the key

Pass the generated key explicitly:

```bash
ansible-playbook -i inventory.ini playbooks/munge.yml -K \
  -e "munge_key_src=$HOME/.munge/files/munge.key"
```

### `shared_storage.yml` fails on the disk check

The target device must already be partitioned and formatted. The playbook does not create a filesystem for you.

### Slurm daemons start but do not form a cluster

Check:

- that `SlurmctldHost` matches the real controller hostname
- that hostnames resolve consistently on every node
- `sinfo -N -l` (RPi)
- `journalctl -u slurmd --no-pager -n 100` (node)
- `journalctl -u slurmctld --no-pager -n 100` (RPi)
