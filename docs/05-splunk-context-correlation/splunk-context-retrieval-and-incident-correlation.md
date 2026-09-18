# Splunk Context Retrieval & AI Incident Correlation

## Overview

this implementation phase extends the **AI-Assisted Hybrid Monitoring & Automation Lab**
from alert-only AI analysis into an evidence-aware incident correlation
workflow.

The AI Backend now retrieves operational context from Splunk around the
time of a Zabbix incident, correlates the evidence with the affected
host, and supplies the resulting context to Gemini for structured
incident analysis.

The completed workflow is:

``` text
Zabbix Trigger
      |
      v
FastAPI /incident/analyze
      |
      +--> Rule-Based Baseline
      |
      +--> Host Identity Mapping
      |       Monitoring-EC2 -> aws-mon-core-01
      |
      +--> Splunk REST API :8089
      |       |
      |       +--> linux_os
      |       +--> linux_security
      |       +--> app_logs
      |       |
      |       +--> Time/Host Filter
      |       +--> Result Limit
      |
      v
Zabbix Alert + Splunk Evidence
      |
      v
Gemini Structured Analysis
      |
      +--> Summary
      +--> Observed Evidence
      +--> Possible Causes
      +--> Recommended Actions
      +--> Confidence
      |
      v
SQLite Incident History
```

This implementation intentionally remains **analysis-only**. Automated
remediation remained outside this correlation layer and was implemented separately in the controlled-remediation phase.

------------------------------------------------------------------------

## Objectives

The this implementation phase implementation focused on the following goals:

-   Query Splunk programmatically from the dedicated AI Backend.
-   Keep Splunk management access private and restricted.
-   Use a least-privilege Splunk service account.
-   Correlate Zabbix incidents with logs from the affected host and
    incident time.
-   Restrict AI context to approved operational indexes.
-   Limit evidence before sending it to the LLM.
-   Distinguish directly observed evidence from AI-inferred possible
    causes.
-   Preserve operation when Splunk or Gemini is unavailable.
-   Store structured evidence-aware analysis in SQLite.
-   Avoid automated remediation until a controlled workflow is designed.

------------------------------------------------------------------------

## Existing Environment

The lab uses an AWS VPC with separate infrastructure roles.

### Public Subnet

-   Bastion Server

### Private Monitoring Subnet

-   Monitoring Server
    -   Zabbix
    -   Grafana
    -   PostgreSQL
-   Dedicated Splunk Server
-   Dedicated AI Backend EC2

### Private Automation Subnet

-   Automation Server
    -   Ansible

The existing Splunk log collection architecture from the earlier Splunk integration phase was reused
rather than redesigned.

Operational indexes used by the correlation service:

  Index              Purpose
  ------------------ -------------------------------------------------------
  `linux_os`         Selected Linux OS, kernel, system, and service events
  `linux_security`   SSH and sudo/security-related events
  `app_logs`         Selected application and container logs

------------------------------------------------------------------------

## 1. Secure Splunk REST API Connectivity

Splunk's management API is available on TCP port `8089`.

The Splunk server was confirmed to be listening on the management
interface:

``` bash
sudo ss -lntp | grep 8089
```

The AWS Security Group was configured so that TCP `8089` is reachable
**only from the AI Backend Security Group**.

``` text
AI Backend SG
     |
     | TCP 8089
     v
Splunk Server SG
```

The management port was not exposed publicly.

This provides a private service-to-service path between the AI Backend
and Splunk.

------------------------------------------------------------------------

## 2. Least-Privilege Splunk Account

A dedicated Splunk role was created for AI context retrieval:

``` text
Role: ai_context_reader
```

The role does not inherit the broad default `user` role.

Only the required indexes were included:

``` text
linux_os
linux_security
app_logs
```

The account was granted only the search capability required for the
project.

A dedicated service user was then assigned to this role:

``` text
ai-context-api
```

Administrative credentials are not embedded in the application.

Splunk credentials and connection settings are loaded from the AI
Backend `.env` file:

``` text
SPLUNK_HOST=<private-splunk-ip>
SPLUNK_PORT=8089
SPLUNK_USERNAME=ai-context-api
SPLUNK_PASSWORD=<secret>
```

The `.env` file is excluded from Git.

------------------------------------------------------------------------

## 3. Manual REST API Validation

Before adding Splunk access to FastAPI, connectivity and authorization
were tested manually.

Authentication was validated against the Splunk REST API, followed by
searches through:

``` text
/services/search/jobs/export
```

Example search pattern:

``` bash
curl -k -u 'ai-context-api' \
  'https://<splunk-private-ip>:8089/services/search/jobs/export' \
  -d search='search index=linux_os host="aws-mon-core-01" | head 5' \
  -d output_mode=json
```

Successful searches confirmed:

-   Network connectivity
-   Security Group configuration
-   Splunk authentication
-   Role permissions
-   Index permissions
-   REST search functionality

