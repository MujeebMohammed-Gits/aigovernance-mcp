"""
Slack Integration for MCP Control‑Tower
Provides real‑time notifications for deployment events, alerts, and metrics.
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests

logger = logging.getLogger('slack_integration')


class SlackIntegration:
    """Slack API integration for MCP Control‑Tower notifications."""

    def __init__(self, webhook_url: Optional[str] = None,
                 bot_token: Optional[str] = None,
                 channel: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        self.channel = channel or os.getenv('SLACK_CHANNEL', '#general')
        self.session = requests.Session()
        self.rate_limit_delay = 1.0

        if self.webhook_url:
            self.session.headers.update({'Content-Type': 'application/json'})

    def _post_payload(self, payload: Dict[str, Any], channel: Optional[str] = None) -> Optional[Dict]:
        target_webhook = self.webhook_url
        if not target_webhook:
            logger.error("No Slack webhook URL configured")
            return None

        final_payload = dict(payload)
        if channel:
            final_payload["channel"] = channel

        try:
            response = self.session.post(target_webhook, json=final_payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Slack message failed: {e}")
            return None

    def send_message(self, text: Optional[str] = None,
                     blocks: Optional[List[Dict]] = None,
                     channel: Optional[str] = None,
                     payload: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        target_channel = channel or self.channel

        if payload is None:
            payload = {"channel": target_channel, "text": text or ""}
            if blocks:
                payload["blocks"] = blocks
        else:
            payload = dict(payload)
            if target_channel and "channel" not in payload:
                payload["channel"] = target_channel

        return self._post_payload(payload, channel=channel)

    def send_deployment_notification(self, environment: str, status: str,
                                     version: str, deployment_id: str,
                                     duration: Optional[float] = None) -> Optional[Dict]:
        emoji = "✅" if status == "success" else "❌"
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

        text = (
            f"{emoji} *Deployment {status.title()}*\n"
            f"> *Environment*: {environment}\n"
            f"> *Version*: {version}\n"
            f"> *Deployed*: {timestamp}\n"
            f"> *Deploy ID*: `{deployment_id}`\n"
        )

        if duration is not None:
            text += f"> *Duration*: {duration:.1f} seconds\n"

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} Deployment {status.title()}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Environment*: {environment}"},
                {"type": "mrkdwn", "text": f"*Version*: {version}"},
                {"type": "mrkdwn", "text": f"*Deployed*: {timestamp}"}
            ]},
            {"type": "context", "elements": [{"type": "plain_text", "text": f"Deploy ID: {deployment_id}"}]}
        ]

        return self.send_message(text=text, blocks=blocks)

    def send_alert(self, alert_type: str, severity: str,
                   message: str, details: Optional[Dict] = None) -> Optional[Dict]:
        color_map = {
            "critical": "#ff0000",
            "high": "#ff6500",
            "medium": "#ffd700",
            "low": "#7fffc0"
        }

        attachment = {
            "color": color_map.get(severity.lower(), "#ffd700"),
            "title": f":warning: {alert_type.title()} Alert",
            "text": message,
            "ts": int(datetime.utcnow().timestamp()),
            "fields": []
        }

        if details:
            for key, value in details.items():
                attachment["fields"].append({
                    "title": key,
                    "value": str(value)[:1024],
                    "short": False
                })

        payload = {
            "channel": self.channel,
            "text": f"{alert_type.title()} alert: {message}",
            "attachments": [attachment]
        }

        return self.send_message(payload=payload)

    def send_metrics_update(self, metrics: Dict[str, Any],
                            title: str = "Monthly Metrics Summary") -> Optional[Dict]:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f":chart_increasing: {title}"}}
        ]

        if metrics:
            blocks.append({
                "type": "section",
                "fields": [{"type": "mrkdwn", "text": f"*{k}*: {v}"} for k, v in metrics.items()]
            })

        return self.send_message(text=f":chart_increasing: {title}", blocks=blocks)
