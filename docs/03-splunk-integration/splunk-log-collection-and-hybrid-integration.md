# Splunk Log Collection and Hybrid Integration

## Overview

This phase extended the dedicated Splunk Enterprise platform into a working **hybrid centralized logging pipeline**.

The work focused on collecting real operating-system, security, and selected application/container logs from AWS and a local VMware Ubuntu VM.

At this implementation stage, the local VMware system reached the private AWS Splunk Server through a **temporary SSH tunnel via the Bastion**. Persistent WireGuard connectivity was intentionally left as a later project phase.

---

## Objectives

- Deploy and validate Splunk Universal Forwarders
- Receive forwarded logs through TCP `9997`
- Collect selected `systemd-journald` events
- Separate OS, security, and application logs
- Collect Zabbix Server container logs through a stable host path
- Avoid dependency on Docker container IDs
- Control unnecessary home-lab log volume
- Extend centralized logging to the local VMware environment
- Validate hybrid forwarding before implementing persistent WireGuard connectivity
- Prepare Splunk evidence for later AI-assisted incident correlation

---

## Log Classification

The logging design uses three indexes:

| Index | Purpose |
| --- | --- |
| `linux_os` | Operating-system, service, kernel, and infrastructure events |
| `linux_security` | SSH authentication, sudo, and selected security events |
| `app_logs` | Application and selected container logs |

```text
Linux Hosts
├── OS / Kernel / Service Events ─────► linux_os
└── SSH / sudo Events ────────────────► linux_security

Applications / Containers
└── Selected Application Logs ────────► app_logs
```

This separation provides a more useful operational dataset than placing all Linux events into one generic index.

Later phases also use `app_logs` for selected structured AI-analysis and remediation/audit events.

---

## AWS Universal Forwarder Clients

Splunk Universal Forwarder is installed on approved AWS log-producing systems.

AWS instances authorized to send logs to the Splunk receiver are associated with:

```text
splunk-client-sg
```

The Splunk Server accepts TCP `9997` from that Security Group.

```text
AWS Forwarder Clients
+ splunk-client-sg
        │
        │ TCP 9997
        ▼
Splunk Enterprise
```

This should be understood as a client authorization/grouping mechanism rather than as a single “managed server” being the Splunk client.

> The dedicated `splunk-client-sg` naming was standardized as the project evolved. It is used here for consistency with the later infrastructure and security documentation.

---

## Amazon Linux 2023 and Journald

During Universal Forwarder deployment on Amazon Linux 2023, traditional files such as:

```text
/var/log/messages
/var/log/secure
```

were not the primary source used by the implementation.

Required events were available through `systemd-journald`.

Examples:

```bash
sudo journalctl -n 20
sudo journalctl -u sshd -n 20
```

Persistent journal storage was also verified.

The Universal Forwarder runs under the dedicated `splunkfwd` account, so the service account requires permission to read the system journal.

---

## Selective Journald Inputs

Rather than forwarding the complete journal, selected inputs were configured.

This reduces ingestion volume, avoids unnecessary duplication, and preserves meaningful index separation.

Example logical configuration:

```ini
[journald://linux_security_ssh]
disabled = 0
index = linux_security
journalctl-unit = sshd.service

[journald://linux_security_sudo]
disabled = 0
index = linux_security
journalctl-identifier = sudo

[journald://linux_os_kernel]
disabled = 0
index = linux_os
journalctl-dmesg = true
```

Service names can differ between Linux distributions and should be verified before applying filters.

---

## Forwarder Configuration Validation

A running Universal Forwarder does not guarantee that every configured input is producing events.

Effective input configuration can be inspected with:

```bash
sudo -u splunkfwd /opt/splunkforwarder/bin/splunk btool inputs list --debug
```

Output configuration can be checked with:

```bash
sudo -u splunkfwd /opt/splunkforwarder/bin/splunk btool outputs list --debug
```

Troubleshooting therefore validates the complete path:

```text
Input configuration
        ↓
Forwarder processing
        ↓
Network forwarding
        ↓
Splunk receiver
        ↓
Indexer ingestion
```

---

## Security Event Collection

SSH and sudo activity is routed to:

```text
linux_security
```

Examples:

