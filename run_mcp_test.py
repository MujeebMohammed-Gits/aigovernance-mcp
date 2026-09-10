
#### FILE 4: Updated run_mcp_test.py — Enhanced Test Script

  # -*- coding: utf-8 -*-
"""
  MCP Control-Tower Production Hardened Test Script
  End-to-end testing with deployment readiness checks and comprehensive validation.
  """
import json
import os
import sys
import logging
from datetime import datetime, timezone

  # Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

  # Configure structured logger
logger = logging.getLogger('mcp_test')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

  # Import deployment readiness module
try:
      from deployments.deploy import main as deployment_main, phase_environment, phase_configuration
      from config import load_env, validate_config, get_config_summary, validate_required_keys
      logger.info("Deployment readiness module imported successfully")
except ImportError as e:
      logger.warning(f"Could not import deployment module: {e}")
      # Fallback: manual environment loading
      from dotenv import load_dotenv
      load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

  # ─── Test Configuration ───

  # Get configuration from environment (with fallbacks)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TEST_AGENT_ID = os.getenv("TEST_AGENT_ID", "test-agent-001")
TEST_PROVIDER = os.getenv("TEST_PROVIDER", "openai")
TEST_MODEL = os.getenv("TEST_MODEL", "gpt-4")
TEST_PURPOSE = os.getenv("TEST_PURPOSE", "testing")

  # ─── Deployment Readiness Checks ───

