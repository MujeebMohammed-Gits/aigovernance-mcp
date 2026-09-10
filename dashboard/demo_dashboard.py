from dashboard import MonitoringDashboard
import time

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
