# Controlled Automated Remediation

## Overview

This implementation extended the AI-Assisted Hybrid Monitoring & Automation Lab from
incident analysis into **controlled remediation**.

The objective was not to allow an LLM to execute arbitrary commands.
Instead, the remediation workflow was designed around a defense-in-depth
model:

> **LLM recommends → deterministic policy decides → human approves →
> allowlisted automation executes**

The completed workflow integrates Zabbix incident detection, the
existing AI Backend, a dedicated Automation Server, a private
Remediation API, Ansible, SQLite lifecycle tracking, authentication,
authorization, and execution auditing.

------------------------------------------------------------------------

## 1. Objectives

The implementation focused on the following requirements:

-   Convert eligible incidents into structured remediation proposals.
-   Keep AI recommendations advisory rather than executable.
-   Use deterministic policy mapping for executable actions.
-   Require human approval before execution.
-   Prevent arbitrary shell commands and arbitrary playbook execution.
-   Restrict remediation to approved targets and approved actions.
-   Execute remediation through Ansible.
-   Track the complete remediation lifecycle in SQLite.
-   Maintain execution audit records.
-   Validate both successful remediation and security safeguards.

------------------------------------------------------------------------

## 2. Final Architecture

``` text
Zabbix Problem
      |
      v
AI Backend
      |
      +--> Incident Analysis
      |      +-- Zabbix evidence
      |      +-- Splunk context
      |      +-- Gemini advisory analysis
      |
      v
Deterministic Remediation Policy
      |
      v
Remediation Proposal
PENDING_APPROVAL
      |
      | Authenticated Human Decision
      v
APPROVED
      |
      | Authenticated Execution Request
      v
EXECUTING
      |
      v
AI Backend Remediation Client
      |
      | Private TCP/8443
      | Service-token authentication
      v
Automation Server Remediation API
      |
      +-- Action allowlist
      +-- Target allowlist
      |
      v
Pre-approved Ansible Playbook / Role
      |
      v
Target Host
      |
      v
SUCCESS / FAILED
      |
      v
Zabbix detects recovery
      |
      v
Problem SOLVED
```

This design intentionally separates **analysis**, **policy**,
**approval**, and **execution**.

------------------------------------------------------------------------

## 3. Remediation Data Model

A controlled remediation lifecycle was introduced with the following
statuses:

``` text
PENDING_APPROVAL
APPROVED
REJECTED
EXECUTING
SUCCESS
FAILED
```

`NOT_ELIGIBLE` is not treated as a lifecycle state. If an incident does
not match an approved remediation policy, no remediation proposal is
created.

The initial approved action is:

``` text
ENSURE_ZABBIX_AGENT_RUNNING
```

The action is intentionally idempotent. It ensures that the Zabbix Agent
2 service is running instead of blindly restarting it.

------------------------------------------------------------------------

## 4. Deterministic Remediation Policy

The AI Backend contains an approved action registry and deterministic
incident-to-action mapping.

For the first remediation use case, Zabbix agent availability incidents
are matched to:

``` text
ENSURE_ZABBIX_AGENT_RUNNING
```

The Zabbix trigger text can contain a timeout suffix such as:

``` text
Linux: Zabbix agent is not available (for 3m)
```

Therefore, deterministic prefix matching is used rather than an exact
string comparison.

AI-generated `recommended_actions` are preserved for analysis and audit
purposes, but they **do not select the executable action**.

This prevents an LLM response from becoming an execution instruction.

------------------------------------------------------------------------

## 5. Remediation Proposal Persistence

A `remediation_history` SQLite table was used to persist the remediation
lifecycle.

The record tracks information including:

-   `remediation_id`
-   `event_id`
-   source host
-   target host
-   action ID
-   action description
-   risk
-   lifecycle status
-   approval requirement
-   AI recommendations
-   decision identity and timestamp
-   execution identity and timestamps
-   execution success
-   Ansible changed state
-   return code
-   result summary
-   execution output

A uniqueness constraint on the incident/action combination helps prevent
duplicate remediation proposals.

