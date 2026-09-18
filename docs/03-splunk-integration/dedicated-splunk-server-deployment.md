# Dedicated Splunk Server Deployment

## Overview

On Splunk deployment and logging integration of the **AI-Assisted Hybrid Monitoring & Automation Lab**, I introduced **Splunk** as the centralized logging platform for the environment.

Zabbix Agent automation focused on deploying the Zabbix Agent with Ansible. The next step was to add centralized log collection so that infrastructure metrics from Zabbix and operating system/application logs from Splunk could later be correlated during incident analysis.

Rather than placing Splunk on the existing monitoring server, I used a **dedicated EC2 instance for Splunk**.

Splunk was installed directly on the Linux operating system rather than being deployed as a Docker container.

---

## Objectives

The main goals for Splunk deployment and logging integration were:

- Add centralized log management to the lab
- Deploy a dedicated Splunk server in AWS
- Keep monitoring and logging workloads separated
- Configure secure network access
- Prepare Splunk to receive logs from managed servers
- Validate Splunk Web access
- Prepare the environment for Splunk Universal Forwarder deployment
- Create the foundation for future AI-assisted incident analysis

---

## Existing Architecture

Before introducing Splunk, the environment already included:

```text
AWS VPC
│
├── Bastion Server
│
├── Monitoring Server
│   ├── Zabbix
│   ├── Grafana
│   └── PostgreSQL
│
└── Automation Server
    └── Ansible
```

The monitoring server was already responsible for the primary monitoring stack.

Instead of adding another resource-intensive service to that system, Splunk was deployed on its own EC2 instance.

---

## Updated Architecture

The resulting architecture became:

```text
                         AWS VPC
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼

   Bastion Server     Monitoring Server   Automation Server
                          │                    │
                     ┌────┴────┐               │
                     │         │               │
                  Zabbix    Grafana          Ansible
                     │
                  PostgreSQL


                         Splunk Server
                              │
                              ▼
                     Splunk Enterprise
                       Direct Install
```

The infrastructure responsibilities are now separated as follows:

```text
Monitoring Server
    → Metrics and availability monitoring

Splunk Server
    → Centralized log collection and analysis

Automation Server
    → Configuration management and deployment automation

Bastion Server
    → Administrative access
```

---

## Why Use a Dedicated Splunk Server?

Deploying Splunk on its own EC2 instance provides several architectural advantages.

## Resource Isolation

Splunk can consume significant memory, CPU, and disk resources, especially during indexing and search operations.

Running it independently prevents Splunk workloads from affecting Zabbix, Grafana, or PostgreSQL.

---

## Fault Isolation

If Splunk experiences high resource utilization or a service failure, the core monitoring services remain available.

This helps prevent a logging problem from becoming a monitoring problem.

---

## Easier Troubleshooting

Each server has a clearly defined responsibility.

```text
Monitoring EC2
    → Metrics

Splunk EC2
    → Logs

Automation EC2
    → Automation
```

This makes system behavior easier to understand and troubleshoot.

---

## Independent Scaling

If Splunk requires more memory or disk capacity later, the Splunk EC2 instance can be resized independently.

The monitoring infrastructure does not need to change.

---

## More Enterprise-Like Architecture

Separating monitoring, centralized logging, and automation into different systems more closely resembles real infrastructure environments.

---

## Splunk Deployment Method

Splunk was installed **directly on the dedicated Linux EC2 instance**.

The deployment structure is therefore:

```text
Splunk EC2
│
├── Ubuntu Linux
│
└── Splunk Enterprise
```

rather than:

```text
Splunk EC2
│
└── Docker
    └── Splunk
```

This direct-install approach makes it easier to understand the native Splunk directory structure, service management, configuration files, and log locations.

---

## Splunk Service Structure

A typical direct Splunk installation uses:

```text
/opt/splunk/
│
├── bin/
├── etc/
└── var/
```

The main Splunk CLI is available from:

```bash
/opt/splunk/bin/splunk
```

Common administrative commands include:

```bash
sudo /opt/splunk/bin/splunk status
```

```bash
sudo /opt/splunk/bin/splunk start
```

```bash
sudo /opt/splunk/bin/splunk restart
```

```bash
sudo /opt/splunk/bin/splunk stop
```

---

## Splunk Web

Splunk Web uses TCP port:

```text
8000
```

Because Splunk runs on a separate EC2 instance, this does not conflict with services running on the monitoring server.

The logical service layout is:

```text
Monitoring Server
    └── Zabbix Web

Splunk Server
    └── Splunk Web : TCP 8000
```

Even if different applications use the same port number, they do not conflict when they run on separate hosts with different IP addresses.

---

