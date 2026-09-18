# Ansible-Based Zabbix Agent & Splunk Universal Forwarder Automation

## Overview

This work expanded the **AI-Assisted Hybrid Monitoring & Automation
Lab** by standardizing both host-side observability components with
Ansible:

-   **Zabbix Agent 2** for infrastructure monitoring
-   **Splunk Universal Forwarder (UF)** for centralized log forwarding

The goal was to replace host-by-host configuration with reusable,
cross-platform Ansible roles while preserving host-specific monitoring
and logging requirements.

------------------------------------------------------------------------

# Part I --- Zabbix Agent 2 Automation

## 1. Reusable Zabbix Agent Role

Zabbix Agent deployment is organized as a reusable role:

``` text
automation/
├── ansible.cfg
├── inventory/
│   ├── hosts.ini
│   ├── group_vars/
│   └── host_vars/
├── playbooks/
│   └── install_zabbix_agent.yml
└── roles/
    └── zabbix_agent/
        ├── defaults/
        │   └── main.yml
        ├── handlers/
        │   └── main.yml
        ├── tasks/
        │   ├── main.yml
        │   ├── Debian.yml
        │   └── RedHat.yml
        └── templates/
```

The project Ansible configuration uses the project inventory and role
directory:

``` ini
[defaults]
inventory = inventory/hosts.ini
roles_path = ./roles
```

A dedicated `[zabbix_agents]` inventory group defines the automation
scope. Inventory connectivity and structure can be checked with:

``` bash
ansible zabbix_agents -m ping
ansible-inventory --graph
```

## 2. Cross-Platform Zabbix Installation

Ansible facts select OS-specific installation tasks:

``` text
Ubuntu / Debian family       → tasks/Debian.yml
Amazon Linux / RedHat family → tasks/RedHat.yml
```

Amazon Linux 2023 is detected as the `RedHat` OS family and uses `dnf`.
This allows the same role structure to support both Ubuntu and Amazon
Linux systems.

The role manages Zabbix Agent 2 installation, repository configuration,
and the environment-specific parameters required in:

``` text
/etc/zabbix/zabbix_agent2.conf
```

Important managed values include:

``` text
Server=
ServerActive=
Hostname=
```

The central Zabbix Server is:

``` text
aws-mon-core-01
10.10.10.10
```

## 3. Service Management and Idempotency

Zabbix Agent 2 is managed through systemd. A handler restarts the Agent
only when managed configuration changes.

``` text
Configuration unchanged → no restart
Configuration changed   → handler → restart zabbix-agent2
```

This avoids unnecessary service interruption and improves idempotency.

## 4. Zabbix Communication and Validation

The deployment accounts for both Zabbix communication models:

``` text
Passive:
Zabbix Server → TCP 10050 → Zabbix Agent

Active:
Zabbix Agent → TCP 10051 → Zabbix Server
```

Useful validation commands include:

``` bash
systemctl status zabbix-agent2
sudo grep -E '^(Server|ServerActive|Hostname)=' /etc/zabbix/zabbix_agent2.conf
sudo ss -tlnp | grep 10050
sudo tail -50 /var/log/zabbix/zabbix_agent2.log
```

Passive communication can be tested from the Zabbix Server:

``` bash
zabbix_get -s <AGENT_PRIVATE_IP> -k agent.ping
```

Expected result:

``` text
1
```

Active-check connectivity can be tested from a managed node:

``` bash
nc -zv 10.10.10.10 10051
```

The automation was validated through Ansible connectivity, OS detection,
Agent installation/configuration, systemd state, network connectivity,
and monitoring data visible in Zabbix.

------------------------------------------------------------------------

# Part II --- Splunk Universal Forwarder Automation

## 5. Splunk Forwarder Scope

The Splunk Forwarder automation covers six AWS servers:

``` text
aws-ai-svr-01
aws-auto-core-01
aws-vpn-gw-01
aws-mon-core-01
aws-mgmt-bastion-01
aws-managed-svr-01
```

The dedicated Splunk server is not a Universal Forwarder target.

## 6. Splunk Forwarder Role

``` text
roles/
└── splunk_forwarder/
    ├── defaults/
    │   └── main.yml
    ├── handlers/
    │   └── main.yml
    ├── tasks/
    │   ├── main.yml
    │   ├── Debian.yml
    │   └── RedHat.yml
    └── templates/
        ├── outputs.conf.j2
        └── common_linux_security_inputs.conf.j2

playbooks/
└── install_splunk_forwarder.yml
```

