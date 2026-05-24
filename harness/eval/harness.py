
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any
from harness.tools.terminal_tools import shell

@dataclass(frozen=True)
class ScoreWeights:
    tests: int = 35
    lint: int = 15
    build: int = 20
    patch_quality: int = 15
    hallucination: int = 10
    runtime: int = 5

class EvaluationHarness:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.weights = ScoreWeights()

    def run_tests(self, command: str = "pytest") -> Dict[str, Any]:
        result = shell(command, cwd=self.repo_path, timeout=300)
        return {
            "success": result["returncode"] == 0,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "returncode": result["returncode"],
            "duration_ms": result.get("duration_ms", 0),
            "timed_out": result.get("timed_out", False),
            "summary": self._parse_pytest_summary(result["stdout"] + result["stderr"]),
        }

    def lint(self, command: str = "flake8 .") -> Dict[str, Any]:
        result = shell(command, cwd=self.repo_path, timeout=60)
        issues = [line for line in (result["stdout"] + result["stderr"]).splitlines() if line.strip()]
        return {
            "success": result["returncode"] == 0,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "issues": issues[:100],
            "issue_count": len(issues),
            "duration_ms": result.get("duration_ms", 0),
        }

    def build(self, command: str = "echo 'no build step'") -> Dict[str, Any]:
        result = shell(command, cwd=self.repo_path, timeout=120)
        return {
            "success": result["returncode"] == 0,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "returncode": result["returncode"],
            "duration_ms": result.get("duration_ms", 0),
        }

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        tests = self.run_tests(context.get("test_command", "pytest"))
        lint = self.lint(context.get("lint_command", "flake8 ."))
        build = self.build(context.get("build_command", "echo 'no build step'"))
        patch = self.patch_quality(context)
        hallucination = self.hallucination_check(context)
        runtime = self.runtime_score(tests, lint, build, context=context)
        score = (
            (self.weights.tests if tests["success"] else 0)
            + self._lint_points(lint)
            + (self.weights.build if build["success"] else 0)
            + patch["score"]
            + hallucination["score"]
            + runtime["score"]
        )
        return {
            "score": score,
            "max_score": sum(self.weights.__dict__.values()),
            "tests": tests,
            "lint": lint,
            "build": build,
            "patch_quality": patch,
            "hallucination": hallucination,
            "runtime": runtime,
            "token_usage": context.get("token_usage", {}),
        }

    def patch_quality(self, context: Dict[str, Any]) -> Dict[str, Any]:
        diff = context.get("diff") or shell("git diff --stat", cwd=self.repo_path, timeout=30)["stdout"]
        changed_files = self._changed_files(diff)
        score = self.weights.patch_quality
        reasons = []
        if not diff.strip():
            score = 0
            reasons.append("no patch detected")
        if len(changed_files) > context.get("max_changed_files", 20):
            score = max(0, score - 5)
            reasons.append("large blast radius")
        if any(path.endswith((".lock", ".min.js")) for path in changed_files):
            score = max(0, score - 3)
            reasons.append("generated or lockfile changes need review")
        return {"score": score, "changed_files": changed_files, "reasons": reasons}

    def hallucination_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        claims = context.get("claims", [])
        missing = []
        for claim in claims:
            path = claim.get("path") if isinstance(claim, dict) else None
            if path and not (Path(self.repo_path) / path).exists():
                missing.append(path)
        score = self.weights.hallucination if not missing else max(0, self.weights.hallucination - len(missing) * 2)
        return {"score": score, "missing_references": missing}

    def runtime_score(self, *results: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        budget_ms = context.get("runtime_budget_ms", 300_000)
        total_ms = sum(float(item.get("duration_ms", 0)) for item in results)
        score = self.weights.runtime if total_ms <= budget_ms else 0
        return {"score": score, "duration_ms": round(total_ms, 2), "budget_ms": budget_ms}

    def _lint_points(self, lint: Dict[str, Any]) -> int:
        if lint["success"]:
            return self.weights.lint
        return max(0, self.weights.lint - min(self.weights.lint, lint.get("issue_count", 0)))

    def _parse_pytest_summary(self, output: str) -> Dict[str, int]:
        summary = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
        for key in summary:
            match = re.search(rf"(\d+)\s+{key}", output)
            if match:
                summary[key] = int(match.group(1))
        return summary

    def _changed_files(self, diff: str) -> list[str]:
        files: list[str] = []
        for line in diff.splitlines():
            if " | " in line:
                files.append(line.split(" | ", 1)[0].strip())
            elif line.startswith("diff --git "):
                parts = line.split()
                if len(parts) >= 4:
                    files.append(parts[3].removeprefix("b/"))
        return sorted(set(files))
