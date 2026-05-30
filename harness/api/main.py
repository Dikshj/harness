import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from harness.db import get_db, init_db
from harness.models.execution import ExecutionStatus, ExecutionStep
from harness.models.task import Task, TaskStatus
from harness.rlm import RLMEngine, RLMRunConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="RLM Harness", version="0.1.0", lifespan=lifespan)


class CreateRunRequest(BaseModel):
    title: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    context: str = ""
    max_depth: int = Field(default=3, ge=0, le=8)
    branch_factor: int = Field(default=3, ge=1, le=8)
    context_window: int = Field(default=1200, ge=200, le=12000)
    repl_timeout_seconds: int = Field(default=5, ge=1, le=30)


@app.post("/runs")
async def create_run(req: CreateRunRequest, db: AsyncSession = Depends(get_db)):
    task = Task(
        id=str(uuid.uuid4()),
        title=req.title,
        description=req.goal,
        status=TaskStatus.PENDING,
        results={
            "context": req.context,
            "config": {
                "max_depth": req.max_depth,
                "branch_factor": req.branch_factor,
                "context_window": req.context_window,
                "repl_timeout_seconds": req.repl_timeout_seconds,
            },
        },
    )
    db.add(task)
    await db.commit()
    return {"run_id": task.id, "status": task.status}


@app.get("/runs")
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    return result.scalars().all()


@app.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, run_id)
    if not task:
        raise HTTPException(status_code=404, detail="Run not found")
    return task


@app.post("/runs/{run_id}/execute")
async def execute_run(run_id: str, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, run_id)
    if not task:
        raise HTTPException(status_code=404, detail="Run not found")
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Run is already running")
    task.status = TaskStatus.RUNNING
    await db.commit()
    background.add_task(_execute_rlm, run_id)
    return {"run_id": run_id, "status": TaskStatus.RUNNING}


@app.get("/runs/{run_id}/steps")
async def list_run_steps(run_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, run_id)
    if not task:
        raise HTTPException(status_code=404, detail="Run not found")
    result = await db.execute(select(ExecutionStep).where(ExecutionStep.task_id == run_id).order_by(ExecutionStep.created_at))
    return result.scalars().all()


@app.get("/runs/{run_id}/events")
async def run_events(run_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, run_id)
    if not task:
        raise HTTPException(status_code=404, detail="Run not found")

    async def stream():
        for event in (task.results or {}).get("traces", []):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/memory/search")
async def search_memory(q: Optional[str] = "", limit: int = 8):
    engine = RLMEngine()
    return engine.memory.search(q or "", limit=limit)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "rlm-harness"}


async def _execute_rlm(run_id: str):
    started = time.perf_counter()
    async for db in get_db():
        task = await db.get(Task, run_id)
        if not task:
            return
        payload = task.results or {}
        config_payload = payload.get("config", {})
        config = RLMRunConfig(**config_payload)
        engine = RLMEngine()
        try:
            result = await engine.run(
                task_id=run_id,
                goal=task.description or task.title,
                context=payload.get("context", ""),
                config=config,
            )
            task.status = TaskStatus.COMPLETED
            task.results = result
            task.plan = result.get("execution_graph")
            task.scores = result.get("score")
            task.retries = 0
        except Exception as exc:
            result = {"error": str(exc), "traces": [], "score": {"score": 0, "max_score": 100}}
            task.status = TaskStatus.FAILED
            task.results = result
            task.scores = result["score"]
        task.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        await _persist_steps(db, run_id, task.results or {})
        await db.commit()


async def _persist_steps(db: AsyncSession, run_id: str, result: dict):
    await db.execute(delete(ExecutionStep).where(ExecutionStep.task_id == run_id))
    for trace in result.get("traces", []):
        db.add(
            ExecutionStep(
                task_id=run_id,
                agent=str(trace.get("node", "rlm-node")),
                tool="sandboxed-python-repl",
                input_payload=trace,
                output_payload=trace,
                status=ExecutionStatus.SUCCESS,
            )
        )
    if "error" in result:
        db.add(
            ExecutionStep(
                task_id=run_id,
                agent="rlm-engine",
                tool="recursive-orchestrator",
                output_payload={"error": result["error"]},
                logs=result["error"],
                status=ExecutionStatus.FAILURE,
            )
        )
