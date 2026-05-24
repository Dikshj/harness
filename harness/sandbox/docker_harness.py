
import tarfile
import io
import uuid
import os
from typing import Any, Optional
from harness.config import get_settings

settings = get_settings()

class DockerSandbox:
    def __init__(self, image: str = "python:3.11-slim", timeout: int = 300, network_disabled: bool = True):
        self.client = None
        self.image = image
        self.timeout = timeout or settings.sandbox_timeout
        self.network_disabled = network_disabled
        self.container: Optional[Any] = None
        self.name = f"harness-sandbox-{uuid.uuid4().hex[:8]}"
        self.trace: list[dict] = []

    def start(self, repo_path: Optional[str] = None):
        try:
            import docker
        except ImportError as exc:
            raise RuntimeError("Docker SDK is not installed. Install requirements.txt to enable sandbox execution.") from exc
        self.client = docker.from_env()
        volumes = {}
        if repo_path and os.path.isdir(repo_path):
            volumes[os.path.abspath(repo_path)] = {"bind": "/repo", "mode": "rw"}
        self.container = self.client.containers.run(
            self.image,
            name=self.name,
            command="sleep infinity",
            detach=True,
            volumes=volumes,
            mem_limit=settings.sandbox_mem_limit,
            cpu_period=100000,
            cpu_quota=int(settings.sandbox_cpu_limit * 100000),
            network_disabled=self.network_disabled,
            pids_limit=256,
            security_opt=["no-new-privileges"],
            labels={"app": "autonomous-harness", "sandbox": "true"},
        )

    def exec(self, cmd: str, workdir: str = "/repo") -> dict:
        if not self.container:
            raise RuntimeError("Sandbox not started")
        result = self.container.exec_run(cmd, workdir=workdir, demux=True)
        exit_code = result.exit_code
        stdout = (result.output[0] or b"").decode(errors="replace")
        stderr = (result.output[1] or b"").decode(errors="replace")
        entry = {"command": cmd, "workdir": workdir, "stdout": stdout, "stderr": stderr, "returncode": exit_code}
        self.trace.append(entry)
        return entry

    def copy_in(self, src_path: str, dest_path: str = "/repo"):
        if not self.container:
            raise RuntimeError("Sandbox not started")
        tarstream = io.BytesIO()
        with tarfile.open(fileobj=tarstream, mode="w") as tar:
            tar.add(src_path, arcname=os.path.basename(dest_path))
        tarstream.seek(0)
        self.container.put_archive(os.path.dirname(dest_path), tarstream.read())

    def logs(self) -> str:
        if not self.container:
            return ""
        return self.container.logs().decode(errors="replace")

    def execution_trace(self) -> list[dict]:
        return list(self.trace)

    def stop(self):
        if self.container:
            try:
                self.container.stop(timeout=10)
                self.container.remove(force=True)
            except Exception:
                pass
            self.container = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()
