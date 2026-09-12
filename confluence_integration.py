  #### 2. Confluence Integration Module

  """
  Confluence Integration for MCP Control-Tower
  Provides automated Confluence page creation and updates for documentation.
  """
  import requests
  import json
  from datetime import datetime
  from typing import Optional, Dict, Any


  class ConfluenceIntegration:
      """Confluence API integration for MCP Control-Tower."""

      def __init__(self, base_url: str, username: str, api_token: str):
          self.base_url = base_url.rstrip('/')
          self.auth = (username, api_token)
          self.session = requests.Session()
          self.session.auth = self.auth
          self.session.headers.update({
              'Accept': 'application/json',
              'Content-Type': 'application/json'
          })

      def create_page(self, space_key: str, title: str, content: str,
                      parent_page_id: Optional[int] = None) -> Optional[Dict]:
          """Create a new Confluence page."""
          url = f"{self.base_url}/rest/api/3/page/"

          # Convert markdown to Confluence storage format (simplified)
          storage_content = self._markdown_to_storage(content)

          page_data = {
              "type": "page",
              "title": title,
              "space": {"key": space_key},
              "body": {
                  "storage": storage_content
              }
          }

          if parent_page_id:
              page_data["ancestors"] = [{"id": parent_page_id}]

          try:
              response = self.session.post(url, json=page_data)
              response.raise_for_status()
              return response.json()
          except requests.exceptions.RequestException as e:
              print(f"Confluence API error: {e}")
              return None

      def update_page(self, page_id: int, title: str, content: str) -> bool:
          """Update an existing Confluence page."""
          url = f"{self.base_url}/rest/api/3/page/{page_id}"

          storage_content = self._markdown_to_storage(content)

          data = {
              "id": page_id,
              "type": "page",
              "title": title,
              "body": {
                  "storage": storage_content
              }
          }

          try:
              response = self.session.put(url, json=data)
              response.raise_for_status()
              return True
          except requests.exceptions.RequestException:
              return False

      def _markdown_to_storage(self, markdown: str) -> str:
          """Convert markdown to Confluence XHTML storage format."""
          html = markdown
          html = html.replace('## ', '<h2>')
          html = html.replace('# ', '<h1>')
          html = html.replace('**', '<strong>')
          html = html.replace('*', '<em>')
          html = html.replace('\n\n', '</p><p>')
          html = f'<p>{html}</p>'
          return html

      def get_page(self, page_id: int) -> Optional[Dict]:
          """Retrieve a Confluence page by ID."""
          url = f"{self.base_url}/rest/api/3/page/{page_id}"

          try:
              response = self.session.get(url)
              response.raise_for_status()
              return response.json()
          except requests.exceptions.RequestException:
              return None
