from harness.tools.github_tools import build_pr_body, github_create_pr


def test_github_create_pr_dry_run():
    result = github_create_pr(
        repo="owner/repo",
        title="Fix bug",
        head="agent/fix-bug",
        body="Harness generated patch",
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["payload"]["title"] == "Fix bug"
    assert result["payload"]["head"] == "agent/fix-bug"


def test_build_pr_body_contains_eval_sections(tmp_path):
    body = build_pr_body(
        "Fixes the issue",
        {"score": 90, "max_score": 100, "tests": {"success": True}, "lint": {"success": True}, "build": {"success": True}},
        repo_path=str(tmp_path),
    )

    assert "## Summary" in body
    assert "Score: 90/100" in body
    assert "## Harness Evaluation" in body
