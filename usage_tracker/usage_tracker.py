
  # -*- coding: utf-8 -*-
"""
    Usage & Cost Tracker Production Hardened
    Tracks AI call metrics including tokens, cost, latency, and provides rollup summaries
    Thread-safe with JSONL persistence and structured validation
"""
import json
import os
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
from dataclasses import dataclass, asdict


  # Configure structured logger
logger = logging.getLogger('mcp_usage_tracker')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

  # Thread lock for concurrent access
_usage_lock = threading.Lock()


  # ============================================================
  # UsageEvent Dataclass
  # ============================================================

@dataclass
class UsageEvent:
      """Dataclass representing a single AI call usage event."""
      event_id: str
      timestamp: str  # ISO format UTC

      # Core metrics
      tokens_used: int
      cost_usd: float
      latency_ms: int

      # Dimensional tracking
      agent_id: str
      provider: str
      model: str
      purpose: str

      # Additional metadata
      metadata: Dict[str, Any] = None

      def to_dict(self) -> dict:
          """Convert to dictionary for serialization."""
          return asdict(self)

      @classmethod
      def from_dict(cls, data: dict) -> 'UsageEvent':
          """Create from dictionary."""
          return cls(**data)


  # ============================================================
  # UsageTracker Class
  # ============================================================

