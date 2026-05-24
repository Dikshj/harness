
import pytest
from harness.eval.harness import EvaluationHarness
from unittest.mock import patch

class TestEvalHarness:
    def test_evaluate_scores(self):
        with patch("harness.eval.harness.shell") as mock_shell:
            mock_shell.return_value = {"stdout": "1 passed", "stderr": "", "returncode": 0}
            harness = EvaluationHarness(".")
            result = harness.evaluate({})
            assert result["score"] == 100
            assert result["tests"]["summary"]["passed"] == 1
            assert "patch_quality" in result
