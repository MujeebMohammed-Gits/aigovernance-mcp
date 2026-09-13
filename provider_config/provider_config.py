# -*- coding: utf-8 -*-
"""
Provider Configuration Service - Production Hardened
Manages provider registration, model allow/denylists, and per-agent/purpose routing
"""
import json
import logging
import os
import threading
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

  # Thread lock for concurrent access
_provider_lock = threading.Lock()


  # ============================================================
  # Provider Configuration Data Classes
  # ============================================================

@dataclass
class ProviderRegistration:
      """
      Metadata for a registered LLM provider.
      """
      provider_name: str
      display_name: str
      api_endpoint: str
      supports_streaming: bool = True
      default_timeout_seconds: int = 60
      max_retries: int = 3
      timeout_backoff_factor: float = 2.0
      metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelConfig:
      """
      Configuration for a specific model with allow/deny settings.
      """
      model_name: str
      display_name: str
      max_tokens: Optional[int] = None
      max_cost_usd_per_call: Optional[float] = None
      max_latency_ms: Optional[int] = None
      allowed_purposes: List[str] = field(default_factory=list)
      denied_purposes: List[str] = field(default_factory=list)
      allowed_agents: List[str] = field(default_factory=list)  # agent IDs
      denied_agents: List[str] = field(default_factory=list)  # agent IDs
      metadata: Dict[str, Any] = field(default_factory=dict)


  # ============================================================
  # ProviderConfigService Class
  # ============================================================

