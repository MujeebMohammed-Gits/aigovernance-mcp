
  ## AuditLogger Design

  Storage Format: JSONL (JSON Lines)

  - Each line in the file is a complete, self-contained JSON object
  - Efficient for appending and sequential reading
  - No database required - pure file-based storage
  - Human-readable and easily inspectable

  Class Methods:

   Method                              Description
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   __init__(log_file_path)             Initialize logger with specified log file
  ──────────────────────────────────  ───────────────────────────────────────────
   add_event(event)                    Append a single event to the JSONL file
  ──────────────────────────────────  ───────────────────────────────────────────
   get_all_events()                    Retrieve all events from the log
  ──────────────────────────────────  ───────────────────────────────────────────
   get_events_by_decision(decision)    Filter events by policy decision
  ──────────────────────────────────  ───────────────────────────────────────────
   get_events_by_rule(rule)            Filter events by triggered rule
  ──────────────────────────────────  ───────────────────────────────────────────
   get_event_count()                   Get total number of logged events
  ──────────────────────────────────  ───────────────────────────────────────────
   get_decision_statistics()           Get decision distribution statistics
  ──────────────────────────────────  ───────────────────────────────────────────
   get_rule_statistics()               Get rule trigger frequency statistics

  Event Schema Inclusion:
  Each stored event includes:

  - Original event schema fields (event_id, timestamp, agent_id, provider, model, purpose, etc.)
  - Policy evaluation results (decision, rules_triggered, policy_explanations)
  - Logging metadata (log_entry_id, logged_at)

  Query Capabilities:

  1. get_all_events() - Returns full event history
  2. get_events_by_decision('allow'/'block'/'warn') - Filters by final policy decision
  3. get_events_by_rule('PII_BLOCK'/'HIGH_RISK_LOG'/'DATA_CLASSIFICATION') - Filters by which rules were triggered

  Statistics Available:

  - Decision distribution (allow/block/warn counts)
  - Rule trigger frequencies (which policies are most active)
  - Total event count

  Usage Example:

  from audit_logger import AuditLogger

  # Initialize logger
  logger = AuditLogger("my_audit_log.jsonl")

  # Receive events from integration layer
  logger.add_event(ai_call_event)

  # Query logged events
  all_events = logger.get_all_events()
  blocked = logger.get_events_by_decision('block')
  pii_cases = logger.get_events_by_rule('PII_BLOCK')

  # Get analytics
  stats = logger.get_decision_statistics()
  rule_stats = logger.get_rule_statistics()

  # This audit_logger module completes the full MVP stack: policy engine → integration layer → monitoring dashboard → audit logging, providing persistent storage and query capabilities for the entire AI governance system.
