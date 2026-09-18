# Automated Zabbix Agent Deployment with Ansible

## Overview

This implementation focused on automating the deployment and configuration of **Zabbix Agent 2** using **Ansible**.

The goal was to move from manual monitoring-agent installation to a reusable configuration-management workflow that can eventually be applied to multiple Linux servers.

The implementation included:

- Ansible inventory organization
- Reusable Ansible Roles
- OS-family detection
- Amazon Linux 2023 package deployment
- Ansible variable precedence
- Automated Zabbix Agent configuration
- Handler-based service management
- Connectivity troubleshooting
- Validation through the Zabbix monitoring interface

---

## Architecture

```text
                        AWS VPC
                           │
             ┌─────────────┴─────────────┐
             │                           │
             │                           │
      Automation Server           Zabbix Server
      aws-auto-core-01             10.10.10.10
          Ubuntu                        │
             │                          │
             │ SSH / Ansible            │ Zabbix Monitoring
             │ TCP 22                   │
             ▼                          │
      aws-managed-svr-01 ◄──────────────────┘
      Amazon Linux 2023
      Zabbix Agent 2
```

The Automation Server acts as the **Ansible control node**, while monitored Linux servers operate as **managed nodes**.

---

## Environment

| Component | Platform / Technology |
|---|---|
| Automation Server | AWS EC2 / Ubuntu |
| Managed Server | AWS EC2 / Amazon Linux 2023 |
| Monitoring Platform | Zabbix 7.4 |
| Monitoring Agent | Zabbix Agent 2 |
| Automation | Ansible |
| Package Manager | DNF |
| Service Manager | systemd |
| Configuration Format | YAML / INI |

---

## 1. Inventory Organization

The existing Ansible inventory was extended with a dedicated group for systems that should receive Zabbix Agent.

Example:

```ini
[monitoring]
aws-mon-core-01 ansible_host=10.10.10.10 ansible_user=ubuntu

[automation]
aws-auto-core-01 ansible_connection=local

[zabbix_agents]
aws-managed-svr-01 ansible_host=<PRIVATE_IP> ansible_user=ec2-user
```

Using a dedicated `zabbix_agents` group allows the Zabbix Agent playbook to target only monitored nodes without modifying existing monitoring or automation servers.

Connectivity was validated before deployment:

```bash
ansible zabbix_agents -m ping
```

---

## 2. Ansible Role Structure

A reusable `zabbix_agent` role was created instead of placing all tasks directly inside the playbook.

```text
automation/
├── ansible.cfg
├── inventory/
│   ├── hosts.ini
│   ├── group_vars/
│   │   └── zabbix_agents.yml
│   └── host_vars/
│
├── playbooks/
│   └── install_zabbix_agent.yml
│
└── roles/
    └── zabbix_agent/
        ├── defaults/
        │   └── main.yml
        ├── handlers/
        │   └── main.yml
        ├── tasks/
        │   ├── main.yml
        │   ├── RedHat.yml
        │   └── Debian.yml
        └── templates/
```

The design separates:

- reusable defaults
- environment-specific variables
- OS-specific installation logic
- service handlers
- deployment orchestration

---

## 3. Configuring the Role Search Path

Initially, Ansible could not locate the `zabbix_agent` role.

The project-level `ansible.cfg` was configured with the role path:

```ini
[defaults]
inventory = inventory/hosts.ini
roles_path = ./roles
```

The active Ansible configuration can be verified with:

```bash
ansible --version
```

and:

```bash
ansible-config dump --only-changed
```

This ensures that Ansible searches:

```text
automation/roles/
```

for project-specific roles.

---

## 4. OS Detection

Ansible facts were used to determine the operating-system family and package manager.

For the Amazon Linux 2023 managed node:

```text
ansible_os_family = RedHat
ansible_pkg_mgr   = dnf
```

Although Amazon Linux is not Red Hat Enterprise Linux, Ansible classifies it as part of the `RedHat` OS family.

The role can therefore dynamically load OS-family-specific tasks:

