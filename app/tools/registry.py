"""Tool registry and initialization."""

import logging

from .base import get_tool_registry, ToolRegistry


logger = logging.getLogger(__name__)
_default_tools_registered = False


def register_default_tools(force: bool = False) -> ToolRegistry:
	"""Register built-in tools once (idempotent by default)."""
	global _default_tools_registered
	registry = get_tool_registry()

	if _default_tools_registered and not force:
		return registry

	try:
		from .azure_ai_search import AzureAISearchTool

		if not registry.get_tool('azure_ai_search'):
			registry.register(AzureAISearchTool())
	except Exception as exc:
		logger.warning('Unable to register default tools: %s', exc)

	_default_tools_registered = True
	return registry


__all__ = ['get_tool_registry', 'ToolRegistry', 'register_default_tools']
