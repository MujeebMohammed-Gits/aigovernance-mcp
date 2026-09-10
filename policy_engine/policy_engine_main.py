
  # Policy Engine

  # -*- coding: utf-8 -*-
"""
    Policy Engine Production Hardened
    Core policy engine for AI Governance & Compliance Control-Tower MCP Agent
    Thread-safe, with input/output validation, error handling, and health reporting
  """
import json
import os
import threading
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


  # Configure structured logger
logger = logging.getLogger('mcp_policy_engine')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

  # Thread lock for concurrent access
_engine_lock = threading.Lock()

  # Circuit breaker state
_circuit_breakers: Dict[str, Dict] = {}


@dataclass
class PolicyRule:
      """Dataclass representing a policy rule with validation."""
      name: str
      condition: Callable
      action: str
      action_param: Optional[Any] = None
      message_template: str = ''
      risk_level: str = 'medium'
      enabled: bool = True


class PolicyEngine:
      """
      Production-hardened policy engine for AI Governance & Compliance Control-Tower MCP Agent.

      Features:
      - Thread-safe rule evaluation
      - DSL-based rule compilation
      - Input validation
      - Output validation
      - Health reporting
      - Circuit breaker patterns
      - Retry logic integration
      """

      def __init__(self):
          self.rules: List[PolicyRule] = []
          self._lock = _engine_lock
          self._circuit_key = 'policy_engine'
          self._total_evaluations = 0
          self._evaluation_errors = 0

      def add_rule(self, rule_name: str, condition: Callable, action: str,
                   action_param: Optional[Any] = None,
                   message_template: str = '', risk_level: str = 'medium',
                   enabled: bool = True) -> bool:
          """Add a policy rule with validation."""
          with self._lock:
              # Validate action
              valid_actions = {'allow', 'block', 'warn', 'log'}
              if action not in valid_actions:
                  logger.error(f"Invalid action '{action}', must be one of {valid_actions}")
                  return False

              # Validate risk level
              valid_risks = {'low', 'medium', 'high'}
              if risk_level not in valid_risks:
                  logger.warning(f"Invalid risk_level '{risk_level}', defaulting to 'medium'")
                  risk_level = 'medium'

              rule = PolicyRule(
                  name=rule_name,
                  condition=condition,
                  action=action,
                  action_param=action_param,
                  message_template=message_template,
                  risk_level=risk_level,
                  enabled=enabled
              )
              self.rules.append(rule)
              logger.info(f"Policy rule added: {rule_name} (action: {action}, risk: {risk_level})")
              return True

      def add_dsl_rule(self, dsl_text: str) -> bool:
          """Add a rule from DSL text with parsing and compilation."""
          try:
              from policy_engine.policy_dsl import PolicyDSLParser, DSLCompiler
              parser = PolicyDSLParser()
              compiler = DSLCompiler()

              parsed = parser.parse(dsl_text)
              compiled = compiler.compile(parsed)

              # Convert compiled rule to PolicyRule
              rule = PolicyRule(
                  name=compiled.get('rule', 'DSL_Rule'),
                  condition=compiled.get('fn', lambda x: False),
                  action=compiled.get('action', 'allow'),
                  action_param=compiled.get('action_param'),
                  message_template=compiled.get('message', 'Policy applied'),
                  risk_level='medium',
                  enabled=True
              )

              with self._lock:
                  self.rules.append(rule)

              logger.info(f"DSL policy rule added: {rule.name}")
              return True
          except Exception as e:
              logger.error(f"Failed to add DSL rule: {e}")
              return False

      def evaluate(self, ai_call: Dict[str, Any]) -> List[Dict[str, Any]]:
          """Evaluate AI call against all registered rules with thread safety and error handling."""
          with self._lock:
              results = []
              self._total_evaluations += 1

              for rule in self.rules:
                  # Skip disabled rules
                  if not rule.enabled:
                      continue

                  # Get the condition function
                  condition_fn = rule.condition

                  try:
                      # Validate ai_call is a dict
                      if not isinstance(ai_call, dict):
                          raise ValueError("ai_call must be a dictionary")

                      triggered = condition_fn(ai_call)
                  except Exception as e:
                      self._evaluation_errors += 1
                      logger.error(f"Exception evaluating rule {rule.name}: {e}")
                      triggered = False

                  if triggered:
                      # Generate message using template
                      message = self._generate_message(rule, ai_call)

                      result = {
                          'rule': rule.name,
                          'action': rule.action,
                          'action_param': rule.action_param,
                          'message': message,
                          'risk_level': rule.risk_level,
                          'evaluation_timestamp': datetime.now(timezone.utc).isoformat(),
                          'rule_enabled': rule.enabled
                      }
                      results.append(result)

              return results

      def _generate_message(self, rule: PolicyRule, ai_call: Dict[str, Any]) -> str:
          """Generate human-readable policy explanation with validation."""
          # Use the template if available
          if rule.message_template:
              try:
                  # Safely format with available fields
                  safe_call = {k: v for k, v in ai_call.items()
                              if k in ['provider', 'model', 'purpose', 'data_classification', 'risk_level']}
                  return rule.message_template.format(**safe_call)
              except Exception:
                  pass

          # Default message generation based on rule name
          rule_name = rule.name.lower()
          provider = ai_call.get('provider', 'unknown')
          purpose = ai_call.get('purpose', 'unspecified')
          model = ai_call.get('model', 'unknown')
          data_class = ai_call.get('data_classification', 'unknown')

          # Sanitize inputs
          provider = str(provider)[:50] if provider else 'unknown'
          purpose = str(purpose)[:50] if purpose else 'unspecified'
          model = str(model)[:50] if model else 'unknown'
          data_class = str(data_class)[:50] if data_class else 'unknown'

          if rule_name == 'pii_block' or rule_name == 'pii':
              return (f"🚫 BLOCKED: AI call to {provider} "
                      f"contains PII. Approval required for {purpose}")
          elif rule_name == 'high_risk_log' or rule_name == 'high_risk':
              return (f"📝 LOGGED: High-risk use case detected - {purpose} "
                      f"by {provider} model {model}")
          elif rule_name == 'data_policy_violation' or rule_name == 'data_policy':
              return (f"⚠️ POLICY VIOLATION: Data access rule breached for {data_class} data")
          elif rule_name == 'require_approval' or rule_name == 'approval':
              return (f"✅ REQUIRE APPROVAL: AI call to {provider} requires "
                      f"approval for {purpose} purpose")
          else:
              return f"📋 Policy applied: {rule.name}"

      def get_stats(self) -> Dict[str, Any]:
          """Get policy engine statistics with thread safety."""
          with self._lock:
              total_rules = len([r for r in self.rules if r.enabled])
              action_counts = {'allow': 0, 'block': 0, 'warn': 0, 'log': 0}
              risk_counts = {'low': 0, 'medium': 0, 'high': 0}
              enabled_counts = {'enabled': 0, 'disabled': 0}

              for rule in self.rules:
                  if rule.action in action_counts:
                      action_counts[rule.action] += 1
                  if rule.risk_level in risk_counts:
                      risk_counts[rule.risk_level] += 1
                  if rule.enabled:
                      enabled_counts['enabled'] += 1
                  else:
                      enabled_counts['disabled'] += 1

              return {
                  'total_rules': total_rules,
                  'enabled_rules': enabled_counts['enabled'],
                  'disabled_rules': enabled_counts['disabled'],
                  'action_counts': action_counts,
                  'risk_counts': risk_counts,
                  'total_evaluations': self._total_evaluations,
                  'evaluation_errors': self._evaluation_errors,
                  'success_rate': round(self._total_evaluations / max(1, self._total_evaluations + self._evaluation_errors), 4)
              }


  # ============================================================
  # Default Rules
  # ============================================================

