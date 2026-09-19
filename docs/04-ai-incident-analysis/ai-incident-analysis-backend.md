# AI-Assisted Incident Analysis Backend

## Overview

AI incident analysis implementation of the **AI-Assisted Hybrid Monitoring & Automation Lab** introduced an AI-assisted incident analysis service into the existing monitoring architecture.

Previous phases established Zabbix for infrastructure monitoring and alerting, Splunk for centralized OS/security/application logging, Grafana for visualization, and Ansible for infrastructure automation.

The objective of this phase was to connect Zabbix alerts to a dedicated Python backend capable of automatically analyzing monitoring incidents.

The resulting workflow is:

```text
Zabbix Alert
    ↓
FastAPI Backend
    ↓
Rule-Based Analysis
    ↓
Gemini LLM Analysis
    ↓
Structured Incident Result
    ↓
SQLite
    ↓
Structured Operational Log
    ↓
Splunk
```

This creates the first AI-assisted incident analysis pipeline in the lab.

---

## Objectives

- Deploy a dedicated AI Backend EC2 instance
- Integrate Zabbix alerts with FastAPI through Webhooks
- Define structured incident models with Pydantic
- Implement deterministic rule-based analysis
- Integrate Gemini for enhanced incident analysis
- Enforce structured LLM output
- Persist incident results in SQLite
- Prevent duplicate event processing
- Provide fallback analysis when the LLM is unavailable
- Generate structured JSON operational logs
- Send AI Backend activity logs to Splunk

---

## 1. AI Backend Architecture

The AI Backend was deployed as a dedicated EC2 instance.

Because the service is part of the monitoring and observability workflow, it was placed in the existing private monitoring subnet.

```text
AWS VPC
│
├── Public Subnet
│   └── Bastion Server
│
├── Private Monitoring Subnet
│   ├── Monitoring Server
│   │   ├── Zabbix
│   │   ├── Grafana
│   │   └── PostgreSQL
│   ├── Splunk Server
│   └── AI Backend
│       ├── FastAPI
│       ├── Gemini Integration
│       └── SQLite
│
└── Private Automation Subnet
    └── Automation Server
        └── Ansible
```

This maintains separation between monitoring, logging, AI analysis, and infrastructure automation responsibilities.

---

## 2. FastAPI Backend

The incident analysis service was implemented using Python and FastAPI.

```text
ai-backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── incidents.py
│   ├── models/
│   │   ├── incident.py
│   │   └── db.py
│   └── services/
│       ├── incident_analyzer.py
│       ├── incident_repository.py
│       ├── llm_service.py
│       └── structured_logger.py
├── .env
├── requirements.txt
└── incidents.db
```

The application separates API routing, data models, analysis logic, persistence, LLM integration, and logging.

---

## 3. Zabbix Webhook Integration

A custom Zabbix Webhook Media Type was created:

```text
AI Incident Analyzer
```

Zabbix forwards incident information to:

```text
POST /incident/analyze
```

Example incident payload:

```json
{
  "event_id": "12345",
  "host": "Monitoring-EC2",
  "trigger": "High CPU utilization",
  "severity": "Warning",
  "message": "CPU utilization exceeded the configured threshold."
}
```

The FastAPI backend validates incoming events using Pydantic models before analysis.

---

## 4. Zabbix Action Configuration

The Zabbix Action was configured to send events with:

```text
Severity >= Warning
```

to the AI Incident Analyzer.

A temporary low-threshold CPU trigger was used to generate test incidents.

During testing, an important Zabbix event behavior was observed:

```text
PROBLEM
   ↓
OK
   ↓
PROBLEM
```

A trigger that remains in the `PROBLEM` state does not continuously generate new Problem events.

---

## 5. Zabbix Webhook Troubleshooting

Two configuration issues were identified during integration.

### Missing User Media

Initial error:

```text
No media defined for user.
```

The custom Webhook Media Type had been created but was not assigned to the selected Zabbix user. The AI Incident Analyzer media was added to the user configuration.

### Missing Message Template

The next error was:

```text
No message defined for media type.
```

A Problem Message Template was added to the Webhook Media Type.

After these changes, actual Zabbix Warning events successfully reached the FastAPI backend.

```text
Zabbix Trigger
    ↓
Problem Event
    ↓
Action
    ↓
Media Type
    ↓
Webhook
    ↓
FastAPI
```

---

## 6. Rule-Based Incident Analysis

A deterministic rule-based analysis layer was implemented before introducing the LLM.

For example, a high CPU incident can generate:

