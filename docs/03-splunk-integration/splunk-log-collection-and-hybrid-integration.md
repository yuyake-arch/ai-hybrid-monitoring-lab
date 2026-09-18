# Splunk Log Collection and Hybrid Integration

## Overview

This phase continues the **Splunk deployment and logging integration – Dedicated Splunk Server Deployment** work.

The previous phase established the dedicated Splunk Enterprise server, its AWS network placement, Splunk Web access, and the centralized logging architecture. This phase focuses on the next layer: **collecting real logs from AWS and local systems and forwarding them into Splunk**.

The work included:

- Deploying and configuring Splunk Universal Forwarders
- Collecting `systemd-journald` logs from Amazon Linux 2023 and Ubuntu
- Separating OS, security, and application logs
- Building SPL searches for SSH and sudo activity
- Collecting Zabbix Server container logs without depending on Docker container IDs
- Limiting container log growth for a home-lab environment
- Troubleshooting Docker ACL and DNS side effects
- Connecting a local VMware Ubuntu VM to the private AWS Splunk server through an SSH bastion tunnel
- Validating centralized logging across AWS and the local lab

The result is a working **hybrid centralized logging pipeline** that can later provide incident context to the AI backend.

---

## Starting Point

The dedicated Splunk server was already operational from the previous Splunk deployment and logging integration phase.

The existing architecture included:

```text
AWS VPC
│
├── Bastion Server
├── Monitoring Server
│   ├── Zabbix Server
│   ├── Zabbix Web
│   ├── Grafana
│   └── PostgreSQL
├── Automation Server
├── Managed Linux Servers
└── Dedicated Splunk Server
    └── Splunk Enterprise
```

Splunk Enterprise was already configured as the centralized logging platform. This phase extended that platform to actual log-producing systems.

---

## Objectives

The main objectives were:

- Validate Universal Forwarder deployment manually before automation
- Receive logs through Splunk TCP port `9997`
- Collect useful Linux events without ingesting the entire journal
- Separate logs into purpose-specific indexes
- Integrate Docker-based Zabbix application logs
- Avoid unstable Docker container-ID-based log paths
- Reduce unnecessary home-lab log ingestion
- Extend centralized logging to the local VMware environment
- Maintain the Splunk server as a private AWS resource
- Prepare the environment for future WireGuard connectivity and AI-assisted incident analysis

---

## Log Classification

The logging design uses three indexes:

| Index | Purpose |
|---|---|
| `linux_os` | Operating system, service, and kernel events |
| `linux_security` | SSH authentication and sudo activity |
| `app_logs` | Application and selected container logs |

This provides clearer separation than placing all Linux events into one general-purpose index.

The logical model is:

```text
Linux Hosts
│
├── OS / Kernel / Service Events ─────► linux_os
│
└── SSH / sudo Events ────────────────► linux_security

Applications / Containers
│
└── Selected Application Logs ───────► app_logs
```

---

## 1. Amazon Linux 2023 Universal Forwarder

The first monitored system was an **Amazon Linux 2023 x86_64 EC2 instance**.

A key difference from older Linux distributions was discovered immediately.

Traditional log files such as:

```text
/var/log/messages
/var/log/secure
```

were not available.

Instead, the required events were available through `systemd-journald`.

Examples:

```bash
sudo journalctl -n 20
```

```bash
sudo journalctl -u sshd -n 20
```

Persistent journal storage was also verified:

```bash
ls -ld /var/log/journal
```

The Universal Forwarder runs under the dedicated `splunkfwd` account, so journal access was granted with:

```bash
sudo usermod -aG systemd-journal splunkfwd
```

TCP connectivity from the managed server to the Splunk receiver on port `9997` was also validated.

---

## 2. Journald Input Configuration

Rather than forwarding the complete system journal, selected inputs were configured.

This was an intentional design decision to:

- Reduce Splunk ingestion volume
- Avoid duplicate events
- Keep security and OS events logically separated
- Make future searches and AI context retrieval more precise

The configuration used Splunk's `journald://` modular input with filters such as:

```text
journalctl-unit
journalctl-identifier
journalctl-dmesg
```

Example logical design:

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

Service names can differ between distributions, so they were verified on each host before applying filters.

---

## 3. Journald Troubleshooting

During initial testing, the Universal Forwarder was running and Splunk recognized the `journald` input scheme, but journal events were not appearing in Splunk.

The Forwarder processes were inspected:

