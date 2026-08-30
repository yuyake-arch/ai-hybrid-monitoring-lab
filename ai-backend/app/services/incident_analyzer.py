from app.models.incident import IncidentRequest, IncidentAnalysis


def analyze_incident(incident: IncidentRequest) -> IncidentAnalysis:

    trigger = incident.trigger.lower()

    if "cpu" in trigger:
        possible_causes = [
            "CPU-intensive application process",
            "Unexpected background process or scheduled job",
            "Insufficient CPU resources",
        ]

        recommended_actions = [
            "Check top CPU-consuming processes",
            "Review system load using uptime or top",
            "Review recent system and application logs",
            "Compare CPU usage with memory and disk I/O",
        ]

    elif "memory" in trigger:
        possible_causes = [
            "Application memory leak",
            "High memory consumption by one or more processes",
            "Insufficient available memory",
        ]

        recommended_actions = [
            "Check memory usage with free -h",
            "Identify high-memory processes",
            "Review application logs",
            "Check whether swap usage is increasing",
        ]

    elif "disk" in trigger:
        possible_causes = [
            "Large log files",
            "Application-generated temporary files",
            "Insufficient disk capacity",
        ]

        recommended_actions = [
            "Check disk usage with df -h",
            "Identify large directories using du",
            "Review log retention settings",
            "Check for unexpected file growth",
        ]

    elif "service" in trigger or "unavailable" in trigger:
        possible_causes = [
            "Application or system service stopped",
            "Dependency failure",
            "Configuration error",
        ]

        recommended_actions = [
            "Check service status using systemctl",
            "Review service logs using journalctl",
            "Check dependent services",
            "Verify recent configuration changes",
        ]

    else:
        possible_causes = [
            "Unknown system or application issue",
        ]

        recommended_actions = [
            "Review system metrics",
            "Check recent logs",
            "Investigate recent infrastructure changes",
        ]

    summary = f"{incident.trigger} detected on {incident.host}."

    if incident.value is not None:
        summary += f" Current value: {incident.value}."

    if incident.duration_minutes is not None:
        summary += (
            f" The condition has persisted for "
            f"{incident.duration_minutes} minutes."
        )

    return IncidentAnalysis(
        host=incident.host,
        severity=incident.severity,
        summary=summary,
        possible_causes=possible_causes,
        recommended_actions=recommended_actions,
        confidence="low",
        analysis_source="rule-based",
    )
