
import json
from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from harness.agents.base import BaseAgent
from harness.tools.registry import get_registry

class CoderAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "You are a Coder Agent. You have access to tools. Use them to read, write, and edit files. "
        "Think step by step and return a JSON object with 'actions' (list of tool calls) and 'summary'."
    )

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.has_model_credentials():
            return {
                "agent": self.name,
                "actions": [],
                "summary": "No model API key configured; coder ran in dry-run mode after repository analysis.",
            }
        llm = self.llm(temperature=0.2)
        registry = get_registry()
        tools = registry.schemas()
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(context, default=str)),
        ]
        response = await llm.bind_tools(tools).ainvoke(messages)
        actions = []
        if response.tool_calls:
            for tc in response.tool_calls:
                tool = registry.get(tc["name"])
                result = tool.handler(**tc["args"])
                actions.append({"tool": tc["name"], "args": tc["args"], "result": result})
        return {"agent": self.name, "actions": actions, "summary": response.content}
