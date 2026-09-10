  # ============================================================
  # Demo / Test Code
  # ============================================================

try:
    from .provider_config import ModelConfig, ProviderConfigService, ProviderRegistration
except ImportError:
    from provider_config import ModelConfig, ProviderConfigService, ProviderRegistration

if __name__ == "__main__":
      print("=" * 70)
      print("PROVIDER CONFIGURATION SERVICE DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize provider config service
      pc_service = ProviderConfigService(storage_path="provider_config.json")

      # Register providers
      print("Registering providers...")
      try:
          pc_service.register_provider(ProviderRegistration(
              provider_name="openai",
              display_name="OpenAI",
              api_endpoint="https://api.openai.com/v1"
          ))
          pc_service.register_provider(ProviderRegistration(
              provider_name="anthropic",
              display_name="Anthropic",
              api_endpoint="https://api.anthropic.com/v1"
          ))
          pc_service.register_provider(ProviderRegistration(
              provider_name="google",
              display_name="Google AI",
              api_endpoint="https://generativelanguage.googleapis.com/v1"
          ))
          pc_service.register_provider(ProviderRegistration(
              provider_name="internal",
              display_name="Internal LLM",
              api_endpoint="http://localhost:8000/internal-llm"
          ))
      except ValueError as e:
          print(f"âŒ Error: {e}")

      # Set model allowlist/denylist
      print("\nSetting model allowlist/denylist...")
      pc_service.set_model_allowlist({"gpt-4", "gpt-3.5-turbo", "claude-2", "gemini-pro"})
      pc_service.set_model_denylist({"gpt-4-32k"})

      # Add model configurations
      print("\nAdding model configurations...")
      try:
          pc_service.add_model_config(ModelConfig(
              model_name="gpt-4",
              display_name="GPT-4",
              max_tokens=8192,
              max_cost_usd_per_call=0.06,
              allowed_purposes=["customer_support", "code_generation"],
              denied_purposes=["fraud_detection"]
          ))
          pc_service.add_model_config(ModelConfig(
              model_name="claude-2",
              display_name="Claude 2",
              max_tokens=100000,
              max_cost_usd_per_call=0.08,
              allowed_purposes=["fraud_detection"],
              denied_purposes=["code_generation"]
          ))
          pc_service.add_model_config(ModelConfig(
              model_name="gemini-pro",
              display_name="Gemini Pro",
              max_tokens=30720,
              max_cost_usd_per_call=0.05,
              allowed_purposes=["data_analysis"]
          ))
      except ValueError as e:
          print(f"âŒ Error: {e}")

      # Set agent provider routing
      print("\nSetting agent provider routing...")
      pc_service.set_agent_provider_routing("support-bot-01", "customer_support", "openai")
      pc_service.set_agent_provider_routing("fraud-detector-01", "fraud_detection", "anthropic")

      # Set purpose provider routing
      print("\nSetting purpose provider routing...")
      pc_service.set_purpose_provider_routing("customer_support", "openai", "gpt-4")
      pc_service.set_purpose_provider_routing("fraud_detection", "anthropic", "claude-2")

      # Get routing info for orchestrator
      print("\nGetting routing info for orchestrator...")
      routing = pc_service.get_routing_info_for_orchestrator("support-bot-01", "customer_support")
      print(f"Agent: {routing.get('agent_id')} | Purpose: {routing.get('purpose')}")
      print(f"Provider: {routing.get('provider')} (type: {routing.get('routing_type')})")

      routing2 = pc_service.get_routing_info_for_orchestrator("fraud-detector-01", "fraud_detection")
      print(f"\nAgent: {routing2.get('agent_id')} | Purpose: {routing2.get('purpose')}")
      print(f"Provider: {routing2.get('provider')} (type: {routing2.get('routing_type')})")

      # Validate model for purpose
      print("\nValidating model for purpose...")
      validation = pc_service.validate_model_for_purpose("gpt-4", "customer_support")
      print(f"Model: {validation['model']} | Purpose: {validation['purpose']} | Valid: {validation['valid']}")
      if validation['errors']:
          print(f"Errors: {', '.join(validation['errors'])}")
      if validation['warnings']:
          print(f"Warnings: {', '.join(validation['warnings'])}")

      # Get registry stats
      print("\nRegistry statistics...")
      stats = pc_service.get_registry_stats()
      for key, value in stats.items():
          print(f"  {key}: {value}")

      # Export configuration
      print("\nExporting configuration (JSON):")
      export = pc_service.export_config('json')
      print(f"  (First 200 chars): {export[:200]}...")

      export_summary = pc_service.export_config('summary')
      print("\nExport configuration (summary):")
      print(export_summary)

      print("\n" + "=" * 70)
      print("DEMONSTRATION COMPLETE")
      print("=" * 70)
