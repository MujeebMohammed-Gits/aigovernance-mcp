from audit_logger import AuditLogger
import os
from datetime import datetime, timezone

# ============================================================
# Demonstration & Testing
# ============================================================

if __name__ == "__main__":
      print("=" * 70)
      print("AUDIT LOGGER PRODUCTION HARDENING DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize audit logger
      logger = AuditLogger(log_file_path="audit_log.jsonl")

      # Test logging events with different decisions
      print("Logging test events...\n")

      # Event 1: Allowed call
      event1 = {
          'event_id': 'evt-001',
          'timestamp': datetime.now(timezone.utc).isoformat(),
          'provider': 'openai',
          'model': 'gpt-4',
          'purpose': 'customer_support',
          'policy_evaluation': {
              'decision': 'allow',
              'rules_triggered': [],
              'policy_explanations': ['No policy violations detected']
          },
          'data_classification': 'internal',
          'has_pii': False,
          'has_sensitive_data': False
      }
      result1 = logger.add_event(event1)
      print(f"Event 1 (allowed) logged: {result1}")

      # Event 2: Blocked call
      event2 = {
          'event_id': 'evt-002',
          'timestamp': datetime.now(timezone.utc).isoformat(),
          'provider': 'openai',
          'model': 'gpt-4',
          'purpose': 'customer_support',
          'policy_evaluation': {
              'decision': 'block',
              'rules_triggered': ['PII_BLOCK'],
              'policy_explanations': ['PII detected in call']
          },
          'data_classification': 'confidential',
          'has_pii': True,
          'has_sensitive_data': False
      }
      result2 = logger.add_event(event2)
      print(f"Event 2 (blocked) logged: {result2}")

      # Event 3: Warned call
      event3 = {
          'event_id': 'evt-003',
          'timestamp': datetime.now(timezone.utc).isoformat(),
          'provider': 'anthropic',
          'model': 'claude-2',
          'purpose': 'fraud_detection',
          'policy_evaluation': {
              'decision': 'warn',
              'rules_triggered': ['HIGH_RISK_LOG'],
              'policy_explanations': ['High-risk use case detected']
          },
          'data_classification': 'restricted',
          'has_pii': False,
          'has_sensitive_data': True
      }
      result3 = logger.add_event(event3)
      print(f"Event 3 (warn) logged: {result3}")

      # Query events
      print("\nQuerying events...")

      allowed_events = logger.get_events_by_decision('allow')
      print(f"Allowed events: {len(allowed_events)}")

      blocked_events = logger.get_events_by_decision('block')
      print(f"Blocked events: {len(blocked_events)}")

      warned_events = logger.get_events_by_decision('warn')
      print(f"Warned events: {len(warned_events)}")

      # Rule-based query
      pii_events = logger.get_events_by_rule('PII_BLOCK')
      print(f"Events with PII_BLOCK rule: {len(pii_events)}")

      # Health report
      print("\nHealth report:")
      health = logger.get_health_report()
      for key, value in health.items():
          print(f"  {key}: {value}")

      # Statistics
      print("\nDecision statistics:")
      decisions = logger.get_decision_statistics()
      for key, value in decisions.items():
          print(f"  {key}: {value}")

      rules = logger.get_rule_statistics()
      print(f"Rule statistics: {rules}")

      print("\n" + "=" * 70)
      print("DEMONSTRATION COMPLETE")
      print("=" * 70)
