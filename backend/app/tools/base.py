from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel

Permission = Literal["read", "write", "exec"]


class ToolContext(BaseModel):
    workspace: str


class Tool(BaseModel):
    name: str
    description: str
    permission: Permission
    input_model: type[BaseModel]
    handler: Callable[[ToolContext, BaseModel], Awaitable[Any]]

    model_config = {"arbitrary_types_allowed": True}

    def schema_for_ollama(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")

        return self._tools[name]

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema_for_ollama() for t in self._tools.values()]


registry = ToolRegistry()