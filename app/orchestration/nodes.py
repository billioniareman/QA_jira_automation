"""LangGraph node implementations for chat orchestration."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.azure.llm import get_llm
from app.guardrails.guardrails import input_validator, output_validator, tool_execution_guardrails
from app.prompts.prompt_store import PromptStore
from app.tools.registry import register_default_tools

from .routing import classify_intent
from .state import AgentState, Intent, ToolCall


logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract first JSON object from model output."""
    text = (text or '').strip()

    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}

    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


async def _invoke_llm(prompt: str) -> str:
    """Invoke LLM in async-safe way."""
    llm = get_llm()

    if hasattr(llm, 'ainvoke'):
        response = await llm.ainvoke(prompt)
    else:
        response = await asyncio.to_thread(llm.invoke, prompt)

    if hasattr(response, 'content'):
        return str(response.content)
    return str(response)


def _default_tool_args(tool_name: str, user_message: str) -> dict[str, Any]:
    """Generate minimal fallback arguments for known tools."""
    if tool_name == 'azure_ai_search':
        return {'query': user_message, 'top': 5}
    return {}


async def routing_node(agent_state: AgentState) -> AgentState:
    """Route request to Jira/general/unknown branch."""
    agent_state.status = 'running'
    agent_state.add_execution_step('Routing started')

    is_valid, error = input_validator.validate_message(agent_state.user_message)
    if not is_valid:
        agent_state.intent = Intent.UNKNOWN
        agent_state.status = 'failed'
        agent_state.error_message = error
        agent_state.add_execution_step(f'Routing failed: {error}')
        return agent_state

    intent, confidence, reasoning = await classify_intent(agent_state.user_message)

    agent_state.intent = intent
    agent_state.routing_confidence = confidence
    agent_state.add_execution_step(
        f'Routing completed -> intent={intent.value}, confidence={confidence:.2f}, reason={reasoning}'
    )
    return agent_state


async def planning_node(agent_state: AgentState) -> AgentState:
    """Create execution plan and resolve tool calls."""
    agent_state.add_execution_step('Planning started')

    registry = register_default_tools()
    available_tools = [tool.name for tool in registry.list_tools()]

    if not available_tools:
        agent_state.plan = 'No tools registered. Generate direct answer from model context.'
        agent_state.identified_tools = []
        agent_state.add_execution_step('Planning finished (no tools available)')
        return agent_state

    prompt = PromptStore.format_prompt(
        'planning',
        user_message=agent_state.user_message,
        available_tools=', '.join(available_tools),
    )

    try:
        response_text = await _invoke_llm(prompt)
        payload = _extract_json_object(response_text)

        plan = str(payload.get('plan', '')).strip()
        required_tools = payload.get('required_tools') or []

        if not isinstance(required_tools, list):
            required_tools = []

        valid_tools = [
            str(tool_name).strip()
            for tool_name in required_tools
            if str(tool_name).strip() in available_tools
        ]

        # Fallback: retrieval/search intent should use Azure AI Search when possible.
        if not valid_tools and 'azure_ai_search' in available_tools:
            text = agent_state.user_message.lower()
            retrieval_cues = ('search', 'find', 'lookup', 'rule', 'acceptance criteria', 'knowledge')
            if any(cue in text for cue in retrieval_cues):
                valid_tools = ['azure_ai_search']

        agent_state.plan = plan or 'Execute selected tools and synthesize final response.'
        agent_state.identified_tools = valid_tools
        agent_state.tool_calls = [
            ToolCall(name=tool_name, args=_default_tool_args(tool_name, agent_state.user_message))
            for tool_name in valid_tools
        ]
        agent_state.add_execution_step(
            f'Planning completed -> tools={agent_state.identified_tools}'
        )
        return agent_state

    except Exception as exc:
        logger.warning('Planning failed, continuing without tools: %s', exc)
        agent_state.plan = 'Planning failed; continue with direct response.'
        agent_state.identified_tools = []
        agent_state.tool_calls = []
        agent_state.add_execution_step('Planning fallback (no tools)')
        return agent_state


async def tool_execution_node(agent_state: AgentState) -> AgentState:
    """Execute planned tools with guardrails."""
    agent_state.add_execution_step('Tool execution started')

    registry = register_default_tools()

    for idx, tool_call in enumerate(agent_state.tool_calls):
        agent_state.current_tool_index = idx

        if not tool_execution_guardrails.check_tool_call_limit(agent_state.thread_id):
            tool_call.error = 'Tool call limit exceeded for this thread'
            agent_state.add_execution_step(f'Tool skipped ({tool_call.name}): call limit exceeded')
            continue

        result = await registry.execute_tool(tool_call.name, **tool_call.args)
        if result.success:
            tool_call.result = result.data
            agent_state.add_execution_step(f'Tool executed: {tool_call.name}')
        else:
            tool_call.error = result.error or 'Unknown tool execution error'
            agent_state.add_execution_step(
                f'Tool failed: {tool_call.name} ({tool_call.error})'
            )

    agent_state.add_execution_step('Tool execution finished')
    return agent_state


async def response_node(agent_state: AgentState) -> AgentState:
    """Generate final assistant response from context + tool outputs."""
    agent_state.add_execution_step('Response synthesis started')

    tool_outputs = [
        {
            'tool': tool_call.name,
            'args': tool_call.args,
            'result': tool_call.result,
            'error': tool_call.error,
        }
        for tool_call in agent_state.tool_calls
    ]

    context = {
        'intent': agent_state.intent.value if agent_state.intent else Intent.UNKNOWN.value,
        'plan': agent_state.plan,
        'execution_steps': agent_state.execution_steps,
        'status': agent_state.status,
    }

    prompt = PromptStore.format_prompt(
        'response_synthesis',
        user_message=agent_state.user_message,
        context=json.dumps(context, ensure_ascii=False),
        tool_outputs=json.dumps(tool_outputs, ensure_ascii=False),
    )

    try:
        response_text = await _invoke_llm(prompt)
    except Exception as exc:
        agent_state.status = 'failed'
        agent_state.error_message = str(exc)
        agent_state.final_response = 'I could not generate a final response due to an internal error.'
        agent_state.add_execution_step(f'Response synthesis failed: {exc}')
        return agent_state

    is_valid, error = output_validator.validate_response(response_text)
    if not is_valid:
        agent_state.status = 'failed'
        agent_state.error_message = error
        agent_state.final_response = 'I could not return a safe response. Please rephrase and try again.'
        agent_state.add_execution_step(f'Response validation failed: {error}')
        return agent_state

    sanitized_response = output_validator.sanitize_jira_urls(response_text)

    agent_state.final_response = sanitized_response
    agent_state.status = 'completed'
    agent_state.add_execution_step('Response synthesis completed')
    return agent_state
