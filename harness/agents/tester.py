
import re
from typing import Any, Dict
from harness.agents.base import BaseAgent
from harness.tools.terminal_tools import shell

class TesterAgent(BaseAgent):
    __test__ = False

    SYSTEM_PROMPT = (
        "You are a Tester Agent. Run tests and report results. "
        "Return JSON with 'tests_passed', 'tests_failed', 'coverage', and 'logs'."
    )

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        repo = context.get("repo_path", ".")
        cmd = context.get("test_command", "pytest")
        result = shell(cmd, cwd=repo, timeout=120)
        logs = result["stdout"] + result["stderr"]
        summary = {
            "tests_passed": self._count_pytest_result(logs, "passed"),
            "tests_failed": self._count_pytest_result(logs, "failed"),
            "logs": logs,
        }
        if result["returncode"] != 0 and summary["tests_failed"] == 0:
            summary["tests_failed"] = 1
        summary["returncode"] = result["returncode"]
        summary["duration_ms"] = result.get("duration_ms", 0)
        return {"agent": self.name, "summary": summary}

    def _count_pytest_result(self, output: str, label: str) -> int:
        match = re.search(rf"(\d+)\s+{label}\b", output)
        return int(match.group(1)) if match else 0