------------------------------------------------------------------------

## 6. Human-in-the-Loop Approval

Remediation is not executed immediately after AI analysis.

The AI Backend exposes remediation endpoints for:

``` text
GET  /remediation/
GET  /remediation/{remediation_id}
POST /remediation/{remediation_id}/approve
POST /remediation/{remediation_id}/reject
POST /remediation/{remediation_id}/execute
```

The approval workflow enforces atomic state transitions. For example:

``` text
PENDING_APPROVAL -> APPROVED
```

is allowed, while attempting to approve an already processed remediation
results in a conflict.

Similarly, execution can only transition:

``` text
APPROVED -> EXECUTING
```

This prevents lifecycle stages from being skipped.

------------------------------------------------------------------------

## 7. Human Operator Authentication

The approval, rejection, and execution endpoints were protected using
HTTP Basic Authentication for the lab environment.

Credentials are not accepted as an `approved_by` field supplied by the
request body. Instead, the authenticated username becomes the audit
identity.

This provides a meaningful distinction between:

``` text
User-supplied actor name
```

and:

``` text
Authenticated operator identity
```

The implementation uses constant-time secret comparison and rejects
invalid credentials with HTTP `401`.

The AI Backend remains bound to localhost and is accessed through an SSH
tunnel, protecting the Basic Authentication exchange in the current lab
design.

------------------------------------------------------------------------

## 8. Automation Server Remediation API

A small FastAPI service was implemented on the dedicated Automation
Server.

Project structure:

``` text
automation/
├── inventory/
├── playbooks/
├── roles/
└── remediation_api/
    └── app/
        ├── main.py
        ├── models/
        ├── services/
        ├── config/
        └── security/
```

The API accepts only structured remediation identifiers:

``` json
{
  "remediation_id": "rem-example",
  "event_id": "event-example",
  "action_id": "ENSURE_ZABBIX_AGENT_RUNNING",
  "target": "aws-mon-core-01"
}
```

It deliberately does **not** accept fields such as:

``` text
command
shell
script
playbook_path
extra_args
```

This prevents callers from turning the API into a generic remote command
execution interface.

------------------------------------------------------------------------

## 9. Private Network Access

The Remediation API uses private network access on TCP port `8443`.

The Automation Server Security Group restricts inbound access to the AI
Backend security group rather than exposing the service publicly.

The communication path is therefore:

``` text
AI Backend
    |
    | Private VPC connectivity
    v
Automation Server :8443
```

Network-level restrictions are combined with application-level
authentication.

------------------------------------------------------------------------

## 10. Service-to-Service Authentication

The AI Backend and Automation API share a dedicated remediation service
token.

Requests include:

``` text
X-Remediation-Token
```

The Automation API validates the token before accepting an execution
request.

Tests confirmed:

``` text
Missing/invalid token -> 401 Unauthorized
Valid token           -> request processed
```

This creates a second control beyond the AWS Security Group.

------------------------------------------------------------------------

## 11. Action Allowlist

The Automation Server maintains its own approved action registry.

Example:

``` python
APPROVED_ACTIONS = {
    "ENSURE_ZABBIX_AGENT_RUNNING": {
        "description": "Ensure Zabbix Agent 2 service is running",
        "playbook": "ensure_zabbix_agent_running.yml",
    },
}
```

The caller sends only an `action_id`.

The actual playbook path is selected internally by the Automation
Server.

This provides an independent enforcement layer even if the AI Backend
sends an unexpected request.

------------------------------------------------------------------------

## 12. Target Allowlist

The Automation Server also maintains a separate target allowlist.

Remediation authorization is intentionally separate from general
Ansible inventory membership. A host is executable only when it is
present in both of the final authorization locations:

``` text
automation/remediation_api/app/config/targets.py
└── ALLOWED_TARGETS

automation/inventory/hosts.ini
└── [remediation_targets]
```

This keeps deployment automation and remediation automation logically
separate. Adding a new remediation target therefore requires updating
both the Automation API target allowlist and the
`[remediation_targets]` inventory group. Host identity normalization is
used for correlation only and does not grant remediation authorization.

