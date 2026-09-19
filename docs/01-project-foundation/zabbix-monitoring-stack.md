# Zabbix Monitoring Stack

## Purpose
This document describes the **monitoring platform foundation** of the lab, including preparation of the Monitoring Server as a Docker host, deployment of the containerized Zabbix/Grafana stack, component responsibilities, and Zabbix's role in problem detection and recovery verification.

AI analysis, Splunk correlation, remediation, and detailed end-to-end validation are documented separately.

## Monitoring Server Architecture
The monitoring platform runs on:

```text
aws-mon-core-01
```

Its core monitoring services are deployed with Docker Compose:

```text
Monitoring Server
├── Docker
│   ├── Zabbix Server
│   ├── Zabbix Web
│   ├── PostgreSQL
│   └── Grafana
├── Operator Console
└── Splunk Universal Forwarder
```

The Operator Console and Splunk Universal Forwarder share the host but are separate project components rather than part of the Zabbix container stack.

## Docker Host Preparation
The Monitoring Server was prepared with Docker Engine and Docker Compose support before the monitoring stack was deployed.

Docker provides a repeatable runtime boundary for the core monitoring services, while the host remains responsible for system-level access, persistent project data, networking, and supporting host services.

Not every project component is containerized. The project uses different runtime models where appropriate:

- Docker Compose for the Zabbix/Grafana monitoring stack
- systemd-managed Python services for selected application components
- direct Splunk Enterprise installation on the dedicated Splunk server

This keeps containerization as an implementation mechanism rather than making it an architectural requirement for every service.

## Monitoring Components
| Component | Responsibility |
| --- | --- |
| Zabbix Server | Collects monitoring data and evaluates triggers/problems |
| Zabbix Web | Provides administration and problem visibility |
| PostgreSQL | Stores Zabbix configuration and monitoring data |
| Grafana | Visualizes Zabbix-derived infrastructure metrics and problems |
| Zabbix Agent 2 | Collects host-level metrics and availability data |

The Zabbix Server host itself is excluded from the project-wide Zabbix Agent 2 deployment. Agent 2 is installed on the other monitored systems where host-level collection is required.

## Monitoring Model
Zabbix is the project's authoritative **problem-detection and recovery-verification platform**.

Typical monitored signals include:

- host availability
- CPU utilization
- memory utilization
- filesystem usage
- network traffic
- Linux service availability

```text
Monitored Host
     ↓
Zabbix Agent 2
     ↓
Zabbix Server
     ↓
Trigger Evaluation
     ↓
Problem / Recovery State
```

The local Ubuntu environment reaches AWS monitoring services through the final WireGuard hybrid path.

## Grafana Integration
Grafana is the visualization layer for Zabbix-derived infrastructure data.

The final dashboard includes:

- Host Availability
- CPU Utilization
- Memory Utilization
- Disk Utilization
- Network Traffic
- Recent Zabbix Problems

Grafana does **not** replace Zabbix problem detection. Zabbix owns trigger and problem state; Grafana presents monitoring data operationally.

## Role in the Incident Lifecycle
Zabbix both begins and closes the monitored incident lifecycle:

```text
Zabbix detects a problem
        ↓
Downstream correlation and analysis
        ↓
Human-approved remediation
        ↓
Automation executes
        ↓
Zabbix independently observes recovery
```

An automation result of `SUCCESS` is therefore not treated as proof of service recovery. Zabbix independently determines whether the original monitoring condition has cleared.

## Administrative Access
Zabbix Web and Grafana are internal administrative interfaces accessed through the Bastion/SSH-tunnel model.

Port-forwarding details are maintained in [AWS EC2 Secure Network Access](aws-ec2-secure-network-access.md) rather than duplicated here.

## Agent Configuration Management
Zabbix Agent 2 deployment is automated separately with Ansible. Platform-specific installation, configuration, handlers, and repeatable deployment are documented in [Automated Zabbix Agent Deployment](../02-ansible-zabbix-agent/automated-zabbix-agent-deployment.md).

## Validation
Controlled failure testing confirmed that Zabbix could:

1. observe a monitored host,
2. detect loss of Zabbix Agent availability,
3. create a problem event,
4. provide the incident signal used by the downstream workflow, and
5. independently mark the problem resolved after service restoration.

The complete evidence chain is documented in [End-to-End Failure & Recovery Validation](../10-end-to-end-validation/end-to-end-failure-recovery-validation.md).

## Related Documentation
- [AWS Cloud Infrastructure](aws-cloud-infrastructure.md)
- [AWS EC2 Secure Network Access](aws-ec2-secure-network-access.md)
- [Automated Zabbix Agent Deployment](../02-ansible-zabbix-agent/automated-zabbix-agent-deployment.md)
- [Dashboard & Observability](../09-observability-dashboards/dashboard-observability.md)
- [End-to-End Failure & Recovery Validation](../10-end-to-end-validation/end-to-end-failure-recovery-validation.md)
