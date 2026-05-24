
import json
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response, StreamingResponse
try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    def generate_latest():
        return b"# prometheus_client is not installed\n"
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

from harness.db import get_db, init_db
from harness.models.task import Task, TaskStatus
from harness.models.execution import ExecutionStep, ExecutionStatus
from harness.workflows.swe_graph import swe_graph, SWEState
from harness.workflows.pr_lifecycle import prepare_pull_request
from harness.observability.logger import setup_logging
from harness.observability.metrics import active_tasks, task_latency, tasks_total
from harness.memory.redis_cache import get_json

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Autonomous Software Engineering Harness", version="0.1.0", lifespan=lifespan)

class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str
    repo_url: Optional[str] = None
    issue_url: Optional[str] = None
    repo_path: Optional[str] = "."
    test_command: Optional[str] = "pytest"
    max_retries: int = Field(default=3, ge=0, le=10)

class PreparePullRequestRequest(BaseModel):
    github_repo: Optional[str] = None
    base_branch: str = "main"
    dry_run: bool = True

@app.post("/tasks")
async def create_task(req: CreateTaskRequest, db: AsyncSession = Depends(get_db)):
    task = Task(
        id=str(uuid.uuid4()),
        title=req.title,
        description=req.description,
        repo_url=req.repo_url,
        issue_url=req.issue_url,
        status=TaskStatus.PENDING,
        results={"repo_path": req.repo_path, "test_command": req.test_command, "max_retries": req.max_retries},
    )
    db.add(task)
    await db.commit()
    return {"task_id": task.id, "status": task.status}

@app.get("/tasks")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    tasks = result.scalars().all()
    return tasks

@app.get("/tasks/{task_id}")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/tasks/{task_id}/steps")
async def list_task_steps(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    result = await db.execute(select(ExecutionStep).where(ExecutionStep.task_id == task_id).order_by(ExecutionStep.created_at))
    return result.scalars().all()

@app.post("/tasks/{task_id}/pull-request")
async def prepare_task_pull_request(
    task_id: str,
    req: PreparePullRequestRequest,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    results = task.results or {}
    repo_path = results.get("repo_path") or results.get("context", {}).get("repo_path") or "."
    evaluation = task.scores or results.get("eval_result") or {}
    summary = (
        results.get("code_result", {}).get("summary")
        or results.get("summary")
        or task.description
        or "Autonomous harness patch."
    )
    lifecycle = prepare_pull_request(
        repo_path=repo_path,
        task_id=task.id,
        title=task.title,
        summary=summary,
        evaluation=evaluation,
        github_repo=req.github_repo or task.repo_url,
        base_branch=req.base_branch,
        dry_run=req.dry_run,
    )
    task.results = {**results, "pr_lifecycle": lifecycle}
    await db.commit()
    return lifecycle

@app.post("/tasks/{task_id}/run")
async def run_task(task_id: str, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Task is already running")
    task.status = TaskStatus.RUNNING
    await db.commit()
    background.add_task(_execute_graph, task_id, task)
    active_tasks.inc()
    return {"task_id": task_id, "status": TaskStatus.RUNNING}

async def _execute_graph(task_id: str, task: Task):
    started = time.perf_counter()
    state: SWEState = {
        "task_id": task_id,
        "context": {
            "title": task.title,
            "description": task.description,
            "repo_url": task.repo_url,
            "repo_path": (task.results or {}).get("repo_path") or (task.repo_url.split("/")[-1].replace(".git", "") if task.repo_url else "."),
            "test_command": (task.results or {}).get("test_command", "pytest"),
        },
        "plan": [],
        "code_result": {},
        "test_result": {},
        "debug_result": {},
        "review_result": {},
        "eval_result": {},
        "repo_context": {},
        "execution_graph": {},
        "traces": [],
        "retries": 0,
        "max_retries": task.results.get("max_retries", 3) if task.results else 3,
    }
    try:
        result = await swe_graph.ainvoke(state)
        tasks_total.labels(status="completed").inc()
    except Exception as e:
        tasks_total.labels(status="failed").inc()
        result = {
            "error": str(e),
            "traces": state.get("traces", []),
            "eval_result": {"score": 0, "max_score": 100},
        }
    finally:
        active_tasks.dec()
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    task_latency.observe(latency_ms / 1000)
    async for db in get_db():
        db_task = await db.get(Task, task_id)
        if db_task:
            db_task.status = TaskStatus.COMPLETED if "error" not in result else TaskStatus.FAILED
            db_task.plan = result.get("plan")
            db_task.results = result
            db_task.scores = result.get("eval_result")
            db_task.retries = result.get("retries", 0)
            db_task.latency_ms = latency_ms
            await _persist_execution_steps(db, task_id, result)
            await db.commit()
    print(f"Task {task_id} finished with result keys {list(result.keys())}")

async def _persist_execution_steps(db: AsyncSession, task_id: str, result: dict):
    await db.execute(delete(ExecutionStep).where(ExecutionStep.task_id == task_id))
    traces = result.get("traces", [])
    for trace in traces:
        db.add(
            ExecutionStep(
                task_id=task_id,
                agent=str(trace.get("node", "unknown")),
                input_payload=trace,
                output_payload=trace,
                status=ExecutionStatus.SUCCESS,
            )
        )
    if "error" in result:
        db.add(
            ExecutionStep(
                task_id=task_id,
                agent="workflow",
                output_payload={"error": result["error"]},
                logs=result["error"],
                status=ExecutionStatus.FAILURE,
            )
        )

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/tasks/{task_id}/events")
async def task_events(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def stream():
        cached = await get_json(f"task:{task_id}:events") or []
        events = cached or (task.results or {}).get("traces", [])
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")
