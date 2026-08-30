import json
import os
from datetime import datetime, timedelta
from typing import Any

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

class SplunkService:
    def __init__(self) -> None:
        self.host = os.getenv("SPLUNK_HOST")
        self.port = os.getenv("SPLUNK_PORT", "8089")
        self.username = os.getenv("SPLUNK_USERNAME")
        self.password = os.getenv("SPLUNK_PASSWORD")

        self.base_url = f"https://{self.host}:{self.port}"
        self.timeout = 10

    def search_incident_context(
        self,
        host: str,
        incident_time: datetime,
        window_minutes: int = 5,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:

        earliest = incident_time - timedelta(minutes=window_minutes)
        latest = incident_time + timedelta(minutes=window_minutes)

        search_query = (
            "search "
            "(index=linux_os OR index=linux_security OR index=app_logs) "
            f'host="{host}" '
            "| sort 0 _time "
            f"| head {max_results} "
            "| table _time index host source sourcetype _raw"
        )

        return self._search(
            search_query,
            earliest=earliest.timestamp(),
            latest=latest.timestamp(),
       )

    def _search(
        self,
        search_query: str,
        earliest: float,
        latest: float,
    ) -> dict[str, Any]:

        url = f"{self.base_url}/services/search/jobs/export"

        payload = {
            "search": search_query,
            "output_mode": "json",
            "earliest_time": str(earliest),
            "latest_time": str(latest),
        }

        try:
            response = requests.post(
                url,
                data=payload,
                auth=HTTPBasicAuth(
                    self.username,
                    self.password,
                ),
                verify=False,
                timeout=self.timeout,
            )

            response.raise_for_status()

            return {
                "available": True,
                "events": self._parse_export_response(
                response.text
            ),
        }

        except requests.RequestException as exc:
            print(f"Splunk search failed: {exc}")
            return []

    def _parse_export_response(
        self,
        text: str,
    ) -> list[dict[str, Any]]:

        results = []

        for line in text.splitlines():
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            result = item.get("result")

            if not result:
                continue

            results.append(
                {
                    "timestamp": result.get("_time"),
                    "index": result.get("index"),
                    "host": result.get("host"),
                    "source": result.get("source"),
                    "sourcetype": result.get("sourcetype"),
                    "message": result.get("_raw"),
                }
            )

        return results