def test_deployment_readiness() -> bool:
      """Test deployment readiness across all areas."""
      logger.info("=" * 70)
      logger.info("TEST: Deployment Readiness")
      logger.info("=" * 70)

      passed = 0
      total = 0

      # Check 1: Environment files
      total += 1
      env_file = os.path.join(PROJECT_ROOT, ".env")
      if os.path.exists(env_file):
          logger.info(f"  ✓ .env file exists: {env_file}")
          passed += 1
      else:
          logger.warning(f"  ✗ .env file missing: {env_file}")

      # Check 2: Configuration validation
      total += 1
      try:
          from config import validate_config
          config_status = validate_config()
          if config_status["valid"]:
              logger.info(f"  ✓ Configuration valid: {config_status['message']}")
              passed += 1
          else:
              logger.warning(f"  ✗ Configuration invalid: {config_status['message']}")
      except Exception as e:
          logger.error(f"  ✗ Configuration validation error: {e}")

      # Check 3: Required API keys
      total += 1
      if OPENAI_API_KEY and ANTHROPIC_API_KEY and GOOGLE_API_KEY:
          logger.info(f"  ✓ All required API keys present")
          passed += 1
      else:
          missing = [k for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"] if not os.getenv(k)]
          logger.warning(f"  ✗ Missing API keys: {', '.join(missing)}")

      # Check 3: Directory structure
      total += 1
      required_dirs = ["logs", "config", "deployments"]
      all_exist = all(os.path.isdir(os.path.join(PROJECT_ROOT, d)) for d in required_dirs)
      if all_exist:
          logger.info(f"  ✓ Required directories exist: {', '.join(required_dirs)}")
          passed += 1
      else:
          missing_dirs = [d for d in required_dirs if not os.path.isdir(os.path.join(PROJECT_ROOT, d))]
          logger.warning(f"  ✗ Missing directories: {', '.join(missing_dirs)}")

      # Check 4: Key modules importable
      total += 1
      modules = ["mcp_service.mcp_service", "policy_engine.policy_engine_main",
                 "agent_registry.agent_registry", "usage_tracker.usage_tracker"]
      all_importable = True
      for mod in modules:
          try:
              __import__(mod)
          except ImportError:
              all_importable = False
              break

      if all_importable:
          logger.info(f"  ✓ All key modules importable")
          passed += 1
      else:
          logger.warning(f"  ✗ Some key modules not importable")

      # Summary
      print()
      print_color = lambda c, t: print(t)  # Simplified
      print("=" * 70)
      logger.info(f"  Deployment Readiness: {passed}/{total} checks passed")

      if passed == total:
          logger.info("  ✓ Deployment readiness OK")
          return True
      else:
          logger.warning(f"  ✗ {total - passed} checks need attention")
          return False

  # ─── Original Test Functions (from earlier) ───

def test_orchestrator_initialization():
      """Test MCP Orchestrator initialization with proper error handling."""
      logger.info("=" * 70)
      logger.info("TEST 1: MCP Orchestrator Initialization")
      logger.info("=" * 70)

      try:
          from mcp_service.mcp_service import MCPOrchestrator

          orchestrator = MCPOrchestrator(
              openai_api_key=OPENAI_API_KEY,
              anthropic_api_key=ANTHROPIC_API_KEY,
              google_api_key=GOOGLE_API_KEY
          )
          logger.info("✓ MCP Orchestrator initialized successfully")
          logger.info(f"  - Policy Engine: active")
          logger.info(f"  - OpenAI integration: {'configured' if orchestrator._openai_integration else 'not configured'}")
          logger.info(f"  - Anthropic integration: {'configured' if orchestrator._anthropic_integration else 'not configured'}")
          logger.info(f"  - Google integration: {'configured' if orchestrator._google_integration else 'not configured'}")
          logger.info(f"  - Audit Logger: active")
          logger.info(f"  - Monitoring Dashboard: active")
          logger.info(f"  - Agent Registry: active")
          logger.info(f"  - Provider Config: active")
          logger.info(f"  - Usage Tracker: active")
          return True
      except Exception as e:
          logger.error(f"✗ MCP Orchestrator initialization failed: {e}")
          import traceback
          logger.error(traceback.format_exc())
          return False


def test_policy_evaluation():
      """Test policy evaluation with various scenarios."""
      logger.info("\n" + "=" * 70)
      logger.info("TEST 2: Policy Evaluation")
      logger.info("=" * 70)

      try:
          from policy_engine.policy_engine_main import PolicyEngine, block_pii_external_llms, log_high_risk_uses, enforce_data_classification

          engine = PolicyEngine()
          engine.add_rule('PII_BLOCK', block_pii_external_llms, 'block')
          engine.add_rule('HIGH_RISK_LOG', log_high_risk_uses, 'log')
          engine.add_rule('DATA_CLASSIFICATION', enforce_data_classification, 'warn')

          test_cases = [
              {
                  'name': 'PII Block Test',
                  'call': {
                      'provider': 'openai',
                      'model': 'gpt-4',
                      'purpose': 'customer_support',
                      'data': 'Customer SSN: 123-45-6789',
                      'has_sensitive_data': True,
                      'risk_level': 'medium',
                      'data_classification': 'confidential'
                  }
              },
              {
                  'name': 'High-Risk Log Test',
                  'call': {
                      'provider': 'anthropic',
                      'model': 'claude-2',
                      'purpose': 'fraud_detection',
                      'data': 'Transaction records',
                      'has_sensitive_data': True,
                      'risk_level': 'high',
                      'data_classification': 'restricted'
                  }
              },
              {
                  'name': 'Allowed Call Test',
                  'call': {
                      'provider': 'openai',
                      'model': 'gpt-4',
                      'purpose': 'code_generation',
                      'data': 'Python script for data processing',
                      'has_sensitive_data': False,
                      'risk_level': 'low',
                      'data_classification': 'internal'
                  }
              }
          ]

          for test_case in test_cases:
              results = engine.evaluate(test_case['call'])
              actions = [r['action'] for r in results]
              logger.info(f"  {test_case['name']}: actions = {', '.join(actions) if actions else 'ALLOW'}")

          logger.info("✓ Policy evaluation test completed successfully")
          return True
      except Exception as e:
          logger.error(f"✗ Policy evaluation test failed: {e}")
          import traceback
          logger.error(traceback.format_exc())
          return False


def test_agent_registry():
      """Test Agent Registry CRUD operations."""
      logger.info("\n" + "=" * 70)
      logger.info("TEST 3: Agent Registry CRUD Operations")
      logger.info("=" * 70)

      try:
          from agent_registry.agent_registry import AgentRegistry, AgentProfile

          registry = AgentRegistry(storage_path=os.path.join(PROJECT_ROOT, "test_agent_registry.json"))

          # Create test agent
          test_agent = AgentProfile(
              agent_id="test-agent-001",
              agent_name="Test Agent",
              owner="Test Owner",
              department="Test Department",
              risk_level="low",
              allowed_providers=["openai"],
              allowed_models=["gpt-4"],
              allowed_purposes=["testing"],
              default_data_classification="internal",
              approval_requirements="none",
              metadata={"description": "Test agent for MCP hardening"}
          )

          # Register
          registry.register_agent(test_agent)
          logger.info("  ✓ Agent registered successfully")

          # Get agent
          retrieved = registry.get_agent("test-agent-001")
          if retrieved:
              logger.info("  ✓ Agent retrieved successfully")
          else:
              logger.error("  ✗ Failed to retrieve agent")
              return False

          # Update agent
          retrieved.risk_level = "medium"
          registry.update_agent(retrieved)
          logger.info("  ✓ Agent updated successfully")

          # Check compliance
          compliance = registry.check_agent_policy_compliance(
              agent_id="test-agent-001",
              provider="openai",
              model="gpt-4",
              purpose="testing"
          )
          logger.info(f"  ✓ Policy compliance check: {compliance['compliant']}")

          # Get execution config
          config = registry.get_agent_execution_config("test-agent-001")
          logger.info(f"  ✓ Execution config retrieved: {len(config)} fields")

          # Delete agent
          registry.delete_agent("test-agent-001")
          logger.info("  ✓ Agent deleted successfully")

          # Clean up
          if os.path.exists(os.path.join(PROJECT_ROOT, "test_agent_registry.json")):
              os.remove(os.path.join(PROJECT_ROOT, "test_agent_registry.json"))

          logger.info("✓ Agent Registry CRUD test completed successfully")
          return True
      except Exception as e:
          logger.error(f"✗ Agent Registry test failed: {e}")
          import traceback
          logger.error(traceback.format_exc())
          return False


def test_usage_tracking():
      """Test Usage Tracker operations."""
      logger.info("\n" + "=" * 70)
      logger.info("TEST 4: Usage Tracking")
      logger.info("=" * 70)

      try:
          from usage_tracker.usage_tracker import UsageTracker

          tracker = UsageTracker(storage_path=os.path.join(PROJECT_ROOT, "usage_tracker_test.jsonl"))

          # Track usage events
          event1 = tracker.track_usage(
              tokens_used=1500,
              cost_usd=0.045,
              latency_ms=850,
              agent_id="support-bot-01",
              provider="openai",
              model="gpt-4",
              purpose="customer_support",
              user_id="user-123"
          )
          logger.info(f"  ✓ Event 1 tracked: {event1.event_id}")

          event2 = tracker.track_usage(
              tokens_used=2000,
              cost_usd=0.06,
              latency_ms=1200,
              agent_id="fraud-detector-01",
              provider="anthropic",
              model="claude-2",
              purpose="fraud_detection",
              user_id="user-456"
          )
          logger.info(f"  ✓ Event 2 tracked: {event2.event_id}")

          # Get usage summary
          summary = tracker.get_usage_summary()
          logger.info(f"  ✓ Usage summary: {summary['total_calls']} calls, {summary['total_tokens']} tokens")

          # Get cost summary
          cost_summary = tracker.get_cost_summary()
          logger.info(f"  ✓ Cost summary: ${cost_summary['total_cost']:.4f} total")

          # Get agent usage
          agent_usage = tracker.get_agent_usage("support-bot-01")
          logger.info(f"  ✓ Agent usage: {agent_usage['total_calls']} calls")

          # Get daily rollup
          daily = tracker.get_daily_rollup("2024-01-15")
          logger.info(f"  ✓ Daily rollup: {'available' if daily else 'no data'}")

          # Get statistics
          stats = tracker.get_statistics()
          logger.info(f"  ✓ Overall statistics: {stats['total_events']} events")

          # Clean up
          if os.path.exists(os.path.join(PROJECT_ROOT, "usage_tracker_test.jsonl")):
              os.remove(os.path.join(PROJECT_ROOT, "usage_tracker_test.jsonl"))

          logger.info("✓ Usage Tracking test completed successfully")
          return True
      except Exception as e:
          logger.error(f"✗ Usage Tracking test failed: {e}")
          import traceback
          logger.error(traceback.format_exc())
          return False


def test_audit_logging():
      """Test Audit Logger operations."""
      logger.info("\n" + "=" * 70)
      logger.info("TEST 5: Audit Logging")
      logger.info("=" * 70)

      try:
          from audit.audit_logger import AuditLogger

          logger = AuditLogger(log_file_path=os.path.join(PROJECT_ROOT, "test_audit_log.jsonl"))

          # Log test events
          event1 = {
              'event_id': 'evt-test-001',
              'timestamp': datetime.now(timezone.utc).isoformat(),
              'provider': 'openai',
              'model': 'gpt-4',
              'purpose': 'customer_support',
              'policy_evaluation': {
                  'decision': 'allow',
                  'rules_triggered': [],
                  'policy_explanations': ['No policy violations detected']
              },
              'data_classification': 'internal',
              'has_pii': False,
              'has_sensitive_data': False
          }

          result1 = logger.add_event(event1)
          logger.info(f"  ✓ Event 1 logged: {result1}")

          event2 = {
              'event_id': 'evt-test-002',
              'timestamp': datetime.now(timezone.utc).isoformat(),
              'provider': 'openai',
              'model': 'gpt-4',
              'purpose': 'customer_support',
              'policy_evaluation': {
                  'decision': 'block',
                  'rules_triggered': ['PII_BLOCK'],
                  'policy_explanations': ['PII detected in call']
              },
              'data_classification': 'confidential',
              'has_pii': True,
              'has_sensitive_data': False
          }

          result2 = logger.add_event(event2)
          logger.info(f"  ✓ Event 2 logged: {result2}")

          # Query events
          allowed = logger.get_events_by_decision('allow')
          logger.info(f"  ✓ Retrieved {len(allowed)} allowed events")

          blocked = logger.get_events_by_decision('block')
          logger.info(f"  ✓ Retrieved {len(blocked)} blocked events")

          pii_events = logger.get_events_by_rule('PII_BLOCK')
          logger.info(f"  ✓ Retrieved {len(pii_events)} events with PII_BLOCK rule")

          # Health report
          health = logger.get_health_report()
          logger.info(f"  ✓ Health report: {health['total_events']} total events, {health['success_rate']:.2%} success rate")

          # Clean up
          if os.path.exists(os.path.join(PROJECT_ROOT, "test_audit_log.jsonl")):
              os.remove(os.path.join(PROJECT_ROOT, "test_audit_log.jsonl"))

          logger.info("✓ Audit Logging test completed successfully")
          return True
      except Exception as e:
          logger.error(f"✗ Audit Logging test failed: {e}")
          import traceback
          logger.error(traceback.format_exc())
          return False


  # ─── Main Test Runner ───

def main() -> int:
      """Run all production hardening tests."""
      print("=" * 70)
      print("MCP CONTROL-TOWER PRODUCTION HARDENING TEST SUITE")
      print("=" * 70)
      print()

      results = {}

      # Run deployment readiness test
      results['deployment_readiness'] = test_deployment_readiness()

      # Run original tests
      results['orchestrator_init'] = test_orchestrator_initialization()
      results['policy_evaluation'] = test_policy_evaluation()
      results['agent_registry'] = test_agent_registry()
      results['usage_tracking'] = test_usage_tracking()
      results['audit_logging'] = test_audit_logging()

      # Summary
      print("\n" + "=" * 70)
      print("TEST SUMMARY")
      print("=" * 70)
      passed = sum(1 for v in results.values() if v)
      total = len(results)

      for test_name, passed_result in results.items():
          status = "✓ PASSED" if passed_result else "✗ FAILED"
          print(f"  {test_name:30s}: {status}")

      print()
      print(f"  Results: {passed}/{total} tests passed")

      if passed == total:
          print("  🎉 All tests passed!")
      else:
          print("  ⚠ Some tests failed - see logs above for details")

      print("=" * 70)

      # Return exit code
      return 0 if passed == total else 1


if __name__ == "__main__":
      try:
          exit_code = main()
          sys.exit(exit_code)
      except KeyboardInterrupt:
          logger.info("Test interrupted by user")
          sys.exit(1)
      except Exception as e:
          logger.error(f"Unexpected test error: {e}")
          import traceback
          logger.error(traceback.format_exc())
          sys.exit(1)

