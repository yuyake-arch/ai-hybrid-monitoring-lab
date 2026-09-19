# AWS EC2 Secure Network Access

## Purpose
This document is the source of truth for **administrative access** to AWS systems and internal web interfaces in the lab.

## Access Model
```text
Administrator
     ↓ SSH
aws-mgmt-bastion-01
     ↓ ProxyJump / SSH tunnel
Internal AWS services
```

The Bastion is the administrative SSH entry point. Public-addressing rationale is documented in [AWS Cloud Infrastructure](aws-cloud-infrastructure.md).

## SSH Key and Agent Model
Private SSH keys remain on the administrator workstation. The local SSH agent is used so credentials do not need to be copied to AWS servers.

For selected internal hosts that require GitHub access, SSH agent forwarding makes the workstation's GitHub credential available to that SSH session without storing the GitHub private key on the server.

## Sanitized SSH Config Example
```sshconfig
Host bastion
    HostName <BASTION_PUBLIC_IP>
    User ubuntu
    IdentityFile ~/.ssh/<EC2_PRIVATE_KEY>
    ForwardAgent no

Host monitoring
    HostName 10.10.10.10
    User ubuntu
    IdentityFile ~/.ssh/<EC2_PRIVATE_KEY>
    ProxyJump bastion
    ForwardAgent yes
```

`ProxyJump bastion` routes the internal connection through the Bastion. `ForwardAgent` remains disabled on the Bastion itself and is enabled only on an internal host when forwarded credentials are required, such as for GitHub access.

The real private-key filename is intentionally not documented.

With the EC2 key loaded in the local agent, direct ProxyJump syntax can also be used:

```powershell
ssh -J ubuntu@<BASTION_PUBLIC_IP> ubuntu@<PRIVATE_IP>
```

## Internal Web Access
Administrative web interfaces are accessed through SSH local port forwarding rather than routine public exposure.

| Service | Local Access |
| --- | --- |
| Zabbix Web | `localhost:8080` |
| Grafana | `localhost:3000` |
| Splunk Web | `localhost:8000` |
| Operator Console | `localhost:8501` |

This table is maintained here rather than duplicated across infrastructure documents.

## Security Principles
- Keep private SSH keys on the administrator workstation.
- Use the Bastion as the administrative entry point.
- Use ProxyJump for internal SSH access.
- Use SSH tunnels for internal administrative web interfaces.
- Do not copy GitHub private keys to AWS servers.
- Enable agent forwarding only where required.
- Restrict service paths with Security Groups.

## Related Documentation
- [AWS Cloud Infrastructure](aws-cloud-infrastructure.md)
- [Ansible Automation Server](ansible-automation-server.md)
- [Security & Reliability Review](../13-security-reliability/security-reliability-review.md)
