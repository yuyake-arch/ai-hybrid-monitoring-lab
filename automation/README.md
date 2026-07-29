# Automation - Day 6 (Ansible Setup)

## Overview

This directory contains the Ansible automation environment for the AI-Assisted Hybrid Monitoring & Automation Lab.

The Automation EC2 instance acts as the Ansible Control Node and is responsible for managing infrastructure tasks across the lab environment.

---

## Current Features

- Ansible Control Node deployment
- SSH key-based authentication
- Inventory configuration
- Basic connectivity validation
- System information collection

---

## Directory Structure

```
automation/
├── ansible.cfg
├── inventory/
│   └── hosts.example.ini
├── playbooks/
│   └── system-check.yml
└── README.md
```

---

## Playbooks

### system-check.yml

Collects basic information from managed Linux hosts, including:

- Hostname
- Operating System
- Kernel Version
- Uptime

This playbook is used to verify Ansible connectivity before deploying additional automation tasks.

---

## Security

The actual inventory file (`hosts.ini`) is excluded from version control because it contains environment-specific IP addresses.

The repository includes `hosts.example.ini` as a template.

Private SSH keys, credentials, and secrets are never committed to GitHub.

---

## Lab Environment

| Component | Role |
|-----------|------|
| Automation EC2 | Ansible Control Node |
| Monitoring EC2 | Managed Host |
| SSH | Key-based authentication |
| GitHub | Version Control |

---

## Next Steps

- Create reusable Ansible Roles
- Configure automatic package management
- Deploy Zabbix Agent using Ansible
- Implement configuration management
- Add infrastructure validation playbooks

---

Part of the **AI-Assisted Hybrid Monitoring & Automation Lab** project.
