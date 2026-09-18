# Monitoring Stack & Zabbix Integration

## Overview

This document describes the centralized monitoring foundation implemented for the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The monitoring stack runs on `aws-mon-core-01` using Docker Compose and provides Zabbix Server, Zabbix Web, PostgreSQL, and Grafana. Zabbix serves as the project's primary infrastructure problem-detection system.

## Monitoring Stack

The containerized stack is:

```text
aws-mon-core-01
|
+-- Docker Compose
    |
    +-- Zabbix Server
    +-- Zabbix Web
    +-- PostgreSQL
    +-- Grafana
```

| Component | Role |
|---|---|
| Zabbix Server | Metrics collection, triggers, and problem detection |
| PostgreSQL | Zabbix data store |
| Zabbix Web | Monitoring and configuration interface |
| Grafana | Operational visualization |

Splunk is deployed separately and provides centralized log evidence rather than replacing Zabbix as the infrastructure detection source.

## Zabbix Agent Architecture

Zabbix Agent2 is installed on monitored infrastructure servers, but not on the Zabbix Server host itself in the finalized design.

The project supports both monitoring directions:

### Passive Checks

```text
Zabbix Server
    |
    | TCP 10050
    v
Zabbix Agent2
```

Passive checks are suitable when the Zabbix Server can directly reach the monitored host.

### Active Checks

```text
Zabbix Agent2
    |
    | TCP 10051
    v
Zabbix Server
```

Active checks remain available where the agent needs to initiate monitoring traffic.

The relevant Security Groups retain the required monitoring rules with their purpose documented.

## Hybrid Monitoring

The local Ubuntu VM resides at:

```text
192.168.16.10
```

and is connected to AWS through the WireGuard overlay:

```text
Local wg0: 10.200.0.2
AWS wg0:   10.200.0.1
```

The final hybrid architecture therefore does not depend on exposing Zabbix monitoring through the Monitoring Server's public address. WireGuard provides the private network path between the local environment and AWS.

## AWS Host Monitoring

AWS infrastructure hosts are monitored using Zabbix Agent2 according to their network reachability and host role.

The Automation, AI Backend, Splunk, Managed, Bastion, and WireGuard infrastructure can participate in centralized monitoring. The Monitoring Server itself is the Zabbix Server and is intentionally excluded from the final Agent2 deployment policy.

This avoids the earlier Docker-host self-monitoring complication where a containerized Zabbix Server appeared to the host agent as a Docker bridge source address.

## Docker Networking Lesson

During the earlier implementation, passive monitoring of the Docker host produced an Agent rejection because the Zabbix Server container originated from a Docker bridge address rather than the host's VPC address.

This demonstrated an important principle:

> Containerized monitoring components may present different source addresses than their host operating system.

Although the final design no longer relies on Zabbix Agent2 on the Monitoring Server itself, the troubleshooting remains useful for understanding Docker networking and monitoring-source validation.

## Host Identity

Zabbix display names and infrastructure hostnames are not always identical.

Where normalization is required for incident correlation, explicit identity mapping is used by the application layer. Identity mapping is used for correlation only and does not grant remediation authorization.

Remediation authorization is independently controlled by the Automation Server's target allowlist.

## Security Group Requirements

Monitoring rules are limited to the required communication directions:

```text
Zabbix Server -> Agent2 : TCP 10050
Agent2 -> Zabbix Server : TCP 10051
```

The exact direction depends on the configured monitoring mode.

Broad `0.0.0.0/0` exposure is not required for internal Zabbix monitoring.

## Grafana Integration

Grafana runs in the same Docker Compose stack as Zabbix and uses the Zabbix plugin/data source for infrastructure visualization.

Container-to-container API communication uses Docker internal networking:

```text
Grafana
    |
    | Docker network
    v
Zabbix Web / API
```

This is distinct from administrator browser access, which is provided through the Bastion SSH-tunnel path.

## Dashboard Role

Grafana provides a reusable operational view of:

- Host availability
- CPU utilization
- Memory utilization
- Disk utilization
- Network activity
- Recent Zabbix problems

Host selection and reusable panels avoid creating separate dashboards for every monitored server.

Detailed dashboard polishing and validation evidence are documented in the observability-dashboard phase.

## Zabbix and Splunk Responsibilities

The final observability model intentionally separates metrics/problem detection from log evidence:

| Platform | Primary Role |
|---|---|
| Zabbix | Metrics, availability, triggers, problem/recovery detection |
| Grafana | Operational visualization |
| Splunk | Centralized logs, search, and incident evidence |

This separation is important to the AIOps workflow because a Zabbix problem initiates incident handling, while relevant Splunk evidence is retrieved later for context correlation.

## Integration with Incident Analysis

The completed monitoring flow is:

```text
Infrastructure
    ↓
Zabbix Metrics / Availability
    ↓
Zabbix Problem Detection
    ↓
Incident Analysis Backend
    ↓
Context Correlation and AI-Assisted Analysis
```

The AI layer does not replace Zabbix detection. It receives the detected incident and augments it with deterministic analysis and bounded Splunk evidence.

## Recovery Verification

Zabbix also provides independent recovery verification after remediation.

A successful automation result means that the predefined action executed successfully; it does not by itself prove that the monitored service recovered.

The operational distinction is:

```text
Automation SUCCESS
        !=
Service Recovery

Zabbix RESOLVED
        =
Independent Recovery Evidence
```

This separation was validated during the end-to-end failure and recovery scenario.

## Lessons Learned

- Monitoring mode must match network reachability.
- Zabbix TCP `10050` and `10051` represent different traffic directions.
- Docker networking can change the source address seen by a host service.
- Host identity normalization may be necessary across monitoring, logging, and automation systems.
- Grafana and Zabbix have complementary rather than competing roles.
- Log evidence should not be confused with the monitoring system that detected the incident.
- Automation execution and monitoring recovery are separate operational states.

## Result

The Zabbix stack now provides the project's central infrastructure detection and recovery-verification layer. Together with Grafana, Splunk, the AI Backend, and the controlled remediation workflow, it supports the complete observe-to-verify operational lifecycle.
