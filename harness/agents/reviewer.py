
import json
from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from harness.agents.base import BaseAgent

class ReviewerAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "You are a Reviewer Agent. Review code diffs and test results. "
        "Return JSON with 'score' (0-100), 'issues' (list), and 'approval' (bool)."
    )

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.has_model_credentials():
            tests_failed = context.get("test_result", {}).get("summary", {}).get("tests_failed", 0)
            approval = tests_failed == 0
            return {"agent": self.name, "score": 80 if approval else 35, "issues": [] if approval else ["test failures remain"], "approval": approval}
        llm = self.llm(temperature=0.2)
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(context, default=str)),
        ]
        response = await llm.ainvoke(messages)
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = {"score": 50, "issues": [], "approval": False}
        return {"agent": self.name, **parsed}
