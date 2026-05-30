# RLM Harness

A self-recursive coding-agent harness that decomposes long context by spawning sub-LLM-style calls inside a sandboxed Python REPL, then stores useful summaries in persistent memory.

## What It Does

- Accepts a coding goal plus long context.
- Compresses the active context window.
- Recursively decomposes oversized context into child reasoning nodes.
- Runs each node through a sandboxed Python REPL probe.
- Stores node summaries and final run summaries in JSONL memory.
- Retrieves related memory for later runs.
- Exposes runs, traces, steps, memory search, and health checks through FastAPI.
- Provides a Next.js dashboard for recursion depth, spawned nodes, memory hits, and REPL steps.

This project is intentionally focused on the RLM harness only. The earlier autonomous SWE platform, PR workflow, SWE-bench runner, and multi-role planner/coder/tester/reviewer pipeline have been removed.

## Architecture

- **API**: FastAPI with SQLite persistence.
- **RLM Engine**: Recursive decomposition, context compression, trace graph generation.
- **Sandboxed REPL**: Isolated temporary Python subprocess with timeout.
- **Memory**: Append-only `.rlm_memory.jsonl` store with simple lexical retrieval.
- **Dashboard**: Next.js and TailwindCSS.

## Quick Start

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

## API

- `POST /runs` - Create an RLM run.
- `GET /runs` - List runs.
- `GET /runs/{id}` - Get one run and its result tree.
- `POST /runs/{id}/execute` - Execute recursive decomposition and REPL probes.
- `GET /runs/{id}/steps` - List persisted sandbox steps.
- `GET /runs/{id}/events` - Stream trace events.
- `GET /memory/search?q=...` - Search persistent RLM memory.
- `GET /health` - Health check.

Example:

```bash
curl -X POST http://127.0.0.1:8000/runs ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"Refactor plan\",\"goal\":\"Find implementation strategy\",\"context\":\"very long context here\"}"
```

## Tests

```bash
pytest tests/ -v
```