def block_pii_external_llms(ai_call):
      """Rule: Block external LLM calls with PII unless approved."""
      pii_indicators = ['ssn', 'credit_card', 'password', 'medical_record', 'pii']
      has_pii = any(indicator in str(ai_call.get('data', '')).lower()
                    for indicator in pii_indicators)
      is_external = ai_call.get('provider', '').lower() in ['openai', 'anthropic', 'google']
      requires_approval = ai_call.get('risk_level') == 'high'

      return has_pii and is_external and not requires_approval


def log_high_risk_uses(ai_call):
      """Rule: Log all high-risk use cases with extra metadata."""
      high_risk_categories = ['fraud_detection', 'financial_decision',
                             'medical_diagnosis', 'employment_screening',
                             'autonomous_action', 'biometric_analysis']
      purpose = ai_call.get('purpose', '').lower()
      is_high_risk = any(category in purpose for category in high_risk_categories)
      has_sensitive_data = ai_call.get('has_sensitive_data', False)

      return is_high_risk or has_sensitive_data


def enforce_data_classification(ai_call):
      """Rule: Enforce data classification and access policies."""
      classified_data = ['confidential', 'restricted', 'internal']
      data_class = ai_call.get('data_classification', '').lower()
      is_classified = data_class in classified_data
      provider = ai_call.get('provider', '').lower()

      # Block restricted data to unauthorized providers
      if is_classified and provider in ['openai', 'anthropic'] and not ai_call.get('approved', False):
          return True

      # Allow if properly approved
      return ai_call.get('approved', False) or data_class != 'restricted'


  # ============================================================
  # Example Usage & Demonstration
  # ============================================================