class UsageTracker:
      """
      Tracks AI call usage metrics including tokens, cost, and latency.
      Supports per-agent, per-provider, per-model, and per-purpose tracking
      with daily/weekly/monthly rollup summaries.
      Thread-safe with JSONL persistence.
      """

      def __init__(self, storage_path: str = "usage_tracker.jsonl"):
          self.storage_path = storage_path
          self._events: List[UsageEvent] = []
          self._index: Dict[str, List[int]] = defaultdict(list)  # event_id -> indices
          self._agent_index: Dict[str, List[int]] = defaultdict(list)  # agent_id -> indices
          self._provider_index: Dict[str, List[int]] = defaultdict(list)  # provider -> indices
          self._model_index: Dict[str, List[int]] = defaultdict(list)  # model -> indices
          self._purpose_index: Dict[str, List[int]] = defaultdict(list)  # purpose -> indices
          self._daily_rollup: Dict[str, Dict] = defaultdict(lambda: {
              'tokens': 0, 'cost': 0.0, 'calls': 0, 'latency': 0
          })
          self._weekly_rollup: Dict[str, Dict] = defaultdict(lambda: {
              'tokens': 0, 'cost': 0.0, 'calls': 0, 'latency': 0
          })
          self._monthly_rollup: Dict[str, Dict] = defaultdict(lambda: {
              'tokens': 0, 'cost': 0.0, 'calls': 0, 'latency': 0
          })
          self._load_from_disk()

      def _load_from_disk(self):
          """Load events from persistent JSONL storage."""
          try:
              if not os.path.exists(self.storage_path):
                  return
              with _usage_lock:
                  with open(self.storage_path, 'r', encoding='utf-8') as f:
                      for line_num, line in enumerate(f, 1):
                          line = line.strip()
                          if not line:
                              continue
                          try:
                              data = json.loads(line)
                              event = UsageEvent.from_dict(data)
                              self._add_event_to_indexes(event)
                          except (json.JSONDecodeError, KeyError) as e:
                              logger.warning(f"Skipping malformed usage event at line {line_num}: {e}")
          except IOError as e:
              logger.error(f"Could not load usage tracker from {self.storage_path}: {e}")

      def _add_event_to_indexes(self, event: UsageEvent):
          """Add event to all tracking indexes and rollups."""
          with _usage_lock:
              # Add to main events list
              self._events.append(event)
              event_idx = len(self._events) - 1
              self._index[event.event_id].append(event_idx)

              # Index by dimensions
              self._agent_index[event.agent_id].append(event_idx)
              self._provider_index[event.provider].append(event_idx)
              self._model_index[event.model].append(event_idx)
              self._purpose_index[event.purpose].append(event_idx)

              # Update rollups
              self._update_rollups(event)

              # Persist to disk
              self._persist_event(event)

      def _update_rollups(self, event: UsageEvent):
          """Update daily/weekly/monthly rollup summaries."""
          with _usage_lock:
              # Parse timestamp
              try:
                  ts = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
              except (ValueError, AttributeError):
                  ts = datetime.now(timezone.utc)

              # Daily rollup key (YYYY-MM-DD)
              daily_key = ts.strftime('%Y-%m-%d')
              self._daily_rollup[daily_key]['tokens'] += event.tokens_used
              self._daily_rollup[daily_key]['cost'] += event.cost_usd
              self._daily_rollup[daily_key]['calls'] += 1
              self._daily_rollup[daily_key]['latency'] += event.latency_ms

              # Weekly rollup key (ISO week year-week)
              week_key = ts.strftime('%G-W%V')
              self._weekly_rollup[week_key]['tokens'] += event.tokens_used
              self._weekly_rollup[week_key]['cost'] += event.cost_usd
              self._weekly_rollup[week_key]['calls'] += 1
              self._weekly_rollup[week_key]['latency'] += event.latency_ms

              # Monthly rollup key (YYYY-MM)
              monthly_key = ts.strftime('%Y-%m')
              self._monthly_rollup[monthly_key]['tokens'] += event.tokens_used
              self._monthly_rollup[monthly_key]['cost'] += event.cost_usd
              self._monthly_rollup[monthly_key]['calls'] += 1
              self._monthly_rollup[monthly_key]['latency'] += event.latency_ms

      def _persist_event(self, event: UsageEvent):
          """Append event to JSONL file with atomic write."""
          with _usage_lock:
              try:
                  temp_path = self.storage_path + '.tmp'
                  # Read existing data, append new event, write to temp, then replace
                  events = []
                  if os.path.exists(self.storage_path):
                      with open(self.storage_path, 'r', encoding='utf-8') as f:
                          for line in f:
                              line = line.strip()
                              if line:
                                  events.append(line)

                  events.append(json.dumps(event.to_dict(), ensure_ascii=False))

                  with open(temp_path, 'w', encoding='utf-8') as f:
                      for ev in events:
                          f.write(ev + '\n')

                  os.replace(temp_path, self.storage_path)
              except IOError as e:
                  logger.error(f"Could not persist usage event to disk: {e}")

      # ==========================================================
      # Core Tracking Operations
      # ==========================================================

      def track_usage(self, tokens_used: int, cost_usd: float, latency_ms: int,
                      agent_id: str, provider: str, model: str, purpose: str,
                      **metadata) -> UsageEvent:
          """Track a single AI call usage event."""
          with _usage_lock:
              event_id = f"evt-{int(time.time() * 1000) - len(self._events)}"
              timestamp = datetime.now(timezone.utc).isoformat()

              event = UsageEvent(
                  event_id=event_id,
                  timestamp=timestamp,
                  tokens_used=tokens_used,
                  cost_usd=cost_usd,
                  latency_ms=latency_ms,
                  agent_id=agent_id,
                  provider=provider,
                  model=model,
                  purpose=purpose,
                  metadata=metadata or {}
              )

              # Index in memory and persist
              self._add_event_to_indexes(event)

              return event

      # ==========================================================
      # Query Operations
      # ==========================================================

      def get_usage_summary(self,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> dict:
          """Get overall usage summary."""
          with _usage_lock:
              events = self._get_events_in_range(start_date, end_date)

              if not events:
                  return {
                      'total_calls': 0,
                      'total_tokens': 0,
                      'total_cost': 0.0,
                      'average_latency_ms': 0,
                      'time_range': {'start': start_date, 'end': end_date}
                  }

              total_tokens = sum(e.tokens_used for e in events)
              total_cost = sum(e.cost_usd for e in events)
              total_latency = sum(e.latency_ms for e in events)
              avg_latency = total_latency / len(events) if events else 0

              # Determine time range
              timestamps = [datetime.fromisoformat(e.timestamp.replace('Z', '+00:00')) for e in events]
              range_start = min(ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps)
              range_end = max(ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps)

              return {
                  'total_calls': len(events),
                  'total_tokens': total_tokens,
                  'total_cost': round(total_cost, 4),
                  'average_latency_ms': round(avg_latency, 2),
                  'time_range': {'start': range_start, 'end': range_end}
              }

      def get_cost_summary(self,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> dict:
          """Get cost summary by dimensions."""
          with _usage_lock:
              events = self._get_events_in_range(start_date, end_date)

              if not events:
                  return {
                      'total_cost': 0.0,
                      'by_agent': {},
                      'by_provider': {},
                      'by_model': {},
                      'by_purpose': {},
                      'time_range': {'start': start_date, 'end': end_date}
                  }

              # By agent
              by_agent = defaultdict(float)
              # By provider
              by_provider = defaultdict(float)
              # By model
              by_model = defaultdict(float)
              # By purpose
              by_purpose = defaultdict(float)

              for event in events:
                  by_agent[event.agent_id] += event.cost_usd
                  by_provider[event.provider] += event.cost_usd
                  by_model[event.model] += event.cost_usd
                  by_purpose[event.purpose] += event.cost_usd

              # Sort by cost (descending)
              by_agent = dict(sorted(by_agent.items(), key=lambda x: x[1], reverse=True))
              by_provider = dict(sorted(by_provider.items(), key=lambda x: x[1], reverse=True))
              by_model = dict(sorted(by_model.items(), key=lambda x: x[1], reverse=True))
              by_purpose = dict(sorted(by_purpose.items(), key=lambda x: x[1], reverse=True))

              return {
                  'total_cost': round(sum(e.cost_usd for e in events), 4),
                  'by_agent': {k: round(v, 4) for k, v in by_agent.items()},
                  'by_provider': {k: round(v, 4) for k, v in by_provider.items()},
                  'by_model': {k: round(v, 4) for k, v in by_model.items()},
                  'by_purpose': {k: round(v, 4) for k, v in by_purpose.items()},
                  'time_range': {'start': start_date, 'end': end_date}
              }

      def get_agent_usage(self, agent_id: str,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> dict:
          """Get usage summary for a specific agent."""
          with _usage_lock:
              # Get event indices for this agent
              agent_indices = self._agent_index.get(agent_id, [])

              # Filter by date range if provided
              events = []
              for idx in agent_indices:
                  event = self._events[idx]
                  if self._is_in_date_range(event.timestamp, start_date, end_date):
                      events.append(event)

              if not events:
                  return {
                      'agent_id': agent_id,
                      'total_calls': 0,
                      'total_tokens': 0,
                      'total_cost': 0.0,
                      'average_latency_ms': 0,
                      'provider_breakdown': {},
                      'model_breakdown': {},
                      'purpose_breakdown': {}
                  }

              total_tokens = sum(e.tokens_used for e in events)
              total_cost = sum(e.cost_usd for e in events)
              total_latency = sum(e.latency_ms for e in events)
              avg_latency = total_latency / len(events)

              # Breakdown by provider
              by_provider = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})
              by_model = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})
              by_purpose = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})

              for event in events:
                  by_provider[event.provider]['tokens'] += event.tokens_used
                  by_provider[event.provider]['cost'] += event.cost_usd
                  by_provider[event.provider]['calls'] += 1

                  by_model[event.model]['tokens'] += event.tokens_used
                  by_model[event.model]['cost'] += event.cost_usd
                  by_model[event.model]['calls'] += 1

                  by_purpose[event.purpose]['tokens'] += event.tokens_used
                  by_purpose[event.purpose]['cost'] += event.cost_usd
                  by_purpose[event.purpose]['calls'] += 1

              # Convert defaultdicts to regular dicts
              provider_breakdown = {
                  k: {'tokens': v['tokens'], 'cost': round(v['cost'], 4), 'calls': v['calls']}
                  for k, v in by_provider.items()
              }
              model_breakdown = {
                  k: {'tokens': v['tokens'], 'cost': round(v['cost'], 4), 'calls': v['calls']}
                  for k, v in by_model.items()
              }
              purpose_breakdown = {
                  k: {'tokens': v['tokens'], 'cost': round(v['cost'], 4), 'calls': v['calls']}
                  for k, v in by_purpose.items()
              }

              return {
                  'agent_id': agent_id,
                  'total_calls': len(events),
                  'total_tokens': total_tokens,
                  'total_cost': round(total_cost, 4),
                  'average_latency_ms': round(avg_latency, 2),
                  'provider_breakdown': provider_breakdown,
                  'model_breakdown': model_breakdown,
                  'purpose_breakdown': purpose_breakdown
              }

      def get_daily_rollup(self, date_str: str) -> Optional[dict]:
          """Get daily usage rollup for a specific date."""
          with _usage_lock:
              if date_str in self._daily_rollup:
                  rollup = self._daily_rollup[date_str]
                  return {
                      'date': date_str,
                      'total_calls': rollup['calls'],
                      'total_tokens': rollup['tokens'],
                      'total_cost': round(rollup['cost'], 4),
                      'average_latency_ms': round(rollup['latency'] / max(rollup['calls'], 1), 2)
                  }
              return None

      def get_weekly_rollup(self, week_str: str) -> Optional[dict]:
          """Get weekly usage rollup for a specific week."""
          with _usage_lock:
              if week_str in self._weekly_rollup:
                  rollup = self._weekly_rollup[week_str]
                  return {
                      'week': week_str,
                      'total_calls': rollup['calls'],
                      'total_tokens': rollup['tokens'],
                      'total_cost': round(rollup['cost'], 4),
                      'average_latency_ms': round(rollup['latency'] / max(rollup['calls'], 1), 2)
                  }
              return None

      def get_monthly_rollup(self, month_str: str) -> Optional[dict]:
          """Get monthly usage rollup for a specific month."""
          with _usage_lock:
              if month_str in self._monthly_rollup:
                  rollup = self._monthly_rollup[month_str]
                  return {
                      'month': month_str,
                      'total_calls': rollup['calls'],
                      'total_tokens': rollup['tokens'],
                      'total_cost': round(rollup['cost'], 4),
                      'average_latency_ms': round(rollup['latency'] / max(rollup['calls'], 1), 2)
                  }
              return None

      # ==========================================================
      # Date Range Filtering
      # ==========================================================

      def _get_events_in_range(self, start_date: Optional[str], end_date: Optional[str]) -> List[UsageEvent]:
          """Get events within date range."""
          with _usage_lock:
              if not self._events:
                  return []

              # Parse date boundaries
              start_ts = None
              end_ts = None

              if start_date:
                  try:
                      start_ts = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                  except ValueError:
                      start_ts = None

              if end_date:
                  try:
                      end_ts = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                      # End is inclusive, so add one day
                      end_ts = end_ts + timedelta(days=1)
                  except ValueError:
                      end_ts = None

              # Filter events
              filtered = []
              for event in self._events:
                  try:
                      event_ts = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))

                      if start_ts and event_ts < start_ts:
                          continue
                      if end_ts and event_ts > end_ts:
                          continue

                      filtered.append(event)
                  except (ValueError, AttributeError):
                      continue

              return filtered

      def _is_in_date_range(self, timestamp: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
          """Check if a single timestamp is within date range."""
          with _usage_lock:
              try:
                  event_ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                  if start_date:
                      start_ts = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                      if event_ts < start_ts:
                          return False

                  if end_date:
                      end_ts = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                      # Make end inclusive end of day
                      end_ts_end = end_ts + timedelta(days=1)
                      if event_ts >= end_ts_end:
                          return False

                  return True
              except (ValueError, AttributeError):
                  return False

      # ==========================================================
      # Integration Points
      # ==========================================================

      def record_orchestrator_call(self,
                                    orchestrator_response: dict,
                                    event_schema: dict) -> Optional[UsageEvent]:
          """Record usage from an MCP Orchestrator call."""
          with _usage_lock:
              try:
                  ai_response = orchestrator_response.get('ai_response', {})
                  policy_evaluation = orchestrator_response.get('policy_evaluation', {})
                  event_schema_data = orchestrator_response.get('event_schema', {})

                  # Extract metrics from AI response
                  usage = ai_response.get('usage', {})
                  tokens_used = usage.get('total_tokens', 0)

                  # Extract cost - could be from policy evaluation or calculated
                  cost_usd = policy_evaluation.get('cost_usd',
                      self._calculate_cost_from_tokens(tokens_used, event_schema_data))

                  # Latency
                  latency_ms = policy_evaluation.get('execution_time_ms',
                      self._estimate_latency(event_schema_data))

                  # Determine tracking dimensions from event schema
                  agent_id = event_schema_data.get('agent_id', 'unknown')
                  provider = event_schema_data.get('provider', 'unknown')
                  model = event_schema_data.get('model', 'unknown')
                  purpose = event_schema_data.get('purpose', 'unknown')

                  # Create usage event
                  event = self.track_usage(
                      tokens_used=tokens_used,
                      cost_usd=cost_usd,
                      latency_ms=latency_ms,
                      agent_id=agent_id,
                      provider=provider,
                      model=model,
                      purpose=purpose,
                      **{'orchestrator_event_id': event_schema_data.get('event_id'),
                         'policy_decision': policy_evaluation.get('decision'),
                         'routing_info': policy_evaluation.get('routing_info')}
                  )

                  return event

              except Exception as e:
                  logger.error(f"Failed to record orchestrator call usage: {e}")
                  return None

      def _calculate_cost_from_tokens(self, tokens_used: int, event_schema: dict) -> float:
          """Calculate cost based on tokens and model pricing."""
          with _usage_lock:
              model = event_schema.get('model', 'unknown')
              provider = event_schema.get('provider', 'unknown')

              # Pricing model - would be replaced with actual pricing config
              pricing = {
                  ('openai', 'gpt-4'): 0.00003,  # $0.03 per 1K tokens
                  ('openai', 'gpt-3.5-turbo'): 0.000001,  # $0.001 per 1K tokens
                  ('anthropic', 'claude-2'): 0.00001,  # $0.01 per 1K tokens
                  ('google', 'gemini-pro'): 0.000005,  # $0.005 per 1K tokens
              }

              price_per_k = pricing.get((provider, model), 0.00001)
              return round((tokens_used / 1000) * price_per_k, 6)

      def _estimate_latency(self, event_schema: dict) -> int:
          """Estimate latency based on event schema."""
          with _usage_lock:
              # In production, this would use actual latency from the API call
              # For now, return a reasonable default
              return 500  # 500ms default

      # ==========================================================
      # Persistence & Utilities
      # ==========================================================

      def get_all_events(self) -> List[UsageEvent]:
          """Get all tracked usage events."""
          with _usage_lock:
              return self._events.copy()

      def get_events_by_agent(self, agent_id: str) -> List[UsageEvent]:
          """Get all events for a specific agent."""
          with _usage_lock:
              agent_indices = self._agent_index.get(agent_id, [])
              return [self._events[idx] for idx in agent_indices]

      def get_events_by_provider(self, provider: str) -> List[UsageEvent]:
          """Get all events for a specific provider."""
          with _usage_lock:
              provider_indices = self._provider_index.get(provider, [])
              return [self._events[idx] for idx in provider_indices]

      def get_events_by_model(self, model: str) -> List[UsageEvent]:
          """Get all events for a specific model."""
          with _usage_lock:
              model_indices = self._model_index.get(model, [])
              return [self._events[idx] for idx in model_indices]

      def get_events_by_purpose(self, purpose: str) -> List[UsageEvent]:
          """Get all events for a specific purpose."""
          with _usage_lock:
              purpose_indices = self._purpose_index.get(purpose, [])
              return [self._events[idx] for idx in purpose_indices]

      def get_statistics(self) -> dict:
          """Get overall statistics about tracked usage."""
          with _usage_lock:
              if not self._events:
                  return {
                      'total_events': 0,
                      'total_tokens': 0,
                      'total_cost': 0.0,
                      'average_latency_ms': 0,
                      'by_agent': {},
                      'by_provider': {},
                      'by_model': {},
                      'by_purpose': {}
                  }

              # By agent
              by_agent = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})
              # By provider
              by_provider = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})
              # By model
              by_model = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})
              # By purpose
              by_purpose = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})

              for event in self._events:
                  by_agent[event.agent_id]['tokens'] += event.tokens_used
                  by_agent[event.agent_id]['cost'] += event.cost_usd
                  by_agent[event.agent_id]['calls'] += 1

                  by_provider[event.provider]['tokens'] += event.tokens_used
                  by_provider[event.provider]['cost'] += event.cost_usd
                  by_provider[event.provider]['calls'] += 1

                  by_model[event.model]['tokens'] += event.tokens_used
                  by_model[event.model]['cost'] += event.cost_usd
                  by_model[event.model]['calls'] += 1

                  by_purpose[event.purpose]['tokens'] += event.tokens_used
                  by_purpose[event.purpose]['cost'] += event.cost_usd
                  by_purpose[event.purpose]['calls'] += 1

              # Sort and convert
              sorted_agents = sorted(by_agent.items(), key=lambda x: x[1]['tokens'], reverse=True)[:10]
              sorted_providers = sorted(by_provider.items(), key=lambda x: x[1]['tokens'], reverse=True)[:10]
              sorted_models = sorted(by_model.items(), key=lambda x: x[1]['tokens'], reverse=True)[:10]
              sorted_purposes = sorted(by_purpose.items(), key=lambda x: x[1]['tokens'], reverse=True)[:10]

              return {
                  'total_events': len(self._events),
                  'total_tokens': sum(e.tokens_used for e in self._events),
                  'total_cost': round(sum(e.cost_usd for e in self._events), 4),
                  'average_latency_ms': round(sum(e.latency_ms for e in self._events) / len(self._events), 2),
                  'top_agents': {k: {'tokens': v['tokens'], 'cost': round(v['cost'], 4), 'calls': v['calls']}
                                 for k, v in sorted_agents},
                  'top_providers': {k: {'tokens': v['tokens'], 'cost': round(v['cost'], 4), 'calls': v['calls']}
                                    for k, v in sorted_providers},
                  'top_models': {k: {'tokens': v['tokens'], 'cost': round(v['cost'], 4), 'calls': v['calls']}
                                 for k, v in sorted_models},
                  'top_purposes': {k: {'tokens': v['tokens'], 'cost': round(v['cost'], 4), 'calls': v['calls']}
                                   for k, v in sorted_purposes}
              }