------------------------------------------------------------------------

## 4. Splunk Context Retrieval Service

A dedicated service was added:

``` text
app/services/splunk_service.py
```

Its responsibilities are:

1.  Receive the correlated Splunk hostname and incident timestamp.
2.  Build a bounded time window around the incident.
3.  Search only approved indexes.
4.  Filter by host.
5.  Limit the number of returned events.
6.  Return only fields needed for incident analysis.

Conceptual SPL:

``` spl
search
(index=linux_os OR index=linux_security OR index=app_logs)
host="<splunk-host>"
| sort 0 _time
| head <max_results>
| table _time index host source sourcetype _raw
```

Time boundaries are passed to the Splunk REST API using epoch
timestamps:

``` text
earliest_time
latest_time
```

Using epoch values avoids ambiguity between application, server, and
Splunk timezone interpretation.

------------------------------------------------------------------------

## 5. Context Size Control

Raw Splunk search output is not forwarded without restriction.

The retrieval layer applies:

-   Approved index filtering
-   Host filtering
-   Incident time window
-   Maximum result count
-   Selected output fields

The returned evidence is normalized into fields such as:

``` text
timestamp
index
host
source
sourcetype
message
```

This reduces irrelevant context, token usage, and the risk of the LLM
over-weighting unrelated log data.

------------------------------------------------------------------------

## 6. Host Identity Correlation

An important integration issue was discovered during testing.

Zabbix identified the monitored system as:

``` text
Monitoring-EC2
```

while the actual operating system hostname recorded by Splunk was:

``` text
aws-mon-core-01
```

Therefore, searching Splunk directly with the Zabbix host name returned
zero results even though relevant logs existed.

A host identity mapping layer was introduced:

``` text
Zabbix identity        Splunk / OS identity

Monitoring-EC2   --->  aws-mon-core-01
```

This is an example of a real observability challenge: different
monitoring platforms may use different identifiers for the same
infrastructure entity.

The current implementation uses a simple mapping appropriate for the
lab. A future version could move aliases into a configuration file,
inventory, CMDB, or dedicated resolver.

------------------------------------------------------------------------

## 7. FastAPI Integration

Splunk context retrieval was integrated into:

``` text
app/api/incidents.py
```

The incident flow now performs:

``` text
1. Duplicate event check
2. Resolve incident timestamp
3. Resolve Zabbix host -> Splunk host
4. Retrieve Splunk context
5. Generate rule-based baseline
6. Send incident + evidence to Gemini
7. Fall back when required
8. Save structured result
9. Return IncidentAnalysis
```

A successful test retrieved relevant context while keeping the API
healthy:

``` text
[INFO] Retrieved 5 Splunk events for host=Monitoring-EC2
POST /incident/analyze HTTP/1.1 200 OK
```

------------------------------------------------------------------------

## 8. Evidence-Aware Gemini Analysis

The Gemini service was extended so that the LLM receives:

-   Zabbix incident information
-   Initial deterministic rule-based analysis
-   Filtered Splunk evidence

The prompt explicitly instructs the model to:

-   Use logs as evidence only when relevant.
-   Avoid inventing unsupported facts.
-   Distinguish observation from inference.
-   Avoid treating temporal correlation as proof of causation.
-   Avoid destructive recommendations.
-   Reduce confidence when evidence is inconclusive.

The structured Gemini schema was extended with:

``` python
observed_evidence: list[str]
```

The final incident structure now separates:

``` text
Summary
Observed Evidence
Possible Causes
Recommended Actions
Confidence
Analysis Source
```

This is important because a log event occurring near an alert does not
automatically prove that it caused the alert.

------------------------------------------------------------------------

## 9. Observed Evidence vs. Probable Cause

One test incident demonstrated why this separation matters.

Zabbix reported a high CPU warning while Splunk showed recurring
AppArmor denial events involving the `who` utility near the incident
time.

The evidence layer can safely state:

``` text
Observed:
- Zabbix reported high CPU utilization.
- Splunk recorded recurring AppArmor DENIED events involving 'who'.
```

The AI may then separately infer:

``` text
Possible:
- A scheduled/background process may be involved.
- Another CPU-intensive process may be responsible.
- The AppArmor activity may be related, but temporal proximity alone does not prove causation.
```

This separation improves explainability and reduces unsupported
root-cause claims.

------------------------------------------------------------------------

## 10. SQLite Evidence Persistence

`IncidentAnalysis` was extended with:

``` python
observed_evidence: list[str]
```

A safe default was used so that older records and fallback paths remain
compatible:

``` python
observed_evidence: list[str] = Field(default_factory=list)
```

The existing SQLite table was migrated without deleting historical
incidents:

``` sql
ALTER TABLE incidents
ADD COLUMN observed_evidence TEXT;
```

Evidence is serialized as JSON when stored and parsed back into a list
when retrieved.

