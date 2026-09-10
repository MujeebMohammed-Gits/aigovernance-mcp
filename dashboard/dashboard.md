 ## Dashboard Features

  Display Components:

  1. Live Event Stream - Shows recent AI call events with provider, purpose, and policy decision
  2. Decision Icons - Visual indicators (✅ allow, 🚫 block, ⚠️ warn)
  3. Triggered Rules - Lists which policy rules were activated
  4. Policy Explanations - Human-readable explanations for each decision
  5. Summary Statistics - Total calls, allow/block/warn counts with percentages
  6. Top Rules - Most frequently triggered rules with counts

  Design Highlights:

  - Console-based: No frontend framework required - works in any terminal
  - Real-time updating: Background thread refreshes display at configurable rate
  - Event schema compatible: Accepts the same event format from the integration layer
  - Statistics tracking: Automatic counting of decisions and rules
  - Thread-safe: Uses deque with maxlen for memory-efficient event history
  - Graceful start/stop: Clean initialization and termination

  Compatibility:

  - Receives events in the same format as the integration layer prototype
  - Decision types: allow, block, warn
  - Rule names: PII_BLOCK, HIGH_RISK_LOG, DATA_CLASSIFICATION, etc.
  - Explanations: Human-readable strings with emoji icons

  Usage:

  from dashboard import MonitoringDashboard

  dashboard = MonitoringDashboard()
  dashboard.start()

  # Receive events from integration layer
  dashboard.receive_event(ai_call_event)

  # Stop when finished
  dashboard.stop()

  # This dashboard prototype completes the MVP triad: policy engine → integration layer → monitoring dashboard, providing a fully functional (though minimal) governance system for AI call management.