```yaml
- name: Load OS-specific installation tasks
  ansible.builtin.include_tasks: "{{ ansible_os_family }}.yml"
```

For Amazon Linux 2023, this resolves to:

```text
tasks/RedHat.yml
```

This allows the same role architecture to support additional Linux distributions later.

---

## 5. Zabbix Version and Repository Management

The Zabbix version is defined as a reusable role default.

Example:

```yaml
zabbix_version: "7.4"
```

The Amazon Linux repository URL is generated using that variable rather than hardcoding the version repeatedly.

```yaml
zabbix_repo_rpm_amazon_2023: "https://repo.zabbix.com/zabbix/{{ zabbix_version }}/release/amazonlinux/2023/noarch/zabbix-release-latest-{{ zabbix_version }}.amzn2023.noarch.rpm"
```

This makes future version changes easier to manage.

---

## 6. Understanding Ansible Variable Precedence

One troubleshooting issue occurred when:

```yaml
zabbix_version: "7.4"
```

was defined in:

```text
roles/zabbix_agent/defaults/main.yml
```

but Ansible attempted to access a Zabbix 7.0 repository.

The project was searched for another definition:

```bash
grep -RIn --exclude-dir=.git \
  -E 'zabbix_version|zabbix_repo_rpm|7\.0' .
```

This demonstrated an important Ansible concept:

> Role defaults are intentionally low-priority variables and can be overridden by inventory or other higher-precedence variables.

A simplified precedence model used in this project is:

```text
Lower precedence

Role defaults
     ↓
group_vars
     ↓
host_vars
     ↓
Playbook variables
     ↓
Role vars
     ↓
Extra variables (-e)

Higher precedence
```

For example:

### Role Default

```yaml
zabbix_agent_server: "127.0.0.1"
zabbix_agent_server_active: "127.0.0.1"
```

### Environment Configuration

`inventory/group_vars/zabbix_agents.yml`

```yaml
zabbix_agent_server: "10.10.10.10"
zabbix_agent_server_active: "10.10.10.10"
```

The effective values become:

```text
Server=10.10.10.10
ServerActive=10.10.10.10
```

This keeps the Role reusable while allowing environment-specific configuration.

---

## 7. Installing Zabbix Agent 2

Amazon Linux 2023 uses DNF.

The RedHat-family task installs the Zabbix repository and Agent 2 package.

Conceptually:

```yaml
- name: Install Zabbix repository
  ansible.builtin.dnf:
    name: "{{ zabbix_repo_rpm_amazon_2023 }}"
    state: present
    disable_gpg_check: true

- name: Refresh DNF metadata
  ansible.builtin.dnf:
    update_cache: true

- name: Install Zabbix Agent 2
  ansible.builtin.dnf:
    name: "{{ zabbix_agent_package }}"
    state: present
```

This keeps package-management logic separate from the main role workflow.

---

## 8. Check Mode Limitation

During testing, the playbook was executed with:

```bash
ansible-playbook playbooks/install_zabbix_agent.yml \
  --check --diff
```

A package error occurred because check mode can report that the repository task *would* change the system without actually installing the repository.

The subsequent DNF operation therefore could not locate:

```text
zabbix-agent2
```

This demonstrated an important limitation of Ansible check mode:

> Dry-run results can be incomplete when later tasks depend on changes that earlier tasks would have made.

Repository and package dependencies therefore need to be considered when interpreting `--check` results.

---

## 9. Agent Configuration

Instead of replacing the complete package-provided `zabbix_agent2.conf`, the existing configuration file can be modified selectively with `lineinfile`.

Target configuration:

```text
/etc/zabbix/zabbix_agent2.conf
```

Important parameters include:

```text
Server=
ServerActive=
Hostname=
```

Example:

