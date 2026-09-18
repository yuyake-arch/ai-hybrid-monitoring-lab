# AWS EC2 Deployment & Secure Network Access

## Overview

This document describes the EC2 deployment and administrative-access foundation used by the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The environment began with Bastion, Monitoring, and Automation servers and later expanded into a seven-server AWS architecture. The original access model remains important: administrative SSH enters through a dedicated Bastion host, while application and infrastructure services use restricted internal communication paths.

## Network Foundation

The AWS environment uses:

| Network | CIDR |
|---|---|
| VPC | `10.10.0.0/16` |
| Public Subnet | `10.10.1.0/24` |
| Monitoring Subnet | `10.10.10.0/24` |
| Automation Subnet | `10.10.20.0/24` |

The public subnet contains the Bastion and WireGuard gateway as separate EC2 instances. Monitoring, logging, AI, managed workloads, and automation services are separated by role.

## EC2 Roles

The final AWS environment contains:

| Instance | Role |
|---|---|
| `aws-mgmt-bastion-01` | Administrative jump host and SSH tunneling |
| `aws-mon-core-01` | Zabbix, Grafana, PostgreSQL, Operator Console |
| `aws-splunk-svr-01` | Splunk Enterprise |
| `aws-ai-svr-01` | AI incident-analysis backend |
| `aws-auto-core-01` | Remediation API and Ansible control node |
| `aws-managed-svr-01` | Managed workload and remediation target |
| `aws-vpn-gw-01` | WireGuard gateway |

## Bastion-Controlled Administration

The administrator connects from the local Windows workstation to `aws-mgmt-bastion-01` over SSH.

Internal EC2 administration is then performed through the Bastion rather than exposing SSH broadly to the Internet.

```text
Administrator
    |
    | SSH / TCP 22
    v
aws-mgmt-bastion-01
    |
    | Restricted internal SSH
    v
AWS Internal Servers
```

The Bastion and WireGuard gateway serve different purposes. The Bastion is the administrative entry point; `aws-vpn-gw-01` provides hybrid network connectivity.

## SSH Key Management

The administrative EC2 private key remains on the local Windows workstation and is not copied to the Bastion.

Windows ACLs can be used to restrict access to the key:

```powershell
icacls "C:\Users\<USERNAME>\.ssh\ai-monitoring-lab-key.pem" /inheritance:r
icacls "C:\Users\<USERNAME>\.ssh\ai-monitoring-lab-key.pem" /grant:r "$($env:USERNAME):(R)"
```

This keeps the Bastion from becoming a storage location for the administrator's private key.

## Proxy-Based SSH Access

During initial deployment, direct ProxyJump authentication exposed an important SSH behavior: reaching the Bastion successfully does not automatically make the required identity available for authentication to the destination host.

An explicit proxy configuration was used during troubleshooting:

```powershell
ssh -i C:\Users\<USERNAME>\.ssh\ai-monitoring-lab-key.pem `
  -o IdentitiesOnly=yes `
  -o ProxyCommand="ssh -i C:\Users\<USERNAME>\.ssh\ai-monitoring-lab-key.pem -o IdentitiesOnly=yes -W %h:%p ubuntu@<BASTION_PUBLIC_IP>" `
  ubuntu@<PRIVATE_IP>
```

The resulting path is:

```text
Windows Workstation
    |
    | Local private key
    v
Bastion
    |
    | SSH transport
    v
Private/Internal EC2
```

## Security Group Design

Security Groups represent infrastructure roles and required communication paths.

Examples include:

- Bastion SSH from the administrator's approved public IP
- Internal SSH from approved management roles
- Zabbix agent traffic only between monitoring and monitored roles
- Splunk forwarding only from approved forwarder clients
- Splunk API access only from the AI Backend role
- Remediation API access only from authorized internal callers
- WireGuard UDP traffic only for the VPN endpoint

Security Group references are preferred where appropriate because they express role-based trust without coupling every rule to an individual private IP.

## Internet Egress and Cost Trade-off

The initial private workloads demonstrated that a private IPv4 address and VPC local routing do not provide Internet egress by themselves.

Package installation, container pulls, Git access, and software repositories require a valid outbound path.

A NAT Gateway was evaluated as the production-oriented approach, but its recurring hourly and data-processing costs were not justified for this lab. Selected workloads therefore retain public IPv4 connectivity where required, while inbound access remains restricted through Security Groups.

This is a cost-conscious lab decision rather than a production recommendation.

## Private and Public Network Behavior

A server's effective exposure depends on several components together:

```text
Addressing
    +
Subnet Route Table
    +
Internet Gateway / Egress Path
    +
Security Groups
    +
Network ACLs
    +
Host Configuration
```

A public IPv4 address does not by itself expose every service, and a server without a public IPv4 address does not automatically have outbound Internet connectivity.

## Administrative Web Access

Operational interfaces are not intended for unrestricted public access. The Bastion provides SSH tunnels for administrative access:

| Service | Local Endpoint |
|---|---|
| Zabbix Web | `localhost:8080` |
| Grafana | `localhost:3000` |
| Splunk Web | `localhost:8000` |
| Operator Console | `localhost:8501` |

This keeps administrative access separate from normal monitoring, logging, AI, and remediation traffic.

## Validation and Lessons Learned

The deployment validated several important concepts:

- VPC subnet segmentation and role-based server placement
- Bastion-controlled SSH administration
- Local retention of administrative private keys
- Security Group references for role-based trust
- Separation of routing problems from authentication problems
- The difference between private addressing and Internet egress
- NAT Gateway versus public IPv4 cost/security trade-offs
- The need to evaluate the complete network path during troubleshooting

## Result

The EC2 access foundation evolved from three initial infrastructure servers into the current distributed AWS environment without changing its core management principle:

> Administrative access is controlled through the Bastion, while operational service traffic follows explicitly permitted internal paths.

This access model supports the project's monitoring, centralized logging, AI-assisted analysis, controlled remediation, and hybrid connectivity layers.