Older incidents with `NULL` evidence are safely represented as:

``` json
"observed_evidence": []
```

A successful stored incident included evidence from both Zabbix and
Splunk.

------------------------------------------------------------------------

## 11. Failure Handling and Graceful Degradation

The final this implementation phase workflow was tested under multiple failure scenarios.

### Normal Path

``` text
Zabbix
  +
Splunk available
  +
Gemini available
  |
  v
Evidence-aware Gemini analysis
```

Result:

``` text
analysis_source = gemini
```

### Splunk Unavailable

``` text
Zabbix
  |
Splunk unavailable
  |
  v
Gemini analyzes available Zabbix context
```

The incident endpoint continues operating rather than returning an
application failure.

### Gemini Unavailable

``` text
Zabbix
  |
Gemini unavailable
  |
  v
Deterministic rule-based fallback
```

Result:

``` text
analysis_source = rule-based-fallback
```

Both fallback paths were tested successfully.

------------------------------------------------------------------------

## 12. Splunk Availability Observability Cleanup

Initially, `SplunkService` returned an empty list for both:

``` text
Splunk unavailable
```

and:

``` text
Splunk available, but zero matching events
```

Although functionally safe, these states are operationally different.

The return structure was improved to distinguish them:

``` python
{
    "available": True,
    "events": [...]
}
```

versus:

``` python
{
    "available": False,
    "events": []
}
```

This allows the application to distinguish:

``` text
Splunk available + 0 events
```

from:

``` text
Splunk unavailable
```

and provides better observability for future dashboards and operational
troubleshooting.

------------------------------------------------------------------------

## 13. Security Considerations

this implementation phase applies several security controls:

-   Splunk management port `8089` is not publicly exposed.
-   AWS Security Groups restrict API access to the AI Backend.
-   A dedicated least-privilege Splunk account is used.
-   Search access is restricted to approved indexes.
-   Credentials are stored outside source code.
-   Search results are filtered and bounded before LLM processing.
-   Gemini is instructed not to recommend destructive operations.
-   No automated remediation is performed.

### Known Lab Limitation

The current Splunk REST client uses:

``` python
verify=False
```

because the lab Splunk instance uses a self-signed certificate.

This generates an expected `InsecureRequestWarning`.

A production implementation should validate the Splunk certificate using
an appropriate trusted CA/certificate chain rather than disabling TLS
verification.

------------------------------------------------------------------------

## 14. Validation Results

The completed implementation successfully demonstrated:

-   [x] Private AI Backend -\> Splunk REST connectivity
-   [x] Security Group restriction on TCP 8089
-   [x] Least-privilege Splunk service account
-   [x] Search restricted to approved indexes
-   [x] Host-based context retrieval
-   [x] Incident-time correlation
-   [x] Host identity normalization
-   [x] Search result limiting
-   [x] Splunk evidence supplied to Gemini
-   [x] Structured Gemini response
-   [x] Observed evidence separated from possible causes
-   [x] Evidence persisted in SQLite
-   [x] Existing incident history preserved during schema migration
-   [x] Duplicate Zabbix event protection retained
-   [x] Splunk-unavailable fallback validated
-   [x] Gemini-unavailable deterministic fallback validated
-   [x] Splunk unavailable vs. zero-results states distinguished
-   [x] End-to-end Zabbix -\> Splunk -\> Gemini workflow validated

------------------------------------------------------------------------

## 15. Key Lessons Learned

### Cross-platform host identity must be normalized

Monitoring systems do not necessarily use the same hostname or asset
identifier. Correlation requires an explicit identity strategy rather
than assuming names match.

### Time correlation is not causation

Logs occurring near an alert are evidence, but they do not automatically
identify root cause. Separating `observed_evidence` from
`possible_causes` makes the analysis more defensible.

### LLM context should be bounded

Filtering by index, host, time, fields, and result count provides more
useful context than sending large volumes of raw logs to an LLM.

### AI dependencies should fail gracefully

An incident pipeline should continue to provide useful output when
Splunk or the LLM is unavailable.

### Observability applies to the correlation service itself

"Zero matching events" and "Splunk unavailable" have very different
operational meanings. Explicit service status improves troubleshooting
and future monitoring.

------------------------------------------------------------------------

## 16. this implementation phase Outcome

this implementation phase transforms the project from:

``` text
Alert -> AI interpretation
```

into:

``` text
Alert
  +
Operational log evidence
  +
Deterministic baseline
  |
  v
Evidence-aware AI incident analysis
```

The AI Backend can now correlate a Zabbix incident with bounded Splunk
context, distinguish observed facts from inferred causes, persist the
structured result, and continue operating under dependency failures.

This creates the foundation for **the implementation phase --- Controlled Automated
Remediation**, where selected incident recommendations can be mapped to
approved Ansible actions with safety controls rather than allowing
unrestricted AI-generated commands.
