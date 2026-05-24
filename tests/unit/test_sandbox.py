
import pytest
docker = pytest.importorskip("docker")
from harness.sandbox.docker_harness import DockerSandbox

@pytest.mark.integration
class TestDockerSandbox:
    def test_sandbox_lifecycle(self):
        try:
            docker.from_env().ping()
        except Exception as exc:
            pytest.skip(f"Docker daemon is not available: {exc}")
        with DockerSandbox() as box:
            result = box.exec("echo hello")
            assert result["stdout"].strip() == "hello"
