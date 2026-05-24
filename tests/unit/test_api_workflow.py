import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from harness.api import app
from harness.db import AsyncSessionLocal
from harness.models.task import Task, TaskStatus


async def _mark_task_running(task_id: str):
    async with AsyncSessionLocal() as session:
        task = await session.get(Task, task_id)
        task.status = TaskStatus.RUNNING
        await session.commit()


def test_api_offline_workflow_completes():
    with TestClient(app) as client:
        created = client.post(
            "/tasks",
            json={
                "title": "API workflow smoke",
                "description": "Verify graph execution through API",
                "repo_path": ".",
                "test_command": "python -m pytest tests\\unit\\test_eval.py -q",
                "max_retries": 1,
            },
        )
        assert created.status_code == 200
        task_id = created.json()["task_id"]

        run = client.post(f"/tasks/{task_id}/run")
        assert run.status_code == 200
        assert run.json()["status"] == "running"

        detail = client.get(f"/tasks/{task_id}")
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["status"] == "completed"
        assert payload["latency_ms"] > 0
        assert payload["scores"]["score"] > 0
        assert [trace["node"] for trace in payload["results"]["traces"]] == [
            "repo_context",
            "planner",
            "coder",
            "tester",
            "reviewer",
            "eval",
        ]

        events = client.get(f"/tasks/{task_id}/events")
        assert events.status_code == 200
        assert "data:" in events.text
        assert "repo_context" in events.text

        steps = client.get(f"/tasks/{task_id}/steps")
        assert steps.status_code == 200
        assert [step["agent"] for step in steps.json()] == [
            "repo_context",
            "planner",
            "coder",
            "tester",
            "reviewer",
            "eval",
        ]


def test_task_events_returns_404_for_unknown_task():
    with TestClient(app) as client:
        response = client.get("/tasks/missing/events")
        assert response.status_code == 404


def test_run_rejects_already_running_task():
    with TestClient(app) as client:
        created = client.post(
            "/tasks",
            json={
                "title": "Duplicate run guard",
                "description": "Verify duplicate runs are rejected",
                "repo_path": ".",
            },
        )
        assert created.status_code == 200
        task_id = created.json()["task_id"]

        asyncio.run(_mark_task_running(task_id))

        response = client.post(f"/tasks/{task_id}/run")
        assert response.status_code == 409
        assert response.json()["detail"] == "Task is already running"


def test_create_task_validates_retry_bounds():
    with TestClient(app) as client:
        response = client.post(
            "/tasks",
            json={
                "title": "Invalid retries",
                "description": "Retry count should be bounded",
                "max_retries": 99,
            },
        )
        assert response.status_code == 422


def test_failed_workflow_persists_score_and_latency():
    with TestClient(app) as client:
        created = client.post(
            "/tasks",
            json={
                "title": "Failure shape",
                "description": "Verify failed graph runs still persist normalized results",
                "repo_path": ".",
            },
        )
        assert created.status_code == 200
        task_id = created.json()["task_id"]

        with patch("harness.api.main.swe_graph.ainvoke", AsyncMock(side_effect=RuntimeError("boom"))):
            run = client.post(f"/tasks/{task_id}/run")

        assert run.status_code == 200
        detail = client.get(f"/tasks/{task_id}")
        payload = detail.json()
        assert payload["status"] == "failed"
        assert payload["results"]["error"] == "boom"
        assert payload["scores"] == {"score": 0, "max_score": 100}
        assert payload["latency_ms"] > 0

        steps = client.get(f"/tasks/{task_id}/steps")
        assert steps.status_code == 200
        assert steps.json()[-1]["status"] == "failure"


def test_task_steps_returns_404_for_unknown_task():
    with TestClient(app) as client:
        response = client.get("/tasks/missing/steps")
        assert response.status_code == 404
