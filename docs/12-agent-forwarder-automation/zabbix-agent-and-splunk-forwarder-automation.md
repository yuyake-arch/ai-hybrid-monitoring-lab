# Ansible-Based Zabbix Agent & Splunk Universal Forwarder Automation

## Overview

This phase standardized the two host-side observability components used by the **AI-Assisted Hybrid Monitoring & Automation Lab**:

- **Zabbix Agent 2** for infrastructure monitoring
- **Splunk Universal Forwarder (UF)** for centralized log forwarding

Reusable Ansible roles replaced host-by-host configuration while preserving OS-specific installation logic and server-specific monitoring and logging requirements.

The resulting onboarding model is:

```text
New / Managed Linux Host
        │
        ▼
      Ansible
        │
   ┌────┴────┐
   ▼         ▼
Zabbix     Splunk UF
Agent 2
   │         │
   ▼         ▼
Zabbix     Splunk
Monitoring  Logging
```

---

## 1. Automation Structure

Both components use inventory-based targeting and reusable roles.

```text
automation/
├── ansible.cfg
├── inventory/
│   ├── hosts.ini
│   ├── group_vars/
│   └── host_vars/
├── playbooks/
│   ├── install_zabbix_agent.yml
│   ├── ensure_zabbix_agent_running.yml
│   └── install_splunk_forwarder.yml
├── roles/
│   ├── zabbix_agent/
│   │   ├── defaults/
│   │   ├── handlers/
│   │   └── tasks/
│   │       ├── main.yml
│   │       ├── Debian.yml
│   │       └── RedHat.yml
│   └── splunk_forwarder/
│       ├── defaults/
│       ├── handlers/
│       ├── tasks/
│       │   ├── main.yml
│       │   ├── Debian.yml
│       │   └── RedHat.yml
│       └── templates/
└── vault/
    └── splunk.yml
```

The project configuration uses the local inventory and role directory:

```ini
[defaults]
inventory = inventory/hosts.ini
roles_path = ./roles
```

Dedicated inventory groups define automation scope:

```text
[zabbix_agents]       → Zabbix Agent deployment
[splunk_forwarders]   → Splunk Universal Forwarder deployment
```

Basic connectivity and inventory structure can be validated with:

```bash
ansible zabbix_agents -m ping
ansible-inventory --graph
```

---

## 2. Zabbix Agent 2 Automation

### Cross-Platform Deployment

Ansible facts select the appropriate installation path:

```text
Ubuntu / Debian family       → tasks/Debian.yml
Amazon Linux / RedHat family → tasks/RedHat.yml
```

Amazon Linux 2023 is detected by Ansible as the `RedHat` OS family and uses `dnf`.

The role installs Zabbix Agent 2 and manages the required values in:

```text
/etc/zabbix/zabbix_agent2.conf
```

The important managed parameters are:

```text
Server=
ServerActive=
Hostname=
```

The central Zabbix Server is:

```text
aws-mon-core-01
10.10.10.10
```

### Service Management

Zabbix Agent 2 is managed through systemd. A handler restarts the service only when managed configuration changes.

```text
Configuration unchanged → no restart
Configuration changed   → handler → restart zabbix-agent2
```

This keeps repeated Ansible runs idempotent and avoids unnecessary service interruption.

### Communication Model

```text
Passive:
Zabbix Server → TCP 10050 → Zabbix Agent

Active:
Zabbix Agent → TCP 10051 → Zabbix Server
```

Useful validation commands:

```bash
systemctl status zabbix-agent2
sudo grep -E '^(Server|ServerActive|Hostname)=' /etc/zabbix/zabbix_agent2.conf
sudo ss -tlnp | grep 10050
sudo tail -50 /var/log/zabbix/zabbix_agent2.log
```

Passive communication can be tested from the Zabbix Server:

```bash
zabbix_get -s <AGENT_PRIVATE_IP> -k agent.ping
```

Expected result:

```text
1
```

Active-check connectivity can be tested from the managed node:

```bash
nc -zv 10.10.10.10 10051
```

The deployment was validated through Ansible connectivity, OS detection, Agent installation/configuration, systemd state, network connectivity, and monitoring data visible in Zabbix.

---

## 3. Splunk Universal Forwarder Automation

### Forwarder Scope

