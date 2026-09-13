"""
Jira Integration for MCP Control‑Tower
Provides automated Jira issue creation and status updates for deployment events.
"""

import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any


class JiraIntegration:
    """Jira API integration for MCP Control‑Tower."""

    def __init__(self, base_url: str, username: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, api_token)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def create_issue(self, project: str, summary: str, description: str,
                     issue_type: str = 'Task', labels: Optional[list] = None) -> Optional[Dict]:
        """Create a new Jira issue."""
        url = f"{self.base_url}/rest/api/3/issue"

        issue_data = {
            "fields": {
                "project": {"key": project},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }
        }

        if labels:
            issue_data["fields"]["labels"] = labels

        try:
            response = self.session.post(url, json=issue_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Jira API error: {e}")
            return None

    def transition_issue(self, issue_key: str, transition_id: str) -> bool:
        """Transition a Jira issue to a new status."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        data = {"transition": {"id": transition_id}}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False

    def update_issue_field(self, issue_key: str, field: str, value: Any) -> bool:
        """Update a custom field on a Jira issue."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        data = {"fields": {field: value}}

        try:
            response = self.session.put(url, json=data)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False

    def get_issue(self, issue_key: str) -> Optional[Dict]:
        """Retrieve a Jira issue by key."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