```bash
ps -ef | grep -E '[j]ournalctl|[s]plunkd'
```

The Splunk Forwarder internal log was also examined:

```bash
sudo grep -iE 'journald|journalctl' \
/opt/splunkforwarder/var/log/splunk/splunkd.log
```

This confirmed that Splunk recognized the external `journald://` scheme and its supported parameters.

Effective configuration was validated using `btool`:

```bash
sudo -u splunkfwd \
/opt/splunkforwarder/bin/splunk btool inputs list --debug
```

After correcting the journald input configuration and restarting the Forwarder, the events appeared successfully in Splunk Web.

### Lesson Learned

A running Universal Forwarder does not guarantee that every configured input is actively producing data.

For Splunk troubleshooting, the following three layers should be validated independently:

```text
Input configuration
        ↓
Forwarder processing
        ↓
Network forwarding
        ↓
Indexer ingestion
```

---

## 4. Security Event Collection

Security-focused collection was designed around SSH and sudo activity.

The primary index is:

```text
linux_security
```

Basic validation:

```spl
index=linux_security
```

SSH-focused searches can use:

```spl
index=linux_security
("sshd" OR "ssh")
```

Sudo activity can be searched with:

```spl
index=linux_security
sudo
```

These searches form the basis for future panels showing:

- SSH authentication success
- SSH authentication failure
- sudo activity
- Security event volume by host

---

## 5. Operating System Event Collection

The `linux_os` index is reserved for selected system, service, and kernel events.

Rather than ingesting the complete journal, filters were used to keep only operationally useful events.

Example categories include:

```text
Kernel events
System services
Login/session management
Selected systemd units
```

This keeps the home-lab dataset manageable while still providing useful troubleshooting context.

---

## 6. Ubuntu Universal Forwarders

The logging architecture was then extended to Ubuntu-based AWS servers.

The same principles were applied:

```text
Universal Forwarder
        │
        ├── selected journald security events
        │       └── linux_security
        │
        └── selected OS/service events
                └── linux_os
```

Forwarding destinations were configured with the Splunk CLI, while log inputs were maintained through local Splunk application configuration rather than editing default files directly.

This follows the standard Splunk configuration principle:

```text
default/
    → vendor/default configuration

local/
    → environment-specific overrides
```

Using `local/` makes configuration easier to maintain and reduces the risk of changes being overwritten by upgrades.

---

## 7. Docker-Based Zabbix Server Logging

The monitoring server runs the main monitoring stack with Docker Compose:

```text
grafana
zabbix-web
zabbix-server
postgres
```

The Zabbix Server container initially used Docker's:

```text
json-file
```

logging driver.

The actual container log therefore existed under a path similar to:

```text
/var/lib/docker/containers/<container-id>/<container-id>-json.log
```

The first approach was to allow the Splunk Forwarder to read the Docker log directly.

This worked, but it introduced two design problems.

## Problem 1 – Container IDs Are Ephemeral

A recreated container receives a new ID.

Therefore, directly depending on:

```text
/var/lib/docker/containers/<container-id>/
```

creates an unstable monitoring path.

## Problem 2 – Docker Internal Storage Permissions

Docker deliberately protects:

```text
/var/lib/docker
```

with restrictive permissions.

Giving the Splunk Forwarder recursive access to Docker's internal storage was unnecessarily broad for a logging solution.

A more stable architecture was therefore implemented.

---

## 8. Stable Zabbix Container Log Pipeline

Only the **Zabbix Server container** was selected for continuous application log ingestion.

Its Docker logging driver was changed to `syslog`.

Example Compose configuration:

```yaml
services:
  zabbix-server:
    image: zabbix/zabbix-server-pgsql:latest
    container_name: zabbix-server

    logging:
      driver: syslog
      options:
        syslog-address: "unixgram:///dev/log"
        tag: "zabbix-server"
```

Host `rsyslog` then writes those events to a stable path:

```text
/var/log/docker/zabbix-server.log
```

Example rsyslog rule:

```text
if $programname == 'zabbix-server' then {
    action(
        type="omfile"
        file="/var/log/docker/zabbix-server.log"
        createDirs="on"
    )
    stop
}
```

The resulting architecture is:

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

This removes the dependency on Docker container IDs.

---

## 9. Splunk Input for Zabbix Logs

The Universal Forwarder monitors the stable host log path.

Example:

