
  # ============================================================
  # Demonstration & Testing
  # ============================================================
import sys, os
import time
from datetime import datetime, timezone, timedelta

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from usage_tracker import UsageTracker
from datetime import timezone

if __name__ == "__main__":
      print("=" * 70)
      print("USAGE TRACKER PRODUCTION HARDENING DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize usage tracker
      tracker = UsageTracker(storage_path="usage_tracker.jsonl")

      # Track some sample events
      print("Tracking sample AI calls...\n")

      event1 = tracker.track_usage(
          tokens_used=1500,
          cost_usd=0.045,
          latency_ms=850,
          agent_id="support-bot-01",
          provider="openai",
          model="gpt-4",
          purpose="customer_support",
          user_id="user-123",
          session_id="sess-abc"
      )
      print(f"Event 1 tracked: {event1.event_id} - {event1.provider} {event1.model}")

      event2 = tracker.track_usage(
          tokens_used=2000,
          cost_usd=0.06,
          latency_ms=1200,
          agent_id="fraud-detector-01",
          provider="anthropic",
          model="claude-2",
          purpose="fraud_detection",
          user_id="user-456",
          session_id="sess-def"
      )
      print(f"Event 2 tracked: {event2.event_id} - {event2.provider} {event2.model}")

      event3 = tracker.track_usage(
          tokens_used=1000,
          cost_usd=0.03,
          latency_ms=600,
          agent_id="support-bot-01",
          provider="openai",
          model="gpt-4",
          purpose="customer_support",
          user_id="user-789",
          session_id="sess-ghi"
      )
      print(f"Event 3 tracked: {event3.event_id} - {event3.provider} {event3.model}")

      # Get usage summary
      print("\nUsage summary:")
      summary = tracker.get_usage_summary()
      for key, value in summary.items():
          print(f"  {key}: {value}")

      # Get cost summary
      print("\nCost summary:")
      cost_summary = tracker.get_cost_summary()
      for key, value in cost_summary.items():
          if key != 'time_range':
              print(f"  {key}: {value}")

      # Get agent usage
      print("\nAgent usage (support-bot-01):")
      agent_usage = tracker.get_agent_usage("support-bot-01")
      for key, value in agent_usage.items():
          print(f"  {key}: {value}")

      # Get daily rollup
      print("\nDaily rollup (2024-01-15):")
      daily = tracker.get_daily_rollup("2024-01-15")
      if daily:
          for key, value in daily.items():
              print(f"  {key}: {value}")
      else:
          print("  No data for this date")

      # Get statistics
      print("\nOverall statistics:")
      stats = tracker.get_statistics()
      for key, value in stats.items():
          if isinstance(value, dict):
              print(f"  {key}: {len(value)} items")
          else:
              print(f"  {key}: {value}")

      print("\n" + "=" * 70)
      print("DEMONSTRATION COMPLETE")
      print("=" * 70)
