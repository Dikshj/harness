
import os
from pathlib import Path
from harness.tools.registry import register_tool

@register_tool(
    name="file_read",
    description="Read a file from the repository.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
)
def file_read(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    return p.read_text()

@register_tool(
    name="file_write",
    description="Write content to a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    },
)
def file_write(path: str, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Wrote {len(content)} chars to {path}"

@register_tool(
    name="file_grep",
    description="Search for pattern in files recursively.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "default": "."},
        },
        "required": ["pattern"],
    },
)
def file_grep(pattern: str, path: str = ".") -> list:
    import re
    results = []
    root = Path(path)
    for f in root.rglob("*"):
        if f.is_file() and f.stat().st_size < 5_000_000:
            try:
                text = f.read_text(errors="ignore")
                for i, line in enumerate(text.splitlines(), 1):
                    if re.search(pattern, line):
                        results.append(str(f) + f":" + str(i) + ":" + line.strip())
            except Exception:
                pass
    return results[:50]
