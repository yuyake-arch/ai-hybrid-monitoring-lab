# AWS Cloud Infrastructure

## Purpose
This document defines the AWS infrastructure foundation of the **AI-Assisted Hybrid Monitoring & Automation Lab**: network segmentation, EC2 role separation, hybrid routing, and public-addressing decisions. Administrative SSH procedures and application configuration are documented separately.

## Network Architecture
| Network | CIDR | Purpose |
| --- | --- | --- |
| AWS VPC | `10.10.0.0/16` | Project VPC |
| Public Subnet | `10.10.1.0/24` | Bastion and WireGuard gateway |
| Monitoring Subnet | `10.10.10.0/24` | Monitoring, logging, AI, and managed workloads |
| Automation Subnet | `10.10.20.0/24` | Automation services |
| WireGuard Overlay | `10.200.0.0/24` | AWS ↔ local routed connectivity |
| Local VMware Network | `192.168.16.0/24` | Local lab environment |

The public subnet contains two independent roles: the **Bastion Server** for administrative access and the **WireGuard Server** for routed hybrid connectivity.

## EC2 Role Separation
| Instance | Primary Responsibility |
| --- | --- |
| `aws-mgmt-bastion-01` | Administrative SSH access and tunnels |
| `aws-mon-core-01` | Monitoring platform and operator interface |
| `aws-splunk-svr-01` | Centralized logging |
| `aws-ai-svr-01` | Incident analysis and correlation |
| `aws-auto-core-01` | Controlled remediation and Ansible |
| `aws-managed-svr-01` | Managed workload |
| `aws-vpn-gw-01` | WireGuard gateway |

Role separation keeps monitoring, logging, analysis, and remediation boundaries explicit and allows Security Groups to be scoped to service requirements.

## Hybrid Routing
The local Ubuntu VM uses WireGuard address `10.200.0.2`; the AWS gateway uses `10.200.0.1`. The routed VPN provides private monitoring and log-forwarding connectivity between the local environment and AWS.

Administrative access is intentionally separate and enters through the Bastion Server.

## Public Addressing and NAT Trade-off
The Bastion and WireGuard gateway require public connectivity for their roles. Some earlier lab workloads also retain public IPv4 addresses because the lab avoids the ongoing cost of a NAT Gateway.

Public addressing does not imply unrestricted service exposure; Security Groups remain the primary network-access control. A production design could move internal workloads to private-only addressing with controlled egress.

## Infrastructure Ownership
Terraform manages the AWS infrastructure layer, including VPC/subnets, routing, EC2, Security Groups, Elastic IPs, hybrid routes, and WireGuard `source_dest_check` configuration. Ansible manages operating-system and application configuration.

## Related Documentation
- [AWS EC2 Secure Network Access](aws-ec2-secure-network-access.md)
- [Local Virtualization Environment](local-virtualization-environment.md)
- [Zabbix Monitoring Stack](zabbix-monitoring-stack.md)
- [Ansible Automation Server](ansible-automation-server.md)
