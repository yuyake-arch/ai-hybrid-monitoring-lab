# Documentation

This directory contains the implementation documentation for the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The documentation is organized by implementation phase rather than by calendar day. Each phase focuses on a specific infrastructure, monitoring, observability, AI-assisted analysis, automation, or security capability developed and validated in the lab.

For the high-level project overview, architecture, workflow, and selected validation evidence, see the repository root `README.md`.

---

## Implementation Documentation

### 01 — Project Foundation

Core AWS and local infrastructure, secure administrative access, the containerized monitoring foundation, and the Ansible automation environment.

- [AWS Cloud Infrastructure](01-project-foundation/aws-cloud-infrastructure.md)
- [AWS EC2 Secure Network Access](01-project-foundation/aws-ec2-secure-network-access.md)
- [Local Virtualization Environment](01-project-foundation/local-virtualization-environment.md)
- [Zabbix Monitoring Stack](01-project-foundation/zabbix-monitoring-stack.md)
- [Ansible Automation Server](01-project-foundation/ansible-automation-server.md)

### 02 — Automated Zabbix Agent Deployment
- [Automated Zabbix Agent Deployment](02-ansible-zabbix-agent/automated-zabbix-agent-deployment.md)

### 03 — Splunk Integration
- [Dedicated Splunk Server Deployment](03-splunk-integration/dedicated-splunk-server-deployment.md)
- [Splunk Log Collection and Hybrid Integration](03-splunk-integration/splunk-log-collection-and-hybrid-integration.md)

### 04 — AI-Assisted Incident Analysis
- [AI Incident Analysis Backend](04-ai-incident-analysis/ai-incident-analysis-backend.md)

### 05 — Splunk Context Retrieval & Correlation
- [Splunk Context Retrieval and Incident Correlation](05-splunk-context-correlation/splunk-context-retrieval-and-incident-correlation.md)

### 06 — Controlled Automated Remediation
- [Controlled Automated Remediation](06-controlled-remediation/controlled-automated-remediation.md)

### 07 — WireGuard Hybrid Connectivity
- [WireGuard Hybrid Connectivity](07-wireguard-hybrid-connectivity/wireguard-hybrid-connectivity.md)

### 08 — Terraform Infrastructure as Code
- [Terraform Infrastructure as Code](08-terraform-infrastructure/terraform-infrastructure-as-code.md)

### 09 — Dashboard & Observability
- [Dashboard and Observability](09-observability-dashboards/dashboard-observability.md)

### 10 — End-to-End Failure & Recovery Validation
- [End-to-End Failure & Recovery Validation](10-end-to-end-validation/end-to-end-failure-recovery-validation.md)

### 11 — Operator Console
- [Operator Console and Remediation Audit](11-operator-console/operator-console-and-remediation-audit.md)

### 12 — Agent & Forwarder Automation
- [Zabbix Agent and Splunk Forwarder Automation](12-agent-forwarder-automation/zabbix-agent-and-splunk-forwarder-automation.md)

### 13 — Security & Reliability Review
- [Security and Reliability Review](13-security-reliability/security-reliability-review.md)

---

## End-to-End Design Principle

```text
Zabbix Detection
      ↓
Splunk Evidence Correlation
      ↓
Deterministic Baseline + Gemini-Assisted Analysis
      ↓
Deterministic Remediation Policy
      ↓
Human Approval
      ↓
Allowlisted Automation
      ↓
Zabbix Recovery Verification
```

The LLM is used for **analysis and recommendations only**. It does not directly execute infrastructure changes. Executable remediation is determined by deterministic policy, requires operator approval, and is constrained by predefined automation controls.

## Documentation Scope

These documents focus on implementation decisions, configuration, troubleshooting, validation, and security controls. Phase-specific screenshots remain alongside the relevant implementation documents, while the repository-level documentation presents the final architecture and selected end-to-end evidence.
