"""Tests for tool registry and execution."""

import pytest
from pydantic import Field

from app.tools.base import BaseTool, ToolInput, ToolOutput, ToolRegistry, get_tool_registry
from app.tools.registry import get_tool_registry


# Test tool implementations
class SimpleToolInput(ToolInput):
    value: int = Field(description="Input value")


class SimpleTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="simple_tool",
            description="A simple test tool",
            input_schema=SimpleToolInput,
        )

    async def execute(self, value: int) -> ToolOutput:
        return ToolOutput(success=True, data={"result": value * 2})


class FailingTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="failing_tool",
            description="A tool that always fails",
            input_schema=SimpleToolInput,
        )

    async def execute(self, value: int) -> ToolOutput:
        raise ValueError("Tool intentionally failed")


class TestToolRegistry:
    """Test tool registry operations."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = SimpleTool()
        
        registry.register(tool)
        
        retrieved = registry.get_tool("simple_tool")
        assert retrieved is not None
        assert retrieved.name == "simple_tool"

    def test_list_tools(self):
        """Test listing all tools."""
        registry = ToolRegistry()
        registry.register(SimpleTool())
        registry.register(FailingTool())
        
        tools = registry.list_tools()
        assert len(tools) == 2
        assert any(t.name == "simple_tool" for t in tools)
        assert any(t.name == "failing_tool" for t in tools)

    def test_get_openai_tools_schema(self):
        """Test generating OpenAI-compatible schema."""
        registry = ToolRegistry()
        registry.register(SimpleTool())
        
        schemas = registry.get_openai_tools_schema()
        
        assert len(schemas) == 1
        assert schemas[0]['type'] == 'function'
        assert schemas[0]['function']['name'] == 'simple_tool'
        assert 'parameters' in schemas[0]['function']

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        registry = ToolRegistry()
        registry.register(SimpleTool())
        
        result = await registry.execute_tool("simple_tool", value=5)
        
        assert result.success is True
        assert result.data['result'] == 10

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test tool not found error."""
        registry = ToolRegistry()
        
        result = await registry.execute_tool("nonexistent_tool")
        
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_failure(self):
        """Test handling tool execution failure."""
        registry = ToolRegistry()
        registry.register(FailingTool())
        
        result = await registry.execute_tool("failing_tool", value=10)
        
        assert result.success is False
        assert result.error is not None


class TestToolSchema:
    """Test tool OpenAI schema generation."""

    def test_simple_tool_schema(self):
        """Test schema for simple tool."""
        tool = SimpleTool()
        schema = tool.get_openai_tool_schema()
        
        assert schema['type'] == 'function'
        assert schema['function']['name'] == 'simple_tool'
        assert 'value' in schema['function']['parameters']['properties']
        assert schema['function']['parameters']['required'] == ['value']

    def test_get_json_type_mapping(self):
        """Test Python to JSON type mapping."""
        tool = SimpleTool()
        
        assert tool._get_json_type(str) == 'string'
        assert tool._get_json_type(int) == 'integer'
        assert tool._get_json_type(float) == 'number'
        assert tool._get_json_type(bool) == 'boolean'
        assert tool._get_json_type(list) == 'array'
        assert tool._get_json_type(dict) == 'object'


class TestGlobalRegistry:
    """Test global registry singleton."""

    def test_get_tool_registry_singleton(self):
        """Test that get_tool_registry returns the same instance."""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        
        assert registry1 is registry2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
