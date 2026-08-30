from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

from app.models.incident import IncidentRequest, IncidentAnalysis


load_dotenv()

client = genai.Client()


class GeminiIncidentAnalysis(BaseModel):
    summary: str
    observed_evidence: list[str]
    possible_causes: list[str]
    recommended_actions: list[str]
    confidence: str

def format_splunk_evidence(
    splunk_evidence: list[dict],
) -> str:

    if not splunk_evidence:
        return "No relevant Splunk log evidence was found."

    formatted_events = []

    for event in splunk_evidence:
        formatted_events.append(
            (
                f"- Time: {event.get('timestamp')}\n"
                f"  Index: {event.get('index')}\n"
                f"  Source: {event.get('source')}\n"
                f"  Sourcetype: {event.get('sourcetype')}\n"
                f"  Message: {event.get('message')}"
            )
        )

    return "\n".join(formatted_events)





def analyze_with_llm(
    incident: IncidentRequest,
    rule_analysis: IncidentAnalysis,
    splunk_evidence: list[dict],
) -> IncidentAnalysis:

    evidence_text = format_splunk_evidence(
        splunk_evidence
    )

    prompt = f"""
You are an infrastructure incident analyst.

Analyze the following monitoring incident using both the
Zabbix alert and the available Splunk log evidence.

Host:
{incident.host}

Trigger:
{incident.trigger}

Severity:
{incident.severity}

Zabbix message:
{incident.message}

Initial rule-based analysis:

Summary:
{rule_analysis.summary}

Possible causes:
{rule_analysis.possible_causes}

Recommended actions:
{rule_analysis.recommended_actions}

Splunk log evidence:

{evidence_text}


Requirements:
- Produce a concise technical incident summary.
- observed_evidence must contain only facts directly supported by the Zabbix alert or Splunk logs.
- Clearly distinguish observed evidence from inferred or probable causes.
- Do not treat temporal correlation as proof of causation.
- Do not claim that a probable cause is confirmed unless the evidence directly supports it.
- Identify the most likely causes based on the available evidence.
- Provide practical troubleshooting actions.
- Do not invent facts not present in the monitoring data or logs.
- Do not recommend destructive actions.
- If Splunk evidence is unavailable or inconclusive, rely primarily on the Zabbix incident and rule-based analysis.
- Confidence must be one of: low, medium, high.
"""

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": GeminiIncidentAnalysis.model_json_schema(),
        },
        store=False,
    )

    result = GeminiIncidentAnalysis.model_validate_json(
        interaction.output_text
    )


    return IncidentAnalysis(
        host=incident.host,
        severity=incident.severity,
        summary=result.summary,
        observed_evidence=result.observed_evidence,
        possible_causes=result.possible_causes,
        recommended_actions=result.recommended_actions,
        confidence=result.confidence,
        analysis_source="gemini",
    )
