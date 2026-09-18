# Terraform Infrastructure as Code

## Overview

Terraform infrastructure adoption focused on adopting the existing AWS infrastructure of the **AI-Assisted Hybrid Monitoring & Automation Lab** into Terraform.

Rather than rebuilding the environment, existing manually configured AWS resources were imported into Terraform state and converted into Infrastructure as Code (IaC). Each stage was validated with `terraform plan` to avoid unintended infrastructure changes.

---

## Objectives

- Introduce Terraform to the existing AWS lab
- Import existing resources instead of recreating them
- Manage networking, security, compute, routing, and public IP resources as code
- Preserve the existing hybrid AWS/VMware architecture
- Reduce hardcoded infrastructure dependencies
- Establish a reusable and version-controlled Terraform structure

---

## Terraform Project Structure

```text
terraform/
├── versions.tf
├── providers.tf
├── variables.tf
├── network.tf
├── routes.tf
├── security_groups.tf
├── security_group_rules.tf
├── compute.tf
├── eip.tf
├── outputs.tf
├── terraform.tfvars.example
├── .terraform.lock.hcl
└── .gitignore
```

The AWS environment is deployed in `us-east-2`.

---

## Infrastructure Adopted into Terraform

### Networking

Terraform now manages:

- 1 VPC
- 3 subnets: Public, Private, and Management
- Internet Gateway
- 3 route tables
- Route table associations
- Internet routes
- Hybrid routes between AWS and the local VMware environment

Hybrid routes include:

```text
10.200.0.0/24
192.168.16.0/24
```

These networks are routed through the WireGuard gateway.

### Compute

Seven existing EC2 instances were imported:

| Role | Instance Name |
|---|---|
| Bastion | `aws-mgmt-bastion-01` |
| Monitoring | `aws-mon-core-01` |
| Automation | `aws-auto-core-01` |
| AI Backend | `aws-ai-svr-01` |
| Splunk | `aws-splunk-svr-01` |
| Managed Server | `aws-managed-svr-01` |
| WireGuard Gateway | `aws-vpn-gw-01` |

Root EBS volumes and primary network interfaces remain managed through their EC2 resources rather than as separate Terraform resources.

### Security Groups

Terraform manages:

- 10 security groups
- 19 ingress rules
- 10 egress rules

Security group rules are defined separately with:

```hcl
aws_vpc_security_group_ingress_rule
aws_vpc_security_group_egress_rule
```

This keeps individual access rules easier to review and maintain.

### Elastic IP Addresses

Two permanent Elastic IP configurations are managed:

- Bastion host EIP
- WireGuard gateway EIP

EIP resources and their EC2 associations are managed separately.

---

## WireGuard Routing Improvement

Initially, hybrid routes referenced the WireGuard network interface using a hardcoded ENI ID.

After importing the WireGuard EC2 instance, the routes were refactored to use:

```hcl
network_interface_id = aws_instance.wireguard.primary_network_interface_id
```

This removes an unnecessary hardcoded dependency.

The WireGuard instance also preserves:

```hcl
source_dest_check = false
```

because it forwards traffic between networks.

---

## Variables and Outputs

Common environment values were moved into `variables.tf`, including:

- AWS region
- VPC CIDR
- Subnet CIDRs
- Existing EC2 key pair name
- EC2 instance types

A `terraform.tfvars.example` file documents the expected variable structure without storing environment-specific credentials.

Useful outputs include:

- Bastion public IP
- WireGuard public IP
- Core server private IP addresses
- VPC ID
- WireGuard primary ENI ID

---

## Resources Intentionally Outside Terraform

The following remain outside Terraform by design:

- Existing EC2 key pair resource and private key material
- IAM users and user credentials
- WireGuard peer configuration
- Zabbix configuration
- Splunk configuration
- AI backend application configuration
- Ansible-managed OS and application configuration

Terraform manages the **AWS infrastructure layer**, while Ansible remains responsible for **server and application configuration**.

---

## Validation

Resources were imported incrementally and checked throughout the adoption process.

```bash
terraform fmt
terraform validate
terraform plan
```

The primary validation target was:

```text
No changes. Your infrastructure matches the configuration.
```

The final Terraform state contains **65 managed resources**. A no-change plan confirmed that the Terraform configuration matched the existing AWS environment.

---

## Git and State Security

Terraform source files are version-controlled, while local state, `.terraform/`, private variable files, and private key material are excluded from Git.

`.terraform.lock.hcl` and `terraform.tfvars.example` are retained in the repository for reproducibility and documentation.

---

## Key Takeaways

- Existing AWS infrastructure can be adopted safely through Terraform import.
- `terraform plan` is essential when migrating manually created resources into IaC.
- Terraform references are preferable to hardcoded AWS resource IDs.
- Separating security group rules improves access-control visibility.
- Terraform and Ansible have complementary responsibilities.
- Terraform state and credentials should never be committed to a public repository.

---

## Result

Terraform infrastructure adoption established Terraform as the infrastructure management layer for the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The existing hybrid environment was preserved while its AWS networking, security, EC2, routing, and EIP resources were brought under Terraform management and validated against the live infrastructure.

This provides a stronger foundation for repeatable infrastructure changes, configuration review, and future automation.