The role detects existing installations before package installation and
separates Debian and RedHat installation paths. New installations are
currently pinned to Splunk Universal Forwarder `10.4.2`; existing
installations are not automatically upgraded.

## 7. First-Time Initialization and Scoped Ansible Vault

The role uses:

``` text
/opt/splunkforwarder/etc/passwd
```

as the first-time initialization marker. New installations are
initialized non-interactively, while the Splunk administrator password
is protected with Ansible Vault.

### Vault Scope Issue Discovered During Validation

The initial Vault file was stored under the Splunk inventory group:

``` text
inventory/group_vars/splunk_forwarders/vault.yml
```

This worked for the Splunk playbook, but it introduced an unintended
dependency. A server such as `aws-managed-svr-01` belongs to both the
Zabbix Agent and Splunk Forwarder automation scopes. Because Ansible
automatically loads `group_vars` for every group associated with a
target host, even a simple ad-hoc command such as:

``` bash
ansible aws-managed-svr-01 \
  -i inventory/hosts.ini \
  -m ping
```

attempted to decrypt the Splunk Vault and failed when no Vault secret
was provided.

The same behavior affected Zabbix-only automation even though Zabbix did
not need the Splunk administrator password.

### Final Vault Design

The Splunk secret was moved out of automatically loaded inventory
variables:

``` text
automation/
├── inventory/
│   ├── hosts.ini
│   ├── group_vars/
│   │   ├── splunk_forwarders/
│   │   └── zabbix_agents.yml
│   └── host_vars/
├── playbooks/
│   ├── ensure_zabbix_agent_running.yml
│   └── install_splunk_forwarder.yml
└── vault/
    └── splunk.yml
```

The encrypted file contains only the Splunk secret:

``` yaml
---
splunk_admin_password: "<encrypted secret>"
```

The Splunk playbook explicitly loads the Vault file:

``` yaml
---
- name: Install and configure Splunk Universal Forwarder
  hosts: splunk_forwarders
  become: true
  gather_facts: true

  vars_files:
    - ../vault/splunk.yml

  roles:
    - splunk_forwarder
```

This scopes the credential dependency to the workflow that actually
needs it.

  Operation                                                  Vault Required
  -------------------------------------------------------- ----------------
  Ad-hoc Ansible host connectivity test                                  No
  Zabbix Agent installation/remediation                                  No
  Splunk Forwarder installation/configuration                           Yes
  Operations requiring the Splunk administrator password                Yes

Validation commands:

``` bash
# General Ansible connectivity: no Vault required
ansible aws-managed-svr-01 \
  -i inventory/hosts.ini \
  -m ping

# Zabbix remediation: no Vault required
ansible-playbook \
  playbooks/ensure_zabbix_agent_running.yml \
  --limit aws-managed-svr-01

# Splunk workflow: Vault explicitly required
ansible-playbook \
  playbooks/install_splunk_forwarder.yml \
  --limit aws-managed-svr-01 \
  --ask-vault-pass
```

This change removed unnecessary coupling between the Zabbix and Splunk
automation workflows while keeping the Splunk credential encrypted.

## 8. systemd and Central Forwarding

The role detects whether `SplunkForwarder.service` is already registered
before initial boot-start configuration and then manages the service
through systemd.

All managed forwarders send data to:

``` text
Splunk Server: 10.10.10.30
Receiving Port: TCP 9997
```

The common forwarding destination is managed in:

``` text
/opt/splunkforwarder/etc/system/local/outputs.conf
```

The role intentionally does not replace
`/opt/splunkforwarder/etc/apps/`, preserving host-specific Splunk
applications.

## 9. Common Linux Security Logging

SSH and sudo collection was standardized across all six forwarders with:

``` text
/opt/splunkforwarder/etc/apps/common_linux_security/local/inputs.conf
```

``` ini
[journald://linux_security_ssh]
disabled = 0
index = linux_security
sourcetype = linux:ssh
journalctl-unit = <OS-specific SSH service>

[journald://linux_security_sudo]
disabled = 0
index = linux_security
sourcetype = linux:sudo
journalctl-identifier = sudo
```

The `splunkfwd` account is granted the required `systemd-journal`
access.

