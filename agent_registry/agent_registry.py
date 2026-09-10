
  # -*- coding: utf-8 -*-
"""
    Agent Registry Production Hardened
    Manages agent profiles with CRUD operations, validation, and integration points
    Thread-safe with JSON persistence and compliance checks
  """
import json
import os
import threading
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, ClassVar
from datetime import datetime, timezone


  # Configure structured logger
logger = logging.getLogger('mcp_agent_registry')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

  # Thread lock for concurrent access
_registry_lock = threading.Lock()


  # ============================================================
  # AgentProfile Dataclass
  # ============================================================

@dataclass
class AgentProfile:
      """Dataclass representing an AI agent profile in the MCP registry."""

      # Core identification
      agent_id: str
      agent_name: str
      owner: str
      department: str

      # Risk & compliance configuration
      risk_level: str  # 'low', 'medium', 'high'
      allowed_providers: List[str]  # e.g., ['openai', 'anthropic']
      allowed_models: List[str]  # e.g., ['gpt-4', 'claude-2']
      allowed_purposes: List[str]  # e.g., ['customer_support', 'code_generation']
      default_data_classification: str  # e.g., 'internal', 'confidential', 'restricted'
      approval_requirements: str  # e.g., 'none', 'manager', 'director', 'compliance'

      # Additional metadata
      metadata: Dict[str, Any] = None

      # Class-level constraints (allowlists)
      _provider_allowlist: ClassVar = ['openai', 'anthropic', 'google', 'internal']
      _risk_level_allowlist: ClassVar = ['low', 'medium', 'high']
      _approval_requirements_allowlist: ClassVar = ['none', 'manager', 'director', 'compliance']

      def __post_init__(self):
          """Validate agent profile upon creation."""
          self._validate_provider_allowlist()
          self._validate_risk_level()
          self._validate_approval_requirements()
          self._set_default_metadata()

      def _validate_provider_allowlist(self):
          """Validate that all allowed providers are in the global allowlist."""
          for provider in self.allowed_providers:
              if provider not in self._provider_allowlist:
                  raise ValueError(
                      f"Invalid provider '{provider}'. "
                      f"Must be one of: {', '.join(self._provider_allowlist)}"
                  )

      def _validate_risk_level(self):
          """Validate risk level is in allowlist."""
          if self.risk_level not in self._risk_level_allowlist:
              raise ValueError(
                  f"Invalid risk_level '{self.risk_level}'. "
                  f"Must be one of: {', '.join(self._risk_level_allowlist)}"
              )

      def _validate_approval_requirements(self):
          """Validate approval requirements are in allowlist."""
          if self.approval_requirements not in self._approval_requirements_allowlist:
              raise ValueError(
                  f"Invalid approval_requirements '{self.approval_requirements}'. "
                  f"Must be one of: {', '.join(self._approval_requirements_allowlist)}"
              )

      def _set_default_metadata(self):
          """Set default metadata if not provided."""
          if self.metadata is None:
              self.metadata = {}
          if 'registered_at' not in self.metadata:
              self.metadata['registered_at'] = datetime.now(timezone.utc).isoformat()

      def to_dict(self) -> dict:
          """Convert to dictionary for serialization."""
          # Remove internal class fields
          data = asdict(self)
          return {k: v for k, v in data.items() if not k.startswith('_')}

      @classmethod
      def from_dict(cls, data: dict) -> 'AgentProfile':
          """Create from dictionary."""
          # Extract and remove internal fields
          metadata = data.pop('metadata', {})
          # Remove class-level constraint fields if present
          data_copy = {k: v for k, v in data.items()
                       if k not in ['_provider_allowlist', '_risk_level_allowlist', '_approval_requirements_allowlist']}
          # Remove internal fields that might be present
          for key in list(data_copy.keys()):
              if key.startswith('_'):
                  del data_copy[key]
          return cls(**data_copy, metadata=metadata)

      def __repr__(self) -> str:
          return f"<AgentProfile {self.agent_id}: {self.agent_name}>"


  # ============================================================
  # AgentRegistry Class
  # ============================================================

