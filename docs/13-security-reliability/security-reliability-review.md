# Security & Reliability Review

## 1. Overview

This phase focused on a final **security and reliability review** of the
AI-Assisted Hybrid Monitoring & Automation Lab.

Rather than adding new functionality, this phase reviewed the existing
platform for network exposure, least-privilege authorization, secrets
and file permissions, structured log retention, Ansible credential
scope, remediation authorization, service recovery, and auditability.

The review identified practical hardening opportunities. Some were
remediated and validated immediately, while others were documented as
accepted lab limitations or future hardening work.

------------------------------------------------------------------------

## 2. Review Scope

-   AWS Security Groups and inter-service network paths
-   SSH and Linux access controls
-   AI Backend and Remediation API security
-   Splunk Server and Universal Forwarder security
-   Splunk API authorization
-   Ansible and Ansible Vault usage
-   WireGuard gateway security
-   Structured application and remediation logs
-   Docker and systemd service reliability
-   Remediation state control and audit history
-   Git repository and configuration hygiene

------------------------------------------------------------------------

## 3. Key Security Improvements

### 3.1 Splunk API Least-Privilege Access

The AI Backend retrieves operational context from Splunk through the
Management API on TCP 8089.

The dedicated `ai-context-api` account was found to use the built-in
Splunk `user` role. Although non-administrative, that role allowed
searches across all non-restricted indexes. Code review confirmed that
the AI Backend requires only:

-   `app_logs`
-   `linux_os`
-   `linux_security`

The existing `ai_context_reader` role was verified to restrict
searchable indexes to exactly those three indexes. The API account was
reassigned from `user` to `ai_context_reader`.

``` text
ai-context-api
└── ai_context_reader
    ├── app_logs
    ├── linux_os
    └── linux_security
```

After the role change, a live AI analysis successfully retrieved three
Splunk events, confirming that least-privilege authorization did not
break the integration.

**Result: FIXED / VALIDATED**

### 3.2 AI Analysis Log Security and Retention

The AI Backend structured log was standardized as:

``` text
/var/log/ai-backend/analysis.json.log
```

A dedicated `incident-analysis-logs` group was introduced. The directory
uses mode `2750`, while the active log uses mode `0640`. The AI Backend
systemd service uses `SupplementaryGroups=incident-analysis-logs` and
`UMask=0027`.

This allows the application to write logs and the Splunk Forwarder to
read them without granting unnecessary access to other local users.

Daily log rotation with 14 retained rotations, compression, delayed
compression, and `copytruncate` was configured and validated. The
Remediation API structured execution log was hardened using the same
general model.

**Result: FIXED / VALIDATED**

### 3.3 SQLite Incident Database Permissions

The AI Backend SQLite database contained incident and remediation state
information but was found with mode `0644`. It was restricted to:

``` text
0600 ubuntu:ubuntu
```

The existing systemd `UMask=0027` also supports restrictive permissions
for future application-created files.

**Result: FIXED / VALIDATED**

### 3.4 Scoped Ansible Vault

The Splunk Forwarder credential Vault had originally been placed under a
group-variable path. Because a managed host can belong to both Zabbix
and Splunk Ansible groups, unrelated Zabbix remediation operations
attempted to load and decrypt the Splunk Vault.

The secret was moved to:

``` text
automation/vault/splunk.yml
```

Only the Splunk Forwarder playbook explicitly loads this Vault file.
General Ansible connectivity and Zabbix remediation therefore no longer
depend on Splunk credentials.

This reduced credential scope and removed an unnecessary dependency
between independent automation workflows.

**Result: FIXED / VALIDATED**

### 3.5 Repository Hygiene

Local backup files existed inside the automation source tree.
Repository-wide ignore rules were added:

``` gitignore
*.bak
*.bak.*
*.backup
*.old
```

`git check-ignore` confirmed that the identified backup files are
excluded. Existing protections for SSH keys, environment files, Vault
password files, Terraform state, local Ansible inventory, and logs were
also reviewed.

**Result: FIXED / VALIDATED**

------------------------------------------------------------------------

