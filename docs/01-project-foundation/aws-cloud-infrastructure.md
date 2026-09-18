# AWS Cloud Infrastructure

## Overview

This document describes the AWS infrastructure foundation implemented for the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The environment uses AWS as the centralized platform for monitoring, logging, AI-assisted incident analysis, and controlled remediation while maintaining hybrid connectivity with a local VMware-based Ubuntu system.

The infrastructure was designed around several practical goals:

- Separate infrastructure responsibilities through network and server-role segmentation
- Restrict administrative and service-to-service access
- Support hybrid AWS-to-local monitoring through WireGuard
- Provide dedicated monitoring, logging, AI analysis, and automation services
- Keep the lab operationally realistic while controlling cloud cost
- Manage the finalized AWS infrastructure through Terraform

---

## Final AWS Network Foundation

The AWS environment uses a dedicated VPC:

| Network | CIDR | Purpose |
|---|---|---|
| AWS VPC | `10.10.0.0/16` | Project network |
| Public Subnet | `10.10.1.0/24` | Bastion and WireGuard gateway |
| Monitoring Subnet | `10.10.10.0/24` | Monitoring, logging, AI, and managed workloads |
| Automation Subnet | `10.10.20.0/24` | Automation and remediation services |

The subnet separation provides logical boundaries between public access, observability workloads, and automation services.

The public subnet contains two independent infrastructure roles:

- **Bastion Server** — administrative SSH entry point and SSH tunneling
- **WireGuard Gateway** — VPN endpoint for hybrid AWS-to-local connectivity

These roles are intentionally separated rather than combined into a single gateway host.

---

## AWS Server Roles

The final AWS environment contains seven EC2 instances with distinct responsibilities.

| Server | Primary Role |
|---|---|
| `aws-mgmt-bastion-01` | Administrative access and SSH tunneling |
| `aws-mon-core-01` | Zabbix Server, Grafana, PostgreSQL, Incident Operator |
| `aws-splunk-svr-01` | Splunk Enterprise and centralized log indexing |
| `aws-ai-svr-01` | FastAPI-based incident analysis and correlation backend |
| `aws-auto-core-01` | Remediation API and Ansible automation |
| `aws-managed-svr-01` | Monitored and automation-managed workload |
| `aws-vpn-gw-01` | WireGuard VPN gateway |

This separation avoids placing monitoring, logging, AI analysis, and remediation execution on a single host and makes the operational boundaries easier to understand and secure.

---

## Administrative Access

Administrative access is routed through `aws-mgmt-bastion-01`.

The Bastion server provides SSH access to internal EC2 instances and is also used for local port forwarding when administrative web interfaces need to be accessed without exposing them publicly.

Examples include:

| Service | Local Access |
|---|---|
| Zabbix Web | `localhost:8080` |
| Grafana | `localhost:3000` |
| Splunk Web | `localhost:8000` |
| Operator Console | `localhost:8501` |

The Bastion is not the WireGuard VPN endpoint. Hybrid connectivity is handled independently by `aws-vpn-gw-01`.

---

## Hybrid Connectivity

WireGuard provides encrypted connectivity between AWS and the local VMware environment.

The VPN overlay uses:

| Endpoint | WireGuard Address |
|---|---|
| AWS WireGuard Gateway | `10.200.0.1` |
| Local Ubuntu VM | `10.200.0.2` |

The local environment can communicate with AWS monitoring and logging services through the WireGuard tunnel without exposing those service interfaces directly to the public Internet.

Conceptually:

```text
Local Ubuntu VM
192.168.16.10
      |
      | WireGuard
      |
10.200.0.2
      |
      | Encrypted Tunnel
      |
10.200.0.1
aws-vpn-gw-01
      |
      v
AWS VPC 10.10.0.0/16
```

Hybrid routes are part of the AWS routing design so traffic for the WireGuard overlay and local lab network can be directed through the VPN gateway.

---

## Security Group Strategy

Security Groups are used as role-based network controls rather than maintaining large collections of individual host IP rules.

Examples of service relationships include:

```text
Zabbix Server
    |
    | TCP 10050
    v
Zabbix Agents
```

Zabbix active-agent communication can use TCP `10051` toward the Zabbix Server.

Splunk log forwarding follows:

```text
Splunk Universal Forwarder
    |
    | TCP 9997
    v
Splunk Server
```

The AI Backend accesses the Splunk management/API interface on TCP `8089`, with access restricted to the required source role.

The Automation Server exposes the private remediation API only to authorized internal callers rather than as a public Internet service.

Using Security Group references allows access policies to follow infrastructure roles as the environment grows.

---

## Routing and Internet Access

Subnet behavior is determined by the combination of route tables, gateways, Security Groups, and instance networking.

A public subnet requires a route through the Internet Gateway:

```text
10.10.0.0/16  -> local
0.0.0.0/0     -> Internet Gateway
```

Hybrid routing additionally directs the relevant WireGuard/local network traffic through the WireGuard gateway.

A key lesson from the implementation is that assigning a public or Elastic IP does not independently guarantee connectivity. Troubleshooting must consider the complete path:

```text
Application
    ↓
Listening Port
    ↓
Host Firewall
    ↓
Security Group
    ↓
Subnet / Route Table
    ↓
Gateway / VPN
    ↓
Remote Host
```

---

## Public IPv4, Elastic IP, and NAT Trade-offs

Public addressing and NAT solve different problems.

