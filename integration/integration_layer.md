 # Policy Engine Integration Layer Design

  ## 1. AI Call Event Schema

  The event schema defines what data gets collected and sent to the policy engine for evaluation. This is the "contract" between AI
  agents and the MCP.

  {
    "event_id": "unique-call-id-12345",
    "timestamp": "2026-09-01T10:30:00Z",
    "agent_id": "internal-ticket-triage-bot",
    "agent_name": "Ticket Triage Bot v2.1",
    "provider": "openai",          // openai, anthropic, google, internal
    "model": "gpt-4",              // specific model identifier
    "purpose": "customer_support", // business purpose category
    "data_classification": "confidential", // public, internal, confidential, restricted
    "has_pii": false,              // boolean flag
    "has_sensitive_data": false,   // boolean flag
    "risk_level": "medium",        // low, medium, high
    "approval_id": null,           // if pre-approved, contains approval ID
    "request_metadata": {
      "request_id": "req-abc-123",
      "user_id": "u-789",
      "session_id": "sess-xyz",
      "ip_address": "192.168.1.45",
      "endpoint": "/api/v1/chat",
      "request_size_bytes": 2048
    },
    "response_metadata": {
      "request_id": "req-abc-123",
      "tokens_used": 150,
      "cost_usd": 0.03,
      "latency_ms": 850,
      "finish_reason": "stop"
    },
    "policy_evaluation": {
      "engine_version": "1.0.0",
      "rules_triggered": ["PII_BLOCK", "HIGH_RISK_LOG"],
      "decision": "allow", // allow, block, warn
      "policy_explanations": [
        "✅ PII check passed - no personal identifiers detected",
        "⚠️ High-risk use case logged for monitoring"
      ],
      "evaluation_timestamp": "2026-09-01T10:30:00.123Z"
    }
  }

  ## 2. How Agents Send Data to the Policy Engine

  The integration pattern follows a pre-flight check model:

  ┌─────────────────────────────────────────────────────────────┐
  │                    AI AGENT REQUEST                         │
  │  ┌─────────────────┐  ┌─────────────────────────────┐       │
  │  │  User/Trigger   │  │  Request Formatter            │       │
  │  └─────────────────┘  └───────┬───────────────────┘       │
  │                              │                             │
  │           ┌──────────────────┴─────────────────┐            │
  │           │  POLICY ENGINE PRE-FLIGHT CHECK    │            │
  │           │  ┌─────────────────────────────┐    │            │
  │           │  │  PolicyEngine.evaluate()    │    │            │
  │           │  │  ← event_schema JSON object │    │            │
  │           │  └───────┬───────────────────┘    │            │
  │           │       │                         │            │
  │           │   ✅   │  PASS: Allow request    │            │
  │           │   ❌   │  BLOCK: Return error    │            │
  │           │   ⚠️   │  WARN: Allow + log      │            │
  │           │       │                         │            │
  │           └───────►│─────────────────────────────┘            │
  │                              │                             │
  │                     ┌────────▼──────────────────┐            │
  │                     │  EXECUTE AI CALL (if allowed)│            │
  │                     └─────────────────────────────┘            │
  │                              │                             │
  │                     ┌────────▼──────────────────┐            │
  │                     │  POST-PROCESSING: Attach       │            │
  │                     │  policy_evaluation to response   │            │
  │                     └─────────────────────────────┘            │
  └─────────────────────────────────────────────────────────────┘

  ## 3. Minimal Integration Layer Design

  ### OpenAI + Anthropic Integration

  """
  Integration Layer Prototype
  Connects OpenAI and Anthropic APIs through the Policy Engine
  """

	"Refer to actual code in 'integration_layer.py'"


 ## 4. Integration Pipeline Summary

  Flow:

  1. Agent prepares AI call request with contextual metadata
  2. AICallContext builds the event schema JSON
  3. PolicyEngine.evaluate() runs rules against the event
  4. Decision made: allow, block, or warn
  5. If allowed: execute actual API call (OpenAI/Anthropic)
  6. Post-processing: attach policy evaluation to response
  7. All events logged for audit trail

  Key Design Decisions:

  - Pre-flight check: Policy evaluation happens BEFORE API call
  - Schema-first: Event structure is defined and validated before processing
  - Rule-action system: Each rule can have different actions (block/log/warn/allow)
  - Human-readable explanations: Policy decisions include explanations for transparency
  - Modular: Easy to add new providers (Google, internal models) by following the same pattern

  # This integration layer design implements the MVP scope we agreed on: core policy engine + minimal integration with OpenAI + Anthropic, with a basic dashboard-ready data output.