```text
Summary:
High CPU utilization detected.

Possible Causes:
- CPU-intensive application process
- Unexpected background process
- Scheduled workload
- Insufficient CPU resources

Recommended Actions:
- Identify top CPU-consuming processes
- Review system load
- Check recent system and application logs
- Compare CPU usage with memory and disk I/O
```

This layer provides immediate deterministic analysis and a fallback when the external AI service is unavailable.

---

## 7. Gemini Integration

Gemini was integrated into the backend using the Google GenAI Python SDK.

The API credential is stored in `.env` and excluded from Git.

```text
Zabbix Incident
      ↓
Rule-Based Analysis
      ↓
Gemini
      ↓
Enhanced Incident Analysis
```

The rule-based result provides initial technical context for LLM-assisted analysis.

---

## 8. Structured LLM Output

An early implementation asked Gemini to return JSON through prompt instructions. This was not sufficiently reliable because the model could still return Markdown or natural-language output.

The integration was therefore changed to schema-enforced structured output.

Example:

```json
{
  "host": "Monitoring-EC2",
  "severity": "Warning",
  "summary": "...",
  "possible_causes": ["..."],
  "recommended_actions": ["..."],
  "confidence": "medium",
  "analysis_source": "gemini"
}
```

Pydantic validates the generated response before it enters the rest of the application.

Structured output provides predictable data for REST API responses, database persistence, Splunk logging, future correlation workflows, and future remediation workflows.

---

## 9. Incident Persistence

SQLite was selected as the initial persistence layer.

The current lab does not require a separate database service or high-concurrency workload, making SQLite appropriate for this stage.

Incident records contain information such as:

- `event_id`
- `host`
- `trigger`
- `severity`
- `message`
- `summary`
- `possible_causes`
- `recommended_actions`
- `confidence`
- `analysis_source`
- `created_at`

Incident history can be retrieved through:

```text
GET /incident/
```

---

## 10. Duplicate Event Protection

The Zabbix `event_id` is used as the unique identifier for an incident.

Before performing an LLM request, the backend checks whether the event has already been processed.

```text
Incoming Event
      ↓
Check event_id
      │
      ├── Existing → Return existing result
      │
      └── New → Analyze → Store
```

This prevents duplicate database records, repeated Gemini API requests, and unnecessary AI processing.

---

## 11. LLM Failure Handling

The monitoring pipeline was designed so that Gemini is an enhancement rather than a hard dependency.

Normal path:

```text
Rule-Based Analysis
        ↓
      Gemini
        ↓
AI-Assisted Result
```

Failure path:

```text
Rule-Based Analysis
        ↓
      Gemini
        ✕
        ↓
Rule-Based Fallback
```

Fallback results are marked with:

```text
analysis_source = rule-based-fallback
```

while successful Gemini results use:

```text
analysis_source = gemini
```

This prevents an external AI service outage from breaking incident processing.

---

## 12. AI Backend Structured Logging

The AI Backend generates machine-readable operational logs using JSON Lines.

Logs are written to:

```text
/var/log/ai-backend/analysis.json.log
```

Example:

```json
{
  "timestamp": "2026-08-23T18:30:21Z",
  "level": "INFO",
  "service": "ai-backend",
  "event": "incident_analysis_completed",
  "incident_id": "INC-001",
  "host": "aws-mon-core-01",
  "source": "zabbix",
  "severity": "high",
  "duration_ms": 1840,
  "analysis_source": "gemini"
}
```

Each line represents an independent backend event.

---

## 13. AI Backend Observability with Splunk

The existing Splunk Universal Forwarder infrastructure was extended to monitor:

```text
/var/log/ai-backend/analysis.json.log
```

The AI Backend logs use a dedicated sourcetype such as:

```text
ai_backend:json
```

Example SPL:

```spl
index=<index> sourcetype="ai_backend:json"
| spath
| table _time event incident_id host severity analysis_source duration_ms
```

This makes the AI service itself observable.

Operational information that can be derived includes:

- Number of analyzed incidents
- Incident severity distribution
- Analysis latency
- Gemini usage
- Fallback frequency
- Backend processing failures

This completes the **AI Observability Path**:

```text
AI Backend
    ↓
Structured JSON Log
    ↓
Splunk Universal Forwarder
    ↓
Splunk
    ↓
Search / Dashboard
```

---

## 14. Current End-to-End Workflow

The completed AI incident analysis implementation workflow is:

