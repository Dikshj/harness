
import os
from typing import Any
from harness.tools.registry import register_tool
from harness.config import get_settings
from harness.tools.git_tools import git_diff

settings = get_settings()


def build_pr_body(summary: str, evaluation: dict[str, Any] | None = None, repo_path: str = ".") -> str:
    evaluation = evaluation or {}
    diff = git_diff(repo_path)
    score = evaluation.get("score", "n/a")
    max_score = evaluation.get("max_score", "n/a")
    sections = [
        "## Summary",
        summary.strip() or "Autonomous harness patch.",
        "",
        "## Harness Evaluation",
        f"- Score: {score}/{max_score}",
        f"- Tests: {'passed' if evaluation.get('tests', {}).get('success') else 'not passed or not run'}",
        f"- Lint: {'passed' if evaluation.get('lint', {}).get('success') else 'not passed or not run'}",
        f"- Build: {'passed' if evaluation.get('build', {}).get('success') else 'not passed or not run'}",
        "",
        "## Patch Preview",
        "```diff",
        diff[:6000],
        "```",
    ]
    return "\n".join(sections)

@register_tool(
    name="github_create_pr",
    description="Create a GitHub pull request from a branch.",
    parameters={
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "title": {"type": "string"},
            "body": {"type": "string"},
            "head": {"type": "string"},
            "base": {"type": "string", "default": "main"},
            "dry_run": {"type": "boolean", "default": False},
        },
        "required": ["repo", "title", "head"],
    },
)
def github_create_pr(repo: str, title: str, head: str, body: str = "", base: str = "main", dry_run: bool = False) -> dict:
    payload = {"title": title, "body": body, "head": head, "base": base}
    if dry_run:
        return {"dry_run": True, "repo": repo, "payload": payload}
    import requests
    token = settings.github_token or os.getenv("GITHUB_TOKEN")
    if not token:
        return {"error": "GitHub token not configured"}
    url = f"https://api.github.com/repos/{repo}/pulls"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    return {"status_code": resp.status_code, "response": resp.json()}
