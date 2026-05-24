
from typing import Callable, Dict, Any
from dataclasses import dataclass

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list(self) -> Dict[str, Tool]:
        return dict(self._tools)

    def schemas(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

_registry = ToolRegistry()
_loaded = False

def register_tool(name: str, description: str, parameters: Dict[str, Any]):
    def decorator(fn: Callable):
        _registry.register(Tool(name=name, description=description, parameters=parameters, handler=fn))
        return fn
    return decorator

def get_registry() -> ToolRegistry:
    global _loaded
    if not _loaded:
        _loaded = True
        from harness.tools import browser_tools, file_tools, git_tools, github_tools, terminal_tools  # noqa: F401
    return _registry
