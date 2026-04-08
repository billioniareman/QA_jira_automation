"""LangGraph orchestration state schema."""

from typing import Optional, Any, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    """User intent routing."""
    JIRA = "jira"
    GENERAL = "general"
    UNKNOWN = "unknown"


@dataclass
class ToolCall:
    """Represents a tool execution request."""
    name: str
    args: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class AgentState:
    """LangGraph agent execution state."""

    # Input
    user_message: str
    thread_id: str
    user_id: str

    # Intent routing
    intent: Optional[Intent] = None
    routing_confidence: float = 0.0

    # Planning
    plan: Optional[str] = None
    identified_tools: List[str] = field(default_factory=list)

    # Tool execution
    tool_calls: List[ToolCall] = field(default_factory=list)
    current_tool_index: int = 0

    # Response synthesis
    final_response: Optional[str] = None
    response_artifacts: List[str] = field(default_factory=list)

    # Metadata
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    execution_steps: List[str] = field(default_factory=list)
    tokens_used: int = 0

    def add_execution_step(self, step: str) -> None:
        """Record execution step."""
        self.execution_steps.append(f"[{len(self.execution_steps) + 1}] {step}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'user_message': self.user_message,
            'thread_id': self.thread_id,
            'user_id': self.user_id,
            'intent': self.intent.value if self.intent else None,
            'routing_confidence': self.routing_confidence,
            'plan': self.plan,
            'identified_tools': self.identified_tools,
            'tool_calls': [
                {
                    'name': tc.name,
                    'args': tc.args,
                    'result': tc.result,
                    'error': tc.error,
                }
                for tc in self.tool_calls
            ],
            'current_tool_index': self.current_tool_index,
            'final_response': self.final_response,
            'response_artifacts': self.response_artifacts,
            'status': self.status,
            'error_message': self.error_message,
            'execution_steps': self.execution_steps,
            'tokens_used': self.tokens_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Reconstruct from dictionary."""
        intent_str = data.get('intent')
        intent = Intent(intent_str) if intent_str else None

        tool_calls = [
            ToolCall(
                name=tc['name'],
                args=tc['args'],
                result=tc.get('result'),
                error=tc.get('error'),
            )
            for tc in data.get('tool_calls', [])
        ]

        return cls(
            user_message=data['user_message'],
            thread_id=data['thread_id'],
            user_id=data['user_id'],
            intent=intent,
            routing_confidence=data.get('routing_confidence', 0.0),
            plan=data.get('plan'),
            identified_tools=data.get('identified_tools', []),
            tool_calls=tool_calls,
            current_tool_index=data.get('current_tool_index', 0),
            final_response=data.get('final_response'),
            response_artifacts=data.get('response_artifacts', []),
            status=data.get('status', 'pending'),
            error_message=data.get('error_message'),
            execution_steps=data.get('execution_steps', []),
            tokens_used=data.get('tokens_used', 0),
        )
