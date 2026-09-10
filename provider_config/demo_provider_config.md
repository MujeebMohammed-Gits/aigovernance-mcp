  # ============================================================
  # Demonstration & Testing
  # ============================================================

  if __name__ == "__main__":
      print("=" * 70)
      print("PROVIDER CONFIGURATION SERVICE DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize service
      config_service = ProviderConfigService(storage_path="test_provider_config.json")

      # Register providers
      print("📝 Registering providers...\n")

      openai_reg = ProviderRegistration(
          provider_name="openai",
          display_name="OpenAI",
          api_endpoint="https://api.openai.com/v1",
          supports_streaming=True,
          default_timeout_seconds=60
      )

      anthropic_reg = ProviderRegistration(
          provider_name="anthropic",
          display_name="Anthropic",
          api_endpoint="https://api.anthropic.com/v1",
          supports_streaming=True,
          default_timeout_seconds=90
      )

      google_reg = ProviderRegistration(
          provider_name="google",
          display_name="Google Gemini",
          api_endpoint="https://generativelanguage.googleapis.com/v1beta",
          supports_streaming=True,
          default_timeout_seconds=60
      )

      try:
          config_service.register_provider(openai_reg)
          config_service.register_provider(anthropic_reg)
          config_service.register_provider(google_reg)
      except ValueError as e:
          print(f"❌ Registration error: {e}")

      # Add model configurations
      print("\n🤖 Adding model configurations...\n")

      gpt4 = ModelConfig(
          model_name="gpt-4",
          display_name="GPT-4",
          max_tokens=8192,
          max_cost_usd_per_call=0.12,
          allowed_purposes=["customer_support", "code_generation", "analysis"],
          denied_purposes=["fraud_detection"],  # Explicitly deny for high-risk
          allowed_agents=["support-bot-01", "dev-assistant"],
          metadata={"modalities": ["text"], "context_window": 8192}
      )

      claude2 = ModelConfig(
          model_name="claude-2",
          display_name="Claude 2",
          max_tokens=100000,
          max_cost_usd_per_call=0.25,
          allowed_purposes=["fraud_detection", "risk_assessment", "analysis"],
          denied_purposes=["code_generation"],  # Don't generate code
          allowed_agents=["fraud-detector-01"],
          metadata={"modalities": ["text"], "context_window": 100000}
      )

      gemini_pro = ModelConfig(
          model_name="gemini-pro",
          display_name="Gemini Pro",
          max_tokens=30720,
          max_cost_usd_per_call=0.05,
          allowed_purposes=["analysis", "summarization"],
          allowed_agents=["data-insights"],
          metadata={"modalities": ["text"], "context_window": 30720}
      )

      try:
          config_service.add_model_config(gpt4)
          config_service.add_model_config(claude2)
          config_service.add_model_config(gemini_pro)
      except ValueError as e:
          print(f"❌ Model config error: {e}")

      # Set per-agent routing
      print("🔄 Setting per-agent provider routing...\n")

      # Support bot uses OpenAI for customer support
      config_service.set_agent_provider_routing("support-bot-01", "customer_support", "openai")

      # Fraud detector uses Anthropic for fraud detection
      config_service.set_agent_provider_routing("fraud-detector-01", "fraud_detection", "anthropic")

      # Code assistant uses OpenAI for code generation
      config_service.set_agent_provider_routing("dev-assistant", "code_generation", "openai")

      # Set per-purpose routing
      print("🎯 Setting per-purpose provider routing...\n")

      # Customer support purpose: OpenAI GPT-4
      config_service.set_purpose_provider_routing("customer_support", "openai", "gpt-4")

      # Fraud detection purpose: Anthropic Claude 2
      config_service.set_purpose_provider_routing("fraud_detection", "anthropic", "claude-2")

      # Code generation purpose: OpenAI GPT-4
      config_service.set_purpose_provider_routing("code_generation", "openai", "gpt-4")

      # Analysis purpose: Google Gemini Pro
      config_service.set_purpose_provider_routing("analysis", "google", "gemini-pro")

      # Demonstrate validation
      print("✅ Validation demonstrations...\n")

      # Validate provider exists
      print("1. Validate provider exists:")
      print(f"   openai: {config_service.validate_provider_exists('openai')}")
      print(f"   unknown-provider: {config_service.validate_provider_exists('unknown-provider')}")

      # Validate model exists
      print("\n2. Validate model exists:")
      exists, model_config = config_service.validate_model_exists("gpt-4")
      print(f"   gpt-4 exists: {exists}")
      if exists:
          print(f"   Allowed purposes: {', '.join(model_config.allowed_purposes)}")

      exists, _ = config_service.validate_model_exists("non-existent-model")
      print(f"   non-existent-model exists: {exists}")

      # Validate model for purpose
      print("\n3. Validate model for purpose:")
      gpt4_purpose = config_service.validate_model_for_purpose("gpt-4", "customer_support")
      print(f"   gpt-4 for customer_support: valid={gpt4_purpose['valid']}")
      if gpt4_purpose['errors']:
          print(f"   Errors: {', '.join(gpt4_purpose['errors'])}")

      gpt4_fraud = config_service.validate_model_for_purpose("gpt-4", "fraud_detection")
      print(f"   gpt-4 for fraud_detection: valid={gpt4_fraud['valid']}")
      if gpt4_fraud['errors']:
          print(f"   Errors: {', '.join(gpt4_fraud['errors'])}")

      # Get provider for agent and purpose
      print("\n4. Get provider for agent and purpose:")
      provider_info = config_service.get_provider_for_agent_purpose("support-bot-01", "customer_support")
      if provider_info:
          print(f"   support-bot-01 + customer_support: {provider_info['provider']} ({provider_info['routing']})")

      provider_info2 = config_service.get_provider_for_agent_purpose("fraud-detector-01", "fraud_detection")
      if provider_info2:
          print(f"   fraud-detector-01 + fraud_detection: {provider_info2['provider']} ({provider_info2['routing']})")

      # Get routing info for orchestrator
      print("\n5. Routing info for MCP Orchestrator:")
      routing = config_service.get_routing_info_for_orchestrator("support-bot-01", "customer_support")
      print(f"   support-bot-01 + customer_support: {routing['routing_type']} - {routing['provider']}")

      routing2 = config_service.get_routing_info_for_orchestrator("fraud-detector-01", "fraud_detection")
      print(f"   fraud-detector-01 + fraud_detection: {routing2['routing_type']} - {routing2['provider']}")

      routing3 = config_service.get_routing_info_for_orchestrator("dev-assistant", "code_generation")
      print(f"   dev-assistant + code_generation: {routing3['routing_type']} - {routing3['provider']}")

      # Export configuration
      print("\n6. Export configuration (summary):")
      export = config_service.export_config('summary')
      print(export[:500] + "..." if len(export) > 500 else export)

      # Export JSON
      json_export = config_service.export_config('json')
      print(f"\n   JSON export size: {len(json_export)} characters")

      # Statistics
      print("\n7. Registry statistics:")
      stats = config_service.get_registry_stats()
      for key, value in stats.items():
          print(f"   • {key}: {value}")

      # Clean up test file
      import os
      if os.path.exists("test_provider_config.json"):
          os.remove("test_provider_config.json")

      print("\n" + "=" * 70)
      print("PROTOTYPE DEMONSTRATION COMPLETE")
      print("=" * 70)