The Splunk Forwarder automation covers six AWS servers:

| Server | Role |
|---|---|
| `aws-ai-svr-01` | AI Backend |
| `aws-auto-core-01` | Automation / Remediation |
| `aws-vpn-gw-01` | WireGuard Gateway |
| `aws-mon-core-01` | Monitoring |
| `aws-mgmt-bastion-01` | Bastion |
| `aws-managed-svr-01` | Managed Server |

The dedicated Splunk Server is **not** a Universal Forwarder target.

The role detects existing installations before package installation and separates Debian and RedHat installation paths. New installations are pinned to Splunk Universal Forwarder `10.4.2`; existing installations are not automatically upgraded.

### First-Time Initialization and Vault Scope

The role uses:

```text
/opt/splunkforwarder/etc/passwd
```

as the first-time initialization marker. New installations are initialized non-interactively.

The Splunk administrator password is encrypted with Ansible Vault.

An earlier design stored the Vault file under:

```text
inventory/group_vars/splunk_forwarders/vault.yml
```

This created unintended coupling because hosts can belong to both the Zabbix and Splunk groups. Ansible automatically loaded the encrypted Splunk variable even for unrelated operations such as a Zabbix playbook or a simple host ping.

The final design moves the secret outside automatically loaded inventory variables:

```text
automation/vault/splunk.yml
```

The Splunk playbook explicitly loads it:

```yaml
vars_files:
  - ../vault/splunk.yml
```

This keeps the credential dependency scoped to the workflow that requires it.

| Operation | Vault Required |
|---|---:|
| General Ansible connectivity | No |
| Zabbix Agent installation/remediation | No |
| Splunk Forwarder installation/configuration | Yes |
| Operation requiring Splunk administrator password | Yes |

Example:

```bash
# No Splunk Vault dependency
ansible aws-managed-svr-01 \
  -i inventory/hosts.ini \
  -m ping

# Splunk workflow explicitly requires Vault
ansible-playbook \
  playbooks/install_splunk_forwarder.yml \
  --limit aws-managed-svr-01 \
  --ask-vault-pass
```

### Central Forwarding

All managed Forwarders send data to:

```text
Splunk Server: 10.10.10.30
Receiving Port: TCP 9997
```

The common destination is managed in:

```text
/opt/splunkforwarder/etc/system/local/outputs.conf
```

The role preserves host-specific applications under:

```text
/opt/splunkforwarder/etc/apps/
```

rather than replacing the directory.

---

## 4. Splunk Log Configuration Matrix

The logging design uses a **common Linux security baseline** plus selective server-specific inputs. This avoids repeating the same SSH/sudo configuration for every server.

### Common Security Baseline

All six Forwarder hosts collect:

| Log Source | Index | Sourcetype | Configuration |
|---|---|---|---|
| SSH authentication | `linux_security` | `linux:ssh` | `common_linux_security/local/inputs.conf` |
| sudo activity | `linux_security` | `linux:sudo` | `common_linux_security/local/inputs.conf` |

The underlying SSH journald unit differs by OS family:

```text
Ubuntu / Debian family       → ssh.service
Amazon Linux / RedHat family → sshd.service
```

The `splunkfwd` account is granted the required `systemd-journal` access.

### Server-Specific Inputs

| Server | Additional Log Source | Index | Sourcetype | Source / Configuration |
|---|---|---|---|---|
| `aws-ai-svr-01` | AI Backend application logs | `app_logs` | application-specific | `ai_backend_logs/local/inputs.conf` |
| `aws-auto-core-01` | Remediation execution log | `app_logs` | `remediation:execution` | `/var/log/remediation-api/execution.json.log` via `remediation_api_logs/local/inputs.conf` |
| `aws-vpn-gw-01` | WireGuard `wg-quick@wg0.service` | `linux_os` | `wireguard:wgquick` | journald via `vpn_gateway_logs/local/inputs.conf` |
| `aws-mon-core-01` | Zabbix Server container log | `app_logs` | `zabbix:server` | `/var/log/docker/zabbix-server.log` |
| `aws-mgmt-bastion-01` | No additional role-specific source documented in this phase | — | — | Common security baseline only |
| `aws-managed-svr-01` | Selected OS journals | `linux_os` | input-specific | `journald_input/local/inputs.conf` |

