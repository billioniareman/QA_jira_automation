"""Tests for orchestration layer (routing, state management, nodes)."""

import pytest
from app.orchestration.graph import run_orchestration
from app.orchestration.nodes import planning_node
from app.orchestration.routing import classify_intent
from app.orchestration.state import AgentState, Intent


class _FakeLLMResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, content: str):
        self._content = content

    async def ainvoke(self, _prompt: str):
        return _FakeLLMResponse(self._content)


class TestAgentState:
    """Test AgentState serialization and deserialization."""

    def test_state_creation(self):
        """Test creating an AgentState."""
        state = AgentState(
            user_message="What are open issues?",
            thread_id="thread-123",
            user_id="user-456",
        )
        assert state.user_message == "What are open issues?"
        assert state.thread_id == "thread-123"
        assert state.status == "pending"
        assert len(state.execution_steps) == 0

    def test_state_to_dict(self):
        """Test serialization to dictionary."""
        state = AgentState(
            user_message="Test",
            thread_id="t1",
            user_id="u1",
            intent=Intent.JIRA,
        )
        state.add_execution_step("Started")
        
        state_dict = state.to_dict()
        
        assert state_dict['user_message'] == "Test"
        assert state_dict['intent'] == "jira"
        assert len(state_dict['execution_steps']) == 1

    def test_state_from_dict(self):
        """Test deserialization from dictionary."""
        original = {
            'user_message': 'Test',
            'thread_id': 't1',
            'user_id': 'u1',
            'intent': 'jira',
            'routing_confidence': 0.95,
            'status': 'running',
            'execution_steps': ['[1] Routing complete'],
        }
        
        state = AgentState.from_dict(original)
        
        assert state.user_message == 'Test'
        assert state.intent == Intent.JIRA
        assert state.routing_confidence == 0.95
        assert len(state.execution_steps) == 1

    def test_state_round_trip(self):
        """Test serialization and deserialization round-trip."""
        original = AgentState(
            user_message="Complex query",
            thread_id="t-123",
            user_id="u-456",
            intent=Intent.JIRA,
            plan="Search and summarize",
        )
        original.add_execution_step("Routing")
        original.add_execution_step("Planning")
        
        serialized = original.to_dict()
        deserialized = AgentState.from_dict(serialized)
        
        assert deserialized.user_message == original.user_message
        assert deserialized.intent == original.intent
        assert len(deserialized.execution_steps) == 2


class TestIntentRouting:
    """Test intent detection and routing."""

    def test_intent_jira(self):
        """Test Jira intent detection."""
        intent = Intent.JIRA
        assert intent.value == "jira"
        assert str(intent) == "Intent.JIRA"

    def test_intent_general(self):
        """Test general intent."""
        intent = Intent.GENERAL
        assert intent.value == "general"

    def test_intent_unknown(self):
        """Test unknown intent."""
        intent = Intent.UNKNOWN
        assert intent.value == "unknown"


@pytest.mark.asyncio
async def test_classify_intent_fallback_heuristic(monkeypatch):
    """If LLM routing fails, heuristic fallback should classify Jira intent."""
    from app.orchestration import routing as routing_module

    async def _raise_error(_prompt: str):
        raise RuntimeError('LLM unavailable')

    monkeypatch.setattr(routing_module, '_invoke_llm', _raise_error)

    intent, confidence, _reason = await classify_intent('Show Jira issues assigned to me')

    assert intent == Intent.JIRA
    assert confidence > 0


@pytest.mark.asyncio
async def test_planning_node_includes_azure_search(monkeypatch):
    """Planning should include azure_ai_search when requested by the model."""
    from app.orchestration import nodes as nodes_module

    monkeypatch.setattr(
        nodes_module,
        '_invoke_llm',
        lambda _prompt: _FakeLLM('{"plan":"Search rules","required_tools":["azure_ai_search"],"estimated_steps":1}').ainvoke(''),
    )

    state = AgentState(user_message='Find rules for checkout', thread_id='t1', user_id='u1', intent=Intent.GENERAL)
    planned = await planning_node(state)

    assert 'azure_ai_search' in planned.identified_tools
    assert len(planned.tool_calls) == 1
    assert planned.tool_calls[0].args['query'] == 'Find rules for checkout'


@pytest.mark.asyncio
async def test_run_orchestration_happy_path(monkeypatch):
    """Graph should execute routing->planning->response end-to-end."""
    from app.orchestration import routing as routing_module
    from app.orchestration import nodes as nodes_module
    from app.tools.registry import get_tool_registry
    from app.tools.base import BaseTool, ToolInput, ToolOutput
    from pydantic import Field

    class FakeInput(ToolInput):
        query: str = Field(description='query')
        top: int = Field(default=5, description='top-k')

    class FakeSearchTool(BaseTool):
        def __init__(self):
            super().__init__('azure_ai_search', 'fake search', FakeInput, ToolOutput)

        async def execute(self, **kwargs):
            return ToolOutput(success=True, data=[{'id': '1', 'content': f"hit:{kwargs['query']}"}])

    registry = get_tool_registry()
    registry._tools = {}
    registry.register(FakeSearchTool())

    async def fake_routing(_prompt: str):
        return '{"intent":"general","confidence":0.9,"reasoning":"test"}'

    async def fake_planning(_prompt: str):
        return '{"plan":"use search","required_tools":["azure_ai_search"],"estimated_steps":1}'

    async def fake_response(_prompt: str):
        return 'Found one matching rule.'

    # `classify_intent` path
    monkeypatch.setattr(routing_module, '_invoke_llm', fake_routing)

    # `planning_node` and `response_node` path
    call_counter = {'count': 0}

    async def dispatch(_prompt: str):
        call_counter['count'] += 1
        if call_counter['count'] == 1:
            return await fake_planning(_prompt)
        return await fake_response(_prompt)

    monkeypatch.setattr(nodes_module, '_invoke_llm', dispatch)

    result = await run_orchestration(
        user_message='Find checkout validation rules',
        thread_id='thread-1',
        user_id='user-1',
    )

    assert result.status == 'completed'
    assert result.intent == Intent.GENERAL
    assert result.final_response
    assert 'Response synthesis completed' in result.execution_steps[-1]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
