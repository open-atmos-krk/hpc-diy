
# HPC DIY

A small, opinionated toolkit for building and operating a DIY HPC cluster.

This repository contains two primary pieces:

- Ansible playbooks and roles for provisioning and configuring cluster nodes — see [ansible/README.md](ansible/README.md).
- A lightweight Python-based cluster control utility for runtime checks and helpers — see [cluster-control/README.md](cluster-control/README.md).


## Quick start

1. Read the Ansible guide if you need to provision or update nodes: [ansible/README.md](ansible/README.md).
2. Use [cluster-control/README.md](cluster-control/README.md) for runtime tools and scripts that help manage and verify the cluster.

## Repository layout (top-level)

- `ansible/` — Ansible playbooks, roles, inventories and configuration for the cluster.
- `cluster-control/` — Python package and CLI for cluster checks and utilities.

