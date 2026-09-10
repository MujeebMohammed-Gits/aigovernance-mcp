import sys, os

# Ensure project root is in Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR
sys.path.insert(0, PROJECT_ROOT)

from agent_registry.agent_registry import AgentRegistry
from agent_registry.agent_registry import AgentProfile

registry = AgentRegistry(storage_path="agent_registry.json")

profile = AgentProfile(
    agent_id="test-agent-001",
    agent_name="Test Agent 001",
    owner="Mujeeb",
    department="Engineering",
    risk_level="low",
    allowed_providers=["openai"],
    allowed_models=["gpt-4"],
    allowed_purposes=["testing", "general"],
    default_data_classification="internal",
    approval_requirements="none",
    metadata={"created_by": "register_test_agent.py"}
)

registry.register_agent(profile)

print("Agent registered successfully.")