## Splunk Forwarder Communication

Managed servers will eventually send logs to the Splunk server through the **Splunk Universal Forwarder**.

The standard forwarding path is:

```text
Managed Server
      │
      │ Logs
      ▼
Splunk Universal Forwarder
      │
      │ TCP 9997
      ▼
Splunk Server
```

TCP port `9997` is used by the Splunk server to receive forwarded event data.

---

## Security Group Design

The dedicated Splunk EC2 instance uses its own Security Group.

Example naming convention:

```text
splunk-sg
```

Typical inbound requirements include:

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | Bastion Server / trusted source | SSH administration |
| 8000 | TCP | Trusted management source | Splunk Web |
| 9997 | TCP | Managed servers | Splunk Forwarder traffic |

The Splunk receiving port should not be exposed unnecessarily to the public Internet.

For example, this should be avoided:

```text
TCP 9997
Source: 0.0.0.0/0
```

A more secure design is:

```text
Managed Server Security Group
            │
            │ TCP 9997
            ▼
       Splunk Security Group
            │
            ▼
       Splunk Server
```

This is easier to manage than manually maintaining individual IP addresses for many servers.

---

## Centralized Logging Architecture

The intended log collection pipeline is:

```text
Linux Server
│
├── /var/log/syslog
├── /var/log/auth.log
└── Application Logs
          │
          ▼
Splunk Universal Forwarder
          │
          │ TCP 9997
          ▼
     Splunk Server
          │
          ▼
        Index
          │
          ▼
      SPL Search
```

This allows system and application logs from multiple machines to be searched from one centralized interface.

---

## Splunk Index Strategy

A dedicated index can be used for Linux infrastructure logs.

Example:

```text
linux
```

A basic SPL query would be:

```spl
index=linux
```

A host-specific query could be:

```spl
index=linux host=<hostname>
```

This allows logs to be filtered by system, application, source type, event type, or time range.

---

## Relationship to Zabbix

Zabbix and Splunk serve different but complementary purposes.

## Zabbix

Zabbix primarily answers questions such as:

- Is the server reachable?
- Is CPU utilization high?
- Is memory exhausted?
- Is disk usage increasing?
- Did a trigger enter a problem state?

The workflow is:

```text
Managed Server
     │
     ▼
Zabbix Agent
     │
     ▼
Zabbix Server
     │
     ▼
Metrics / Alerts
```

---

## Splunk

Splunk provides detailed event context.

For example:

- Authentication failures
- Service errors
- Application exceptions
- System events
- Security events
- Application-specific logs

Its workflow is:

```text
Managed Server
     │
     ▼
Universal Forwarder
     │
     ▼
Splunk Server
     │
     ▼
Logs / Events
```

---

## Combined Observability Model

Together, Zabbix and Splunk provide two complementary observability signals.

```text
                   Managed Server
                        │
               ┌────────┴────────┐
               │                 │
               ▼                 ▼
         Zabbix Agent         Splunk UF
               │                 │
            Metrics              Logs
               │                 │
               ▼                 ▼
            Zabbix             Splunk
```

Zabbix can indicate that something is wrong, while Splunk can provide additional evidence about what was happening when the issue occurred.

---

## Example Incident

Assume Zabbix detects high CPU utilization.

```text
Zabbix Trigger
CPU > Threshold
       │
       ▼
High CPU Incident
```

A monitoring engineer can then search Splunk for events around the same timestamp.

```spl
index=linux host=<affected-host>
```

Potential findings might include:

```text
Application restart
Repeated authentication attempts
Scheduled process
Service failure
Application exception
Unexpected workload
```

This provides better troubleshooting context than metrics alone.

---

## Future AI Integration

The long-term objective of the project is to automate this correlation process.

The planned architecture is:

```text
Zabbix
   │
   │ Alert
   ▼
AI Backend
   │
   ├──────────────► Splunk
   │                 │
   │                 │ Relevant logs
   │◄────────────────┘
   │
   ▼
LLM Analysis
   │
   ▼
Incident Summary
Possible Root Cause
Troubleshooting Recommendations
```

The AI backend can receive a Zabbix incident and query Splunk for related events from the affected host.

The LLM can then analyze:

```text
Monitoring Alert
        +
Relevant Logs
        +
Host Context
        ↓
AI Incident Analysis
```

This forms one of the main observability workflows of the overall project.

---

## Connection to Zabbix Agent automation

Zabbix Agent automation focused on configuration automation.

```text
Ansible
   │
   ▼
Zabbix Agent
   │
   ▼
Managed Server Monitoring
```

Splunk deployment and logging integration extends the infrastructure with centralized logging.

```text
Managed Server
   │
   ▼
Splunk Universal Forwarder
   │
   ▼
Splunk Server
```

