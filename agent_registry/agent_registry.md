  ## Agent Registry Design

  AgentProfile Dataclass - Holds complete agent configuration:

   Field                          Type         Description
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   agent_id                       str          Unique identifier
  ─────────────────────────────  ───────────  ───────────────────────────────
   agent_name                     str          Human-readable name
  ─────────────────────────────  ───────────  ───────────────────────────────
   owner                          str          Team/or person responsible
  ─────────────────────────────  ───────────  ───────────────────────────────
   department                     str          Business unit
  ─────────────────────────────  ───────────  ───────────────────────────────
   risk_level                     str          'low'/'medium'/'high'
  ─────────────────────────────  ───────────  ───────────────────────────────
   allowed_providers              List[str]    Whitelisted LLM providers
  ─────────────────────────────  ───────────  ───────────────────────────────
   allowed_models                 List[str]    Whitelisted model identifiers
  ─────────────────────────────  ───────────  ───────────────────────────────
   allowed_purposes               List[str]    Whitelisted business purposes
  ─────────────────────────────  ───────────  ───────────────────────────────
   default_data_classification    str          Default data sensitivity
  ─────────────────────────────  ───────────  ───────────────────────────────
   approval_requirements          str          Approval workflow level
  ─────────────────────────────  ───────────  ───────────────────────────────
   metadata                       Dict         Custom key-value pairs

  Class-Level Allowlists (shared across all instances):

  - _provider_allowlist: ['openai', 'anthropic', 'google', 'internal']
  - _risk_level_allowlist: ['low', 'medium', 'high']
  - _approval_requirements_allowlist: ['none', 'manager', 'director', 'compliance']

  Validation Triggers:

  - __post_init__() runs validation after dataclass creation
  - Explicit validation in register_agent() and update_agent()
  - Provider/model/purpose allowlist checks
  - Risk level and approval requirements validation

  AgentRegistry Class - Manages collection of AgentProfile objects:

   Method                             Purpose
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   register_agent(profile)            Add new agent (validates ID uniqueness)
  ─────────────────────────────────  ───────────────────────────────────────────────────────────────────────────────────
   get_agent(agent_id)                Retrieve agent by ID
  ─────────────────────────────────  ───────────────────────────────────────────────────────────────────────────────────
   update_agent(profile)              Modify existing agent
  ─────────────────────────────────  ───────────────────────────────────────────────────────────────────────────────────
   delete_agent(agent_id)             Remove agent
  ─────────────────────────────────  ───────────────────────────────────────────────────────────────────────────────────
   get_agents_by_department()         Filter by business unit
  ─────────────────────────────────  ───────────────────────────────────────────────────────────────────────────────────
   get_agents_by_risk_level()         Filter by risk tier
  ─────────────────────────────────  ───────────────────────────────────────────────────────────────────────────────────
   get_agents_by_provider()           Filter by supported LLM
  ─────────────────────────────────  ───────────────────────────────────────────────────────────────────────────────────
   check_agent_policy_compliance()    PolicyEngine integration - validates agent allowlists against proposed AI call
  ─────────────────────────────────  ───────────────────────────────────────────────────────────────────────────────────
   get_agent_execution_config()       MCP Orchestrator integration - provides configured settings for governed AI calls

  
Integration Points:

  1. PolicyEngine Integration (check_agent_policy_compliance):
      - Validates that provider, model, and purpose are in the agent's allowlists
      - Returns compliance status with errors/warnings
      - Can block or warn based on agent risk configuration

  2. MCP Orchestrator Integration (get_agent_execution_config):
      - Provides configured allowlists and risk settings
      - Feeds into execute_ai_call() for pre-flight checks
      - Ensures agents operate within governed boundaries

  Persistence:

  - JSON file-based storage (agent_registry.json)
  - Automatic load on init, save on CRUD operations
  - Export in JSON or CSV format
  - Statistics generation

  Usage Example:

  from agent_registry import AgentRegistry, AgentProfile

  # Initialize registry
  registry = AgentRegistry()

  # Create and register agent
  profile = AgentProfile(
      agent_id="support-bot-01",
      agent_name="Support Bot",
      owner="Customer Success",
      department="Customer Service",
      risk_level="low",
      allowed_providers=["openai"],
      allowed_models=["gpt-3.5-turbo", "gpt-4"],
      allowed_purposes=["customer_support"],
      default_data_classification="internal",
      approval_requirements="none"
  )

  registry.register_agent(profile)

  # Check compliance before AI call
  compliance = registry.check_agent_policy_compliance(
      agent_id="support-bot-01",
      provider="openai",
      model="gpt-4",
      purpose="customer_support"
  )

  if compliance['compliant']:
      # Execute governed AI call via MCP Orchestrator
      config = registry.get_agent_execution_config("support-bot-01")
      # ... pass config to execute_ai_call()

  
# This agent registry module provides the foundation for agent governance, enabling CRUD management, validation, and integration with the policy engine and orchestrator for complete AI call control.