## 4. Network and Access-Control Validation

Terraform-managed Security Group ingress paths were reviewed against
their operational purpose. The major flows were confirmed as
intentional, including Bastion-based administration, monitoring-to-agent
traffic, Monitoring-to-AI traffic, AI-to-Splunk context retrieval,
AI-to-Remediation API access, Automation-to-managed-node SSH, Splunk
forwarding, and WireGuard paths.

No ingress rule requiring immediate removal was identified. TCP 10051
was retained as an explicitly documented future/testing path for Zabbix
active checks.

Splunk ports 8000, 8089, and 9997 listen on host interfaces, while AWS
Security Groups restrict permitted sources. Security Groups therefore
remain the primary network access-control boundary.

### Public IPv4 Design

Bastion and WireGuard intentionally retain public connectivity. Some
early lab workloads retain automatically assigned public IPv4 addresses
from the initial deployment phase, when outbound package installation
was provided without introducing NAT Gateway cost.

The later deployment pattern improved this design: private workloads do
not normally receive permanent public addresses, and temporary public
connectivity can be attached only when needed. Existing legacy instances
were not recreated solely to remove their addresses because application
ingress is already restricted by Security Groups.

**Decision: ACCEPTED / DOCUMENTED LAB TRADE-OFF**

------------------------------------------------------------------------

## 5. Remediation Security Controls

The remediation architecture was reviewed to ensure that an AI
recommendation cannot directly trigger arbitrary automation.

``` text
AI recommendation
        ↓
PENDING_APPROVAL
        ↓
Human approval or rejection
        ↓
APPROVED
        ↓
EXECUTING
        ↓
SUCCESS / FAILED
```

Approval and execution transitions are enforced by the backend and
database rather than only by the Operator Console UI.

The Remediation API applies service-token authentication, action and
target allowlists, fixed action-to-playbook mapping, subprocess
execution without `shell=True`, execution timeout, and explicit
failure/return-code handling. Authentication also fails closed when the
service token is not configured.

**Result: VALIDATED / PASS**

------------------------------------------------------------------------

## 6. Reliability Validation

The AI Backend, Remediation API, Splunk Server, Splunk Universal
Forwarder, and WireGuard services were confirmed active and configured
for boot persistence.

The Docker-based Monitoring Server runs Zabbix Server, Zabbix Web,
Grafana, and PostgreSQL. All four containers were running during
validation, Zabbix Web reported healthy status, and all use:

``` text
restart=unless-stopped
```

This provides automatic container recovery after Docker daemon or host
restart unless a container was intentionally stopped.

**Result: VALIDATED / PASS**

------------------------------------------------------------------------

## 7. Remediation Auditability and Traceability

The remediation database was reviewed to verify that operational
decisions and execution results remain traceable.

Audit records include incident/event association, host and action,
remediation state, operator identity and decision timestamp, execution
actor, execution start/finish timestamps, success/failure,
configuration-change indicator, and Ansible return code.

Actual records contained both successful and failed remediations. Failed
executions remained recorded with `FAILED` status and non-zero return
codes, while pending remediations correctly lacked decision and
execution fields until operator action occurred.

**Result: VALIDATED / PASS**

------------------------------------------------------------------------

