
  # ============================================================
  # Demo / Test Code
  # ============================================================

if __name__ == "__main__":
      print("=" * 70)
      print("MCP CONTROL-TOWER ORCHESTRATOR PRODUCTION HARDENING DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize orchestrator
      print("Initializing MCP Orchestrator...")
      orchestrator = MCPOrchestrator(
          openai_api_key="sk-mock-openai-key",
          anthropic_api_key="sk-ant-mock-key"
      )
      print("  Policy Engine: active")
      print(f"  OpenAI integration: {'ready' if orchestrator._openai_integration else 'not configured'}")
      print(f"  Anthropic integration: {'ready' if orchestrator._anthropic_integration else 'not configured'}")
      print(f"  Audit Logger: active")
      print(f"  Monitoring Dashboard: active")
      print(f"  Agent Registry: active")
      print(f"  Provider Config: active")
      print(f"  Usage Tracker: active")
      print()

      # Test 1: Blocked call with PII
      print("Test 1: OpenAI call with PII (should be BLOCKED)")
      print("-" * 70)
      try:
          response = orchestrator.execute_ai_call(
              agent_id="support-bot-01",
              provider="openai",
              model="gpt-4",
              purpose="customer_support",
              messages=[{"role": "user", "content": "What is my SSN 123-45-6789?"}],
              has_pii=True,
              data="Customer SSN: 123-45-6789",
              data_classification="confidential",
              risk_level="medium",
              request_id="req-test-001",
              user_id="user-123",
              session_id="sess-abc",
              endpoint="/mcp/test"
          )
          print("Should have been blocked!")
      except PolicyViolationError as e:
          print(f"BLOCKED: {e}")
      print()

      # Test 2: Allowed call
      print("Test 2: OpenAI call without PII (should be ALLOWED)")
      print("-" * 70)
      try:
          response = orchestrator.execute_ai_call(
              agent_id="support-bot-01",
              provider="openai",
              model="gpt-4",
              purpose="code_generation",
              messages=[{"role": "user", "content": "Write a Python function to sort a list"}],
              has_pii=False,
              has_sensitive_data=False,
              risk_level="low",
              data_classification="internal",
              request_id="req-test-002",
              user_id="user-123",
              session_id="sess-abc",
              endpoint="/mcp/test"
          )
          print(f"ALLOWED - Decision: {response.get('policy_evaluation', {}).get('decision', 'N/A')}")
          print(f"AI Response: {response.get('ai_response', {}).get('choices', [{}])[0].get('message', {}).get('content', 'N/A')[:50]}...")
      except PolicyViolationError as e:
          print(f"BLOCKED: {e}")
      print()

      # Test 3: Warning call
      print("Test 3: Anthropic high-risk call (should be WARN + LOG)")
      print("-" * 70)
      try:
          response = orchestrator.execute_ai_call(
              agent_id="fraud-detector-01",
              provider="anthropic",
              model="claude-2",
              purpose="fraud_detection",
              messages=[{"role": "user", "content": "Analyze this transaction for fraud"}],
              has_sensitive_data=True,
              risk_level="high",
              data_classification="restricted",
              request_id="req-test-003",
              user_id="user-456",
              session_id="sess-def",
              endpoint="/mcp/test"
          )
          print(f"ALLOWED WITH WARNING - Decision: {response.get('policy_evaluation', {}).get('decision', 'N/A')}")
          print(f"Policy Explanations: {response.get('policy_evaluation', {}).get('policy_explanations', [])}")
      except PolicyViolationError as e:
          print(f"BLOCKED: {e}")
      print()

      print("=" * 70)
      print("DEMONSTRATION COMPLETE")
      print("=" * 70)
