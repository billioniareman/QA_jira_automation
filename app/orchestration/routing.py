"""Intent routing for LangGraph orchestration."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.azure.llm import get_llm
from app.prompts.prompt_store import PromptStore
from .state import Intent


logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract first JSON object from a model response."""
    text = text.strip()

    # Fast path: full JSON payload
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass

    # Fallback: find first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}

    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _heuristic_intent(user_message: str) -> tuple[Intent, float, str]:
    """Fallback intent classification when LLM routing fails."""
    text = (user_message or '').lower()

    jira_terms = {
        'jira', 'ticket', 'issue', 'story', 'epic', 'backlog',
        'sprint', 'assignee', 'jql', 'transition',
    }
    search_terms = {
        'search', 'find', 'lookup', 'rules', 'acceptance criteria',
        'requirement', 'knowledge base', 'vector',
    }

    if any(term in text for term in jira_terms):
        return Intent.JIRA, 0.7, 'Heuristic match on Jira vocabulary'

    if any(term in text for term in search_terms):
        return Intent.GENERAL, 0.65, 'Heuristic match on retrieval/search vocabulary'

    return Intent.UNKNOWN, 0.4, 'No reliable heuristic signal'


async def _invoke_llm(prompt: str) -> str:
    """Invoke LLM in async-safe way."""
    llm = get_llm()

    if hasattr(llm, 'ainvoke'):
        response = await llm.ainvoke(prompt)
    else:
        response = await asyncio.to_thread(llm.invoke, prompt)

    # LangChain response could be AIMessage or string
    if hasattr(response, 'content'):
        return str(response.content)
    return str(response)


async def classify_intent(user_message: str) -> tuple[Intent, float, str]:
    """Classify user message intent for graph routing."""
    prompt = PromptStore.format_prompt('routing', user_message=user_message)

    try:
        response_text = await _invoke_llm(prompt)
        payload = _extract_json_object(response_text)

        intent_raw = str(payload.get('intent', 'unknown')).strip().lower()
        confidence = float(payload.get('confidence', 0.0))
        reasoning = str(payload.get('reasoning', 'LLM classified intent'))

        if intent_raw not in {Intent.JIRA.value, Intent.GENERAL.value, Intent.UNKNOWN.value}:
            logger.warning('Unknown intent from router: %s', intent_raw)
            return _heuristic_intent(user_message)

        return Intent(intent_raw), max(0.0, min(1.0, confidence)), reasoning

    except Exception as exc:
        logger.warning('Intent routing failed, using heuristic fallback: %s', exc)
        return _heuristic_intent(user_message)
