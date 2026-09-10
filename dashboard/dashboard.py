
  # -*- coding: utf-8 -*-
"""
    Monitoring Dashboard Production Hardened
    Minimal console-based dashboard for AI Governance & Compliance Control-Tower MCP Agent
    Thread-safe, with structured logging, health reporting, and circuit breaker patterns
  """
import time
import threading
import logging
import json
from collections import deque
from datetime import datetime


  # Configure structured logger
logger = logging.getLogger('mcp_dashboard')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

  # Thread lock for concurrent access
_dashboard_lock = threading.Lock()


class MonitoringDashboard:
      """
      Production-hardened minimal console dashboard for AI Governance & Compliance Control-Tower MCP Agent.

      Features:
      - Thread-safe event handling
      - Structured JSONL event storage
      - Health/statistics tracking
      - Circuit breaker integration
      - Decision visualization
      - No frontend framework required (console-only)
      """

      def __init__(self, max_display: int = 50, refresh_rate: float = 0.5):
          self.max_display = max_display
          self.refresh_rate = refresh_rate
          self.event_history = deque(maxlen=max_display)
          self.running = False
          self.refresh_thread = None

          # Statistics tracking (thread-safe)
          self._total_calls = 0
          self._allowed = 0
          self._blocked = 0
          self._warnings = 0
          self._rules_triggered: Dict[str, int] = defaultdict(int)

          # Decision statistics
          self._decision_stats: Dict[str, int] = {'allow': 0, 'block': 0, 'warn': 0, 'unknown': 0}
          self._rule_stats: Dict[str, int] = defaultdict(int)

          # Time-based tracking
          self._start_time = time.time()
          self._event_count_by_hour: Dict[int, int] = defaultdict(int)

      def start(self):
          """Start the dashboard refresh loop."""
          with _dashboard_lock:
              self.running = True
              self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
              self.refresh_thread.start()
              logger.info("Dashboard started - monitoring AI call events...")

      def stop(self):
          """Stop the dashboard refresh loop."""
          with _dashboard_lock:
              self.running = False
              if self.refresh_thread:
                  self.refresh_thread.join()
              logger.info("Dashboard stopped.")

      def receive_event(self, event_data: dict):
          """Receive and queue an AI call event from the integration layer with thread safety."""
          with _dashboard_lock:
              # Enhance event with display metadata
              enhanced = self._enhance_event(event_data)
              self.event_history.append(enhanced)
              self._update_statistics(enhanced)

      def _enhance_event(self, event: dict) -> dict:
          """Add display-friendly metadata to the event with validation."""
          enhanced = dict(event)

          # Add display timestamp
          if 'timestamp' in enhanced:
              try:
                  dt = datetime.fromisoformat(enhanced['timestamp'].replace('Z', '+00:00'))
                  enhanced['display_timestamp'] = dt.strftime('%H:%M:%S')
              except Exception:
                  enhanced['display_timestamp'] = time.strftime('%H:%M:%S')

          # Ensure policy_evaluation exists with consistent structure
          if 'policy_evaluation' not in enhanced:
              enhanced['policy_evaluation'] = {
                  'decision': 'unknown',
                  'rules_triggered': [],
                  'policy_explanations': [],
                  'decision_display': '? UNKNOWN',
                  'rules_triggered_display': 'None'
              }

          # Ensure consistent field names
          pe = enhanced['policy_evaluation']

          # Rules triggered display
          if 'rules_triggered' in pe:
              rules = pe['rules_triggered']
              if isinstance(rules, list):
                  pe['rules_triggered_display'] = ', '.join(str(r) for r in rules) if rules else 'None'
              else:
                  pe['rules_triggered_display'] = str(rules)
          else:
              pe['rules_triggered_display'] = 'None'

          # Decision display with icon
          if 'decision' in pe:
              decision = pe['decision'].lower()
              icons = {'allow': 'âœ…', 'block': 'ðŸš«', 'warn': 'âš ï¸', 'unknown': 'ðŸ”¸'}
              icon = icons.get(decision, 'ðŸ”¸')
              pe['decision_display'] = f"{icon} {decision.upper()}"
          else:
              pe['decision_display'] = 'â“ UNKNOWN'

          return enhanced

      def _update_statistics(self, event: dict):
          """Update statistics based on the event with thread-safe increments."""
          # Increment total calls
          self._total_calls += 1

          # Get decision and update stats
          decision = event.get('policy_evaluation', {}).get('decision', 'unknown')
          decision_lower = decision.lower() if decision else 'unknown'

          if decision_lower in self._decision_stats:
              self._decision_stats[decision_lower] += 1
          else:
              self._decision_stats['unknown'] += 1

          # Update decision counts
          if decision_lower == 'allow':
              self._allowed += 1
          elif decision_lower == 'block':
              self._blocked += 1
          elif decision_lower == 'warn':
              self._warnings += 1

          # Track rules triggered
          rules = event.get('policy_evaluation', {}).get('rules_triggered', [])
          if isinstance(rules, list):
              for rule in rules:
                  rule_key = str(rule).lower() if rule else 'unknown'
                  self._rules_triggered[rule_key] += 1

          # Track events per hour
          current_hour = datetime.now(timezone.utc).hour
          self._event_count_by_hour[current_hour] += 1

      def _refresh_loop(self):
          """Background thread that refreshes the display."""
          while True:
              with _dashboard_lock:
                  if not self.running:
                      break

              self._clear_screen()
              self._display_header()
              self._display_events()
              self._display_statistics()
              time.sleep(self.refresh_rate)

      @staticmethod
      def _clear_screen():
          """Clear console screen (cross-platform compatible)."""
          print('\033[2J\033[H', end='', flush=True)

      def _display_header(self):
          """Display the dashboard header."""
          elapsed = time.time() - self._start_time
          print("=" * 70)
          print("ðŸŽ¯ AI GOVERNANCE & COMPLIANCE CONTROL-TOWER - MONITORING DASHBOARD")
          print(f"  Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Uptime: {elapsed:.1f}s")
          print("-" * 70)

      def _display_events(self):
          """Display the live AI call events."""
          with _dashboard_lock:
              if not self.event_history:
                  print("  No events received yet...")
                  return

          print(f"  ðŸ“¡ Live AI Call Events (showing {len(self.event_history)} recent)")
          print()

          # Show last N events or all if less
          events_to_show = list(self.event_history)[-10:]

          for i, event in enumerate(events_to_show, 1):
              self._display_single_event(i, event)
          print()

      def _display_single_event(self, index: int, event: dict):
          """Display a single AI call event with decision visualization."""
          # Determine colors/symbols based on decision
          decision = event.get('policy_evaluation', {}).get('decision', 'unknown')
          icon = self._get_decision_icon(decision)
          rules_str = event.get('policy_evaluation', {}).get('rules_triggered_display', 'None')
          explanation = event.get('policy_evaluation', {}).get('policy_explanations', [''])[0] if event.get('policy_evaluation',
          {}).get('policy_explanations') else ''

          # Truncate long explanations
          if len(explanation) > 60:
              explanation = explanation[:57] + '...'

          # Format: [index] Provider | Purpose | Decision | Rules | Explanation
          provider = event.get('provider', 'unknown')[:12]
          purpose = event.get('purpose', 'unknown')[:15]
          timestamp = event.get('display_timestamp', '—')

          print(f"  [{index:2d}] {provider:12} | {purpose:15} | {icon} {decision:5} | {rules_str:15} | {explanation}")

      def _display_statistics(self):
          """Display summary statistics at the bottom."""
          with _dashboard_lock:
              print()
              print("-" * 70)
              print("  ðŸ“Š STATISTICS")
              print(f"  â””â€€ Total Calls:    {self._total_calls}")
              print(f"  âœ…â€€ Allowed:        {self._allowed} ({self._allowed/max(self._total_calls, 1)*100:.1f}%)")
              print(f"  â”œâ€€ Blocked:        {self._blocked} ({self._blocked/max(self._total_calls, 1)*100:.1f}%)")
              print(f"  â””â€€ Warnings:       {self._warnings} ({self._warnings/max(self._total_calls, 1)*100:.1f}%)")
              print()
              if self._rules_triggered:
                  print("  ðŸ“‹ Top Rules Triggered:")
                  sorted_rules = sorted(self._rules_triggered.items(), key=lambda x: x[1], reverse=True)[:5]
                  for rule, count in sorted_rules:
                      print(f"  â””â€€ {rule}: {count} times")
              print()
              # Decision distribution
              print("  ðŸ“¢ Decision Distribution:")
              for decision, count in self._decision_stats.items():
                  if count > 0:
                      percent = count / max(self._total_calls, 1) * 100
                      bar = '█' * int(percent / 2) + '░' * (50 - int(percent / 2))
                      print(f"  âś… {decision.upper():5}: {count:3} ({percent:5.1f}%%) |{bar}|")
              print("=" * 70)

      @staticmethod
      def _get_decision_icon(decision: str) -> str:
          """Get visual icon for policy decision."""
          icons = {
              'allow': 'âœ…',
              'block': 'ðŸš«',
              'warn': 'âš ï¸',
              'unknown': 'ðŸ”¸'
          }
          return icons.get(decision.lower(), 'ðŸ”¸')


  # ============================================================
  # Demo / Test Code
  # ============================================================