class AgentRegistry:
      """
      Production-hardened registry managing AgentProfile objects with CRUD operations,
      validation, and integration points for PolicyEngine and MCP Orchestrator.
      Thread-safe with JSON persistence.
      """

      def __init__(self, storage_path: str = "agent_registry.json"):
          self.storage_path = storage_path
          self._agents: Dict[str, AgentProfile] = {}
          self._load_from_disk()

      def _load_from_disk(self):
          """Load agents from persistent storage file with error handling."""
          try:
              if os.path.exists(self.storage_path):
                  with _registry_lock:
                      with open(self.storage_path, 'r', encoding='utf-8') as f:
                          data = json.load(f)
                          for agent_id, agent_data in data.items():
                              try:
                                  profile = AgentProfile.from_dict(agent_data)
                                  self._agents[agent_id] = profile
                              except Exception as e:
                                  logger.warning(f"Failed to load agent {agent_id}: {e}")
          except (json.JSONDecodeError, IOError) as e:
              logger.error(f"Could not load registry from {self.storage_path}: {e}")

      def _save_to_disk(self):
          """Persist agents to disk with thread safety and atomic writes."""
          try:
              with _registry_lock:
                  # Convert agents to serializable dict format
                  data = {}
                  for agent_id, profile in self._agents.items():
                      agent_dict = profile.to_dict()
                      data[agent_id] = agent_dict

                  # Write to temp file first, then rename for atomicity
                  temp_path = self.storage_path + '.tmp'
                  with open(temp_path, 'w', encoding='utf-8') as f:
                      json.dump(data, f, indent=2, ensure_ascii=False)
                  os.replace(temp_path, self.storage_path)
          except IOError as e:
              logger.error(f"Could not save registry to disk: {e}")

      # ==========================================================
      # CRUD Operations
      # ==========================================================

      def register_agent(self, profile: AgentProfile) -> bool:
          """
          Register a new agent in the registry.

          :param profile: AgentProfile to register
          :return: True if successfully registered
          :raises ValueError: If agent_id already exists
          """
          with _registry_lock:
              if profile.agent_id in self._agents:
                  raise ValueError(f"Agent ID '{profile.agent_id}' already exists. "
                                 f"Use update_agent() to modify.")

              # Validate on registration (dataclass __post_init__ already does this,
              # but we double-check here for explicit control)
              profile._validate_provider_allowlist()
              profile._validate_risk_level()
              profile._validate_approval_requirements()

              self._agents[profile.agent_id] = profile
              self._save_to_disk()

              logger.info(f"Agent registered: {profile.agent_id} - {profile.agent_name}")
              return True

      def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
          """
          Retrieve an agent profile by ID.

          :param agent_id: Unique agent identifier
          :return: AgentProfile if found, None otherwise
          """
          with _registry_lock:
              agent = self._agents.get(agent_id)
              if agent is None:
                  logger.warning(f"Agent not found: {agent_id}")
              return agent

      def update_agent(self, profile: AgentProfile) -> bool:
          """
          Update an existing agent profile.

          :param profile: AgentProfile with updated values
          :return: True if successfully updated
          :raises ValueError: If agent_id doesn't exist
          """
          with _registry_lock:
              if profile.agent_id not in self._agents:
                  raise ValueError(f"Agent ID '{profile.agent_id}' does not exist. "
                                 f"Use register_agent() to add new agent.")

              # Validate the updated profile
              profile._validate_provider_allowlist()
              profile._validate_risk_level()
              profile._validate_approval_requirements()

              # Preserve the existing agent_id (don't allow changing it via update)
              # The profile.agent_id should match the one we're updating
              target_agent = self._agents[profile.agent_id]
              if profile.agent_id != target_agent.agent_id:
                  # Merge metadata safely
                  profile.metadata = {**target_agent.metadata, **profile.metadata}

              self._agents[profile.agent_id] = profile
              self._save_to_disk()

              logger.info(f"Agent updated: {profile.agent_id} - {profile.agent_name}")
              return True

      def delete_agent(self, agent_id: str) -> bool:
          """
          Delete an agent from the registry.

          :param agent_id: Agent identifier to remove
          :return: True if successfully deleted
          """
          with _registry_lock:
              if agent_id not in self._agents:
                  logger.warning(f"Agent not found for deletion: {agent_id}")
                  return False

              removed_agent = self._agents.pop(agent_id)
              self._save_to_disk()

              logger.warning(f"Agent deleted: {agent_id} - {removed_agent.agent_name}")
              return True

      # ==========================================================
      # Query Operations
      # ==========================================================

      def get_agents_by_department(self, department: str) -> List[AgentProfile]:
          """Get all agents in a specific department."""
          with _registry_lock:
              return [
                  profile for profile in self._agents.values()
                  if profile.department.lower() == department.lower()
              ]

      def get_agents_by_risk_level(self, risk_level: str) -> List[AgentProfile]:
          """Get all agents with a specific risk level."""
          with _registry_lock:
              return [
                  profile for profile in self._agents.values()
                  if profile.risk_level == risk_level
              ]

      def get_agents_by_provider(self, provider: str) -> List[AgentProfile]:
          """Get all agents that allow a specific provider."""
          with _registry_lock:
              return [
                  profile for profile in self._agents.values()
                  if provider in profile.allowed_providers
              ]

      def get_all_agents(self) -> Dict[str, AgentProfile]:
          """Get all agent profiles."""
          with _registry_lock:
              return dict(self._agents)

      def agent_exists(self, agent_id: str) -> bool:
          """Check if an agent exists."""
          with _registry_lock:
              return agent_id in self._agents

      # ==========================================================
      # Integration Points
      # ==========================================================

      def check_agent_policy_compliance(self, agent_id: str,
                                        provider: str, model: str,
                                        purpose: str) -> dict:
          """
          Check if an agent's configuration is compliant with a proposed AI call.

          :param agent_id: Agent to check
          :param provider: Requested LLM provider
          :param model: Requested model
          :param purpose: Requested purpose
          :return: Compliance check result dictionary
          """
          with _registry_lock:
              agent = self.get_agent(agent_id)
              if agent is None:
                  return {
                      'compliant': False,
                      'agent_id': agent_id,
                      'errors': [f"Agent '{agent_id}' not found in registry"]
                  }

              errors = []
              warnings = []

              # Check provider
              if provider not in agent.allowed_providers:
                  errors.append(
                      f"Provider '{provider}' not in agent's allowed_providers: {agent.allowed_providers}"
                  )

              # Check model
              if model not in agent.allowed_models:
                  errors.append(
                      f"Model '{model}' not in agent's allowed_models: {agent.allowed_models}"
                  )

              # Check purpose
              if purpose not in agent.allowed_purposes:
                  errors.append(
                      f"Purpose '{purpose}' not in agent's allowed_purposes: {agent.allowed_purposes}"
                  )

              # Check data classification
              if agent.default_data_classification in ['restricted', 'confidential']:
                  warnings.append(
                      f"Agent has restrictive data classification: {agent.default_data_classification}"
                  )

              compliant = len(errors) == 0

              return {
                  'compliant': compliant,
                  'agent_id': agent_id,
                  'agent_name': agent.agent_name,
                  'errors': errors,
                  'warnings': warnings,
                  'risk_level': agent.risk_level,
                  'approval_requirements': agent.approval_requirements
              }

      def get_agent_execution_config(self, agent_id: str) -> dict:
          """
          Get execution configuration for an agent to pass to MCP Orchestrator.

          :param agent_id: Agent to get config for
          :return: Execution configuration dictionary
          """
          with _registry_lock:
              agent = self.get_agent(agent_id)
              if agent is None:
                  return {}

              return {
                  'agent_id': agent.agent_id,
                  'agent_name': agent.agent_name,
                  'allowed_providers': agent.allowed_providers,
                  'allowed_models': agent.allowed_models,
                  'allowed_purposes': agent.allowed_purposes,
                  'default_data_classification': agent.default_data_classification,
                  'risk_level': agent.risk_level,
                  'approval_requirements': agent.approval_requirements,
                  'metadata': agent.metadata
              }

      # ==========================================================
      # Persistence & Utilities
      # ==========================================================

      def export_registry(self, format: str = 'json') -> str:
          """
          Export the full registry in specified format.

          :param format: Output format ('json' or 'csv')
          :return: Export string
          """
          with _registry_lock:
              if format == 'json':
                  agents_data = {}
                  for agent_id, profile in self._agents.items():
                      agent_dict = profile.to_dict()
                      agents_data[agent_id] = agent_dict
                  return json.dumps(agents_data, indent=2, ensure_ascii=False)

              elif format == 'csv':
                  import csv
                  import io

                  output = io.StringIO()
                  writer = csv.writer(output)

                  if self._agents:
                      first = list(self._agents.values())[0]
                      writer.writerow([
                          'agent_id', 'agent_name', 'owner', 'department',
                          'risk_level', 'approved_providers', 'allowed_models',
                          'allowed_purposes', 'default_data_classification',
                          'approval_requirements', 'metadata'
                      ])

                      for agent_id, profile in self._agents.items():
                          writer.writerow([
                              agent_id,
                              profile.agent_name,
                              profile.owner,
                              profile.department,
                              profile.risk_level,
                              ', '.join(profile.allowed_providers),
                              ', '.join(profile.allowed_models),
                              ', '.join(profile.allowed_purposes),
                              profile.default_data_classification,
                              profile.approval_requirements,
                              json.dumps(profile.metadata)
                          ])

                  return output.getvalue()

              else:
                  raise ValueError(f"Unsupported export format: {format}")

      def get_registry_stats(self) -> dict:
          """Get statistics about the agent registry."""
          with _registry_lock:
              total = len(self._agents)

              if total == 0:
                  return {
                      'total_agents': 0,
                      'by_department': {},
                      'by_risk_level': {},
                      'by_provider': {},
                      'avg_allowed_providers': 0
                  }

              by_department = {}
              by_risk_level = {}
              provider_counts = {}

              for profile in self._agents.values():
                  # Department counts
                  dept = profile.department.lower()
                  by_department[dept] = by_department.get(dept, 0) + 1

                  # Risk level counts
                  risk = profile.risk_level
                  by_risk_level[risk] = by_risk_level.get(risk, 0) + 1

                  # Provider counts
                  for prov in profile.allowed_providers:
                      provider_counts[prov] = provider_counts.get(prov, 0) + 1

              avg_providers = sum(len(p.allowed_providers) for p in self._agents.values()) / total

              return {
                  'total_agents': total,
                  'by_department': by_department,
                  'by_risk_level': by_risk_level,
                  'by_provider': provider_counts,
                  'avg_allowed_providers': round(avg_providers, 2)
              }


  # ============================================================
  # Demo / Test Code
  # ============================================================

