from fastapi.testclient import TestClient

from harness.api import app


def test_rlm_run_lifecycle():
    with TestClient(app) as client:
        created = client.post(
            "/runs",
            json={
                "title": "RLM smoke",
                "goal": "Summarize a long coding context",
                "context": " ".join(["A subsystem needs isolated analysis."] * 80),
                "max_depth": 2,
                "branch_factor": 2,
                "context_window": 240,
            },
        )
        assert created.status_code == 200
        run_id = created.json()["run_id"]

        executed = client.post(f"/runs/{run_id}/execute")
        assert executed.status_code == 200

        detail = client.get(f"/runs/{run_id}")
        payload = detail.json()
        assert payload["status"] == "completed"
        assert payload["results"]["summary"]
        assert payload["results"]["execution_graph"]["nodes"][0] == "root"
        assert payload["scores"]["score"] > 0

        steps = client.get(f"/runs/{run_id}/steps")
        assert steps.status_code == 200
        assert steps.json()

        events = client.get(f"/runs/{run_id}/events")
        assert events.status_code == 200
        assert "data:" in events.text


def test_unknown_run_returns_404():
    with TestClient(app) as client:
        assert client.get("/runs/missing").status_code == 404
        assert client.get("/runs/missing/steps").status_code == 404
