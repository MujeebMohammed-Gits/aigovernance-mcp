
  # -*- coding: utf-8 -*-
"""
    Policy DSL Production Hardened
    Domain Specific Language parser + compiler + rule registry for AI Governance
    Thread-safe with validation and error handling
  """
import re
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass


  # Configure structured logger
logger = logging.getLogger('mcp_policy_dsl')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

  # Thread lock for concurrent access
_dsl_lock = threading.Lock()


  # ============================================================
  # DSL Rule Dataclass
  # ============================================================

@dataclass
class DSLRule:
      """Dataclass representing a compiled DSL rule."""
      name: str
      condition: Callable
      action: str
      action_param: Optional[Any] = None
      message: str = ''
      compiled_at: str = ''


  # ============================================================
  # PolicyDSLParser Class
  # ============================================================

class PolicyDSLParser:
      """
      Production-hardened parser for policy DSL rules.
      Supports RULE name: WHEN condition THEN action MESSAGE "template" format.
      Includes validation and error reporting.
      """

      RULE_PATTERN = re.compile(
          r"RULE\s+(?P<name>\w+):\s*"
          r"WHEN\s+(?P<condition>.+?)\s*"
          r"THEN\s+(?P<action>\w+)(?:\s+(?P<action_param>[^\s]+))?\s*"
          r"MESSAGE\s+\"(?P<message>.+?)\"",
          re.DOTALL
      )

      def parse(self, dsl_text: str) -> DSLRule:
          """
          Parse a DSL rule text into a DSLRule object.

          :param dsl_text: DSL rule text
          :return: DSLRule object
          :raises ValueError: If DSL format is invalid
          """
          if not dsl_text or not dsl_text.strip():
              raise ValueError("DSL text cannot be empty")

          match = self.RULE_PATTERN.search(dsl_text)
          if not match:
              raise ValueError(f"Invalid DSL rule format. Expected: "
                             f"RULE <name>: WHEN <condition> THEN <action> MESSAGE \"<message>\"")

          try:
              rule_name = match.group("name").strip()
              condition = match.group("condition").strip()
              action = match.group("action").lower().strip()
              action_param = match.group("action_param").strip() if match.group("action_param") else None
              message = match.group("message").strip()

              # Validate action
              valid_actions = {'allow', 'block', 'warn', 'log', 'override_provider', 'override_model'}
              if action not in valid_actions:
                  logger.warning(f"Invalid action '{action}', defaulting to 'allow'")
                  action = 'allow'

              # Create a condition function from the condition expression
              # In production, this would be a proper AST-based evaluator
              # For now, we use eval with restricted namespace
              def create_condition_expr(expr: str) -> Callable:
                  """Create a callable condition from expression string."""
                  def condition_fn(call: dict) -> bool:
                      try:
                          # Restricted evaluation - only allow safe operations
                          allowed_names = {
                              'True': True, 'False': False,
                              'len': len, 'isinstance': isinstance,
                          }
                          # Wrap in a function that checks the condition
                          eval_globals = {"__builtins__": {}, **allowed_names}
                          result = eval(f"({expr})", eval_globals, call)
                          return bool(result)
                      except Exception as e:
                          logger.error(f"Error evaluating condition '{expr}': {e}")
                          return False

                  return condition_fn

              condition_fn = create_condition_expr(condition)

              return DSLRule(
                  name=rule_name,
                  condition=condition_fn,
                  action=action,
                  action_param=action_param,
                  message=message,
                  compiled_at=datetime.now(timezone.utc).isoformat()
              )
          except Exception as e:
              logger.error(f"Failed to parse DSL rule: {e}")
              raise


  # ============================================================
  # DSLCompiler Class
  # ============================================================

class DSLCompiler:
      """
      Compiler for DSL rules. Converts parsed DSLRule into callable functions.
      Includes validation and error handling.
      """

      def compile(self, dsl_rule: DSLRule) -> Dict[str, Any]:
          """
          Compile a DSLRule into a dictionary with callable function.

          :param dsl_rule: Parsed DSLRule
          :return: Dictionary with rule and compiled function
          """
          condition_expr = dsl_rule.condition

          def rule_fn(call: dict) -> bool:
              """Compiled condition function."""
              try:
                  # Evaluate condition with safe namespace
                  allowed_names = {
                      'True': True, 'False': False,
                      'len': len, 'isinstance': isinstance,
                      'get': lambda d, k, default=None: d.get(k, default) if isinstance(d, dict) else default,
                  }
                  result = eval(condition_expr, {"__builtins__": {}}, {**call, **allowed_names})
                  return bool(result)
              except Exception as e:
                  logger.warning(f"Error compiling condition: {e}")
                  return False

          return {
              "rule": dsl_rule.name,
              "fn": rule_fn,
              "action": dsl_rule.action,
              "action_param": dsl_rule.action_param,
              "message": dsl_rule.message,
              "compiled_at": dsl_rule.compiled_at
          }


  # ============================================================
  # PolicyEngine Integration (Enhanced)
  # ============================================================

class HardenedPolicyEngine:
      """
      Enhanced policy engine that integrates DSL rules with thread safety.
      """

      def __init__(self):
          self.rules: List[Dict[str, Any]] = []
          self._lock = _dsl_lock
          self._parser = PolicyDSLParser()
          self._compiler = DSLCompiler()

      def add_rule(self, rule_name: str, condition: Callable = None,
                   action: str = 'allow', action_param: Any = None,
                   message: str = '', risk_level: str = 'medium') -> bool:
          """Add a Python-based policy rule."""
          with self._lock:
              rule = {
                  'name': rule_name,
                  'condition': condition,
                  'action': action,
                  'action_param': action_param,
                  'message': message,
                  'risk_level': risk_level
              }
              self.rules.append(rule)
              logger.info(f"Policy rule added: {rule_name} (action: {action})")
              return True

      def add_dsl_rule(self, dsl_text: str) -> bool:
          """Add a rule from DSL text."""
          try:
              with self._lock:
                  # Parse and compile
                  parsed = self._parser.parse(dsl_text)
                  compiled = self._compiler.compile(parsed)

                  # Store as a rule dictionary compatible with evaluate()
                  self.rules.append({
                      'name': compiled['rule'],
                      'condition': compiled['fn'],
                      'action': compiled['action'],
                      'action_param': compiled.get('action_param'),
                      'message': compiled.get('message'),
                      'risk_level': 'medium'
                  })

              logger.info(f"DSL policy rule added: {compiled['rule']}")
              return True
          except Exception as e:
              logger.error(f"Failed to add DSL rule: {e}")
              return False

      def evaluate(self, ai_call: dict) -> List[dict]:
          """Evaluate AI call against all registered rules."""
          with self._lock:
              results = []

              for rule in self.rules:
                  # Get condition function
                  condition_fn = rule.get('condition') or (lambda x: False)

                  try:
                      triggered = condition_fn(ai_call)
                  except Exception:
                      triggered = False
                      logger.warning(f"Exception evaluating rule {rule.get('name')}")

                  if triggered:
                      results.append({
                          'rule': rule.get('name'),
                          'action': rule.get('action'),
                          'action_param': rule.get('action_param'),
                          'message': rule.get('message', 'Policy applied'),
                          'risk_level': rule.get('risk_level', 'medium'),
                          'evaluation_timestamp': datetime.now(timezone.utc).isoformat()
                      })

              return results