```text
Zabbix
   │
   │ Warning+ Event
   ▼
FastAPI AI Backend
   │
   ├── Rule-Based Analysis
   ├── Gemini Analysis
   └── Failure Fallback
   │
   ▼
SQLite
   │
   └── Incident History
   │
   ▼
Structured JSON Log
   │
   ▼
Splunk
   │
   ▼
AI Backend Observability
```

The system can now:

```text
Detect → Forward → Analyze → Store → Observe
```

---

## 15. Key Engineering Decisions

### Dedicated AI Backend

The AI service was separated from Zabbix, Splunk, and Ansible to maintain clear infrastructure responsibilities.

### Private Network Placement

The backend resides in the private monitoring subnet and does not require direct public exposure.

### Hybrid Rule-Based + LLM Analysis

Rule-based analysis provides predictable baseline behavior while Gemini enhances incident analysis.

### Schema-Enforced AI Responses

Structured output is validated before being accepted by the backend.

### Lightweight Persistence

SQLite provides sufficient persistence for the current lab without introducing unnecessary infrastructure overhead.

### Graceful AI Failure

External LLM availability does not determine whether a monitoring event can be processed.

### AI Service Observability

The AI analysis service is itself monitored through structured Splunk logging.

---

## 16. Key Lessons Learned

### Zabbix Integration Requires More Than a Webhook

A functioning integration required:

```text
Media Type
    +
User Media
    +
Message Template
    +
Trigger Action
```

before real Problem events could be delivered.

### Trigger State Matters During Testing

Repeated webhook testing required understanding the Zabbix state transition:

```text
PROBLEM → OK → PROBLEM
```

### Prompting for JSON Is Not Sufficient

Backend systems should not depend on an LLM voluntarily following formatting instructions. Schema-enforced output provides a more reliable integration.

### AI Should Not Become a Monitoring Dependency

The LLM enhances incident analysis, but the monitoring pipeline must continue operating if the AI provider is unavailable.

### AI Systems Also Require Observability

Analysis duration, fallback usage, severity, and backend events should themselves be measurable.

---

## 17. Relationship to the Existing Splunk Layer

Splunk deployment and logging integration established centralized logging from AWS and local systems.

The environment already contains:

- `linux_os`
- `linux_security`
- `app_logs`

These logs provide the operational evidence required for the next phase.

AI incident analysis implementation does not yet retrieve these operational logs as context during incident analysis.

At the end of AI incident analysis implementation, two working data paths exist:

```text
Zabbix
   ↓
AI Backend
   ↓
Gemini
```

and:

```text
Managed Hosts
   ↓
Splunk Universal Forwarder
   ↓
Splunk
```

Splunk context correlation implementation will correlate these paths.

---

## 18. Subsequent Integration — Context Retrieval & Correlation

A subsequent implementation phase added the following Splunk context-correlation path:

```text
AI Backend
    │
    │ Splunk REST API
    ▼
Splunk
    │
    ├── linux_os
    ├── linux_security
    └── app_logs
    │
    ▼
Relevant Host / Time-Window Events
    │
    ▼
AI Backend
    │
    ├── Zabbix Alert
    └── Splunk Evidence
    │
    ▼
Gemini
    │
    ▼
Evidence-Based Incident Analysis
```

The objective is to move from:

> Analyze this monitoring alert.

to:

> Analyze this monitoring alert together with the operational evidence collected from the affected system.

The later context-correlation layer distinguishes:

- Observed evidence
- Probable root cause
- Confidence
- Recommended actions

---

## 19. Subsequent Integration — Controlled Remediation

Automated remediation was intentionally kept outside the initial AI incident-analysis implementation.

A later implementation phase added the controlled workflow:

```text
Detection
    ↓
Context Collection
    ↓
AI Analysis
    ↓
Recommendation
    ↓
Safety / Policy Check
    ↓
Approved Remediation
    ↓
Ansible
    ↓
Verification
```

Keeping analysis and remediation separate prevents AI-generated recommendations from automatically becoming infrastructure changes without appropriate controls.

---

## Final Result

AI incident analysis implementation successfully introduced an **AI-assisted incident analysis layer** into the hybrid monitoring environment.

The completed system integrates:

**Zabbix + FastAPI + Rule-Based Analysis + Gemini + SQLite + Splunk Observability**

The platform can automatically receive monitoring incidents, generate structured analysis, survive external LLM failures, retain incident history, and expose its own operational behavior through Splunk.

The completed project later connected Splunk telemetry back into the AI Backend so incident analysis can use bounded operational evidence together with Zabbix incidents.
