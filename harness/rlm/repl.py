import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReplResult:
    code: str
    stdout: str
    stderr: str
    exit_code: int
    latency_ms: float
    timed_out: bool = False


class SandboxedPythonRepl:
    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds

    def run(self, code: str) -> ReplResult:
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="rlm-repl-") as tmp:
            script = Path(tmp) / "cell.py"
            script.write_text(code, encoding="utf-8")
            try:
                completed = subprocess.run(
                    [sys.executable, str(script)],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                return ReplResult(
                    code=code,
                    stdout=completed.stdout.strip(),
                    stderr=completed.stderr.strip(),
                    exit_code=completed.returncode,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                )
            except subprocess.TimeoutExpired as exc:
                return ReplResult(
                    code=code,
                    stdout=(exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
                    stderr="Timed out",
                    exit_code=124,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    timed_out=True,
                )