class ProviderConfigService:
      """
      Production-hardened service managing LLM provider configurations,
      model allow/deny lists, and per-agent/purpose routing.
      """

      # Class-level default allowlists/denylists
      _default_provider_allowlist: Set[str] = {'openai', 'anthropic', 'google', 'internal'}
      _default_timeout_config: Dict[str, int] = {
          'openai': 60,
          'anthropic': 90,
          'google': 60,
          'internal': 30
      }

      def __init__(self, storage_path: str = "provider_config.json"):
          self.storage_path = storage_path
          self._providers: Dict[str, ProviderRegistration] = {}
          self._model_configs: Dict[str, ModelConfig] = {}
          self._per_agent_routing: Dict[str, Dict[str, str]] = {}  # agent_id -> {purpose: provider}
          self._per_purpose_routing: Dict[str, Dict[str, str]] = {}  # purpose -> {provider: preferred_model}
          self._model_allowlist: Set[str] = set()
          self._model_denylist: Set[str] = set()
          self._load_from_disk()

      def _load_from_disk(self):
          """Load configuration from persistent storage with error handling."""
          try:
              if os.path.exists(self.storage_path):
                  with open(self.storage_path, 'r', encoding='utf-8') as f:
                      data = json.load(f)
                      # Load providers
                      for prov_name, prov_data in data.get('providers', {}).items():
                          try:
                              self._providers[prov_name] = ProviderRegistration(**prov_data)
                          except Exception as e:
                              logger.error(f"Failed to load provider {prov_name}: {e}")

                      # Load model configs
                      for model_name, model_data in data.get('model_configs', {}).items():
                          try:
                              self._model_configs[model_name] = ModelConfig(**model_data)
                          except Exception as e:
                              logger.error(f"Failed to load model config {model_name}: {e}")

                      # Load routing configs
                      self._per_agent_routing = data.get('per_agent_routing', {})
                      self._per_purpose_routing = data.get('per_purpose_routing', {})

                      # Load allow/denylists
                      self._model_allowlist = set(data.get('model_allowlist', []))
                      self._model_denylist = set(data.get('model_denylist', []))
          except (json.JSONDecodeError, IOError) as e:
              logger.error(f"Could not load provider config from {self.storage_path}: {e}")

      def _save_to_disk(self):
          """Persist configuration to disk with error handling and atomic writes."""
          try:
              with _provider_lock:
                  data = {
                      'providers': {name: asdict(provider) for name, provider in self._providers.items()},
                      'model_configs': {name: asdict(config) for name, config in self._model_configs.items()},
                      'per_agent_routing': self._per_agent_routing,
                      'per_purpose_routing': self._per_purpose_routing,
                      'model_allowlist': list(self._model_allowlist),
                      'model_denylist': list(self._model_denylist),
                  }
                  # Write to temp file first, then rename for atomicity
                  temp_path = self.storage_path + '.tmp'
                  with open(temp_path, 'w', encoding='utf-8') as f:
                      json.dump(data, f, indent=2, ensure_ascii=False)
                  os.replace(temp_path, self.storage_path)
          except IOError as e:
              logger.error(f"Could not save provider config to disk: {e}")

      # ==========================================================
      # Provider Registration
      # ==========================================================

      def register_provider(self, provider: ProviderRegistration) -> bool:
          """
          Register a new LLM provider with validation.

          :param provider: ProviderRegistration instance
          :return: True if successfully registered
          :raises ValueError: If provider already exists
          """
          with _provider_lock:
              if provider.provider_name in self._providers:
                  logger.error(f"Provider '{provider.provider_name}' already exists.")
                  raise ValueError(f"Provider '{provider.provider_name}' already exists.")

              # Set default timeout if not specified
              if provider.default_timeout_seconds is None:
                  provider.default_timeout_seconds = self._default_timeout_config.get(
                      provider.provider_name, 60
                  )

              self._providers[provider.provider_name] = provider

              # Auto-add to default allowlist if not already there
              if provider.provider_name not in self._default_provider_allowlist:
                  self._default_provider_allowlist.add(provider.provider_name)

              self._save_to_disk()
              logger.info(f"Provider registered: {provider.provider_name} ({provider.display_name})")
              return True

      def unregister_provider(self, provider_name: str) -> bool:
          """
          Unregister a provider with thread safety.

          :param provider_name: Name of provider to remove
          :return: True if successfully removed
          """
          with _provider_lock:
              if provider_name not in self._providers:
                  logger.warning(f"Provider '{provider_name}' not found for unregistration.")
                  return False

              # Remove from default allowlist if it was there
              self._default_provider_allowlist.discard(provider_name)

              # Remove associated model configs
              models_to_remove = [m for m in self._model_configs if m.startswith(provider_name + '-')]
              for model in models_to_remove:
                  del self._model_configs[model]

              # Remove from per-agent routing
              for agent_id in list(self._per_agent_routing.keys()):
                  self._per_agent_routing[agent_id].pop(provider_name, None)

              # Remove from per-purpose routing
              for purpose in list(self._per_purpose_routing.keys()):
                  self._per_purpose_routing[purpose].pop(provider_name, None)

              del self._providers[provider_name]
              self._save_to_disk()
              logger.info(f"Provider unregistered: {provider_name}")
              return True

      # ==========================================================
      # Model Allow/Denylist Management
      # ==========================================================

      def set_model_allowlist(self, allowlist: Set[str]):
          """Set the global model allowlist with logging."""
          with _provider_lock:
              self._model_allowlist = allowlist
              self._save_to_disk()
              logger.info(f"Model allowlist set: {len(allowlist)} models")

      def set_model_denylist(self, denylist: Set[str]):
          """Set the global model denylist with logging."""
          with _provider_lock:
              self._model_denylist = denylist
              self._save_to_disk()
              logger.info(f"Model denylist set: {len(denylist)} models")

      def add_model_config(self, model_config: ModelConfig) -> bool:
          """
          Add a model configuration with validation and thread safety.

          :param model_config: ModelConfig instance
          :return: True if successfully added
          :raises ValueError: If model already exists
          """
          with _provider_lock:
              if model_config.model_name in self._model_configs:
                  logger.error(f"Model '{model_config.model_name}' already exists.")
                  raise ValueError(f"Model '{model_config.model_name}' already exists. Use update_model_config().")

              self._model_configs[model_config.model_name] = model_config

              # Update global allow/denylists
              if model_config.model_name not in self._model_allowlist:
                  self._model_allowlist.add(model_config.model_name)

              # Handle denied purposes/agents
              for purpose in model_config.denied_purposes:
                  if purpose not in self._per_purpose_routing:
                      self._per_purpose_routing[purpose] = {}
                  self._per_purpose_routing[purpose][model_config.model_name] = 'denied'

              for agent_id in model_config.denied_agents:
                  if agent_id not in self._per_agent_routing:
                      self._per_agent_routing[agent_id] = {}
                  self._per_agent_routing[agent_id][model_config.model_name] = 'denied'

              self._save_to_disk()
              logger.info(f"Model config added: {model_config.model_name}")
              return True

      def update_model_config(self, model_config: ModelConfig) -> bool:
          """
          Update an existing model configuration with thread safety.

          :param model_config: ModelConfig with updated values
          :return: True if successfully updated
          :raises ValueError: If model doesn't exist
          """
          with _provider_lock:
              if model_config.model_name not in self._model_configs:
                  logger.error(f"Model '{model_config.model_name}' does not exist.")
                  raise ValueError(f"Model '{model_config.model_name}' does not exist.")

              old_config = self._model_configs[model_config.model_name]

              # Remove old denied entries
              for purpose in old_config.denied_purposes:
                  if purpose in self._per_purpose_routing:
                      self._per_purpose_routing[purpose].pop(model_config.model_name, None)

              for agent_id in old_config.denied_agents:
                  if agent_id in self._per_agent_routing:
                      self._per_agent_routing[agent_id].pop(model_config.model_name, None)

              # Update the config
              self._model_configs[model_config.model_name] = model_config

              # Add new denied entries
              for purpose in model_config.denied_purposes:
                  if purpose not in self._per_purpose_routing:
                      self._per_purpose_routing[purpose] = {}
                  self._per_purpose_routing[purpose][model_config.model_name] = 'denied'

              for agent_id in model_config.denied_agents:
                  if agent_id not in self._per_agent_routing:
                      self._per_agent_routing[agent_id] = {}
                  self._per_agent_routing[agent_id][model_config.model_name] = 'denied'

              self._save_to_disk()
              logger.info(f"Model config updated: {model_config.model_name}")
              return True

      def remove_model_config(self, model_name: str) -> bool:
          """
          Remove a model configuration with thread safety.

          :param model_name: Model to remove
          :return: True if successfully removed
          """
          with _provider_lock:
              if model_name not in self._model_configs:
                  logger.warning(f"Model '{model_name}' not found for removal.")
                  return False

              removed = self._model_configs.pop(model_name)

              # Remove from allowlist if present
              self._model_allowlist.discard(model_name)

              # Remove denied entries
              for purpose in removed.denied_purposes:
                  if purpose in self._per_purpose_routing:
                      self._per_purpose_routing[purpose].pop(model_name, None)

              for agent_id in removed.denied_agents:
                  if agent_id in self._per_agent_routing:
                      self._per_agent_routing[agent_id].pop(model_name, None)

              self._save_to_disk()
              logger.info(f"Model config removed: {model_name}")
              return True

      # ==========================================================
      # Per-Agent Provider Routing
      # ==========================================================

      def set_agent_provider_routing(self, agent_id: str, purpose: str, provider: str):
          """
          Set per-agent provider routing with validation.

          :param agent_id: Agent identifier
          :param purpose: Business purpose
          :param provider: Preferred provider for this purpose
          """
          with _provider_lock:
              if agent_id not in self._per_agent_routing:
                  self._per_agent_routing[agent_id] = {}

              self._per_agent_routing[agent_id][purpose] = provider
              self._save_to_disk()
              logger.debug(f"Agent routing set: {agent_id} -> {purpose} -> {provider}")

      def get_agent_provider(self, agent_id: str, purpose: str) -> Optional[str]:
          """
          Get the configured provider for an agent and purpose.

          :param agent_id: Agent identifier
          :param purpose: Business purpose
          :return: Provider name or None if not configured
          """
          with _provider_lock:
              agent_routing = self._per_agent_routing.get(agent_id, {})
              return agent_routing.get(purpose)

      def get_agent_all_routings(self, agent_id: str) -> Dict[str, str]:
          """Get all provider routings for an agent with thread safety."""
          with _provider_lock:
              return dict(self._per_agent_routing.get(agent_id, {}))

      # ==========================================================
      # Per-Purpose Provider Routing
      # ==========================================================

      def set_purpose_provider_routing(self, purpose: str, provider: str, model: str = None):
          """
          Set per-purpose provider routing with validation.

          :param purpose: Business purpose
          :param provider: Preferred provider
          :param model: Optional preferred model
          """
          with _provider_lock:
              if purpose not in self._per_purpose_routing:
                  self._per_purpose_routing[purpose] = {}

              if model:
                  self._per_purpose_routing[purpose]['provider'] = provider
                  self._per_purpose_routing[purpose]['model'] = model
              else:
                  self._per_purpose_routing[purpose]['provider'] = provider

              self._save_to_disk()
              model_str = f" and model {model}" if model else ""
              logger.debug(f"Purpose routing set: {purpose} -> {provider}{model_str}")

      def get_purpose_provider(self, purpose: str) -> Optional[Dict[str, str]]:
          """
          Get the configured provider for a purpose with thread safety.

          :param purpose: Business purpose
          :return: Dict with 'provider' and optional 'model', or None
          """
          with _provider_lock:
              purpose_routing = self._per_purpose_routing.get(purpose, {})
              if not purpose_routing:
                  return None

              result = {'provider': purpose_routing.get('provider', '')}
              if 'model' in purpose_routing:
                  result['model'] = purpose_routing['model']
              return result if result['provider'] else None

      def get_purpose_all_routings(self, purpose: str) -> Dict[str, str]:
          """Get all routing for a purpose with thread safety."""
          with _provider_lock:
              return dict(self._per_purpose_routing.get(purpose, {}))

      # ==========================================================
      # Validation
      # ==========================================================

      def validate_provider_exists(self, provider_name: str) -> bool:
          """
          Validate that a provider is registered.

          :param provider_name: Provider to check
          :return: True if provider exists
          """
          exists = provider_name in self._providers
          if not exists:
              logger.warning(f"Provider '{provider_name}' not registered.")
          return exists

      def validate_model_exists(self, model_name: str) -> Tuple[bool, Optional[ModelConfig]]:
          """
          Validate that a model is configured and return its config.

          :param model_name: Model to check
          :return: Tuple of (exists, model_config)
          """
          with _provider_lock:
              config = self._model_configs.get(model_name)
              exists = config is not None
              if not exists:
                  logger.warning(f"Model '{model_name}' not configured.")
              return exists, config

      def validate_agent_has_provider(self, agent_id: str, provider: str) -> bool:
          """
          Check if an agent is configured to use a specific provider.

          :param agent_id: Agent to check
          :param provider: Provider to validate
          :return: True if agent can use this provider
          """
          with _provider_lock:
              # Check global allowlist
              if provider not in self._default_provider_allowlist:
                  # Check per-agent routing
                  agent_routing = self._per_agent_routing.get(agent_id, {})
                  uses_provider = any(p == provider for p in agent_routing.values())
                  if not uses_provider:
                      logger.warning(f"Agent '{agent_id}' not configured for provider '{provider}'.")
                      return False

              # Check model configs for this provider
              for model_name, config in self._model_configs.items():
                  pass

              return True

      def validate_model_for_purpose(self, model_name: str, purpose: str) -> dict:
          """
          Validate that a model is allowed for a specific purpose.

          :param model_name: Model to check
          :param purpose: Business purpose
          :return: Validation result dictionary
          """
          exists, config = self.validate_model_exists(model_name)

          if not exists:
              return {
                  'valid': False,
                  'model': model_name,
                  'purpose': purpose,
                  'errors': [f"Model '{model_name}' not configured"]
              }

          errors = []
          warnings = []

          # Check if purpose is explicitly denied
          if purpose in config.denied_purposes:
              errors.append(f"Purpose '{purpose}' is explicitly denied for model '{model_name}'")

          # Check if purpose is allowed (or not restricted)
          if config.allowed_purposes and purpose not in config.allowed_purposes:
              errors.append(f"Purpose '{purpose}' not in allowed list for model '{model_name}'")

          valid = len(errors) == 0

          return {
              'valid': valid,
              'model': model_name,
              'purpose': purpose,
              'errors': errors,
              'warnings': warnings,
              'allowed_purposes': config.allowed_purposes,
              'denied_purposes': config.denied_purposes
          }

      # ==========================================================
      # Integration Points
      # ==========================================================

      def get_provider_for_agent_purpose(self, agent_id: str, purpose: str) -> Optional[Dict[str, Any]]:
          """
          Integration point with MCP Orchestrator.

          Determines the best provider for an agent to use for a given purpose,
          checking routing config, allowlists, and model availability.

          :param agent_id: Agent identifier
          :param purpose: Business purpose
          :return: Dict with provider, model, and rationale, or None
          """
          with _provider_lock:
              # First check per-agent routing
              agent_provider = self.get_agent_provider(agent_id, purpose)
              if agent_provider:
                  # Check if model is also specified in agent routing
                  agent_routing = self._per_agent_routing.get(agent_id, {})
                  model = None
                  for p, val in agent_routing.items():
                      if p == purpose:
                          # Try to extract model from value
                          if ':' in val:
                              parts = val.split(':', 1)
                              model = parts[1] if len(parts) > 1 else None
                          break

                  # Validate the model exists and is allowed
                  model_valid, model_config = self.validate_model_exists(model) if model else (True, None)

                  if model_valid or not model:
                      return {
                          'provider': agent_provider,
                          'model': model,
                          'routing': 'agent_configured',
                          'rationale': f"Provider {agent_provider} configured for agent {agent_id} purpose {purpose}"
                      }

              # Check per-purpose routing
              purpose_routing = self.get_purpose_provider(purpose)
              if purpose_routing:
                  provider = purpose_routing['provider']
                  model = purpose_routing.get('model')

                  # Validate provider exists
                  if self.validate_provider_exists(provider):
                      # Validate model if specified
                      if model:
                          model_valid, _ = self.validate_model_exists(model)
                          if model_valid:
                              return {
                                  'provider': provider,
                                  'model': model,
                                  'routing': 'purpose_configured',
                                  'rationale': f"Provider {provider} configured for purpose {purpose}"
                              }
                      elif not model:
                          # No model specified, just provider
                          return {
                              'provider': provider,
                              'model': None,
                              'routing': 'purpose_configured',
                              'rationale': f"Provider {provider} configured for purpose {purpose}"
                          }

              # Fallback: use first available provider
              for prov_name in self._default_provider_allowlist:
                  if self.validate_provider_exists(prov_name):
                      # Get first model configured for this provider
                      pass

                      return {
                          'provider': prov_name,
                          'model': list(self._model_configs.keys())[0] if self._model_configs else None,
                          'routing': 'fallback_available',
                          'rationale': (
                                f"Fallback: Provider {prov_name} with model "
                                f"{list(self._model_configs.keys())[0] if self._model_configs else 'N/A'}"
                            )
                      }

          return None

      def get_routing_info_for_orchestrator(self, agent_id: str, purpose: str) -> dict:
          """
          Get routing information formatted for MCP Orchestrator usage with thread safety.

          :param agent_id: Agent identifier
          :param purpose: Business purpose
          :return: Routing configuration dict
          """
          with _provider_lock:
              # Check agent-specific routing first
              agent_provider = self.get_agent_provider(agent_id, purpose)

              if agent_provider:
                  return {
                      'routing_type': 'agent_specific',
                      'provider': agent_provider,
                      'agent_id': agent_id,
                      'purpose': purpose,
                      'fallback': True
                  }

              # Check purpose-level routing
              purpose_routing = self.get_purpose_provider(purpose)
              if purpose_routing:
                  return {
                      'routing_type': 'purpose_specific',
                      'provider': purpose_routing['provider'],
                      'model': purpose_routing.get('model'),
                      'agent_id': agent_id,
                      'purpose': purpose,
                      'fallback': False
                  }

              # Global fallback
              for prov_name in self._default_provider_allowlist:
                  if self.validate_provider_exists(prov_name):
                      return {
                          'routing_type': 'global_fallback',
                          'provider': prov_name,
                          'agent_id': agent_id,
                          'purpose': purpose,
                          'fallback': True
                      }

              return {
                  'routing_type': 'unconfigured',
                  'provider': None,
                  'agent_id': agent_id,
                  'purpose': purpose,
                  'fallback': False,
                  'errors': ['No provider configured for agent and purpose']
              }

      # ==========================================================
      # Persistence & Utilities
      # ==========================================================

      def export_config(self, format: str = 'json') -> str:
          """
          Export the full configuration with thread safety.

          :param format: Output format ('json' or 'summary')
          :return: Export string
          """
          with _provider_lock:
              if format == 'json':
                  data = {
                      'providers': {name: asdict(provider) for name, provider in self._providers.items()},
                      'model_configs': {name: asdict(config) for name, config in self._model_configs.items()},
                      'per_agent_routing': self._per_agent_routing,
                      'per_purpose_routing': self._per_purpose_routing,
                      'model_allowlist': list(self._model_allowlist),
                      'model_denylist': list(self._model_denylist),
                  }
                  return json.dumps(data, indent=2, ensure_ascii=False)

              elif format == 'summary':
                  lines = []
                  lines.append("=" * 60)
                  lines.append("PROVIDER CONFIGURATION SERVICE - SUMMARY")
                  lines.append("=" * 60)
                  lines.append("")

                  lines.append("REGISTERED PROVIDERS:")
                  for name, provider in self._providers.items():
                      lines.append(f"  â€¢ {name}: {provider.display_name}")
                      lines.append(f"    Endpoint: {provider.api_endpoint}")
                      lines.append(f"    Timeout: {provider.default_timeout_seconds}s")
                  lines.append("")

                  lines.append("MODEL CONFIGURATIONS:")
                  for name, config in self._model_configs.items():
                      lines.append(f"  â€¢ {name}: {config.display_name}")
                      lines.append(f"    Allowed purposes: {', '.join(config.allowed_purposes) if config.allowed_purposes else 'All'}")
                      lines.append(f"    Denied purposes: {', '.join(config.denied_purposes) if config.denied_purposes else 'None'}")
                  lines.append("")

                  lines.append("PER-AGENT ROUTING:")
                  for agent_id, routings in self._per_agent_routing.items():
                      for purpose, provider in routings.items():
                          lines.append(f"  â€¢ {agent_id} -> {purpose} -> {provider}")
                  lines.append("")

                  lines.append("PER-PURPOSE ROUTING:")
                  for purpose, routing in self._per_purpose_routing.items():
                      provider = routing.get('provider', 'N/A')
                      model = routing.get('model', 'N/A')
                      lines.append(f"  â€¢ {purpose} -> {provider} (model: {model})")
                  lines.append("")

                  lines.append("GLOBAL SETTINGS:")
                  lines.append(f"  â€¢ Model allowlist: {len(self._model_allowlist)} models")
                  lines.append(f"  â€¢ Model denylist: {len(self._model_denylist)} models")
                  lines.append(f"  â€¢ Provider allowlist: {len(self._default_provider_allowlist)} providers")

                  lines.append("=" * 60)
                  return "\n".join(lines)

              else:
                  raise ValueError(f"Unsupported export format: {format}")

      def get_registry_stats(self) -> dict:
          """Get statistics about the provider configuration."""
          with _provider_lock:
              return {
                  'total_providers': len(self._providers),
                  'total_model_configs': len(self._model_configs),
                  'total_agents_routed': len(self._per_agent_routing),
                  'total_purposes_routed': len(self._per_purpose_routing),
                  'model_allowlist_size': len(self._model_allowlist),
                  'model_denylist_size': len(self._model_denylist),
                  'default_provider_allowlist': list(self._default_provider_allowlist)
              }

