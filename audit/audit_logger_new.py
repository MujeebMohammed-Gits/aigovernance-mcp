"""
Audit Logging Module
JSONL-based persistent storage for AI Governance & Compliance Control-Tower MCP Agent

Stores every event schema JSON object with policy evaluation results.
Provides simple query functions for event retrieval.
"""

import json
import os
from json import JSONDecodeError
from typing import List, Dict, Any


class AuditLogger:
    """
    Minimal audit logger using JSONL (JSON Lines) format.
    Each line in the file is a complete JSON event object.
    """

    def __init__(self, log_file_path: str = "audit_log.jsonl"):
        self.log_file_path = log_file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the log file if it doesn't exist."""
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'w') as f:
                pass

    def add_event(self, event: Dict[str, Any]) -> None:
        """Append a single event to the JSONL log file."""
        try:
            if not isinstance(event, dict):
                raise ValueError("Event must be a dictionary")

            if 'logged_at' not in event:
                event['logged_at'] = self._get_current_timestamp()

            if 'log_entry_id' not in event:
                event['log_entry_id'] = f"entry-{int(self._get_timestamp_ms())}"

            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')

        except Exception as e:
            print(f"âš ï¸ Warning: Failed to write audit event: {e}")

    @staticmethod
    def _get_current_timestamp() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _get_timestamp_ms() -> float:
        import time
        return time.time() * 1000

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Retrieve all events from the log file."""
        events = []
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            events.append(event)
                        except JSONDecodeError:
                            continue
        except FileNotFoundError:
            pass

        return events

    def get_events_by_decision(self, decision: str) -> List[Dict[str, Any]]:
        """Retrieve events filtered by policy decision."""
        decision_lower = decision.lower()
        events = []

        for event in self.get_all_events():
            event_decision = event.get('policy_evaluation', {}).get('decision', '').lower()
            if event_decision == decision_lower:
                events.append(event)

        return events

    def get_events_by_rule(self, rule: str) -> List[Dict[str, Any]]:
        """Retrieve events filtered by triggered policy rule."""
        rule_lower = rule.lower()
        events = []

        for event in self.get_all_events():
            rules_triggered = event.get('policy_evaluation', {}).get('rules_triggered', [])
            if isinstance(rules_triggered, list) and rule_lower in [r.lower() for r in rules_triggered]:
                events.append(event)

        return events

    def get_event_count(self) -> int:
        return len(self.get_all_events())

    def get_decision_statistics(self) -> Dict[str, int]:
        events = self.get_all_events()
        stats = {'allow': 0, 'block': 0, 'warn': 0, 'unknown': 0}

        for event in events:
            decision = event.get('policy_evaluation', {}).get('decision', 'unknown').lower()
            if decision in stats:
                stats[decision] += 1
            else:
                stats['unknown'] += 1

        return stats

    def get_rule_statistics(self) -> Dict[str, int]:
        events = self.get_all_events()
        rules = {}

        for event in events:
            rules_triggered = event.get('policy_evaluation', {}).get('rules_triggered', [])
            if isinstance(rules_triggered, list):
                for rule in rules_triggered:
                    rules[rule] = rules.get(rule, 0) + 1

        return rules