Testing confirmed:

``` text
Ubuntu / Debian family       → ssh.service
Amazon Linux / RedHat family → sshd.service
```

Examples:

``` text
aws-ai-svr-01       Ubuntu 26.04      → ssh.service
aws-mon-core-01     Ubuntu 26.04      → ssh.service
aws-managed-svr-01  Amazon Linux 2023 → sshd.service
```

## 10. Existing Journald Migration

`aws-managed-svr-01` already collected SSH and sudo events through:

``` text
/opt/splunkforwarder/etc/apps/journald_input/local/inputs.conf
```

Those security stanzas overlapped with the new common app. The legacy
SSH/sudo stanzas were removed while existing OS-specific inputs such as
kernel, NetworkManager, chronyd, and systemd-logind were retained.

Final responsibility:

``` text
journald_input
└── host/OS-specific journald inputs

common_linux_security
├── SSH
└── sudo
```

This prevents duplicate collection while preserving existing
configuration.

## 11. Role-Specific Splunk Inputs

Common security logging remains separate from host-specific inputs.

``` text
aws-vpn-gw-01
├── common_linux_security
└── vpn_gateway_logs
    └── wg-quick@wg0.service
```

WireGuard:

``` text
index=linux_os
sourcetype=wireguard:wgquick
```

Automation server:

``` text
aws-auto-core-01
├── common_linux_security
└── remediation_api_logs
    └── /var/log/remediation-api/execution.json.log
```

Remediation execution logs:

``` text
index=app_logs
sourcetype=remediation:execution
```

The selective design avoids indiscriminate collection of the entire
system journal.

## 12. Splunk Validation

Effective configuration can be checked with:

``` bash
sudo -u splunkfwd /opt/splunkforwarder/bin/splunk btool inputs list --debug
```

Forwarder reporting:

``` spl
index=_internal
(host="aws-ai-svr-01"
 OR host="aws-auto-core-01"
 OR host="aws-vpn-gw-01"
 OR host="aws-mon-core-01"
 OR host="aws-mgmt-bastion-01"
 OR host="aws-managed-svr-01")
| stats count AS events latest(_time) AS last_seen by host
| eval last_seen=strftime(last_seen, "%Y-%m-%d %H:%M:%S")
| sort host
```

Common security ingestion:

``` spl
index=linux_security
(sourcetype="linux:ssh" OR sourcetype="linux:sudo")
| stats count latest(_time) AS last_seen by host sourcetype
| eval last_seen=strftime(last_seen, "%Y-%m-%d %H:%M:%S")
| sort host sourcetype
```

Final validation confirmed security-log detection from all six Splunk
Forwarder hosts.

------------------------------------------------------------------------

## 13. Six-Server Splunk Log Mapping

The logging design combines a common Linux security baseline with
selective, role-specific inputs.

  --------------------------------------------------------------------------------------------------------------------------------
  Server                 Role-Specific /         Index / Sourcetype                    Input Configuration
                         Application Logs                                              
  ---------------------- ----------------------- ------------------------------------- -------------------------------------------
  `aws-ai-svr-01`        AI backend application  AI app logs under `app_logs`;         `ai_backend_logs/local/inputs.conf`;
                         logs; common SSH/sudo   `linux_security / linux:ssh`,         `common_linux_security/local/inputs.conf`
                                                 `linux:sudo`                          

  `aws-auto-core-01`     Remediation API         `app_logs / remediation:execution`;   `remediation_api_logs/local/inputs.conf`;
                         execution; common       `linux_security`                      `common_linux_security/local/inputs.conf`
                         SSH/sudo                                                      

  `aws-vpn-gw-01`        WireGuard               `linux_os / wireguard:wgquick`;       `vpn_gateway_logs/local/inputs.conf`;
                         `wg-quick@wg0`; common  `linux_security`                      `common_linux_security/local/inputs.conf`
                         SSH/sudo                                                      

  `aws-mon-core-01`      Zabbix Server           `app_logs / zabbix:server`;           monitors
                         application/container   `linux_security`                      `/var/log/docker/zabbix-server.log`;
                         log; common SSH/sudo                                          effective app source can be verified with
                                                                                       `btool --debug`

  `aws-mgmt-bastion-01`   Common SSH/sudo         `linux_security / linux:ssh`,         `common_linux_security/local/inputs.conf`
                                                 `linux:sudo`                          

  `aws-managed-svr-01`   Selected OS journals    `linux_os`; `linux_security`          `journald_input/local/inputs.conf`;
                         plus common SSH/sudo                                          `common_linux_security/local/inputs.conf`
  --------------------------------------------------------------------------------------------------------------------------------