if __name__ == "__main__":
      print("=" * 70)
      print("AGENT REGISTRY PRODUCTION HARDENING DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize registry
      registry = AgentRegistry(storage_path="agent_registry.json")

      # Create sample agent profiles
      print("Creating agent profiles...\n")

      agent1 = AgentProfile(
          agent_id="support-bot-01",
          agent_name="Customer Support Bot",
          owner="Customer Success Team",
          department="Customer Service",
          risk_level="low",
          allowed_providers=["openai"],
          allowed_models=["gpt-3.5-turbo", "gpt-4"],
          allowed_purposes=["customer_support", "faqs"],
          default_data_classification="internal",
          approval_requirements="none",
          metadata={"description": "Handles customer inquiries and support tickets"}
      )

      agent2 = AgentProfile(
          agent_id="fraud-detector-01",
          agent_name="Fraud Detection Agent",
          owner="Risk Management",
          department="Finance",
          risk_level="high",
          allowed_providers=["openai", "anthropic"],
          allowed_models=["gpt-4", "claude-2"],
          allowed_purposes=["fraud_detection", "risk_assessment"],
          default_data_classification="restricted",
          approval_requirements="director",
          metadata={"description": "Analyzes transactions for potential fraud"}
      )

      agent3 = AgentProfile(
          agent_id="code-assistant-01",
          agent_name="Code Assistant",
          owner="Engineering",
          department="Product",
          risk_level="medium",
          allowed_providers=["openai", "anthropic", "google"],
          allowed_models=["gpt-4", "claude-2", "gemini-pro"],
          allowed_purposes=["code_generation", "code_review", "documentation"],
          default_data_classification="internal",
          approval_requirements="manager",
          metadata={"description": "Assists with code development and review"}
      )

      # Register agents
      print("Registering agents...")
      try:
          registry.register_agent(agent1)
          registry.register_agent(agent2)
          registry.register_agent(agent3)
      except ValueError as e:
          print(f"Registration error: {e}")

      # Demonstrate CRUD operations
      print("\n" + "=" * 70)
      print("CRUD OPERATIONS DEMONSTRATION")
      print("=" * 70)

      # Get agent
      print("\n1. get_agent('support-bot-01'):")
      retrieved = registry.get_agent("support-bot-01")
      if retrieved:
          print(f"   Found: {retrieved.agent_name}")
          print(f"   Risk: {retrieved.risk_level} | Providers: {', '.join(retrieved.allowed_providers)}")

      # Update agent
      print("\n2. update_agent (modify risk_level):")
      try:
          agent1.risk_level = "medium"
          registry.update_agent(agent1)
          updated = registry.get_agent("support-bot-01")
          if updated:
              print(f"   Updated to risk_level: {updated.risk_level}")
      except ValueError as e:
          print(f"   Update error: {e}")

      # Delete agent
      print("\n3. delete_agent('code-assistant-01'):")
      try:
          registry.delete_agent("code-assistant-01")
      except Exception as e:
          print(f"   Delete error: {e}")

      # Query operations
      print("\n4. Query operations:")
      finance_agents = registry.get_agents_by_department("Finance")
      print(f"   Finance department agents: {len(finance_agents)}")
      for a in finance_agents:
          print(f"   - {a.agent_id}: {a.agent_name} (risk: {a.risk_level})")

      high_risk = registry.get_agents_by_risk_level("high")
      print(f"\n   High-risk agents: {len(high_risk)}")

      # Check policy compliance
      print("\n5. Policy compliance check:")
      compliance = registry.check_agent_policy_compliance(
          agent_id="support-bot-01",
          provider="openai",
          model="gpt-4",
          purpose="customer_support"
      )
      print(f"   Agent: {compliance['agent_name']}")
      print(f"   Compliant: {compliance['compliant']}")
      if compliance['errors']:
          print(f"   Errors: {', '.join(compliance['errors'])}")
      if compliance['warnings']:
          print(f"   Warnings: {', '.join(compliance['warnings'])}")

      compliance2 = registry.check_agent_policy_compliance(
          agent_id="fraud-detector-01",
          provider="anthropic",
          model="claude-2",
          purpose="fraud_detection"
      )
      print(f"\n   Agent: {compliance2['agent_name']}")
      print(f"   Compliant: {compliance2['compliant']}")
      if compliance2['errors']:
          print(f"   Errors: {', '.join(compliance2['errors'])}")

      # Execution config
      print("\n6. Execution config:")
      config = registry.get_agent_execution_config("support-bot-01")
      print(f"   Agent: {config['agent_name']}")
      print(f"   Allowed providers: {', '.join(config['allowed_providers'])}")
      print(f"   Allowed models: {', '.join(config['allowed_models'])}")
      print(f"   Allowed purposes: {', '.join(config['allowed_purposes'])}")
      print(f"   Risk level: {config['risk_level']}")
      print(f"   Approval requirements: {config['approval_requirements']}")

      # Registry statistics
      print("\n7. Registry statistics:")
      stats = registry.get_registry_stats()
      print(f"   Total agents: {stats['total_agents']}")
      print(f"   By department: {stats['by_department']}")
      print(f"   By risk level: {stats['by_risk_level']}")
      print(f"   By provider: {stats['by_provider']}")
      print(f"   Average allowed providers: {stats['avg_allowed_providers']}")

      # Export registry
      print("\n8. Export registry (JSON):")
      export = registry.export_registry('json')
      print(f"   (First 200 chars): {export[:200]}...")

      # Clean up test file
      import os
      if os.path.exists("agent_registry.json"):
          os.remove("agent_registry.json")

      print("\n" + "=" * 70)
      print("PROTOTYPE DEMONSTRATION COMPLETE")
      print("=" * 70)