```spl
index=linux_security ("sshd" OR "ssh")
```

```spl
index=linux_security sudo
```

This keeps authentication and privilege-use evidence separate from general operating-system events.

---

## Operating-System Event Collection

Selected system, service, and kernel events are routed to:

```text
linux_os
```

The design intentionally avoids ingesting the entire system journal.

Useful categories include:

- kernel events
- service events
- login/session management
- selected systemd units

This keeps the lab dataset manageable while preserving useful troubleshooting evidence.

---

## Ubuntu Universal Forwarders

The same collection model was applied to Ubuntu-based AWS systems:

```text
Universal Forwarder
        │
        ├── selected security events
        │       └── linux_security
        │
        └── selected OS/service events
                └── linux_os
```

Environment-specific settings are maintained through Splunk `local/` configuration rather than editing vendor defaults.

```text
default/
    → vendor/default configuration

local/
    → environment-specific overrides
```

---

## Stable Zabbix Container Log Pipeline

The Monitoring Server runs the Zabbix/Grafana/PostgreSQL stack with Docker Compose.

The initial idea of reading Docker's internal container log files directly was rejected as the final logging design because:

1. container IDs change when containers are recreated; and
2. broad access under `/var/lib/docker` creates unnecessary permission risk.

Only the **Zabbix Server container** was selected for continuous application-log ingestion.

The stable pipeline is:

```text
Zabbix Server Container
        │
        │ Docker syslog driver
        ▼
Host rsyslog
        │
        ▼
/var/log/docker/zabbix-server.log
        │
        │ Splunk UF
        ▼
app_logs
```

Example Docker logging configuration:

```yaml
services:
  zabbix-server:
    logging:
      driver: syslog
      options:
        syslog-address: "unixgram:///dev/log"
        tag: "zabbix-server"
```

Example Splunk input:

```ini
[monitor:///var/log/docker/zabbix-server.log]
disabled = 0
index = app_logs
sourcetype = zabbix:server
```

Validation:

```spl
index=app_logs sourcetype="zabbix:server"
```

---

## Docker ACL and DNS Troubleshooting

During the earlier direct Docker-log approach, access permissions were added under Docker-managed storage so the Forwarder could read container logs.

A default ACL unintentionally affected files created for newly recreated containers. The Zabbix container's non-root process then lost effective access to resolver configuration and could not resolve the PostgreSQL service through Docker DNS.

The troubleshooting chain was:

```text
Direct Docker log access
        ↓
ACL added under Docker storage
        ↓
Inherited restrictive permissions
        ↓
Container resolver configuration unreadable
        ↓
Docker DNS unavailable to Zabbix process
        ↓
PostgreSQL hostname could not be resolved
```

The unnecessary ACL configuration was removed.

The final design avoids direct dependency on Docker internal storage and instead exports the selected Zabbix log to a stable host path.

---

## Log Volume Control

Collecting every container log continuously would create unnecessary ingestion for the lab.

The selected monitoring-stack strategy is:

```text
Zabbix Server  → Splunk
Grafana        → local logs only
Zabbix Web     → local logs only
PostgreSQL     → local logs only
```

The exported Zabbix log also uses host-side rotation to prevent uncontrolled growth.

---

## Local VMware Ubuntu Integration

The local Ubuntu VM represents the non-AWS side of the hybrid lab.

At this phase, the Splunk Server was private inside AWS and persistent WireGuard routing had not yet been implemented.

A temporary SSH tunnel through the Bastion was therefore used to validate hybrid log forwarding.

```text
Local VMware Ubuntu
        │
        │ Splunk UF
        ▼
127.0.0.1:9997
        │
        │ SSH local forwarding
        ▼
AWS Bastion
        │
        │ TCP 9997
        ▼
Private Splunk Server
```

This was a proof-of-concept connectivity path, not the intended permanent hybrid architecture.

---

## Bastion Tunnel and Security Group Troubleshooting

The local Universal Forwarder initially reported its tunnel destination as inactive.

The important observation was that, with SSH local forwarding, the AWS-side TCP connection to Splunk is established from the **Bastion**, not directly from the original local VM.

```text
Local VM
   ↓
SSH Tunnel
   ↓
AWS Bastion
   ↓
Splunk :9997
```