```ini
[monitor:///var/log/docker/zabbix-server.log]
disabled = 0
index = app_logs
sourcetype = zabbix:server
```

The configuration can be validated with:

```bash
sudo -u splunkfwd \
/opt/splunkforwarder/bin/splunk btool inputs list --debug
```

Splunk search:

```spl
index=app_logs sourcetype="zabbix:server"
```

This confirmed successful Zabbix Server application-log ingestion.

---

## 10. Controlling Log Volume

Collecting all Docker logs continuously would generate unnecessary data for a small home lab.

The final strategy therefore collects only the Zabbix Server container continuously.

```text
Zabbix Server    → Splunk
Grafana          → Local logs only
Zabbix Web       → Local logs only
PostgreSQL       → Local logs only
```

A `10 MB × 3` rotation policy was designed for the exported Zabbix log.

Example:

```text
/var/log/docker/zabbix-server.log {
    size 10M
    rotate 3
    compress
    missingok
    notifempty
    copytruncate
}
```

This provides enough recent history for troubleshooting without allowing logs to grow indefinitely.

---

## 11. Docker ACL and DNS Troubleshooting

One of the most important troubleshooting exercises in this phase came from the original direct Docker-log collection approach.

To allow `splunkfwd` to access Docker logs, ACL permissions had been added under:

```text
/var/lib/docker/containers
```

A default ACL unintentionally affected files created for new containers.

After recreating the Zabbix Server container, the container repeatedly produced:

```text
PostgreSQL server is not available. Waiting 5 seconds..
```

The Docker network itself appeared healthy:

```text
monitoring-lab_default
```

Both `zabbix-server` and `postgres` were attached to the same network, and PostgreSQL could resolve the Zabbix Server.

However, inside the Zabbix Server container:

```bash
getent hosts postgres
```

returned no result.

Further investigation found:

```text
/etc/resolv.conf
```

with permissions similar to:

```text
-rw-r-----+ root root /etc/resolv.conf
```

The Zabbix container runs as a non-root user:

```text
uid=1997(zabbix)
gid=1995(zabbix)
```

Therefore, the Zabbix process could not read `/etc/resolv.conf` and could not use Docker's embedded DNS resolver:

```text
nameserver 127.0.0.11
```

The issue was confirmed further by launching a new Ubuntu container and observing similarly restrictive resolver permissions.

The unnecessary ACL configuration under Docker's internal directory was removed.

After the ACL issue was corrected and the container was recreated, DNS resolution worked again and Zabbix Server connected normally to PostgreSQL.

### Root Cause

```text
Splunk UF needed Docker log access
        ↓
ACL added to Docker internal directory
        ↓
Default ACL inherited by new Docker files
        ↓
Container /etc/resolv.conf became unreadable
        ↓
Non-root Zabbix process could not use Docker DNS
        ↓
"postgres" hostname could not be resolved
        ↓
Zabbix reported PostgreSQL unavailable
```

### Lesson Learned

Avoid recursively modifying permissions or default ACLs inside:

```text
/var/lib/docker
```

unless there is a strong operational requirement.

Docker-managed storage should generally remain under Docker's control.

Exporting selected application logs to a dedicated host path is safer and easier to operate.

---

## 12. Local VMware Ubuntu Integration

After AWS log collection was working, the next objective was to include a local Ubuntu VM running in **VMware Workstation**.

This represents the on-premises side of the hybrid lab.

The challenge was that Splunk Enterprise is hosted on a private AWS EC2 instance.

The local VM cannot directly route to the Splunk private address because it is outside the AWS VPC.

The temporary proof-of-concept solution was an SSH tunnel through the existing AWS Bastion.

---

## 13. Bastion SSH Tunnel

The AWS Bastion private key was transferred securely to the local Ubuntu VM and protected with restrictive permissions:

```bash
chmod 400 <key-name>.pem
```

The SSH tunnel was created from the local VM:

```bash
ssh -i ~/<key-name>.pem \
  -N \
  -L 9997:<SPLUNK_PRIVATE_IP>:9997 \
  ubuntu@<BASTION_PUBLIC_IP>
```

The local endpoint became:

```text
127.0.0.1:9997
```

Connectivity was verified:

```bash
nc -vz 127.0.0.1 9997
```

and again under the Forwarder service account:

```bash
sudo -u splunkfwd nc -vz 127.0.0.1 9997
```

---

## 14. Local Universal Forwarder Configuration

