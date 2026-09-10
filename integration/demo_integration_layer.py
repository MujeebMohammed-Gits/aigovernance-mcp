
  # ============================================================
  # Example Usage & Demonstration
  # ============================================================

if __name__ == "__main__":
      print("=" * 70)
      print("INTEGRATION LAYER PRODUCTION HARDENING DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize policy engine
      from policy_engine.policy_engine_main import PolicyEngine, block_pii_external_llms, log_high_risk_uses, enforce_data_classification
      policy_engine = PolicyEngine()
      policy_engine.add_rule('PII_BLOCK', block_pii_external_llms, 'block')
      policy_engine.add_rule('HIGH_RISK_LOG', log_high_risk_uses, 'log')
      policy_engine.add_rule('DATA_CLASSIFICATION', enforce_data_classification, 'warn')

      # Initialize integrations (mock keys)
      openai_int = OpenAIIntegration(api_key="sk-mock-openai-key")
      anthropic_int = AnthropicIntegration(api_key="sk-ant-mock-key")

      # Initialize dashboard
      from dashboard.dashboard import MonitoringDashboard
      dashboard = MonitoringDashboard(max_display=50, refresh_rate=0.5)
      dashboard.start()
      dashboard_integration = MonitoringDashboardIntegration(dashboard)

      print("ðŸ”§ TEST 1: OpenAI call with PII (should be BLOCKED)")
      print("-" * 70)
      try:
          response = openai_int.send_message(
              agent_id="support-bot-01",
              model="gpt-4",
              purpose="customer_support",
              messages=[{"role": "user", "content": "What is my SSN 123-45-6789?"}],
              has_pii=True,
              data="Customer SSN: 123-45-6789",
              data_classification="confidential",
              risk_level="medium"
          )
          print("âŒ Should have been blocked!")
      except PolicyViolationError as e:
          print(f"ðŸš« BLOCKED: {e}")
          print(f"   Policy: {e.policy_results}")
      print()

      print("ðŸ”§ TEST 2: Anthropic high-risk call (should be LOGGED + WARN)")
      print("-" * 70)
      response = anthropic_int.send_message(
          agent_id="fraud-detection-bot",
          model="claude-2",
          purpose="fraud_detection",
          messages=[{"role": "user", "content": "Analyze this transaction for fraud"}],
          has_sensitive_data=True,
          risk_level="high",
          data_classification="restricted"
      )
      print(f"âœ… ALLOWED (with warning)")
      print(f"   Policy: {response.get('policy_evaluation', {}).get('policy_explanations', [])}")
      print()

      # Send events to dashboard
      print("Sending events to dashboard...")
      test_event1 = {
          "event_id": "evt-001",
          "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "agent_id": "support-bot-01",
          "provider": "openai",
          "model": "gpt-4",
          "purpose": "customer_support",
          "policy_evaluation": {
              "decision": "block",
              "rules_triggered": ["PII_BLOCK"],
              "policy_explanations": ["PII detected in call"]
          }
      }
      dashboard_integration.receive_event(test_event1)

      test_event2 = {
          "event_id": "evt-002",
          "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "agent_id": "fraud-detection-bot",
          "provider": "anthropic",
          "model": "claude-2",
          "purpose": "fraud_detection",
          "policy_evaluation": {
              "decision": "warn",
              "rules_triggered": ["HIGH_RISK_LOG"],
              "policy_explanations": ["High-risk use case detected"]
          }
      }
      dashboard_integration.receive_event(test_event2)

      # Let dashboard display
      import time
      time.sleep(1)

      dashboard.stop()

      print("\n" + "=" * 70)
      print("DEMONSTRATION COMPLETE")
      print("=" * 70)