The Bastion therefore had to be permitted to reach the Splunk receiver during this temporary forwarding design.

After the relevant Security Group relationship was corrected, the Forwarder became active and events appeared in Splunk.

This reinforced an important network troubleshooting principle: access rules must reflect the **actual network hop establishing the destination connection**.

---

## Hybrid Log Collection Validation

Centralized ingestion was validated from both AWS and the local VMware environment.

Example:

```spl
(index=linux_os OR index=linux_security)
| stats count by host, index
```

At this implementation stage, the hybrid path was:

```text
                     Splunk Enterprise
                      Private AWS EC2
                            ▲
                ┌───────────┴───────────┐
                │                       │
           TCP 9997                TCP 9997
                │                       │
      AWS Forwarder Clients         AWS Bastion
      + splunk-client-sg                ▲
                                        │
                                   SSH Tunnel
                                        │
                                  Local Ubuntu VM
```

---

## Security Decisions

- Splunk receiving port `9997` is not exposed publicly.
- Approved AWS Forwarder clients are associated with `splunk-client-sg`.
- Universal Forwarder services run under dedicated non-root accounts.
- Docker internal storage is not directly exposed to Splunk.
- Only selected journald and container events are continuously ingested.
- Security and OS logs are separated into dedicated indexes.
- The local SSH tunnel is treated as a temporary hybrid connectivity mechanism.
- Persistent private hybrid routing is deferred to the WireGuard phase.

---

## Preparation for AI Context Retrieval

The log-classification work provides the evidence layer later consumed by the AI Backend.

The later correlation model is:

```text
Zabbix Incident
      ↓
AI Backend
      ↓
Bounded Splunk Search
      ↓
Relevant Observed Evidence
      ↓
Deterministic Baseline + Gemini-Assisted Analysis
```

The approved Splunk indexes later exposed to the restricted AI context role are:

```text
linux_os
linux_security
app_logs
```

The LLM uses filtered evidence for analysis and recommendations. It does not directly execute Ansible or remediation actions.

---

## Next Step – WireGuard Hybrid Connectivity

The SSH tunnel proved that the local VMware environment could forward logs to the private AWS Splunk Server.

However, it required an active SSH session and was therefore treated as an interim solution.

The planned next step was persistent WireGuard connectivity:

```text
Local VMware Lab
        │
        │ WireGuard VPN
        ▼
AWS WireGuard Gateway
        │
        ▼
AWS VPC
        │
        └── Splunk Server
```

The planned tunnel network was:

```text
10.200.0.0/24
```

with the design later using:

```text
AWS WireGuard Gateway    10.200.0.1
Local Ubuntu VM          10.200.0.2
```

WireGuard was implemented in a later project phase and became the final hybrid connectivity path. Keeping it as a planned next step here preserves the implementation chronology of this phase.

---

## Key Lessons Learned

### Selective Collection Is Better Than Indiscriminate Ingestion

Filtering at the source reduces noise and storage while preserving useful incident evidence.

### Splunk `btool` Is Essential for Configuration Validation

`btool` shows effective configuration after Splunk's configuration layers are merged.

### Application Logs Should Not Depend on Container IDs

```text
Docker syslog → rsyslog → stable host file → Splunk UF
```

is more maintainable than depending on ephemeral Docker paths.

### Docker-Managed Storage Should Remain Under Docker Control

Broad permission or default-ACL changes inside `/var/lib/docker` can produce unexpected container side effects.

### Network Rules Must Follow the Real Connection Path

The temporary SSH tunnel demonstrated why Security Group rules must reflect the host that actually establishes the connection to the receiver.

### Hybrid Connectivity Can Be Validated Before the Final VPN Design

The Bastion tunnel provided a useful proof of concept before persistent WireGuard routing was implemented in a later phase.

---

## Outcome

This phase completed practical centralized log collection from AWS and the local VMware environment.

```text
AWS Systems
   │
   ├── linux_os
   ├── linux_security
   └── app_logs
          │
          ▼
       Splunk
          ▲
          │
Local Ubuntu
via temporary Bastion SSH tunnel
```

The resulting evidence layer prepared the project for later WireGuard hybrid networking and AI-assisted correlation of Zabbix incidents with relevant Splunk events.