The local Ubuntu VM's Universal Forwarder was configured to use the SSH tunnel:

```bash
sudo -u splunkfwd \
/opt/splunkforwarder/bin/splunk add forward-server \
127.0.0.1:9997
```

The logical path is:

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

The local Ubuntu VM was also configured with selected journald inputs for:

```text
linux_os
linux_security
```

This allowed AWS and local Linux hosts to use the same centralized log classification model.

---

## 15. Hybrid Forwarding Troubleshooting

Initially, the Universal Forwarder showed:

```text
127.0.0.1:9997
```

as an inactive forward.

The Forwarder log contained:

```text
Connection to host=127.0.0.1:9997 failed
```

and:

```text
Connect to 127.0.0.1:9997 failed. Connection refused
```

Repeated failures also caused Splunk to temporarily quarantine the destination.

The local tunnel itself was reachable, so troubleshooting continued across the complete path.

The critical realization was that with SSH local forwarding, the AWS-side connection to Splunk is made through the Bastion.

Therefore, the relevant path is:

```text
Local VM
   │
   ▼
SSH Tunnel
   │
   ▼
AWS Bastion
   │
   ▼
Splunk :9997
```

The Bastion had not been included in the Security Group access used for Splunk clients.

After correcting the Security Group relationship so the Bastion was permitted to reach Splunk on TCP `9997`, the Forwarder connection became active and events appeared in Splunk Web.

### Lesson Learned

When troubleshooting tunneled connections, firewall and Security Group rules must reflect the **actual network hop that establishes the destination connection**, not only the original application host.

---

## 16. Hybrid Log Collection Validation

The final result was verified directly in Splunk Web.

Both AWS and local Linux events can now be searched centrally.

Example:

```spl
(index=linux_os OR index=linux_security)
| stats count by host, index
```

The completed hybrid path is:

```text
                       Splunk Enterprise
                        Private AWS EC2
                              ▲
                ┌─────────────┴─────────────┐
                │                           │
           TCP 9997                    TCP 9997
                │                           │
          AWS Linux Hosts              AWS Bastion
                                            ▲
                                            │
                                       SSH Tunnel
                                            │
                                     Local Ubuntu VM
                                      VMware Workstation
```

This demonstrates centralized logging across two different infrastructure environments.

---

## 17. Current Logging Architecture

The current environment can be summarized as:

```text
                       AWS Splunk Enterprise
                              │
          ┌───────────────────┼────────────────────┐
          │                   │                    │
          ▼                   ▼                    ▼
     linux_security        linux_os             app_logs
          ▲                   ▲                    ▲
          │                   │                    │
   SSH / sudo events    OS / kernel events    Zabbix Server
          │                   │               container log
          │                   │                    │
     AWS Linux Hosts ─────────┘             rsyslog export
          ▲
          │
          │
Local Ubuntu VM
    Splunk UF
       │
       └── SSH Tunnel → AWS Bastion → Splunk
```

---

## 18. Security Decisions

The following security practices were applied:

- Splunk Enterprise remains on a private AWS EC2 instance.
- Splunk receiving port `9997` is not exposed publicly.
- AWS Security Groups restrict which systems can reach the Splunk receiver.
- Local-to-AWS forwarding currently uses an encrypted SSH tunnel.
- Bastion authentication uses an SSH private key.
- Private-key filesystem permissions are restricted.
- Universal Forwarder services use dedicated non-root accounts.
- Docker internal storage is no longer directly exposed to Splunk.
- Only selected journald and container events are continuously ingested.
- Security and OS logs are separated into dedicated indexes.

---

## 19. Key Lessons Learned

## 1. Modern Linux Logging Requires Distribution Awareness

Amazon Linux 2023 does not necessarily provide the traditional log files used in older examples.

`systemd-journald` should be treated as a primary log source on modern distributions.

---

## 2. Selective Collection Is Better for a Home Lab

Collecting every system and container event creates unnecessary ingestion and storage.

Filtering at the source provides a smaller and more meaningful dataset.

---

## 3. Splunk `btool` Is Essential for Configuration Validation

When multiple Splunk configuration layers exist, `btool` shows the effective configuration and the file from which each setting originates.

Examples:

```bash
/opt/splunkforwarder/bin/splunk btool inputs list --debug
```

```bash
/opt/splunkforwarder/bin/splunk btool outputs list --debug
```

---

## 4. Application Logs Should Not Depend on Docker Container IDs

Container IDs change during recreation.