## 8. Findings and Risk Decisions

  ------------------------------------------------------------------------------------
  Finding                   Risk              Decision               Status
  ------------------------- ----------------- ---------------------- -----------------
  Splunk API account        Medium            Assigned               **FIXED /
  inherited broad default                     `ai_context_reader`,   VALIDATED**
  `user` index access                         restricted to three    
                                              required indexes       

  Application/remediation   Medium            Dedicated groups,      **FIXED /
  log permissions and                         restrictive modes,     VALIDATED**
  retention required                          systemd umask, log     
  hardening                                   rotation               

  SQLite incident database  Medium            Restricted database to **FIXED /
  was locally readable with                   `0600`                 VALIDATED**
  mode `0644`                                                        

  Splunk Vault created an   Medium            Moved secret to        **FIXED /
  unnecessary                                 workflow-scoped Vault  VALIDATED**
  cross-workflow dependency                                          

  AI Backend disables       Medium            Private SG-restricted  **ACCEPTED /
  Splunk TLS certificate                      HTTPS path; trusted    DOCUMENTED**
  verification                                PKI deferred           

  RedHat UF RPM             Low--Medium       Pinned official        **ACCEPTED /
  installation lacks                          version/build; vendor  DOCUMENTED**
  independent package                         checksum/signature     
  verification                                planned                

  Current RedHat host       Low               Validate on a future   **PARTIALLY
  predates the Ansible UF                     new/disposable         VALIDATED**
  fresh-install workflow                      RedHat-family host     

  Core service              Low               Existing systemd and   **VALIDATED /
  startup/restart                             Docker persistence     PASS**
  persistence                                 controls retained      
  ------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 9. Accepted Limitations and Future Hardening

### Splunk TLS Certificate Verification

The AI Backend connects to Splunk over HTTPS, but the Python client
currently uses `verify=False`. The Splunk server uses the default Splunk
certificate chain (`SplunkServerDefaultCert` issued by
`SplunkCommonCA`).

Current compensating controls include private VPC communication, TCP
8089 restricted by AWS Security Group, a dedicated non-admin API
account, and the index-restricted `ai_context_reader` role.

Future hardening should deploy a trusted internal certificate, use a
matching DNS identity, establish CA trust on the AI Backend, and enable
certificate verification.

### RedHat Splunk Forwarder Package Integrity

The RedHat-family installation task uses an official Splunk HTTPS
download URL with a pinned version/build, but currently uses
`disable_gpg_check: true` and does not independently validate a vendor
checksum.

Future hardening should verify the RPM using a trusted vendor checksum
or signature before installation.

### RedHat Fresh-Install Validation

`aws-managed-svr-01` currently runs Splunk Universal Forwarder 10.4.1,
but the installation predates the current Ansible Splunk role. The role
correctly detects the existing installation and avoids an implicit
upgrade.

A future new or disposable RedHat-family host should be used to validate
the complete Ansible fresh-install path without disrupting a working
monitored system.

------------------------------------------------------------------------

## 10. Evidence

### Evidence 1 --- Splunk Least-Privilege Role

The `ai_context_reader` role allows only the three indexes required by
the AI Backend. Wildcard index access is not enabled.

![Splunk AI Context
Reader](splunk-ai-context-reader.png)

### Evidence 2 --- Splunk Context Retrieval After Role Hardening

After changing `ai-context-api` to the dedicated role, the AI Backend
successfully retrieved three Splunk events.

![Splunk Context
Retrieval](splunk-context-retrieval.png)

### Evidence 3 --- AI Analysis Log Permissions and Rotation

The active and rotated AI analysis logs retain the dedicated
`incident-analysis-logs` group and restrictive permissions.

![AI Analysis Log
Security](analysis-log-security.png)

### Evidence 4 --- Remediation Audit Trail

The remediation database contains pending, successful, and failed
operations together with operator identity and execution results.

![Remediation Audit
Trail](remediation-audit-trail.png)

### Evidence 5 --- Monitoring Stack Reliability

The Zabbix Server, Zabbix Web, Grafana, and PostgreSQL containers were
running, with Zabbix Web healthy, and all use the `unless-stopped`
restart policy.

![Monitoring
Reliability](monitoring-reliability.png)

------------------------------------------------------------------------

## 11. Outcome

This phase completed a security and reliability review of the integrated
monitoring and remediation platform without introducing unnecessary
architectural redesign.

The review produced concrete hardening improvements in Splunk least
privilege, structured-log protection and retention, SQLite permissions,
Ansible Vault scope, and repository hygiene. It also validated the
existing defense layers around network access, SSH, WireGuard,
remediation authorization, human approval, service persistence, and
audit history.

Remaining TLS and package-integrity limitations were explicitly
documented with compensating controls and future hardening paths rather
than represented as fully resolved.

This review establishes a clearer operational security baseline for the
completed AI-assisted hybrid monitoring and automation lab.
