import re
import subprocess
from pathlib import Path


AUTOMATION_ROOT = Path(
    "/home/ubuntu/ai-hybrid-monitoring-lab/automation"
)

def _extract_changed(stdout: str) -> bool:
    matches = re.findall(r"changed=(\d+)", stdout)

    return any(
        int(value) > 0
        for value in matches
    )

def execute_playbook(
    *,
    playbook_name: str,
    target: str,
) -> dict:

    playbook_path = (
        AUTOMATION_ROOT
        / "playbooks"
        / playbook_name
    )

    if not playbook_path.is_file():
        return {
            "success": False,
            "changed": False,
            "return_code": None,
            "message": "Approved remediation action could not be found",
            "stdout": "",
            "stderr": (
                f"Approved playbook not found: "
                f"{playbook_name}"
            ),
        }

    command = [
        "ansible-playbook",
        str(playbook_path),
        "--limit",
        target,
    ]

    try:
        result = subprocess.run(
            command,
            cwd=AUTOMATION_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        no_hosts_matched = (
            "skipping: no hosts matched" in result.stdout.lower()
            or "no hosts matched" in result.stderr.lower()
        )

        success = (
            result.returncode == 0
            and not no_hosts_matched
        )

        if no_hosts_matched:
            message = (
                f"Target '{target}' did not match any hosts "
                f"in the remediation playbook scope"
            )
        elif result.returncode != 0:
            message = "Remediation execution failed"
        else:
            message = "Remediation completed successfully"

        return {
            "success": success,
            "changed": _extract_changed(
                result.stdout
            ),
            "return_code": result.returncode,
            "message": message,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "changed": False,
            "return_code": None,
            "message": "Remediation execution timed out",
            "stdout": exc.stdout or "",
            "stderr": "Ansible execution timed out",
        }
