
  ## MCP Orchestrator Design

  Core Function: execute_ai_call(agent_id, provider, model, purpose, messages, **metadata)

  This single unified function orchestrates the complete AI call governance flow:

  ### Flow Summary

   Step    Action                               Component
  ━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   1       Build event schema                   AICallContext → event dict
  ──────  ───────────────────────────────────  ────────────────────────────────────────────────
   2       Policy evaluation (pre‑flight)       PolicyEngine.evaluate()
  ──────  ───────────────────────────────────  ────────────────────────────────────────────────
   3       Decision: allow/block/warn           Based on rule triggers
  ──────  ───────────────────────────────────  ────────────────────────────────────────────────
   4       If allowed: execute AI call          OpenAIIntegration or AnthropicIntegration
  ──────  ───────────────────────────────────  ────────────────────────────────────────────────
   5       Send event to MonitoringDashboard    MonitoringDashboard.receive_event()
  ──────  ───────────────────────────────────  ────────────────────────────────────────────────
   6       Log event to AuditLogger             AuditLogger.add_event()
  ──────  ───────────────────────────────────  ────────────────────────────────────────────────
   7       Return unified response              {ai_response, policy_evaluation, event_schema}

  ### Decision Logic

   Trigger                       Decision    Action
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   No rules triggered            allow       Proceed with AI call
  ────────────────────────────  ──────────  ─────────────────────────────────────────
   PII_BLOCK rule matches        block       Reject call, raise PolicyViolationError
  ────────────────────────────  ──────────  ─────────────────────────────────────────
   HIGH_RISK_LOG rule matches    warn        Allow but flag for review
  ────────────────────────────  ──────────  ─────────────────────────────────────────
   Both block and warn           block       Priority to block

  ### Unified Response Object

  {
    "ai_response": {
      "id": "chatcmpl-123",
      "object": "chat.completion",
      "created": 1234567890,
      "model": "gpt-4",
      "choices": [{
        "index": 0,
        "message": {"role": "assistant", "content": "..."},
        "finish_reason": "stop"
      }],
      "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60}
    },
    "policy_evaluation": {
      "decision": "allow",
      "rules_triggered": [],
      "policy_explanations": ["✅ No policy violations detected"],
      "execution_time_ms": 850,
      "api_provider": "openai",
      "model": "gpt-4",
      "tokens_used": 60,
      "cost_usd": 0.03
    },
    "event_schema": {
      "event_id": "evt-12345",
      "timestamp": "2026-09-02T10:30:00Z",
      "agent_id": "support-bot-01",
      "provider": "openai",
      "model": "gpt-4",
      "purpose": "customer_support",
      "data_classification": "confidential",
      "has_pii": false,
      "has_sensitive_data": false,
      "risk_level": "medium",
      "policy_evaluation": { ... },
      "ai_response": { ... },
      "logged_at": "2026-09-02T10:30:00.123456Z",
      "log_entry_id": "entry-1234567890"
    }
  }

  ### Error Handling

  PolicyViolationError is raised when:

  - PII detected in external LLM call without approval
  - Any block-level rule triggers
  - Custom business rules prevent the call

  The error contains:

  - Human-readable message explaining the violation
  - policy_results list with detailed rule information
  - Can be caught and handled by calling code

  ### Initialization

  from mcp_service import init_mcp_service, execute_ai_call

  # Initialize with API keys
  init_mcp_service(
      openai_api_key="sk-live-openai-key",
      anthropic_api_key="sk-live-anthropic-key"
  )

  ### Usage Example

  # Execute a governed AI call
  response = execute_ai_call(
      agent_id="customer-support-bot",
      provider="openai",
      model="gpt-4",
      purpose="customer_support",
      messages=[{"role": "user", "content": "Can I change my password?"}],
      data_classification="confidential",
      has_pii=False,
      has_sensitive_data=False,
      risk_level="low",
      request_id="req-001",
      user_id="u-12345"
  )

  # Access results
  ai_output = response['ai_response']
  policy = response['policy_evaluation']
  event = response['event_schema']

  print(f"Decision: {policy['decision']}")
  print(f"Rules: {', '.join(policy.get('rules_triggered', []))}")
  print(f"Tokens: {policy.get('tokens_used', 0)}")

  # This orchestrator module completes the full MCP Control‑Tower stack, providing the unified entry point that coordinates all prototypes into a functional AI governance system.
