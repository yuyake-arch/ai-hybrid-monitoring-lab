# Ansible Automation Server

## Purpose
The Automation Server provides the controlled execution layer for configuration management and remediation. This document focuses only on that server's Ansible and remediation responsibilities.

## Server Role
`aws-auto-core-01` hosts:
- Ansible
- the private Remediation API
- deterministic remediation controls
- predefined playbooks and roles
- execution audit logging

Monitoring and AI analysis remain separate responsibilities.

## Ansible Control Node
Reusable automation covers Zabbix Agent 2, Splunk Universal Forwarder, platform-aware configuration, handlers, and idempotent remediation.

A host being known to monitoring or identity-normalization logic does not authorize remediation.

## Controlled Execution
```text
Human-approved action
        ↓
Private Remediation API
        ↓
Service-token validation
        ↓
Action allowlist
        ↓
Target allowlist
        ↓
Fixed action-to-playbook mapping
        ↓
Ansible
        ↓
Authorized target
```

The API does not accept arbitrary shell commands, scripts, user-supplied playbook paths, or unrestricted extra arguments.

A remediation target must be authorized in both:
```text
automation/remediation_api/app/config/targets.py
automation/inventory/hosts.ini
```

## SSH and Repository Scope
Ansible reaches managed nodes over SSH. The Bastion/ProxyJump and workstation key-handling model is documented in [AWS EC2 Secure Network Access](aws-ec2-secure-network-access.md).

The Automation Server uses the `automation/` portion of the project monorepo as its deployment source. GitHub authentication can use SSH agent forwarding from the administrator workstation; GitHub private keys are not stored on the server.

Project-wide checkout details for other servers are intentionally outside this document.

## Secret Handling
Splunk Forwarder credentials are stored in:
```text
automation/vault/splunk.yml
```

The real Vault file is Git-ignored and explicitly loaded only by the Splunk Forwarder workflow. A safe example file is tracked. Environment-specific inventory is also excluded while an example inventory is tracked.

## Reliability Validation
Validation included Ansible connectivity, reusable agent/forwarder deployment, controlled remediation, idempotency, target allowlist enforcement, and execution-result handling.

A zero process return code is not treated as sufficient when no target host was matched. `changed=false` can still be successful when the target is already in the required state.

## Related Documentation
- [AWS EC2 Secure Network Access](aws-ec2-secure-network-access.md)
- [Automated Zabbix Agent Deployment](../02-ansible-zabbix-agent/automated-zabbix-agent-deployment.md)
- [Controlled Automated Remediation](../06-controlled-remediation/controlled-automated-remediation.md)
- [Zabbix Agent and Splunk Forwarder Automation](../12-agent-forwarder-automation/zabbix-agent-and-splunk-forwarder-automation.md)