Using:

```text
Docker syslog → rsyslog → stable host file → Splunk UF
```

provides a more maintainable logging pipeline.

---

## 5. Infrastructure Permission Changes Can Have Unexpected Side Effects

The Docker ACL issue initially appeared to be a PostgreSQL or Docker networking problem.

The actual cause was filesystem permission inheritance preventing a non-root container process from reading DNS configuration.

Troubleshooting across application, filesystem, container, and network layers was required to identify the root cause.

---

## 6. A Successful Port Test Is Only One Layer of Validation

Testing TCP connectivity with `nc` is useful, but complete Splunk forwarding also requires:

```text
Correct input
        +
Running Forwarder
        +
Valid output configuration
        +
Reachable network path
        +
Splunk receiver
        +
Correct Security Groups
```

---

## 7. Hybrid Connectivity Changes the Security Boundary

When using an SSH bastion tunnel, the destination sees the Bastion-side connection path.

Security Group design must therefore account for the Bastion as part of the forwarding architecture.

---

## 20. Implementation Progress

```text
project foundation   Architecture & Repository Setup                  ✓
AWS infrastructure deployment   AWS Infrastructure Deployment                    ✓
local virtualization setup   Local Virtual Environment                        ✓
Docker host and network preparation   Docker / Cloud Networking                        ✓
monitoring stack integration   Zabbix + Grafana + PostgreSQL                    ✓
Ansible automation setup   Automation Environment                           ✓
Zabbix Agent automation   Ansible Zabbix Agent Deployment                  ✓

Splunk deployment and logging integration   Splunk Centralized & Hybrid Logging
        ├── Dedicated Splunk Server                      ✓
        ├── Splunk Enterprise Deployment                 ✓
        ├── TCP 9997 Receiving                           ✓
        ├── Linux Index Design                           ✓
        ├── Amazon Linux Universal Forwarder             ✓
        ├── Ubuntu Universal Forwarder                   ✓
        ├── Selective Journald Collection                ✓
        ├── SSH / sudo Security Logs                     ✓
        ├── OS / Kernel Logs                             ✓
        ├── Zabbix Container Log Collection              ✓
        ├── Stable Docker Log Export                     ✓
        ├── Docker ACL / DNS Troubleshooting             ✓
        └── Local VMware → AWS Hybrid Log Forwarding     ✓

Next    Persistent Hybrid Network with WireGuard         Planned
```

---

## 21. Next Step – WireGuard Hybrid Connectivity

The SSH tunnel successfully proves that local infrastructure can forward logs into the private AWS Splunk environment.

However, it requires an active SSH session and is therefore a temporary connectivity solution.

This temporary tunnel-based path was later replaced by the final **WireGuard** hybrid connectivity design.

Planned architecture:

```text
Local VMware Lab
        │
        │ WireGuard VPN
        │
        ▼
AWS Bastion / WireGuard Gateway
        │
        ▼
AWS VPC 10.10.0.0/16
        │
        ├── Splunk
        ├── Zabbix
        └── Other private services
```

A separate WireGuard tunnel network is planned:

```text
10.200.0.0/24
```

Example addressing:

```text
AWS WireGuard Gateway    10.200.0.1
Local Ubuntu VM          10.200.0.2
```

Once implemented, the local Universal Forwarder will no longer need:

```text
127.0.0.1:9997
```

through an SSH tunnel.

Instead, it will be able to communicate with the Splunk server through persistent private routing.

The same hybrid network can later support:

- Splunk log forwarding
- Zabbix monitoring
- Infrastructure administration
- AI-assisted incident investigation

---

## Final Result

This phase completed the practical centralized logging layer of the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The lab can now collect selected operating system, security, and application logs from both AWS-hosted systems and a local VMware environment.

The most important result is not simply that logs appear in Splunk, but that the logging architecture now provides a reusable source of operational context:

```text
Zabbix
   │
   │ Metrics / Alerts
   ▼

       Incident Context

   ▲
   │ Logs / Events
   │
Splunk
```

This prepares the environment for the next stages: persistent hybrid networking with WireGuard and AI-assisted correlation of Zabbix incidents with relevant Splunk events.

---

**Project:** AI-Assisted Hybrid Monitoring & Automation Lab  
**Day:** 8  
**Focus:** Splunk Universal Forwarder · Journald · Docker Logging · Zabbix Logs · Hybrid Logging · AWS · VMware · Observability
