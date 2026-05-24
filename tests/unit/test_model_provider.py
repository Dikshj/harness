from harness.agents.planner import PlannerAgent
from harness.config import get_settings


def test_agent_uses_minimax_when_only_minimax_key_is_configured(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "mini-test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    agent = PlannerAgent("planner")
    llm = agent.llm()

    assert agent.has_model_credentials() is True
    assert llm.model_name == "MiniMax-M2.7"
    assert str(llm.openai_api_base).rstrip("/") == "https://api.minimax.io/v1"

    get_settings.cache_clear()


def test_agent_uses_openai_settings_before_minimax(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("MINIMAX_API_KEY", "mini-test-key")
    get_settings.cache_clear()

    agent = PlannerAgent("planner")
    llm = agent.llm()

    assert llm.model_name == "gpt-4o"
    assert str(llm.openai_api_base).rstrip("/") == "https://example.test/v1"

    get_settings.cache_clear()
