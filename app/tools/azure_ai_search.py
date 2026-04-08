"""Azure AI Search tool integration for chat orchestration."""

from __future__ import annotations

import asyncio
from typing import Optional, Any

from pydantic import Field

from app.services.azure_search_service import search_rules
from .base import BaseTool, ToolInput, ToolOutput


class AzureAISearchInput(ToolInput):
    """Input schema for Azure AI Search tool."""

    query: str = Field(description='Search query')
    module_filter: Optional[str] = Field(default=None, description='Optional module filter')
    top: int = Field(default=5, description='Maximum number of results')


class AzureAISearchTool(BaseTool):
    """Tool wrapper over Azure AI Search hybrid retrieval."""

    def __init__(self):
        super().__init__(
            name='azure_ai_search',
            description='Search QA rules and Jira-derived knowledge from Azure AI Search.',
            input_schema=AzureAISearchInput,
            output_schema=ToolOutput,
        )

    async def execute(self, **kwargs) -> ToolOutput:
        """Execute Azure AI Search call asynchronously."""
        query = kwargs.get('query', '')
        module_filter = kwargs.get('module_filter')
        top = kwargs.get('top', 5)

        # Existing service is sync, so run it off the event loop.
        result: Any = await asyncio.to_thread(
            search_rules,
            query,
            module_filter,
            top,
        )

        if isinstance(result, dict) and result.get('error'):
            return ToolOutput(success=False, data=None, error=result['error'])

        return ToolOutput(success=True, data=result, error=None)
