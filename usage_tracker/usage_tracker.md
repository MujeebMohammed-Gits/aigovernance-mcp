
  ## UsageTracker Design

  UsageEvent Dataclass - Core metrics for each AI call:

   Field          Type     Description
  ━━━━━━━━━━━━━  ━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   event_id       str      Unique identifier
  ─────────────  ───────  ────────────────────────────
   timestamp      str      ISO format UTC
  ─────────────  ───────  ────────────────────────────
   tokens_used    int      Number of tokens consumed
  ─────────────  ───────  ────────────────────────────
   cost_usd       float    Cost in USD
  ─────────────  ───────  ────────────────────────────
   latency_ms     int      Latency in milliseconds
  ─────────────  ───────  ────────────────────────────
   agent_id       str      Agent identifier
  ─────────────  ───────  ────────────────────────────
   provider       str      LLM provider
  ─────────────  ───────  ────────────────────────────
   model          str      Model identifier
  ─────────────  ───────  ────────────────────────────
   purpose        str      Business purpose
  ─────────────  ───────  ────────────────────────────
   metadata       Dict     Additional key-value pairs

  Tracking Dimensions:

  - Per-agent (_agent_index)
  - Per-provider (_provider_index)
  - Per-model (_model_index)
  - Per-purpose (_purpose_index)

  Rollup Summaries:

  - Daily (_daily_rollup) - keyed by YYYY-MM-DD
  - Weekly (_weekly_rollup) - keyed by ISO week (YYYY-WWW)
  - Monthly (_monthly_rollup) - keyed by YYYY-MM

  Tracker Methods:

   Method                  Purpose
  ━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   track_usage()           Record a single AI call usage event
  ──────────────────────  ────────────────────────────────────────────────
   get_usage_summary()     Overall usage summary (tokens, cost, latency)
  ──────────────────────  ────────────────────────────────────────────────
   get_cost_summary()      Cost breakdown by agent/provider/model/purpose
  ──────────────────────  ────────────────────────────────────────────────
   get_agent_usage()       Usage summary for specific agent
  ──────────────────────  ────────────────────────────────────────────────
   get_daily_rollup()      Daily summary for a specific date
  ──────────────────────  ────────────────────────────────────────────────
   get_weekly_rollup()     Weekly summary for a specific ISO week
  ──────────────────────  ────────────────────────────────────────────────
   get_monthly_rollup()    Monthly summary for a specific YYYY-MM
  ──────────────────────  ────────────────────────────────────────────────
   get_statistics()        Overall statistics with top N by dimensions

  Date Filtering:

  - _get_events_in_range() - Filter events by start/end date
  - _is_in_date_range() - Check single event against date range
  - Supports inclusive/exclusive boundary handling

  Integration Points:

  1. MCP Orchestrator Integration (record_orchestrator_call):
      - Extracts metrics from execute_ai_call() unified response
      - Captures: tokens used, cost, latency, agent/provider/model/purpose
      - Automatic cost calculation from tokens using pricing config
      - Estimates latency from policy evaluation execution time
      - Stores additional context: policy decision, routing info

  2. Usage Event Extraction from orchestrator response:
      - ai_response.usage.total_tokens → tokens_used
      - policy_evaluation.cost_usd or calculated from tokens → cost_usd
      - policy_evaluation.execution_time_ms → latency_ms
      - event_schema fields → dimensional tracking

  3. Cost Calculation (_calculate_cost_from_tokens):
      - Uses pricing dictionary: (provider, model) → price per 1K tokens
      - Default fallbacks for unknown providers/models
      - Rounded to 6 decimal places for precision

  4. Latency Estimation (_estimate_latency):
      - Returns default 500ms if not provided
      - In production would use actual API response latency

  Persistence:

  - JSONL file-based (usage_tracker.jsonl)
  - Automatic append on each track_usage() call
  - Load on initialization
  - All events stored in memory (_events list) for fast querying

  Usage Example:

  from usage_tracker import UsageTracker

  # Initialize tracker
  tracker = UsageTracker()

  # Track usage from AI call
  event = tracker.track_usage(
      tokens_used=150,
      cost_usd=0.0045,
      latency_ms=850,
      agent_id="support-bot-01",
      provider="openai",
      model="gpt-4",
      purpose="customer_support"
  )

  # Get summaries
  summary = tracker.get_usage_summary()
  cost_summary = tracker.get_cost_summary()
  agent_usage = tracker.get_agent_usage("support-bot-01")

  # Get rollups
  daily = tracker.get_daily_rollup("2026-09-03")
  weekly = tracker.get_weekly_rollup("2026-35")  # ISO week
  monthly = tracker.get_monthly_rollup("2026-09")

  # Record from orchestrator
  orchestrator_response = {...}  # From execute_ai_call()
  tracker.record_orchestrator_call(orchestrator_response, event_schema)

  Usage Flow Integration:

  AI Call Executed
       ↓
  MCP Orchestrator returns unified response
       ↓
  UsageTracker.record_orchestrator_call() extracts metrics
       ↓
  Event stored in JSONL + indexes updated
       ↓
  Rollups updated (daily/weekly/monthly)
       ↓
  Queries available via get_* methods
       ↓
  Dashboard displays real-time stats
       ↓
  Audit log captures full event history
