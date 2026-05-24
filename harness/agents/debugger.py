
import json
from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from harness.agents.base import BaseAgent

class DebuggerAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "You are a Debugger Agent. Analyze failure logs, identify root causes, "
        "and suggest minimal fixes. Return JSON with 'root_cause', 'suggested_fix', 'confidence'."
    )

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.has_model_credentials():
            logs = context.get("test_result", {}).get("summary", {}).get("logs", "")
            root = logs.splitlines()[-1] if logs.splitlines() else "tests failed without logs"
            return {"agent": self.name, "root_cause": root, "suggested_fix": "Inspect failing test logs and apply a targeted patch.", "confidence": 0.4}
        llm = self.llm(temperature=0.2)
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(context, default=str)),
        ]
        response = await llm.ainvoke(messages)
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = {"root_cause": "unknown", "suggested_fix": str(response.content), "confidence": 0.5}
        return {"agent": self.name, **parsed}