A public IPv4 address can make an instance Internet-addressable when routing and Security Groups permit it. An Elastic IP provides a stable public address and is useful for infrastructure endpoints that require predictable addressing, such as the Bastion and WireGuard gateway.

A NAT Gateway instead allows private instances to initiate outbound Internet connections without making those instances directly reachable from the Internet.

For this lab, NAT Gateway cost was an important design consideration. Some workloads retain public IPv4 connectivity where necessary rather than introducing a continuously billed NAT Gateway solely to reproduce a production-style topology.

This is an intentional lab trade-off rather than an assumption that public addressing is preferable for production infrastructure.

---

## Monitoring and Observability Placement

The Monitoring Server hosts the containerized monitoring stack:

```text
aws-mon-core-01
|
+-- Docker
    |
    +-- Zabbix Server
    +-- Zabbix Web
    +-- PostgreSQL
    +-- Grafana
```

Splunk Enterprise is deployed separately on `aws-splunk-svr-01`, while the AI incident-analysis backend runs on `aws-ai-svr-01`.

This evolved from the earlier compact lab design into a distributed architecture with clearer service boundaries.

---

## Infrastructure as Code

The AWS environment was initially built and validated manually to develop hands-on understanding of VPC networking, EC2 access, routing, and Security Groups.

The finalized AWS infrastructure was then imported into Terraform and brought under Infrastructure as Code management.

Terraform manages the AWS infrastructure layer, including:

- VPC and subnet resources
- Internet Gateway
- Route tables and associations
- Internet and hybrid routes
- EC2 instances
- Security Groups and rules
- Elastic IP resources
- WireGuard gateway network behavior required for routing

The finalized Terraform state manages the existing AWS environment without recreating the manually established infrastructure.

Terraform is responsible for AWS infrastructure resources, while Ansible remains responsible for operating-system and application configuration.

Sensitive and environment-specific Terraform runtime data such as state files and the actual `terraform.tfvars` are excluded from Git.

---

## Configuration Management Boundary

Infrastructure responsibilities are intentionally separated:

```text
Terraform
    ↓
AWS Infrastructure
VPC / Subnets / Routes / EC2 / Security Groups
```

```text
Ansible
    ↓
Operating System and Application Configuration
Agents / Forwarders / Service Configuration / Remediation
```

This prevents Terraform from becoming responsible for application-level configuration and keeps Ansible focused on repeatable host configuration and operational automation.

---

## Cost-Aware Architecture

Cost control is part of the lab architecture.

Practical measures include:

- Using appropriately sized EC2 instances
- Stopping lab resources when they are not required
- Avoiding a NAT Gateway where its ongoing cost is not justified
- Using Elastic IPs only where stable public endpoints are needed
- Consolidating suitable monitoring components with Docker
- Removing unused cloud resources
- Monitoring AWS billing and budgets

The design intentionally balances security, operational realism, learning value, and cost rather than reproducing every high-availability production component.

---

## Key Design Decisions

### Separate Bastion and WireGuard Roles

Administrative SSH access and hybrid VPN routing are handled by different EC2 instances. This keeps administrative access independent from the hybrid network gateway.

### Dedicated Service Roles

Monitoring, Splunk, AI analysis, and automation are separated into dedicated server roles instead of being hosted together.

### Role-Based Security Groups

Security Group relationships represent infrastructure roles and required communication paths rather than relying on broad network access.

### Private Service Communication Where Practical

Internal services such as the Splunk API and Remediation API use restricted AWS network paths and Security Group controls.

### Terraform for AWS Infrastructure, Ansible for Host Configuration

The project uses separate tools for infrastructure lifecycle management and operating-system/application automation.

### Cost-Conscious Internet Egress

The lab does not use a NAT Gateway simply to imitate an enterprise reference architecture. Public IPv4 use on selected lab workloads is an accepted cost trade-off.

---

## Lessons Learned

The AWS implementation reinforced several infrastructure concepts:

1. **Network reachability depends on the entire path.**  
   IP addressing alone is insufficient; routing, gateways, Security Groups, host configuration, and application listeners must all align.

2. **Public IPs and NAT serve different purposes.**  
   Direct addressing provides inbound/outbound reachability, while NAT primarily provides outbound Internet access for private workloads.

3. **Security Groups scale better when they represent roles.**  
   Role-based relationships are easier to maintain than large collections of host-specific rules.

4. **Hybrid connectivity introduces routing requirements beyond the VPN tunnel itself.**  
   The tunnel, AWS routing, host routing, and security policies must work together.

5. **Infrastructure ownership should be clearly divided.**  
   Terraform manages AWS resources while Ansible manages host and application configuration.

6. **Cloud architecture must account for cost.**  
   A technically valid production pattern may not be appropriate for a continuously operated learning environment.

---

## Result

The AWS foundation evolved from a manually configured learning environment into a segmented, Terraform-managed hybrid infrastructure supporting the complete monitoring and remediation workflow.

It now provides the infrastructure required for:

```text
Hybrid Infrastructure
        ↓
Monitoring + Centralized Logging
        ↓
Incident Detection
        ↓
Context Correlation
        ↓
AI-Assisted Analysis
        ↓
Deterministic Remediation Control
        ↓
Human Approval
        ↓
Controlled Automation
        ↓
Independent Recovery Verification
```

The resulting AWS environment provides the foundation for the project's monitoring, observability, AI-assisted incident analysis, controlled remediation, and hybrid operations capabilities.
