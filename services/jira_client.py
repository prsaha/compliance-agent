"""
JiraClient — Thin HTTP client for the Jira REST API v2.

Extracted from ApprovalService so that Jira integration concerns are isolated
from business logic. Inject JiraClient into ApprovalService via its constructor.

Usage:
    from services.jira_client import JiraClient
    jira = JiraClient()               # reads env vars
    ticket_key = jira.create_issue(fields={...})
"""

import os
import logging
from typing import Any, Dict, Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class JiraConfigError(Exception):
    """Raised when required Jira env vars are missing."""


class JiraClient:
    """
    HTTP client for the Jira REST API v2.

    Configuration via environment variables:
        JIRA_URL          — e.g. https://yourcompany.atlassian.net
        JIRA_EMAIL        — service-account email
        JIRA_API_TOKEN    — API token (not password)
        JIRA_PROJECT      — default project key (default: COMP)
    """

    def __init__(
        self,
        jira_url: Optional[str] = None,
        jira_email: Optional[str] = None,
        jira_api_token: Optional[str] = None,
        jira_project: Optional[str] = None,
    ) -> None:
        self.url = jira_url or os.getenv("JIRA_URL", "")
        self.email = jira_email or os.getenv("JIRA_EMAIL", "")
        self.token = jira_api_token or os.getenv("JIRA_API_TOKEN", "")
        self.project = jira_project or os.getenv("JIRA_PROJECT", "COMP")

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.email and self.token)

    def _auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth(self.email, self.token)

    def _headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json", "Accept": "application/json"}

    # ------------------------------------------------------------------
    # Issue operations
    # ------------------------------------------------------------------

    def create_issue(self, fields: Dict[str, Any]) -> Optional[str]:
        """
        Create a Jira issue.

        Args:
            fields: The ``fields`` dict for the Jira issue (project, summary,
                    description, issuetype, priority, labels, assignee, etc.).
                    The caller is responsible for populating the ``project`` key
                    if it differs from the default.

        Returns:
            Issue key (e.g. "COMP-42") on success, None on failure or misconfiguration.
        """
        if not self.is_configured:
            logger.warning("Jira not configured — skipping issue creation")
            return None

        # Inject default project if not set by caller
        if "project" not in fields:
            fields["project"] = {"key": self.project}

        try:
            response = requests.post(
                f"{self.url}/rest/api/2/issue",
                auth=self._auth(),
                json={"fields": fields},
                headers=self._headers(),
                timeout=30,
            )
            if response.status_code == 201:
                key = response.json().get("key")
                logger.info(f"Created Jira issue: {key}")
                return key
            else:
                logger.error(
                    f"Jira create_issue failed: HTTP {response.status_code} — {response.text[:200]}"
                )
                return None
        except requests.RequestException as exc:
            logger.error(f"Jira create_issue network error: {exc}")
            return None

    def add_comment(self, issue_key: str, comment_body: str) -> bool:
        """Add a comment to an existing issue. Returns True on success."""
        if not self.is_configured:
            return False
        try:
            response = requests.post(
                f"{self.url}/rest/api/2/issue/{issue_key}/comment",
                auth=self._auth(),
                json={"body": comment_body},
                headers=self._headers(),
                timeout=30,
            )
            return response.status_code == 201
        except requests.RequestException as exc:
            logger.error(f"Jira add_comment error: {exc}")
            return False

    def transition_issue(self, issue_key: str, transition_id: str) -> bool:
        """Transition an issue to a new status. Returns True on success."""
        if not self.is_configured:
            return False
        try:
            response = requests.post(
                f"{self.url}/rest/api/2/issue/{issue_key}/transitions",
                auth=self._auth(),
                json={"transition": {"id": transition_id}},
                headers=self._headers(),
                timeout=30,
            )
            return response.status_code == 204
        except requests.RequestException as exc:
            logger.error(f"Jira transition_issue error: {exc}")
            return False