Common security input:

``` text
/opt/splunkforwarder/etc/apps/common_linux_security/local/inputs.conf
```

Role-specific confirmed inputs include:

``` text
aws-auto-core-01
└── /var/log/remediation-api/execution.json.log
    → app_logs / remediation:execution

aws-vpn-gw-01
└── wg-quick@wg0.service
    → linux_os / wireguard:wgquick

aws-mon-core-01
└── /var/log/docker/zabbix-server.log
    → app_logs / zabbix:server
```

The effective source file for any merged Splunk input can be audited
with:

``` bash
sudo -u splunkfwd /opt/splunkforwarder/bin/splunk \
  btool inputs list --debug
```

### Validation Queries

Three searches provide concise evidence of centralized ingestion and
role-specific logging.

**1. All six forwarder hosts and collected log types**

``` spl
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

Optional validation capture:

``` text
images/splunk-all-host-log-validation.png
```

**2. Automation Server - Remediation execution**

``` spl
index=app_logs host="aws-auto-core-01" sourcetype="remediation:execution"
| spath
| eval Time=strftime(_time,"%Y-%m-%d %H:%M:%S")
| table Time event_id target_host action_id status
| sort - Time
```

The exact displayed JSON fields can be adjusted to match the current
`execution.json.log` schema.

Optional validation capture:

``` text
images/splunk-remediation-execution-validation.png
```

**3. VPN Gateway - WireGuard service events**

``` spl
index=linux_os host="aws-vpn-gw-01" sourcetype="wireguard:wgquick"
| eval Time=strftime(_time,"%Y-%m-%d %H:%M:%S")
| rename host AS "VPN Gateway"
         _SYSTEMD_UNIT AS "Service"
         MESSAGE AS "Event"
| table Time "VPN Gateway" Service Event
| sort - Time
```

Optional validation capture:

``` text
images/splunk-wireguard-log-validation.png
```

------------------------------------------------------------------------

# Part III --- Combined Monitoring Automation Model

## 14. Unified Host Onboarding

The resulting model combines monitoring and logging automation:

``` text
New / Managed Linux Host
          │
          ▼
       Ansible
          │
     ┌────┴────┐
     │         │
     ▼         ▼
Zabbix Agent  Splunk UF
     │         │
     ▼         ▼
 Monitoring   Logging
     │         │
     ▼         ▼
 Zabbix      Splunk
```

-   **Zabbix Agent 2** provides infrastructure metrics and availability
    monitoring.
-   **Splunk Universal Forwarder** provides centralized system,
    security, and application logs.
-   Both use reusable roles, inventory-based targeting,
    OS-family-specific tasks, and idempotent service management.

## 15. Key Outcomes

This work established:

-   reusable Ansible roles for Zabbix Agent 2 and Splunk Universal
    Forwarder;
-   Debian and RedHat family handling;
-   inventory groups that clearly define automation scope;
-   systemd-based service management;
-   handler-driven configuration updates;
-   centralized Zabbix monitoring;
-   centralized Splunk forwarding over TCP 9997;
-   standardized SSH and sudo security logging across six forwarders;
-   preservation of host-specific Splunk applications;
-   cleanup of overlapping legacy journald inputs;
-   role-specific WireGuard and remediation execution log ingestion;
-   end-to-end validation in Zabbix and Splunk.

The result is a more scalable onboarding workflow for future Linux hosts
in the hybrid monitoring lab.

## 16. Security & Reliability Status

The following items were reviewed in the later **Security & Reliability Review**:

-   verify Splunk DEB/RPM package integrity and improve RPM GPG
    validation;
-   define a controlled Splunk Forwarder version/upgrade policy;
-   validate the complete new-install RPM workflow on a RedHat-family
    test target;
-   implement log rotation for
    `/var/log/remediation-api/execution.json.log`;
-   verify least-privilege remediation-log permissions survive rotation;
-   document Ansible configuration ownership boundaries and drift
    handling.

The final Security & Reliability Review documents which items were validated, hardened, or retained as accepted limitations.
