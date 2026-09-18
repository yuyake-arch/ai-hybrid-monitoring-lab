# AWS Docker Host Preparation and Internet Connectivity

## Overview

This document records the preparation of `aws-mon-core-01` as the Docker host for the centralized monitoring stack and the AWS networking troubleshooting performed before container deployment.

The work established the runtime foundation later used by Zabbix Server, Zabbix Web, PostgreSQL, and Grafana.

## Monitoring Host Role

`aws-mon-core-01` was selected as the Docker host because the core monitoring services belong to the same operational stack.

The implemented container layout is:

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

Splunk Enterprise, the AI Backend, and the Automation/Remediation service were later deployed on dedicated EC2 instances rather than being added to this Docker host.

## Instance Sizing

The Monitoring Server initially used a `t3.micro` instance with 1 GiB RAM.

Because multiple monitoring containers run together, the instance was resized to `t3.small`:

```text
Instance Type: t3.small
vCPU:          2
Memory:        2 GiB
```

This provided a more practical baseline for the containerized monitoring workload.

## Internet Connectivity Problem

Before Docker and monitoring components could be installed, the Monitoring Server required repository and package access.

The server had private address `10.10.10.10` and had been assigned public addressing, but external connectivity failed:

```bash
ping 8.8.8.8
sudo apt update
```

Linux routing and Security Group egress were checked first:

```bash
ip route
```

The host had a valid local default gateway, and outbound Security Group traffic was permitted.

## Root Cause

The associated AWS route table did not contain a default route to the Internet Gateway.

The required path was:

```text
0.0.0.0/0 -> Internet Gateway
```

This demonstrated that public or Elastic IP addressing alone is insufficient. Internet access requires the subnet routing path and Internet Gateway configuration to align with the instance addressing and security policy.

## Route Table Design

The monitoring subnet uses its own routing configuration rather than requiring the Monitoring Server to be moved into the Bastion subnet.

Conceptually:

```text
aws-mon-core-01
10.10.10.10
      |
Monitoring Subnet
10.10.10.0/24
      |
Route Table
      |
0.0.0.0/0
      |
Internet Gateway
```

This allowed access to Ubuntu repositories, Docker packages/images, Git repositories, and other required software sources.

## Public Addressing and NAT Trade-off

A NAT Gateway would allow private workloads to initiate Internet connections without public IPv4 addressing, but it introduces recurring cost.

For this lab, direct Internet connectivity on selected workloads was retained where required, with inbound exposure constrained by Security Groups.

The decision balances:

- Lab operating cost
- Required software/repository access
- Hands-on AWS networking
- Restricted inbound access

A production environment would normally evaluate managed NAT, VPC endpoints, or other controlled egress mechanisms according to its availability and security requirements.

## Docker Installation and Runtime

After network connectivity was corrected, Docker Engine and the Docker Compose plugin were installed and validated on the Monitoring Server.

The monitoring stack was subsequently deployed with Docker Compose and became the operational platform for:

- Zabbix Server
- Zabbix Web
- PostgreSQL
- Grafana

Containers communicate through the Docker network where appropriate rather than exposing every component externally.

## Security Considerations

Internet connectivity does not imply unrestricted inbound access.

Administrative and web access remains controlled through Security Groups and the Bastion access path. Operational interfaces are accessed through SSH tunnels where appropriate instead of being broadly exposed.

## Validation

The preparation work established and validated:

- Monitoring Server sizing appropriate for the lab workload
- Working AWS route-table and Internet Gateway path
- Repository and package connectivity
- Docker Engine
- Docker Compose
- Container runtime
- Docker networking for the monitoring stack
- Deployment readiness for Zabbix, PostgreSQL, and Grafana

Useful host-level validation commands included:

```bash
ip addr
ip route
ping -c 4 8.8.8.8
sudo apt update
docker version
docker compose version
docker ps
```

## Lessons Learned

### Public Addressing Does Not Replace Routing

An Elastic/public IP mapping requires a valid route through an Internet Gateway before it can provide direct Internet connectivity.

### Subnet Classification Is a Routing Property

A subnet's effective public/private behavior depends heavily on its route table, not merely on whether an individual EC2 instance has a public address.

### Network Troubleshooting Should Follow the Path

A useful sequence is:

```text
Application
    ↓
Host Interface
    ↓
Host Route
    ↓
Security Policy
    ↓
Subnet Route Table
    ↓
Gateway
    ↓
Remote Service
```

### Cost Is an Architectural Constraint

The lab deliberately avoided adding a continuously billed NAT Gateway solely to imitate a production reference architecture.

## Result

`aws-mon-core-01` was successfully prepared as the Docker host for the monitoring platform. The network issue discovered during preparation became an important AWS routing lesson, and the resulting Docker foundation now supports the operational Zabbix, PostgreSQL, and Grafana stack.
