
from harness.tools.registry import register_tool

@register_tool(
    name="git_diff",
    description="Show git diff in a repository.",
    parameters={
        "type": "object",
        "properties": {"repo_path": {"type": "string", "default": "."}},
        "required": [],
    },
)
def git_diff(repo_path: str = ".") -> str:
    from harness.tools.terminal_tools import shell
    return shell("git diff", cwd=repo_path, timeout=30)["stdout"]

@register_tool(
    name="git_status",
    description="Show git status.",
    parameters={
        "type": "object",
        "properties": {"repo_path": {"type": "string", "default": "."}},
        "required": [],
    },
)
def git_status(repo_path: str = ".") -> str:
    from harness.tools.terminal_tools import shell
    return shell("git status --short", cwd=repo_path, timeout=30)["stdout"]
