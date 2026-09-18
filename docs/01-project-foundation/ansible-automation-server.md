# Ansible Automation Server Setup

## Overview

This document describes the foundation of `aws-auto-core-01` as the Ansible control node for the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The server began as a basic Ansible management host and later evolved into the project's controlled remediation execution layer, hosting both Ansible automation and the private Remediation API.

## Automation Server Role

The final Automation Server responsibilities include:

- Ansible control node
- Reusable infrastructure roles and playbooks
- Zabbix Agent2 deployment automation
- Splunk Universal Forwarder deployment automation
- Private Remediation API
- Deterministic action and target validation
- Execution logging and audit support

The AI Backend does not directly execute Ansible.

The control path is:

```text
AI-Assisted Recommendation
        ↓
Deterministic Remediation Policy
        ↓
Human Approval
        ↓
Private Remediation API
        ↓
Action / Target Validation
        ↓
Ansible Playbook
        ↓
Managed Target
```

## Ansible Installation

Ansible was installed on `aws-auto-core-01` using `pipx` to avoid modifying Ubuntu's system-managed Python environment.

```bash
sudo apt update
sudo apt install -y pipx git openssh-client netcat-openbsd
pipx ensurepath
pipx install --include-deps ansible
```

Validation:

```bash
ansible --version
```

The Ansible executable path used by the automation service must be explicit or available in the service environment. This became important when Ansible was invoked from systemd-managed application code rather than an interactive shell.

## Managed-Node Connectivity

Ansible manages Linux targets over SSH.

Connectivity can be tested independently from ICMP:

```bash
nc -zv -w 5 <TARGET_PRIVATE_IP> 22
ansible all -i automation/inventory/hosts.ini -m ping
```

Ansible `ping` uses SSH and remote Python execution; it is not an ICMP echo request.

Security Groups must therefore allow TCP `22` from the Automation Server to the intended managed hosts.

## SSH Authentication

Ansible-managed nodes use SSH key-based authentication.

Private SSH keys are not committed to Git. Public keys are installed in the managed user's `authorized_keys` as required.

Host-key verification is also part of SSH trust. New managed hosts may require their host key to be established before unattended Ansible execution unless host-key management is handled through another trusted mechanism.

## Repository Layout

Automation code is maintained in the project monorepo under:

```text
automation/
├── ansible.cfg
├── inventory/
├── playbooks/
├── roles/
├── host_vars/
├── vault/
└── remediation_api/
```

The actual inventory is environment-specific:

```text
automation/inventory/hosts.ini
```

and is excluded from Git.

A reusable example is tracked:

```text
automation/inventory/hosts.example.ini
```

## Inventory and Host Variables

The inventory defines Ansible-managed infrastructure and remediation targets.

Host-specific configuration is maintained under `host_vars/` where appropriate. For example, a host can define its Zabbix identity or whether the Splunk Forwarder role should apply.

This keeps reusable role logic separate from host-specific behavior.

## Ansible Vault

Splunk Forwarder administrative credentials are protected using Ansible Vault.

The final secret file is:

```text
automation/vault/splunk.yml
```

It is excluded from Git, while a safe example file is tracked.

The Splunk Forwarder playbook explicitly loads the Vault file through `vars_files` rather than relying on unrelated automatic variable loading.

This prevents Splunk-specific secrets from interfering with other playbooks such as Zabbix Agent deployment.

## Reusable Roles

The automation layer evolved beyond the initial system-check playbook into reusable configuration roles.

Major automated components include:

- Zabbix Agent2 deployment/configuration
- Splunk Universal Forwarder deployment/configuration
- Service enablement and restart handlers
- Idempotent host configuration

The Zabbix role supports the Linux distributions used in the lab, while Splunk Forwarder deployment accounts for existing and newly installed versions rather than assuming every host runs the same build.

## Remediation Execution

The Automation Server also hosts the private Remediation API.

The API does not accept arbitrary commands, scripts, playbook paths, or free-form Ansible arguments.

Instead, it validates:

1. Service authentication
2. Action identifier
3. Target identifier
4. Fixed action-to-playbook mapping

A validated remediation is executed in the controlled form:

```text
ansible-playbook <internal-playbook> --limit <allowlisted-target>
```

This constrains both what automation can run and where it can run.

## Target Onboarding

Adding a new remediation target requires updates to two distinct control points:

1. The Remediation API target allowlist
2. The Ansible inventory remediation-target group

This is intentional. Being known to Ansible does not automatically authorize a host for remediation.

## Execution Semantics

Automation results distinguish command execution from higher-level recovery.

Important rules include:

- Return code `0` is required for execution success.
- A non-empty target execution scope must be present.
- `changed=false` can still represent successful idempotent execution.
- HTTP `200` from the API does not by itself mean remediation succeeded.
- Zabbix independently determines whether the monitored problem recovered.

## Git and Deployment Model

The project uses one GitHub monorepo.

The local Windows workstation maintains the full repository and is the primary location for repository-wide changes.

Servers use role-specific working trees/sparse checkouts:

- Monitoring Server: monitoring and Operator Console
- AI Backend: AI backend
- Automation Server: automation

GitHub SSH authentication is provided from the local workstation through SSH agent forwarding when server-side Git access is required. GitHub private keys are not copied onto the EC2 servers.

Runtime files such as virtual environments, Vault secrets, local inventories, `.env` files, and databases remain outside Git tracking.

## Monitoring

`aws-auto-core-01` is itself monitored by Zabbix Agent2.

This allows failures of the automation infrastructure to be detected by the same centralized monitoring platform used for the rest of the environment.

The Automation Server also forwards relevant operational logs to Splunk for audit and troubleshooting.

## Lessons Learned

- Ansible management depends on SSH, not ICMP.
- Security Group routing and SSH authentication must both be validated.
- Reusable roles are preferable to host-specific one-off playbooks.
- Secrets should be scoped only to the automation that needs them.
- Inventory membership and remediation authorization are separate controls.
- Ansible idempotency means a successful execution does not always produce a change.
- A private API can provide a controlled boundary between application logic and Ansible.
- AI recommendations must remain separate from deterministic authorization and execution.
- Git deployment design should avoid copying repository private keys to servers.

## Result

`aws-auto-core-01` evolved from an Ansible control node into a controlled automation platform.

It now supports repeatable configuration management and allowlisted remediation while preserving the project's central safety boundary:

> **LLM recommends → deterministic policy decides → human approves → allowlisted automation executes → monitoring independently verifies recovery**
