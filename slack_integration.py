  #### 7. Slack Integration Module

  """
  Slack Integration for MCP Control-Tower
  Provides real-time notifications for deployment events, alerts, and metrics.
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
      """Slack API integration for MCP Control-Tower notifications."""

      def __init__(self, webhook_url: Optional[str] = None,
                   bot_token: Optional[str] = None,
                   channel: Optional[str] = None):
          self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
          self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
          self.channel = channel or os.getenv('SLACK_CHANNEL', '#general')
          self.session = requests.Session()
          self.rate_limit_delay = 1.0  # Seconds between messages

          if self.webhook_url:
              self.session.headers.update({
                  'Content-Type': 'application/json'
              })

      def send_message(self, text: str,
                       blocks: Optional[List[Dict]] = None,
                       channel: Optional[str] = None) -> Optional[Dict]:
          """Send a message to Slack."""
          target_channel = channel or self.channel
          target_webhook = self.webhook_url

          if not target_webhook:
              logger.error("No Slack webhook URL configured")
              return None

          payload = {
              "channel": target_channel,
              "text": text
          }

          if blocks:
              payload["blocks"] = blocks

          try:
              response = self.session.post(target_webhook, json=payload)
              response.raise_for_status()
              return response.json()
          except requests.exceptions.RequestException as e:
              logger.error(f"Slack message failed: {e}")
              return None

      def send_deployment_notification(self,
                                       environment: str,
                                       status: str,
                                       version: str,
                                       deployment_id: str,
                                       duration: Optional[float] = None) -> Optional[Dict]:
          """Send a formatted deployment notification to Slack."""

          emoji = "✅" if status == "success" else "❌"
          timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

          text = f"{emoji} *Deployment {status.title()}*\n"
          text += f"> *Environment*: {environment}\n"
          text += f"> *Version*: {version}\n"
          text += f"> *Deployed*: {timestamp}\n"
          if duration:
              text += f"> *Duration*: {duration:.1f} seconds\n"
          text += f"> *Deploy ID*: `{deployment_id}`\n"

          blocks = [
              {
                  "type": "header",
                  "text": {
                      "type": "plain_text",
                      "text": f"{emoji} Deployment {status.title()}"
                  }
              },
              {
                  "type": "section",
                  "fields": [
                      {"type": "mrkdown", "text": f"*Environment*: {environment}"},
                      {"type": "mrkdown", "text": f"*Version*: {version}"},
                      {"type": "mrkdown", "text": f"*Deployed*: {timestamp}"}
                  ]
              },
              {
                  "type": "context",
                  "elements": [
                      {"type": "plain_text", "text": f"Deploy ID: {deployment_id}"}
                  ]
              }
          ]

          return self.send_message(text=text, blocks=blocks)

      def send_alert(self,
                     alert_type: str,
                     severity: str,
                     message: str,
                     details: Optional[Dict] = None) -> Optional[Dict]:
          """Send an alert to Slack."""

          color_map = {
              "critical": "#ff0000",
              "high": "#ff6500",
              "medium": "#ffd700",
              "low": "#7fffc0"
          }

          embed = {
              "title": f":warning: {alert_type.title()} Alert",
              "description": message,
              "color": color_map.get(severity.lower(), "#ffd700"),
              "timestamp": datetime.utcnow().isoformat(),
              "fields": []
          }

          if details:
              for key, value in details.items():
                  embed["fields"].append({
                      "title": key,
                      "value": str(value)[:1024],
                      "short": False
                  })

          payload = {
              "channel": self.channel,
              "embeds": [embed]
          }

          return self.send_message(payload=payload)

      def send_metrics_update(self,
                             metrics: Dict[str, Any],
                             title: str = "Monthly Metrics Summary") -> Optional[Dict]:
          """Send metrics summary to Slack."""

          blocks = [
              {
                  "type": "header",
                  "text": {
                      "type": "plain_text",
                      "text": f":chart_increasing: {title}"
                  }
              }
          ]
          # ... (truncated for brevity - full implementation includes metric fields)
          return self.send_message(blocks=blocks)
