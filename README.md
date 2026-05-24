# Autonomous Software Engineering Harness

A production-grade agentic AI platform for autonomous repository understanding, planning, coding, testing, evaluation, retry, and pull-request workflows.

## Architecture

- **Backend**: FastAPI, LangGraph, Celery, PostgreSQL, Redis
- **Agent Graph**: Planner, Coder, Tester, Debugger, Reviewer, and Evaluator nodes with retry routing
- **Repository Understanding**: AST symbol extraction, dependency graphs, deterministic semantic snippets, and persisted repo memory
- **Tool Framework**: file operations, grep, shell execution, git diff/status, GitHub helpers, browser research hooks
- **Sandbox**: Docker SDK with CPU, memory, pid limits, network isolation by default, log capture, and execution traces
- **Evaluation Harness**: tests, lint, build, runtime budget, patch quality, hallucination checks, token usage, and numeric scoring
- **Search**: offline hashed embeddings by default, with Qdrant and sentence-transformers adapters available
- **Frontend**: Next.js and TailwindCSS observability dashboard
- **Observability**: Prometheus metrics, structured logging, execution traces, and DAG visibility

## Quick Start

```bash
cp .env.example .env
# edit .env with your API keys when model-backed agents are needed
docker-compose up --build
```

The harness also supports offline demo mode. If no `OPENAI_API_KEY` is configured, agents use deterministic fallback behavior so local smoke tests, dashboard demos, and sandbox verification still run without external model calls.

For MiniMax/OpenCode-style keys, set:

```bash
MINIMAX_API_KEY=your_key_here
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_MODEL=MiniMax-M2.7
```

When `MINIMAX_API_KEY` is set and `OPENAI_API_KEY` is empty, the planner, coder, debugger, and reviewer use MiniMax through the OpenAI-compatible client.

## Local Development

The default database is SQLite (`harness.db`) so the API can run without Docker:

```bash
python -m pip install --user -r requirements.txt
python -m uvicorn harness.api:app --host 127.0.0.1 --port 8000
```

Run the dashboard separately:

```bash
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

If port `8000` is already occupied, run the API on another port and point the dashboard proxy at it:

```bash
python -m uvicorn harness.api:app --host 127.0.0.1 --port 8001

cd frontend
$env:HARNESS_API_URL="http://127.0.0.1:8001"
npm run dev -- --hostname 127.0.0.1 --port 3001
```

Docker Compose overrides the database with PostgreSQL, Redis, and Qdrant for production-like runs.

## API Endpoints

- `POST /tasks` - Create a new task
- `GET /tasks` - List tasks
- `GET /tasks/{id}` - Get task status and results
- `POST /tasks/{id}/run` - Execute the SWE agent workflow
- `GET /tasks/{id}/events` - Stream persisted execution trace events
- `GET /tasks/{id}/steps` - List durable execution step records
- `POST /tasks/{id}/pull-request` - Prepare or create a branch/commit/PR artifact
- `GET /metrics` - Prometheus metrics
- `GET /health` - Health check

`POST /tasks/{id}/pull-request` defaults to dry-run mode. Dry runs return the intended branch, commit message, PR body, and Git commands without pushing or creating a remote PR. Set `dry_run` to `false` only after `GITHUB_TOKEN` is configured and the target repository remote is ready.

## Evaluation Harness

Automatically scores attempts on:

- Test success: 35 pts
- Lint quality: 15 pts
- Build success: 20 pts
- Patch quality and blast radius: 15 pts
- Hallucination/reference checks: 10 pts
- Runtime budget: 5 pts

Every evaluation returns machine-readable subreports so benchmark runs, PR checks, and retry loops can compare attempts consistently.

## Benchmarks

Place SWE-bench JSON in `data/swe_bench.json` and run:

```python
from harness.benchmarks.swe_bench import SWEBenchRunner

runner = SWEBenchRunner("data/swe_bench.json")
results = await runner.run(limit=10)
```

## Tests

```bash
pytest tests/ -v
```

## License

MIT
