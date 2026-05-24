
import json
from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from harness.agents.base import BaseAgent

class PlannerAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "You are a Planner Agent. Given a coding task or GitHub issue, break it into "
        "a list of subtasks. Output valid JSON with a key 'plan' containing a list of "
        "objects with 'step', 'description', 'agent', and 'depends_on'."
    )

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.has_model_credentials():
            return {
                "agent": self.name,
                "plan": [
                    {"step": 1, "description": "Index repository context and identify relevant files", "agent": "planner", "depends_on": []},
                    {"step": 2, "description": "Implement the smallest patch that satisfies the task", "agent": "coder", "depends_on": [1]},
                    {"step": 3, "description": "Run targeted tests, lint, and build checks", "agent": "tester", "depends_on": [2]},
                    {"step": 4, "description": "Review diff quality and failure risks", "agent": "reviewer", "depends_on": [3]},
                ],
                "execution_graph": {
                    "nodes": ["repo_context", "planner", "coder", "tester", "reviewer", "eval"],
                    "edges": [["repo_context", "planner"], ["planner", "coder"], ["coder", "tester"], ["tester", "reviewer"], ["reviewer", "eval"]],
                },
            }
        llm = self.llm(temperature=0.2)
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(context, default=str)),
        ]
        response = await llm.ainvoke(messages)
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = {"plan": [{"step": 1, "description": str(response.content), "agent": "coder", "depends_on": []}]}
        return {"agent": self.name, "plan": parsed.get("plan", [])}
