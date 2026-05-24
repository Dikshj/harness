
import subprocess
import time
from harness.tools.registry import register_tool

@register_tool(
    name="shell",
    description="Execute a shell command and return stdout/stderr.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "cwd": {"type": "string", "default": "."},
            "timeout": {"type": "integer", "default": 60},
        },
        "required": ["command"],
    },
)
def shell(command: str, cwd: str = ".", timeout: int = 60) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "stdout": stdout,
            "stderr": stderr or f"Timeout after {timeout}s",
            "returncode": -1,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "timed_out": True,
        }