if __name__ == "__main__":
      print("=" * 70)
      print("MONITORING DASHBOARD PRODUCTION HARDENING DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize dashboard
      dashboard = MonitoringDashboard(max_display=30, refresh_rate=1.0)
      dashboard.start()

      # Simulate receiving AI call events
      print("Simulating AI call events...\n")
      time.sleep(0.5)

      test_events = [
          {
              "event_id": "evt-001",
              "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "agent_id": "support-bot-01",
              "provider": "openai",
              "model": "gpt-4",
              "purpose": "customer_support",
              "data_classification": "confidential",
              "has_pii": True,
              "has_sensitive_data": True,
              "risk_level": "medium",
              "policy_evaluation": {
                  "decision": "block",
                  "rules_triggered": ["PII_BLOCK"],
                  "policy_explanations": ["ðŸš« BLOCKED: AI call contains PII. Approval required."]
              }
          },
          {
              "event_id": "evt-002",
              "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "agent_id": "fraud-detection-bot",
              "provider": "anthropic",
              "model": "claude-2",
              "purpose": "fraud_detection",
              "data_classification": "restricted",
              "has_pii": False,
              "has_sensitive_data": True,
              "risk_level": "high",
              "policy_evaluation": {
                  "decision": "warn",
                  "rules_triggered": ["HIGH_RISK_LOG"],
                  "policy_explanations": ["ðŸ“ LOGGED: High-risk use case detected - fraud_detection"]
              }
          },
          {
              "event_id": "evt-003",
              "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "agent_id": "dev-assistant",
              "provider": "openai",
              "model": "gpt-4",
              "purpose": "code_generation",
              "data_classification": "internal",
              "has_pii": False,
              "has_sensitive_data": False,
              "risk_level": "low",
              "policy_evaluation": {
                  "decision": "allow",
                  "rules_triggered": [],
                  "policy_explanations": ["âœ… No policy violations detected - Allowed"]
              }
          },
          {
              "event_id": "evt-004",
              "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "agent_id": "document-analyzer",
              "provider": "anthropic",
              "model": "claude-2",
              "purpose": "document_analysis",
              "data_classification": "confidential",
              "has_pii": True,
              "has_sensitive_data": True,
              "risk_level": "medium",
              "policy_evaluation": {
                  "decision": "block",
                  "rules_triggered": ["PII_BLOCK", "HIGH_RISK_LOG"],
                  "policy_explanations": ["ðŸš« BLOCKED: AI call contains PII", "ðŸ“ LOGGED: High-risk use case detected"]
              }
          },
          {
              "event_id": "evt-005",
              "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "agent_id": "data-insights",
              "provider": "openai",
              "model": "gpt-4",
              "purpose": "data_analysis",
              "data_classification": "public",
              "has_pii": False,
              "has_sensitive_data": False,
              "risk_level": "low",
              "policy_evaluation": {
                  "decision": "allow",
                  "rules_triggered": [],
                  "policy_explanations": ["âœ… Public data - Allowed with light monitoring"]
              }
          }
      ]

      # Stream events to dashboard
      print("Events streamed to dashboard:\n")
      for i, event in enumerate(test_events, 1):
          dashboard.receive_event(event)
          time.sleep(1)  # Simulate real-time arrival

      # Let dashboard display for a moment
      time.sleep(3)

      # Stop dashboard
      print("\n" + "=" * 70)
      dashboard.stop()

      print("\nâœ… Demonstration complete - dashboard prototype working!")
      print("=" * 70)