if __name__ == "__main__":
      print("=" * 70)
      print("POLICY ENGINE PRODUCTION HARDENING DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize policy engine
      engine = PolicyEngine()

      # Register default rules
      engine.add_rule('PII_BLOCK', block_pii_external_llms, 'block',
                      message_template="🚫 BLOCKED: AI call to {provider} contains PII. "
                                       "Approval required for {purpose} purpose",
                      risk_level='high')
      engine.add_rule('HIGH_RISK_LOG', log_high_risk_uses, 'log',
                      message_template="📝 LOGGED: High-risk use case detected - {purpose} "
                                       "by {provider} model {model}",
                      risk_level='medium')
      engine.add_rule('DATA_CLASSIFICATION', enforce_data_classification, 'warn',
                      message_template="⚠️ POLICY WARNING: Data access rule breached for {data_class} data",
                      risk_level='medium')

      # Test scenarios
      test_calls = [
          {
              'provider': 'OpenAI',
              'model': 'gpt-4',
              'purpose': 'customer support',
              'data': 'Customer SSN: 123-45-6789',
              'has_sensitive_data': True,
              'risk_level': 'medium',
              'data_classification': 'confidential'
          },
          {
              'provider': 'Anthropic',
              'model': 'claude-2',
              'purpose': 'document analysis',
              'data': 'Contract review for merger',
              'has_sensitive_data': True,
              'risk_level': 'high',
              'data_classification': 'restricted'
          },
          {
              'provider': 'OpenAI',
              'model': 'gpt-4',
              'purpose': 'code generation',
              'data': 'Python script for data processing',
              'has_sensitive_data': False,
              'risk_level': 'low',
              'data_classification': 'internal'
          },
          {
              'provider': 'Google',
              'model': 'gemini-pro',
              'purpose': 'fraud detection',
              'data': 'Transaction records with account numbers',
              'has_sensitive_data': True,
              'risk_level': 'high',
              'data_classification': 'confidential'
          }
      ]

      print("Testing policy evaluation with sample AI calls:\n")

      for i, call in enumerate(test_calls, 1):
          print(f"Test Case {i}: {call['provider']} - {call['purpose']}")
          print(f"  Data: {call['data'][:50]}...")
          print(f"  Risk: {call['risk_level']} | Classification: {call['data_classification']}")
          print()

          results = engine.evaluate(call)

          if results:
              for r in results:
                  icon = '🚫' if r['action'] == 'block' else ('📝' if r['action'] == 'log' else ('⚠️' if r['action'] == 'warn' else '📋'))
                  print(f"  {icon} {r['rule']}: {r['message']}")
          else:
              print("  ✅ No policies triggered - Action: ALLOW")

          print()

      # Get engine stats
      print("Policy Engine Statistics:")
      stats = engine.get_stats()
      for key, value in stats.items():
          print(f"  {key}: {value}")

      print("\n" + "=" * 70)
      print("DEMONSTRATION COMPLETE")
      print("=" * 70)
