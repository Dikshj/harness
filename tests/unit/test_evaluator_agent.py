from unittest.mock import patch

import pytest

from harness.agents.evaluator import EvaluatorAgent


@pytest.mark.asyncio
async def test_evaluator_scores_context_with_existing_diff():
    agent = EvaluatorAgent("evaluator")

    with patch("harness.agents.evaluator.EvaluationHarness") as mock_harness:
        mock_harness.return_value.evaluate.return_value = {
            "score": 91,
            "max_score": 100,
            "tests": {"success": True},
        }

        result = await agent.run(
            {
                "repo_path": "C:\\Users\\Test User\\repo with spaces",
                "test_command": "python -m pytest -q",
                "lint_command": "ruff check .",
                "build_command": "python -m compileall .",
                "diff": "diff --git a/app.py b/app.py",
            }
        )

    mock_harness.assert_called_once_with("C:\\Users\\Test User\\repo with spaces")
    evaluated_context = mock_harness.return_value.evaluate.call_args.args[0]
    assert evaluated_context["test_command"] == "python -m pytest -q"
    assert evaluated_context["lint_command"] == "ruff check ."
    assert evaluated_context["build_command"] == "python -m compileall ."
    assert evaluated_context["diff"] == "diff --git a/app.py b/app.py"
    assert result["agent"] == "evaluator"
    assert result["score"] == 91


@pytest.mark.asyncio
async def test_evaluator_collects_git_diff_when_missing():
    agent = EvaluatorAgent("evaluator")

    with (
        patch("harness.agents.evaluator.git_diff", return_value="diff --git a/x.py b/x.py") as mock_diff,
        patch("harness.agents.evaluator.EvaluationHarness") as mock_harness,
    ):
        mock_harness.return_value.evaluate.return_value = {"score": 50, "max_score": 100}

        result = await agent.run({"repo_path": "."})

    mock_diff.assert_called_once_with(".")
    evaluated_context = mock_harness.return_value.evaluate.call_args.args[0]
    assert evaluated_context["diff"] == "diff --git a/x.py b/x.py"
    assert result["score"] == 50