```yaml
- name: Configure allowed Zabbix server
  ansible.builtin.lineinfile:
    path: "{{ zabbix_agent_config_path }}"
    regexp: '^Server='
    line: "Server={{ zabbix_agent_server }}"
    backup: true
  notify: Restart Zabbix Agent 2

- name: Configure active Zabbix server
  ansible.builtin.lineinfile:
    path: "{{ zabbix_agent_config_path }}"
    regexp: '^ServerActive='
    line: "ServerActive={{ zabbix_agent_server_active }}"
  notify: Restart Zabbix Agent 2

- name: Configure Zabbix hostname
  ansible.builtin.lineinfile:
    path: "{{ zabbix_agent_config_path }}"
    regexp: '^Hostname='
    line: "Hostname={{ zabbix_agent_hostname }}"
  notify: Restart Zabbix Agent 2
```

This approach preserves most of the vendor-provided configuration while automating only the parameters required by the lab.

---

## 10. Handler-Based Service Management

A handler was added to restart Zabbix Agent only when its configuration changes.

`roles/zabbix_agent/handlers/main.yml`:

```yaml
---
- name: Restart Zabbix Agent 2
  ansible.builtin.systemd:
    name: "{{ zabbix_agent_service }}"
    state: restarted
```

Tasks trigger it using:

```yaml
notify: Restart Zabbix Agent 2
```

This provides idempotent behavior:

```text
Configuration unchanged
        ↓
No restart

Configuration changed
        ↓
Handler triggered
        ↓
Zabbix Agent restarted
```

---

## 11. systemd Service Management

Both Ubuntu and Amazon Linux 2023 use systemd, so the role uses:

```yaml
ansible.builtin.systemd
```

Example:

```yaml
- name: Enable and start Zabbix Agent 2
  ansible.builtin.systemd:
    name: "{{ zabbix_agent_service }}"
    enabled: true
    state: started
```

The service can be verified manually with:

```bash
systemctl status zabbix-agent2
```

---

## 12. Zabbix Communication Model

Troubleshooting also reinforced the difference between passive and active Zabbix checks.

### Passive Checks

```text
Zabbix Server
      │
      │ TCP 10050
      ▼
Zabbix Agent
```

The Zabbix Server initiates the connection.

The monitored server therefore needs to allow TCP `10050` from the Zabbix Server.

### Active Checks

```text
Zabbix Agent
      │
      │ TCP 10051
      ▼
Zabbix Server
```

The Agent initiates the connection to the Zabbix Server.

Understanding this direction is important when configuring AWS Security Groups and troubleshooting connectivity.

---

## 13. Troubleshooting Agent Connectivity

After deployment, the Agent service was successfully running:

```bash
systemctl status zabbix-agent2
```

but Zabbix initially showed no monitoring data.

The following checks were useful.

### Verify Agent Configuration

```bash
sudo grep -E '^(Server|ServerActive|Hostname)=' \
  /etc/zabbix/zabbix_agent2.conf
```

### Verify Listening Port

```bash
sudo ss -tlnp | grep 10050
```

### Check Agent Logs

```bash
sudo tail -50 /var/log/zabbix/zabbix_agent2.log
```

### Test Passive Communication

From the Zabbix Server:

```bash
zabbix_get -s <AGENT_PRIVATE_IP> -k agent.ping
```

Expected result:

```text
1
```

### Test Active-Check Connectivity

From the Agent:

```bash
nc -zv 10.10.10.10 10051
```

An active-check configuration issue was identified through the Agent log and corrected in the Zabbix configuration.

After correcting the configuration, monitoring data was successfully collected.

---

## 14. AWS Security Group Considerations

For Ansible management:

```text
Automation Server
       │
       │ TCP 22
       ▼
Managed Server
```

For Zabbix passive monitoring:

```text
Zabbix Server
       │
       │ TCP 10050
       ▼
Managed Server
```

For active checks:

```text
Managed Server
       │
       │ TCP 10051
       ▼
Zabbix Server
```

For larger environments, individual IP-based Security Group rules are not scalable.

A better architecture is to use dedicated Security Groups such as:

```text
sg-automation
sg-zabbix-server
sg-zabbix-agents
```

and reference Security Groups as sources rather than adding individual server IP addresses.

Example concept:

```text
sg-zabbix-agents

Inbound:
TCP 22     ← sg-automation
TCP 10050  ← sg-zabbix-server
```

This design allows the same monitoring Security Group to be attached to many managed EC2 instances.

