import subprocess

from fastapi.testclient import TestClient

from harness.api import app
from harness.workflows.pr_lifecycle import prepare_pull_request


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=30)


def test_prepare_pull_request_dry_run_reports_commands(tmp_path):
    _git(tmp_path, "init")
    (tmp_path / "app.py").write_text("print('hello')\n")

    result = prepare_pull_request(
        repo_path=str(tmp_path),
        task_id="1234567890",
        title="Fix greeting bug",
        summary="Updates greeting behavior",
        evaluation={"score": 80, "max_score": 100},
        github_repo="owner/repo",
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["has_changes"] is True
    assert result["branch"] == "agent/fix-greeting-bug-12345678"
    assert ["git", "checkout", "-B", result["branch"]] in result["commands"]
    assert result["pull_request"]["dry_run"] is True
    assert "## Harness Evaluation" in result["pr_body"]


def test_prepare_pull_request_commits_local_changes_without_pushing(tmp_path):
    _git(tmp_path, "init")
    (tmp_path / "app.py").write_text("print('hello')\n")

    result = prepare_pull_request(
        repo_path=str(tmp_path),
        task_id="abcdef1234",
        title="Add app",
        summary="Adds app file",
        dry_run=False,
    )

    assert "error" not in result
    assert result["branch"] == "agent/add-app-abcdef12"
    assert _git(tmp_path, "status", "--short").stdout == ""
    assert "Add app" in _git(tmp_path, "log", "-1", "--pretty=%B").stdout


def test_api_prepares_pull_request_artifact(tmp_path):
    _git(tmp_path, "init")
    (tmp_path / "app.py").write_text("print('hello')\n")

    with TestClient(app) as client:
        created = client.post(
            "/tasks",
            json={
                "title": "Prepare PR",
                "description": "Create PR artifact",
                "repo_path": str(tmp_path),
            },
        )
        task_id = created.json()["task_id"]

        response = client.post(
            f"/tasks/{task_id}/pull-request",
            json={"github_repo": "owner/repo", "dry_run": True},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["dry_run"] is True
        assert payload["has_changes"] is True
        assert payload["pull_request"]["payload"]["head"] == payload["branch"]

        detail = client.get(f"/tasks/{task_id}").json()
        assert detail["results"]["pr_lifecycle"]["branch"] == payload["branch"]
