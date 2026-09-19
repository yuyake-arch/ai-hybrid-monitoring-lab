# Dedicated Splunk Server Deployment

## Overview

This phase introduced **Splunk Enterprise** as the centralized logging platform for the **AI-Assisted Hybrid Monitoring & Automation Lab**.

Rather than adding Splunk to the existing Monitoring Server, a dedicated EC2 instance was used to separate monitoring and logging workloads. Splunk Enterprise was installed directly on Linux rather than deployed as a container.

The deployment established the centralized logging foundation later used for hybrid log collection, incident-context retrieval, and operational evidence.

---

## Objectives

- Deploy Splunk Enterprise on a dedicated AWS EC2 instance
- Separate logging workloads from the Zabbix/Grafana monitoring stack
- Configure Splunk Web for administration
- Configure TCP `9997` for Universal Forwarder traffic
- Restrict AWS forwarding access through a dedicated client Security Group
- Establish purpose-specific indexes for operating-system, security, and application logs
- Prepare the logging platform for later AI-assisted incident correlation

---

## Architecture

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
├── AI Backend Server
├── AWS Log-Producing Servers
└── Dedicated Splunk Server
    └── Splunk Enterprise
```

The main infrastructure responsibilities are separated as follows:

```text
Monitoring Server
    → Metrics, availability, problem detection, recovery verification

Splunk Server
    → Centralized log collection, search, and evidence

Automation Server
    → Configuration management and controlled remediation

AI Backend
    → Incident correlation and AI-assisted analysis

Bastion Server
    → Administrative access
```

---

## Why a Dedicated Splunk Server?

### Resource Isolation

Splunk indexing and search can consume significant CPU, memory, disk, and I/O resources.

Running Splunk independently prevents those workloads from competing directly with Zabbix, Grafana, and PostgreSQL.

### Fault Isolation

A Splunk service issue does not make the core monitoring platform unavailable.

### Independent Scaling

Logging capacity can be changed independently from monitoring and automation capacity.

### Clear Service Ownership

Separating monitoring, logging, AI analysis, and automation provides clearer operational boundaries and makes troubleshooting easier.

---

## Deployment Model

Splunk Enterprise is installed directly on the dedicated Linux host:

```text
aws-splunk-svr-01
│
└── Splunk Enterprise
    └── /opt/splunk/
```

The main CLI is:

```bash
/opt/splunk/bin/splunk
```

Common service commands include:

```bash
sudo /opt/splunk/bin/splunk status
sudo /opt/splunk/bin/splunk start
sudo /opt/splunk/bin/splunk restart
sudo /opt/splunk/bin/splunk stop
```

The direct-install model exposes native Splunk service management, configuration, and log locations without introducing an additional container layer.

---

## Splunk Web

Splunk Web listens on TCP `8000`.

In the project architecture, Splunk Web is treated as an internal administrative interface. Administrative browser access is performed through the Bastion SSH-tunnel model rather than exposing the management interface broadly.

```text
Administrator
      │
      │ SSH tunnel through Bastion
      ▼
localhost:8000
      │
      ▼
Splunk Web
```

Detailed Bastion and SSH configuration is documented separately in the project foundation access documentation.

---

## Splunk Forwarder Communication

Approved AWS systems send logs through the **Splunk Universal Forwarder**.

```text
AWS Log-Producing Server
        │
        ▼
Splunk Universal Forwarder
        │
        │ TCP 9997
        ▼
Splunk Server
```

The Splunk Server itself does not require a Universal Forwarder because Splunk Enterprise is already running on that host.

---

## Security Group Design

AWS instances approved as Splunk Universal Forwarder clients are associated with:

```text
splunk-client-sg
```

The Splunk Server accepts TCP `9997` from this Security Group.

```text
AWS Forwarder Client
+ splunk-client-sg
        │
        │ TCP 9997
        ▼
Splunk Server
```

This Security-Group-to-Security-Group model is more scalable than defining access around one specific managed server or maintaining individual client IP addresses.

The receiver should not expose TCP `9997` to the public Internet.

> The dedicated client Security Group was standardized as the project evolved. It is shown here using the final repository naming so that the documentation remains consistent across later phases.

---

## Splunk Index Strategy

The logging architecture uses three purpose-specific indexes:

| Index | Purpose |
| --- | --- |
| `linux_os` | Operating-system, service, kernel, and infrastructure events |
| `linux_security` | SSH authentication, sudo, and selected security events |
| `app_logs` | Application and selected container logs; later extended to structured AI/remediation events |

This replaced the early idea of placing Linux events into one general-purpose index.

Example searches:

```spl
index=linux_os host=<HOST>
```

```spl
index=linux_security host=<HOST>
```

```spl
index=app_logs
```

The separation provides clearer operational searches and later supports bounded incident-context retrieval.

---

## Centralized Logging Model

```text
Linux / Infrastructure Hosts
├── OS / service / kernel ───────────► linux_os
└── SSH / sudo / security ───────────► linux_security

Applications / Selected Containers
└── application logs ────────────────► app_logs
```

This structure allows logs from multiple systems to be searched centrally while retaining meaningful classification boundaries.

---

## Relationship to Zabbix

Zabbix and Splunk have complementary but separate responsibilities.

```text
Zabbix
→ metrics
→ availability
→ problem detection
→ recovery state

Splunk
→ centralized logs
→ event search
→ troubleshooting evidence
→ incident context
```

Zabbix can indicate that a monitored condition has entered a problem state. Splunk provides additional evidence about events occurring around the same host and time window.

---

## Preparation for AI-Assisted Correlation

The dedicated Splunk platform was designed to support a later incident-analysis workflow:

```text
Zabbix Incident
      ↓
AI Backend
      ↓
Relevant Splunk Evidence
      ↓
Incident Analysis
```

Later phases add bounded Splunk API retrieval and structured AI-assisted analysis. Splunk remains the evidence source; it does not decide or execute remediation.

---

## Security Decisions

- Splunk Enterprise runs on a dedicated AWS host.
- TCP `9997` is not exposed publicly.
- AWS forwarding access is controlled through `splunk-client-sg`.
- Splunk Web is reached through the Bastion administrative-access path.
- Universal Forwarders use dedicated service accounts.
- Log collection is divided into purpose-specific indexes.
- Logging and monitoring remain separate infrastructure responsibilities.

---

## Validation

The deployment was validated by confirming:

- Splunk Enterprise service operation
- Splunk Web access
- TCP `9997` receiving configuration
- Universal Forwarder connectivity
- event ingestion into the expected indexes
- SPL searches returning forwarded events

---

## Outcome

The dedicated Splunk deployment established the centralized evidence layer for the project.

```text
Infrastructure Events
        ↓
Splunk Universal Forwarder
        ↓
Splunk Enterprise
        ↓
Centralized Search and Evidence
```

Later phases extend this foundation with hybrid log forwarding, AI context retrieval, structured analysis logs, and remediation audit evidence.
