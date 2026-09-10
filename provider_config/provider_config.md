
  ## ProviderConfigService Design

  Core Data Classes:

   Class                   Purpose
  ━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ProviderRegistration    Metadata for LLM provider (name, endpoint, capabilities)
  ──────────────────────  ───────────────────────────────────────────────────────────────────
   ModelConfig             Model configuration with allow/deny lists for purposes and agents

  Provider Management:

  - register_provider() - Add new LLM provider
  - unregister_provider() - Remove provider, cleanup associated configs
  - Default allowlist: {'openai', 'anthropic', 'google', 'internal'}

  Model Configuration:

  - add_model_config() - Add model with granular allow/deny settings
  - update_model_config() - Modify existing model config
  - remove_model_config() - Remove model configuration
  - Global allowlist/denylist sets for quick validation

  Provider Routing:

   Method                                 Purpose
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   set_agent_provider_routing()           Per-agent, per-purpose provider assignment
  ─────────────────────────────────────  ────────────────────────────────────────────────
   get_agent_provider()                   Retrieve configured provider for agent+purpose
  ─────────────────────────────────────  ────────────────────────────────────────────────
   set_purpose_provider_routing()         Per-purpose provider (with optional model)
  ─────────────────────────────────────  ────────────────────────────────────────────────
   get_purpose_provider()                 Retrieve configured provider for purpose
  ─────────────────────────────────────  ────────────────────────────────────────────────
   get_provider_for_agent_purpose()       Integrated routing decision
  ─────────────────────────────────────  ────────────────────────────────────────────────
   get_routing_info_for_orchestrator()    Format for MCP Orchestrator integration

  Validation:

   Method                           Validates
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   validate_provider_exists()       Provider is registered
  ───────────────────────────────  ─────────────────────────────────────
   validate_model_exists()          Model is configured, returns config
  ───────────────────────────────  ─────────────────────────────────────
   validate_model_for_purpose()     Model allowed for specific purpose
  ───────────────────────────────  ─────────────────────────────────────
   validate_agent_has_provider()    Agent configured for provider

  Integration Points:

  1. AgentRegistry Integration (validate_agent_has_provider):
      - Checks if agent is configured to use a specific provider
      - Can cross-reference agent allowlists from the registry

  2. MCP Orchestrator Integration (get_provider_for_agent_purpose, get_routing_info_for_orchestrator):
      - Determines optimal provider for execute_ai_call()
      - Checks agent-specific routing first, then purpose-level, then fallback
      - Returns routing type and rationale for logging/decisions

  Flow Example:

  User calls: execute_ai_call(agent_id, provider, model, purpose, messages)
       ↓
  ProviderConfigService.get_provider_for_agent_purpose(agent_id, purpose)
       ↓
  Checks: 1. Agent-specific routing → 2. Purpose-level routing → 3. Fallback
       ↓
  Returns: {provider, model, routing_type, rationale}
       ↓
  MCP Orchestrator uses this to determine which API wrapper to call
       ↓
  PolicyEngine evaluates the call against agent's allowlists
       ↓
  AI call executed under governance

  Persistence:

  - JSON file-based (provider_config.json)
  - Automatic save on all CRUD operations
  - Export in JSON or summary format
  - Statistics generation

  Usage Example:

  from provider_config import ProviderConfigService, ProviderRegistration, ModelConfig

  # Initialize
  config_service = ProviderConfigService()

  # Register providers
  config_service.register_provider(ProviderRegistration(
      provider_name="openai", display_name="OpenAI", api_endpoint="..."
  ))

  # Add model config
  config_service.add_model_config(ModelConfig(
      model_name="gpt-4", allowed_purposes=["customer_support"]
  ))

  # Set routing
  config_service.set_agent_provider_routing("agent-01", "customer_support", "openai")
  config_service.set_purpose_provider_routing("customer_support", "openai", "gpt-4")

  # Get routing for orchestrator
  routing = config_service.get_provider_for_agent_purpose("agent-01", "customer_support")
  # routing = {'provider': 'openai', 'model': 'gpt-4', 'routing': 'agent_configured'}
