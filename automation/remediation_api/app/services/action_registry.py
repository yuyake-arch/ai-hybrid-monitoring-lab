APPROVED_ACTIONS = {
    "ENSURE_ZABBIX_AGENT_RUNNING": {
        "description": "Ensure Zabbix Agent 2 service is running",
        "playbook": "ensure_zabbix_agent_running.yml",
    },
}


def get_action_policy(
    action_id: str,
) -> dict | None:
    return APPROVED_ACTIONS.get(action_id)