Every server in the table also receives the common SSH/sudo configuration.

### Configuration Ownership

```text
common_linux_security
├── SSH
└── sudo

journald_input
└── selected host / OS-specific journals

ai_backend_logs
└── AI Backend application logs

remediation_api_logs
└── remediation execution log

vpn_gateway_logs
└── WireGuard service events
```

`aws-managed-svr-01` already had SSH/sudo collection in `journald_input`. Those overlapping stanzas were removed when `common_linux_security` was introduced, while its OS-specific inputs such as kernel, NetworkManager, chronyd, and systemd-logind were retained.

This prevents duplicate ingestion while preserving server-specific logging.

---

## 5. Splunk Validation

Effective input configuration can be audited with:

```bash
sudo -u splunkfwd /opt/splunkforwarder/bin/splunk \
  btool inputs list --debug
```

A concise search for all six Forwarder hosts is:

```spl
(index=app_logs OR index=linux_os OR index=linux_security)
(host="aws-ai-svr-01"
 OR host="aws-auto-core-01"
 OR host="aws-vpn-gw-01"
 OR host="aws-mon-core-01"
 OR host="aws-mgmt-bastion-01"
 OR host="aws-managed-svr-01")
| stats count latest(_time) AS last_seen by host index sourcetype
| eval last_seen=strftime(last_seen, "%Y-%m-%d %H:%M:%S")
| sort host index sourcetype
```

Role-specific validation examples:

**Remediation execution**

```spl
index=app_logs host="aws-auto-core-01" sourcetype="remediation:execution"
| spath
| eval Time=strftime(_time,"%Y-%m-%d %H:%M:%S")
| table Time event_id target_host action_id status
| sort - Time
```

**WireGuard service**

```spl
index=linux_os host="aws-vpn-gw-01" sourcetype="wireguard:wgquick"
| eval Time=strftime(_time,"%Y-%m-%d %H:%M:%S")
| rename host AS "VPN Gateway"
         _SYSTEMD_UNIT AS "Service"
         MESSAGE AS "Event"
| table Time "VPN Gateway" Service Event
| sort - Time
```

Final validation confirmed common security-log ingestion from all six Forwarder hosts together with the documented role-specific sources.

---

## 6. Unified Host Onboarding

The two roles establish a consistent onboarding model for Linux systems:

```text
Managed Linux Host
        │
        ▼
      Ansible
        │
   ┌────┴────┐
   │         │
   ▼         ▼
Zabbix     Splunk
Agent 2      UF
   │         │
   ▼         ▼
Metrics    Logs
   │         │
   ▼         ▼
Zabbix     Splunk
```

The responsibilities remain intentionally separate:

| Component | Responsibility |
|---|---|
| Zabbix Agent 2 | Infrastructure metrics and availability monitoring |
| Splunk Universal Forwarder | System, security, and application log forwarding |
| Ansible | Repeatable installation, configuration, and service management |

Both automation paths use inventory-based targeting, OS-family-specific tasks, systemd service management, and idempotent configuration.

---

## 7. Key Outcomes

This phase established:

- reusable Ansible roles for Zabbix Agent 2 and Splunk Universal Forwarder;
- Debian/Ubuntu and RedHat/Amazon Linux handling;
- inventory groups defining automation scope;
- handler-driven and systemd-based service management;
- centralized Zabbix Agent deployment;
- centralized Splunk forwarding to TCP `9997`;
- standardized SSH and sudo logging across six AWS Forwarders;
- selective role-specific application and infrastructure logging;
- preservation of existing host-specific Splunk inputs;
- explicit Vault scoping that avoids coupling Splunk credentials to unrelated Ansible operations;
- end-to-end validation through Zabbix and Splunk.

The result is a reusable onboarding workflow for monitored Linux systems in the hybrid lab.

---

## 8. Security & Reliability Follow-Up

The later **Security & Reliability Review** evaluates items that extend beyond the deployment focus of this phase, including:

- Splunk DEB/RPM package integrity and RPM GPG validation;
- controlled Universal Forwarder version and upgrade policy;
- fresh-install RPM validation on a RedHat-family test target;
- remediation execution-log rotation;
- least-privilege log permissions after rotation;
- Ansible configuration ownership and drift handling.

Keeping those items in the dedicated security review avoids duplicating their final status in this implementation document.
