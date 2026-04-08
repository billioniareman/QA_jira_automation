"""Base class for tools and tool registry."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ToolInput(BaseModel):
    """Base input schema for tools."""
    pass


class ToolOutput(BaseModel):
    """Base output schema for tools."""
    success: bool = Field(default=True, description='Whether tool executed successfully')
    data: Optional[Any] = Field(default=None, description='Tool output data')
    error: Optional[str] = Field(default=None, description='Error message if execution failed')


class BaseTool(ABC):
    """Abstract base class for all tools."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: type,
        output_schema: type = ToolOutput,
    ):
        """
        Initialize tool.
        
        Args:
            name: Tool name (used in LLM tool selection)
            description: Human-readable description
            input_schema: Pydantic model for input validation
            output_schema: Pydantic model for output
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema

    @abstractmethod
    async def execute(self, **kwargs) -> ToolOutput:
        """
        Execute the tool.
        
        Args:
            **kwargs: Inputs matching input_schema
            
        Returns:
            ToolOutput instance
        """
        pass

    def get_openai_tool_schema(self) -> Dict[str, Any]:
        """Generate OpenAI-compatible tool schema for function calling."""
        properties = {}
        required = []

        for field_name, field_info in self.input_schema.model_fields.items():
            properties[field_name] = {
                'type': self._get_json_type(field_info.annotation),
                'description': field_info.description or '',
            }
            if field_info.is_required():
                required.append(field_name)

        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': properties,
                    'required': required,
                },
            },
        }

    @staticmethod
    def _get_json_type(python_type: type) -> str:
        """Map Python type to JSON schema type."""
        type_mapping = {
            str: 'string',
            int: 'integer',
            float: 'number',
            bool: 'boolean',
            list: 'array',
            dict: 'object',
        }
        return type_mapping.get(python_type, 'string')


class ToolRegistry:
    """Registry for all available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info(f'Registered tool: {tool.name}')

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_openai_tools_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool schema for all registered tools."""
        return [tool.get_openai_tool_schema() for tool in self._tools.values()]

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolOutput:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool
            **kwargs: Tool inputs
            
        Returns:
            ToolOutput instance
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolOutput(
                success=False,
                error=f'Tool not found: {tool_name}',
            )

        try:
            # Validate input
            validated_input = tool.input_schema(**kwargs)
            # Execute tool
            result = await tool.execute(**validated_input.model_dump())
            return result
        except Exception as e:
            logger.error(f'Tool execution failed ({tool_name}): {e}')
            return ToolOutput(
                success=False,
                error=str(e),
            )


# Global tool registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
