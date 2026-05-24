from unittest.mock import patch

import pytest

from harness.agents.tester import TesterAgent


@pytest.mark.asyncio
async def test_tester_runs_command_with_repo_as_cwd():
    agent = TesterAgent("tester")

    with patch("harness.agents.tester.shell") as mock_shell:
        mock_shell.return_value = {
            "stdout": "================ 2 passed in 0.01s ================\n",
            "stderr": "",
            "returncode": 0,
            "duration_ms": 12.5,
        }

        result = await agent.run(
            {
                "repo_path": "C:\\Users\\Test User\\repo with spaces",
                "test_command": "python -m pytest -q",
            }
        )

    mock_shell.assert_called_once_with(
        "python -m pytest -q",
        cwd="C:\\Users\\Test User\\repo with spaces",
        timeout=120,
    )
    assert result["summary"]["tests_passed"] == 2
    assert result["summary"]["tests_failed"] == 0


@pytest.mark.asyncio
async def test_tester_marks_non_pytest_failure_as_failed():
    agent = TesterAgent("tester")

    with patch("harness.agents.tester.shell") as mock_shell:
        mock_shell.return_value = {
            "stdout": "",
            "stderr": "command not found",
            "returncode": 127,
            "duration_ms": 3,
        }

        result = await agent.run({"repo_path": ".", "test_command": "missing-command"})

    assert result["summary"]["tests_passed"] == 0
    assert result["summary"]["tests_failed"] == 1
    assert result["summary"]["returncode"] == 127