------------------------------------------------------------------------

## 13. Ansible Remediation Role

A dedicated remediation role was created:

``` text
roles/remediation_zabbix_agent/
└── tasks/
    └── main.yml
```

The role performs only service recovery:

``` yaml
---
- name: Ensure Zabbix Agent 2 service is enabled and running
  ansible.builtin.service:
    name: "{{ zabbix_agent_service_name | default('zabbix-agent2') }}"
    enabled: true
    state: started
```

It does not install packages, modify repositories, or rewrite
configuration.

This deliberately keeps remediation scope smaller than provisioning
scope.

The corresponding playbook targets only the remediation inventory group.

------------------------------------------------------------------------

## 14. Idempotency Validation

The remediation playbook was first tested directly with:

``` bash
ansible-playbook playbooks/ensure_zabbix_agent_running.yml \
  --limit aws-mon-core-01
```

When the service was already running, Ansible returned:

``` text
ok=1
changed=0
unreachable=0
failed=0
```

This confirmed that the remediation is idempotent and does not introduce
unnecessary changes.

------------------------------------------------------------------------

## 15. Controlled Ansible Execution

The Automation API executes Ansible using Python `subprocess.run()` with
an argument list.

Conceptually:

``` python
[
    "ansible-playbook",
    playbook_path,
    "--limit",
    target,
]
```

Important controls include:

-   no `shell=True`
-   internal playbook lookup
-   allowlisted action ID
-   allowlisted target
-   fixed automation root
-   execution timeout
-   captured stdout/stderr
-   return-code tracking

This prevents arbitrary shell expansion and limits the API to the
intended automation workflow.

------------------------------------------------------------------------

## 16. AI Backend Remediation Client

A dedicated remediation client was added to the AI Backend.

Its responsibility is limited to sending structured requests to the
private Automation API.

The client supplies:

-   remediation ID
-   event ID
-   approved action ID
-   target
-   service authentication token

The client also applies an HTTP timeout slightly longer than the
Automation Server's Ansible execution timeout.

This isolates network communication from policy and lifecycle logic.

------------------------------------------------------------------------

## 17. Lifecycle Enforcement

Execution is protected by database state transitions.

The important transitions are:

``` text
PENDING_APPROVAL -> APPROVED
APPROVED         -> EXECUTING
EXECUTING        -> SUCCESS
EXECUTING        -> FAILED
```

SQL updates include the expected previous state in the `WHERE` clause.

For example, entering execution requires:

``` sql
WHERE remediation_id = ?
  AND status = 'APPROVED'
```

This provides an atomic guard against duplicate or invalid transitions.

------------------------------------------------------------------------

## 18. Structured Execution Audit

The AI Backend remediation record was extended to track:

``` text
decision_by
decision_at
executed_by
execution_started_at
execution_finished_at
changed
return_code
success
result_summary
execution_output
```

This allows the project to answer operational questions such as:

-   Who approved or rejected the remediation?
-   Who initiated execution?
-   When did execution begin and finish?
-   Did Ansible actually change the system?
-   What return code was produced?
-   Did the remediation succeed?

The Automation Server also writes a dedicated JSON execution audit log
containing remediation identifiers, target, action, success, changed
state, and return code.

The shared `remediation_id` allows events to be correlated across the AI
Backend and Automation Server.

------------------------------------------------------------------------

## 19. Successful Recovery Test

The main recovery test intentionally stopped the Zabbix Agent 2 service
on the monitoring target.

The controlled remediation workflow then:

1.  produced/used the remediation proposal,
2.  required authenticated human approval,
3.  transitioned the remediation to `APPROVED`,
4.  accepted an authenticated execution request,
5.  transitioned to `EXECUTING`,
6.  called the private Automation API,
7.  passed action and target allowlist validation,
8.  ran the approved Ansible role,
9.  started `zabbix-agent2`,
10. returned `SUCCESS`,
11. recorded `changed=true` and return code `0`.

After execution:

