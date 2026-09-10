  ## Design Notes

  Rules Implemented:

  1. PII_BLOCK - Blocks external LLM calls (OpenAI, Anthropic, Google) containing PII unless explicitly approved
  2. HIGH_RISK_LOG - Logs high-risk use cases (fraud detection, medical diagnosis, financial decisions, etc.) with extra metadata
  3. DATA_CLASSIFICATION - Enforces data classification policies, warns on restricted/confidential data access

  Actions:

  - block: Reject the AI call and return policy violation message
  - log: Record the call with enhanced metadata for audit trail
  - warn: Allow the call but flag it for review and notification

  Test Scenarios (matching our design discussion):

  - OpenAI call with PII for customer support → BLOCK (PII rule)
  - Anthropic call for document analysis (high-risk) → LOG + WARN
  - OpenAI call for code generation (no PII, low-risk) → ALLOW
  - Google call for fraud detection (high-risk) → LOG (high-risk rule)

  # This prototype demonstrates the core policy evaluation engine that was agreed upon in our design discussion, providing the
  foundation for the MVP we'll be building next.