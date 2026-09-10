
  # ============================================================
  # Demo / Test Code
  # ============================================================

if __name__ == "__main__":
      print("=" * 70)
      print("POLICY DSL PRODUCTION HARDENING DEMONSTRATION")
      print("=" * 70)
      print()

      # Initialize parser and compiler
      parser = PolicyDSLParser()
      compiler = DSLCompiler()

      # Test parsing valid DSL rule
      print("Test 1: Parsing valid DSL rule...")
      dsl_text1 = '''
  RULE PII_BLOCK:
      WHEN has_pii and provider in ["openai", "anthropic", "google"]
      THEN BLOCK
      MESSAGE "PII cannot be sent to external LLMs"
  '''
      try:
          parsed = parser.parse(dsl_text1)
          print(f"  Parsed rule: {parsed.name}")
          print(f"  Action: {parsed.action}")
          print(f"  Message: {parsed.message}")
          print(f"  Condition: {parsed.condition}")
      except ValueError as e:
          print(f"  Error: {e}")

      # Test compiling DSL rule
      print("\nTest 2: Compiling DSL rule...")
      try:
          compiled = compiler.compile(parsed)
          print(f"  Compiled rule: {compiled['rule']}")
          print(f"  Action: {compiled['action']}")
          print(f"  Message: {compiled['message']}")

          # Test the compiled function
          test_call = {
              'has_pii': True,
              'provider': 'openai',
              'purpose': 'customer_support'
          }
          result = compiled['fn'](test_call)
          print(f"  Condition result for PII call: {result}")
      except Exception as e:
          print(f"  Error: {e}")

      # Test invalid DSL format
      print("\nTest 3: Invalid DSL format...")
      dsl_text2 = "INVALID DSL TEXT WITHOUT PROPER FORMAT"
      try:
          parsed = parser.parse(dsl_text2)
          print(f"  Should have raised ValueError")
      except ValueError as e:
          print(f"  Correctly raised ValueError: {e}")

      # Test HardenedPolicyEngine
      print("\nTest 4: HardenedPolicyEngine...")
      engine = HardenedPolicyEngine()

      # Add Python rule
      def pii_condition(call):
          pii_indicators = ['ssn', 'credit_card', 'password']
          has_pii = any(indicator in str(call.get('data', '')).lower()
                        for indicator in pii_indicators)
          is_external = call.get('provider', '').lower() in ['openai', 'anthropic', 'google']
          return has_pii and is_external

      engine.add_rule('PII_BLOCK_PYTHON', pii_condition, 'block',
                      message_template="🚫 PII detected in call to {provider}")

      # Add DSL rule
      dsl_text3 = '''
  RULE HIGH_RISK_WARN:
      WHEN risk_level == "high"
      THEN WARN
      MESSAGE "High-risk data requires caution"
  '''
      engine.add_dsl_rule(dsl_text3)

      # Test evaluation
      test_calls = [
          {
              'provider': 'openai',
              'model': 'gpt-4',
              'purpose': 'customer_support',
              'data': 'Customer SSN: 123-45-6789',
              'risk_level': 'medium'
          },
          {
              'provider': 'anthropic',
              'model': 'claude-2',
              'purpose': 'fraud_detection',
              'data': 'Transaction records',
              'risk_level': 'high'
          }
      ]

      for i, call in enumerate(test_calls, 1):
          print(f"  Test Call {i}: provider={call['provider']}, risk={call['risk_level']}")
          results = engine.evaluate(call)
          if results:
              for r in results:
                  print(f"    {r['rule']}: {r['action']} - {r['message']}")
          else:
              print(f"    No rules triggered - ALLOW")

      print("\n" + "=" * 70)
      print("DEMONSTRATION COMPLETE")
      print("=" * 70)