The longer-term goal is to automate both.

```text
                     Ansible
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
       Zabbix Agent           Splunk UF
             │                     │
             ▼                     ▼
          Zabbix                Splunk
```

This creates a repeatable onboarding process for newly deployed servers.

---

## Manual Validation Before Automation

The Splunk Universal Forwarder deployment should first be validated manually on one managed Linux server.

The intended workflow is:

```text
Install Universal Forwarder
           ↓
Configure Splunk Server
           ↓
Configure Log Inputs
           ↓
Test TCP 9997
           ↓
Confirm Log Ingestion
           ↓
Validate with SPL
           ↓
Automate with Ansible
```

This approach avoids automating a configuration before the architecture and communication path have been fully verified.

---

## Splunk deployment and logging integration Implementation Flow

The Splunk deployment and logging integration implementation can be summarized as:

```text
1. Provision dedicated Splunk EC2
        ↓
2. Configure Splunk Security Group
        ↓
3. Configure network connectivity
        ↓
4. Install Splunk Enterprise directly on Linux
        ↓
5. Start and configure Splunk service
        ↓
6. Access Splunk Web
        ↓
7. Configure receiving on TCP 9997
        ↓
8. Prepare Linux index
        ↓
9. Install Universal Forwarder on a test host
        ↓
10. Forward system logs
        ↓
11. Verify events using SPL
```

---

## Key Lessons Learned

## 1. Logging Should Be Treated as a Separate Infrastructure Workload

Centralized log indexing and searching can consume significant CPU, memory, and storage.

Deploying Splunk on a dedicated server improves isolation and makes future scaling easier.

---

## 2. Same Port Numbers Do Not Conflict Across Different Servers

Both services can use the same port number if they run on different EC2 instances.

A port conflict occurs only when multiple processes attempt to bind to the same interface and port on the same host.

---

## 3. Monitoring and Logging Solve Different Problems

Metrics identify abnormal infrastructure behavior.

Logs provide detailed evidence surrounding the abnormal behavior.

Using both provides much stronger troubleshooting capabilities.

---

## 4. Security Groups Should Restrict Log Ingestion

Splunk's forwarding port should be accessible only from systems that legitimately send logs.

Using Security Group-to-Security Group rules provides a scalable way to control this communication.

---

## 5. Manual Validation Should Precede Automation

Before converting Splunk Universal Forwarder deployment into an Ansible role, the installation and log forwarding process should be tested manually.

This ensures that automation reproduces a known working configuration.

---

## 6. Dedicated Infrastructure Improves Scalability

Separating Splunk from Zabbix allows each system to scale according to its own requirements.

For example:

```text
More metrics
    → Scale Monitoring Server

More logs
    → Scale Splunk Server

More managed hosts
    → Expand Ansible automation
```

---

## Implementation Progress

```text
project foundation   Architecture & Repository Setup             ✓
AWS infrastructure deployment   AWS Infrastructure Deployment               ✓
local virtualization setup   Local Virtual Environment                   ✓
Docker host and network preparation   Docker / Cloud Networking                   ✓
monitoring stack integration   Zabbix + Grafana + PostgreSQL               ✓
Ansible automation setup   Automation Environment                      ✓
Zabbix Agent automation   Ansible Zabbix Agent Deployment             ✓

Splunk deployment and logging integration   Splunk Centralized Logging
        ├── Dedicated Splunk EC2                    ✓
        ├── Splunk direct installation              ✓
        ├── Splunk Web configuration                ✓
        ├── Forwarding architecture                 ✓
        └── Centralized logging integration         In Progress

AI incident analysis implementation   Splunk Forwarder Automation with Ansible    Planned
```

---

## Final Architecture Direction

The observability platform now follows this structure:

```text
                        AWS VPC
                           │
       ┌───────────────────┼────────────────────┐
       │                   │                    │
       ▼                   ▼                    ▼

 Bastion Server      Monitoring Server     Automation Server
                           │                     │
                     Zabbix / Grafana          Ansible
                           │
                           │
                           │
                      Splunk Server
                           │
                           ▼
                  Centralized Logging


Managed Servers
│
├── Zabbix Agent ─────────────► Zabbix
│
└── Splunk Universal Forwarder ► Splunk
```

This architecture provides the foundation for the next stage of the project: automatically deploying monitoring and logging agents and correlating Zabbix alerts with Splunk logs for AI-assisted incident analysis.

---

**Project:** AI-Assisted Hybrid Monitoring & Automation Lab  
**Day:** 8  
**Focus:** AWS · Splunk · Centralized Logging · Observability · Security Groups · Infrastructure Monitoring