Infrastructure-level automation of these Security Groups will be handled in a future Terraform phase.

---

## 15. Validation

The completed deployment was validated through:

```bash
ansible zabbix_agents -m ping
```

```bash
ansible-playbook playbooks/install_zabbix_agent.yml \
  --syntax-check
```

```bash
ansible-playbook playbooks/install_zabbix_agent.yml \
  --limit aws-managed-svr-01
```

On the managed server:

```bash
systemctl status zabbix-agent2
```

Final validation included:

- Ansible connectivity successful
- Correct OS detection
- Zabbix repository configured
- Zabbix Agent 2 installed
- Agent configuration automatically updated
- Service enabled and running
- Handler-based restart working
- Zabbix Server connectivity verified
- Monitoring data visible in Zabbix

---

## Challenges and Resolutions

| Challenge | Resolution |
|---|---|
| Ansible could not find the Role | Added the project `roles_path` to `ansible.cfg` |
| SSH connection failed | Verified EC2 SSH key, user, Security Group, and inventory settings |
| Amazon Linux detected as RedHat | Used `ansible_os_family` and separate `RedHat.yml` tasks |
| Wrong Zabbix repository version used | Investigated Ansible variable precedence and removed/updated the overriding variable |
| `zabbix-agent2` package unavailable | Verified repository installation and DNF metadata |
| Missing Jinja2 template | Evaluated template vs `lineinfile` configuration management |
| Missing handler | Added `handlers/main.yml` for controlled service restarts |
| Agent running but no monitoring data | Checked Agent configuration, ports, logs, and active/passive communication |
| Active-check connection failure | Corrected the Zabbix configuration and validated TCP 10051 connectivity |

---

## Key Lessons Learned

### 1. Ansible Roles improve scalability

Separating tasks, variables, handlers, and OS-specific logic makes automation easier to reuse and maintain.

### 2. Inventory groups define automation scope

Using:

```ini
[zabbix_agents]
```

allows the playbook to target monitored systems without accidentally changing unrelated servers.

### 3. Variable precedence matters

Role defaults are designed to be overridden.

This makes it possible to maintain generic automation code while keeping environment-specific configuration in inventory variables.

### 4. OS family and Linux distribution are different concepts

Amazon Linux 2023 is identified by Ansible as:

```text
Distribution: Amazon
OS Family: RedHat
Package Manager: dnf
```

Understanding these facts is important when designing portable Roles.

### 5. Idempotency is fundamental

Handlers ensure that services restart only when necessary rather than every time a playbook runs.

### 6. Monitoring requires both application and network troubleshooting

A running Zabbix Agent service does not guarantee successful monitoring.

Troubleshooting must include:

```text
Service
   ↓
Configuration
   ↓
Listening Ports
   ↓
Security Groups
   ↓
Network Connectivity
   ↓
Zabbix Host / Template Configuration
```

---

## Outcome

This work transformed the Zabbix Agent deployment process from a manual procedure into a reusable Ansible automation workflow.

The Automation Server can now remotely:

1. Identify the managed server's operating system
2. Select the appropriate installation workflow
3. Configure the Zabbix repository
4. Install Zabbix Agent 2
5. Apply environment-specific monitoring configuration
6. Enable and start the service
7. Restart the Agent only when configuration changes
8. Prepare managed nodes for centralized Zabbix monitoring

This provides a scalable foundation for managing additional monitored servers in the hybrid monitoring lab.

---

## Future Improvements

Subsequent project phases extended this automation with:

- AWS dynamic inventory
- Automatic Zabbix host registration using the Zabbix API
- Bulk deployment to multiple managed nodes
- Terraform-based AWS infrastructure provisioning
- Automated Security Group management
- Additional Linux distribution support
- CI/CD validation for Ansible code
- Ansible linting and automated syntax validation

---

## Technologies Used

- AWS EC2
- Ansible
- Zabbix 7.4
- Zabbix Agent 2
- Amazon Linux 2023
- Ubuntu Linux
- DNF
- systemd
- SSH
- YAML
- Git