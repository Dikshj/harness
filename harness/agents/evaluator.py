from typing import Any, Dict

from harness.agents.base import BaseAgent
from harness.eval.harness import EvaluationHarness
from harness.tools.git_tools import git_diff


class EvaluatorAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "You are an Evaluator Agent. Score a completed coding attempt using tests, "
        "lint, build, patch quality, hallucination checks, and runtime budget."
    )

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        repo_path = context.get("repo_path", ".")
        diff = context.get("diff")
        if diff is None:
            diff = git_diff(repo_path)

        harness = EvaluationHarness(repo_path)
        result = harness.evaluate({**context, "diff": diff})
        return {"agent": self.name, **result}