``` bash
systemctl is-active zabbix-agent2
```

returned:

``` text
active
```

Most importantly, **Zabbix independently detected the recovery and
changed the original problem to `Solved`**.

This validated the complete remediation effect rather than relying only
on an Ansible success response.

------------------------------------------------------------------------

## 20. Security / Negative Testing

The implementation was also tested against invalid workflow attempts.

  -----------------------------------------------------------------------
  Test                    Expected Result         Result
  ----------------------- ----------------------- -----------------------
  Execute                 `409 Conflict`          Passed
  `PENDING_APPROVAL`                              
  remediation                                     

  Approval/execution      `401 Unauthorized`      Passed
  without operator                                
  authentication                                  

  Invalid Automation API  `401 Unauthorized`      Passed
  service token                                   

  Action not present in   `403 Forbidden`         Passed
  Automation Server                               
  allowlist                                       

  Target outside          `403 Forbidden`         Passed
  remediation target                              
  allowlist                                       

  Re-execute already      `409 Conflict`          Passed
  successful remediation                          

  Valid approved          Execution allowed       Passed
  remediation                                     
  -----------------------------------------------------------------------

These tests demonstrate that the controls are enforced rather than
merely documented.

------------------------------------------------------------------------

## 21. Defense-in-Depth Design

The remediation path uses multiple independent controls:

``` text
Layer 1: Deterministic AI Backend policy
Layer 2: Human approval
Layer 3: Human operator authentication
Layer 4: Remediation lifecycle state validation
Layer 5: AWS private network / Security Group
Layer 6: Service-to-service token
Layer 7: Automation Server action allowlist
Layer 8: Automation Server target allowlist
Layer 9: Pre-approved Ansible playbook
Layer 10: No arbitrary shell/playbook parameters
Layer 11: Execution timeout and audit
```

Failure of one control does not automatically provide arbitrary
automation capability.

------------------------------------------------------------------------

## 22. Key Troubleshooting and Engineering Lessons

### Zabbix trigger matching

The real trigger included a dynamic suffix such as `(for 3m)`, so exact
matching was too brittle. Deterministic prefix matching was used
instead.

### Inventory semantics

The existing `zabbix_agents` group belonged to earlier deployment
automation. Reusing it for remediation caused target matching problems
and would have mixed responsibilities.

A dedicated `remediation_targets` group resolved this cleanly.

### SQL lifecycle updates

Atomic status conditions were important for preventing duplicate
approvals and duplicate executions.

### Audit field semantics

Using an `approved_by` field for both approval and rejection was
semantically incorrect. The audit model was improved with neutral
decision fields such as `decision_by` and `decision_at`.

### Human identity

Allowing a client to submit an `approved_by` string does not prove
identity. Authentication was therefore added and the operator identity
is derived from authenticated credentials.

### Automation Server as an independent enforcement boundary

The AI Backend already validates remediation policy, but the Automation
Server repeats action and target validation. This is intentional defense
in depth.

------------------------------------------------------------------------

## 23. Security Principles Demonstrated

This implementation demonstrates several infrastructure and security
engineering principles:

-   least privilege
-   human-in-the-loop automation
-   deterministic policy enforcement
-   defense in depth
-   private service communication
-   authenticated service-to-service requests
-   authenticated operator actions
-   allowlisting
-   idempotent configuration management
-   auditability
-   lifecycle/state-machine enforcement
-   separation of analysis and execution
-   failure isolation
-   no arbitrary LLM command execution

------------------------------------------------------------------------

## 24. Final Result

This work transformed the monitoring lab from an AI-assisted incident
analysis platform into a **controlled remediation platform**.

The system can now detect an operational problem, enrich and analyze the
incident, determine whether it matches a pre-approved remediation
policy, create a remediation proposal, require authenticated human
approval, execute an allowlisted Ansible action through a private
Automation API, record the execution lifecycle, and allow Zabbix to
independently confirm service recovery.

The resulting architecture deliberately prioritizes **control,
auditability, and bounded automation** over unrestricted autonomous
execution.
