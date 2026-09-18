# Documentation

This directory contains the implementation documentation for the **AI-Assisted Hybrid Monitoring & Automation Lab**.

The documentation is organized by implementation phase rather than by calendar day. Each phase focuses on a specific infrastructure, monitoring, observability, AI-assisted analysis, automation, or security capability developed and validated in the lab.

For the high-level project overview, architecture, workflow, and selected validation evidence, see the repository root `README.md`.

---

## Implementation Documentation

### 01 — Project Foundation

Core AWS and local infrastructure, secure access, container host preparation, monitoring foundation, and the initial Ansible automation environment.

- [AWS Cloud Infrastructure](01-project-foundation/aws-cloud-infrastructure.md)
- [AWS EC2 Secure Network Access](01-project-foundation/aws-ec2-secure-network-access.md)
- [Local Virtualization Environment](01-project-foundation/local-virtualization-environment.md)
- [Docker Host Preparation](01-project-foundation/docker-host-preparation.md)
- [Zabbix Monitoring Stack](01-project-foundation/zabbix-monitoring-stack.md)
- [Ansible Automation Server](01-project-foundation/ansible-automation-server.md)

### 02 — Automated Zabbix Agent Deployment

Reusable Ansible automation for deploying and configuring Zabbix Agent 2 on managed Linux systems.

- [Automated Zabbix Agent Deployment](02-ansible-zabbix-agent/automated-zabbix-agent-deployment.md)

### 03 — Splunk Integration

Dedicated Splunk Enterprise deployment and centralized collection of operating-system, security, application, and hybrid-environment logs.

- [Dedicated Splunk Server Deployment](03-splunk-integration/dedicated-splunk-server-deployment.md)
- [Splunk Log Collection and Hybrid Integration](03-splunk-integration/splunk-log-collection-and-hybrid-integration.md)

### 04 — AI-Assisted Incident Analysis

FastAPI-based incident-analysis backend combining deterministic baseline analysis, Gemini-assisted reasoning, structured results, persistence, and graceful fallback behavior.

- [AI Incident Analysis Backend](04-ai-incident-analysis/ai-incident-analysis-backend.md)

### 05 — Splunk Context Retrieval & Correlation

Bounded retrieval of relevant Splunk evidence and correlation with Zabbix incidents before AI-assisted analysis.

- [Splunk Context Retrieval and Incident Correlation](05-splunk-context-correlation/splunk-context-retrieval-and-incident-correlation.md)

### 06 — Controlled Automated Remediation

Deterministic remediation policy, human approval, private remediation API, action and target authorization, and allowlisted Ansible execution.

- [Controlled Automated Remediation](06-controlled-remediation/controlled-automated-remediation.md)

### 07 — WireGuard Hybrid Connectivity

Secure connectivity between the local VMware environment and AWS using a dedicated WireGuard gateway and private hybrid routing.

- [WireGuard Hybrid Connectivity](07-wireguard-hybrid-connectivity/wireguard-hybrid-connectivity.md)

### 08 — Terraform Infrastructure as Code

Terraform management of the existing AWS infrastructure, including networking, EC2 instances, Security Groups, routing, and WireGuard-related configuration.

- [Terraform Infrastructure as Code](08-terraform-infrastructure/terraform-infrastructure-as-code.md)

### 09 — Dashboard & Observability

Operational dashboards in Grafana and Splunk for infrastructure health, incident analysis, remediation outcomes, and observability.

- [Dashboard and Observability](09-observability-dashboards/dashboard-observability.md)

### 10 — End-to-End Failure & Recovery Validation

Controlled failure injection validating the complete workflow from Zabbix detection through Splunk evidence, AI-assisted analysis, deterministic policy, human approval, Ansible remediation, and independent recovery verification.

- [End-to-End Failure & Recovery Validation](10-end-to-end-validation/end-to-end-failure-recovery-validation.md)

### 11 — Operator Console

Streamlit-based human-in-the-loop console for reviewing AI recommendations, deterministic executable actions, approval decisions, remediation execution, and audit results.

- [Operator Console and Remediation Audit](11-operator-console/operator-console-and-remediation-audit.md)

### 12 — Agent & Forwarder Automation

Expanded Ansible automation for Zabbix Agent 2 and Splunk Universal Forwarder deployment, including platform-aware behavior and scoped Vault usage.

- [Zabbix Agent and Splunk Forwarder Automation](12-agent-forwarder-automation/zabbix-agent-and-splunk-forwarder-automation.md)

### 13 — Security & Reliability Review

Final review of network exposure, least privilege, secrets handling, log permissions and retention, remediation authorization, service persistence, repository hygiene, and accepted lab limitations.

- [Security and Reliability Review](13-security-reliability/security-reliability-review.md)

---

## End-to-End Design Principle

The completed system follows a controlled AIOps workflow:

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

---

## Documentation Scope

These documents focus on implementation decisions, configuration, troubleshooting, validation, and security controls. Screenshots stored alongside individual phase documents provide phase-specific evidence, while the repository-level documentation presents the final architecture and selected end-to-end evidence.
