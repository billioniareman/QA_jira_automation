"""LangGraph assembly for chat orchestration."""

from __future__ import annotations

import importlib
from typing import TypedDict

from .nodes import planning_node, response_node, routing_node, tool_execution_node
from .state import AgentState, Intent


class GraphState(TypedDict):
    """LangGraph state wrapper around `AgentState`."""

    agent_state: AgentState


async def _routing_graph_node(state: GraphState) -> GraphState:
    state['agent_state'] = await routing_node(state['agent_state'])
    return state


async def _planning_graph_node(state: GraphState) -> GraphState:
    state['agent_state'] = await planning_node(state['agent_state'])
    return state


async def _tools_graph_node(state: GraphState) -> GraphState:
    state['agent_state'] = await tool_execution_node(state['agent_state'])
    return state


async def _response_graph_node(state: GraphState) -> GraphState:
    state['agent_state'] = await response_node(state['agent_state'])
    return state


def _route_after_routing(state: GraphState) -> str:
    agent_state = state['agent_state']
    if agent_state.status == 'failed':
        return 'response'

    if agent_state.intent in {Intent.JIRA, Intent.GENERAL}:
        return 'planning'

    return 'response'


def _route_after_planning(state: GraphState) -> str:
    if state['agent_state'].tool_calls:
        return 'tools'
    return 'response'


def create_orchestration_graph():
    """Create compiled LangGraph instance for the chat agent."""
    langgraph_graph = importlib.import_module('langgraph.graph')
    END = langgraph_graph.END
    START = langgraph_graph.START
    StateGraph = langgraph_graph.StateGraph

    graph = StateGraph(GraphState)

    graph.add_node('routing', _routing_graph_node)
    graph.add_node('planning', _planning_graph_node)
    graph.add_node('tools', _tools_graph_node)
    graph.add_node('response', _response_graph_node)

    graph.add_edge(START, 'routing')
    graph.add_conditional_edges(
        'routing',
        _route_after_routing,
        {
            'planning': 'planning',
            'response': 'response',
        },
    )
    graph.add_conditional_edges(
        'planning',
        _route_after_planning,
        {
            'tools': 'tools',
            'response': 'response',
        },
    )
    graph.add_edge('tools', 'response')
    graph.add_edge('response', END)

    return graph.compile()


_compiled_graph = None


def get_orchestration_graph():
    """Get cached compiled graph instance."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = create_orchestration_graph()
    return _compiled_graph


async def run_orchestration(
    user_message: str,
    thread_id: str,
    user_id: str,
) -> AgentState:
    """Run the orchestration graph from fresh `AgentState`."""
    graph = get_orchestration_graph()
    initial_state: GraphState = {
        'agent_state': AgentState(
            user_message=user_message,
            thread_id=thread_id,
            user_id=user_id,
        )
    }

    final_state: GraphState = await graph.ainvoke(initial_state)
    return final_state['agent_state']
