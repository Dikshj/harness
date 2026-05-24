
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
from harness.agents.planner import PlannerAgent
from harness.agents.coder import CoderAgent
from harness.agents.tester import TesterAgent
from harness.agents.debugger import DebuggerAgent
from harness.agents.reviewer import ReviewerAgent
from harness.agents.evaluator import EvaluatorAgent
from harness.memory.repo_understanding import RepositoryUnderstandingEngine
from harness.memory.redis_cache import set_json, get_json
from harness.observability.metrics import tasks_total, task_latency, retries_total, active_tasks
import time

class SWEState(TypedDict):
    task_id: str
    context: Dict[str, Any]
    plan: List[Dict]
    code_result: Dict
    test_result: Dict
    debug_result: Dict
    review_result: Dict
    eval_result: Dict
    repo_context: Dict
    execution_graph: Dict
    traces: List[Dict[str, Any]]
    retries: int
    max_retries: int

async def repo_context_node(state: SWEState):
    engine = RepositoryUnderstandingEngine(state["context"].get("repo_path", "."))
    context = engine.build_context()
    return {
        "repo_context": {
            "file_count": context["file_count"],
            "symbol_count": len(context["symbols"]),
            "dependency_count": sum(len(deps) for deps in context["dependencies"].values()),
            "top_symbols": context["symbols"][:25],
        },
        "traces": state.get("traces", []) + [{"node": "repo_context", "files": context["file_count"]}],
    }

async def planner_node(state: SWEState):
    agent = PlannerAgent("planner")
    result = await agent.run({**state["context"], "repo_context": state.get("repo_context", {})})
    return {
        "plan": result.get("plan", []),
        "execution_graph": result.get("execution_graph", {}),
        "traces": state.get("traces", []) + [{"node": "planner", "steps": len(result.get("plan", []))}],
    }

async def coder_node(state: SWEState):
    agent = CoderAgent("coder")
    step = state["plan"].pop(0) if state["plan"] else {"description": "implement fix"}
    ctx = {**state["context"], "step": step}
    result = await agent.run(ctx)
    return {"code_result": result, "traces": state.get("traces", []) + [{"node": "coder", "actions": len(result.get("actions", []))}]}

async def tester_node(state: SWEState):
    agent = TesterAgent("tester")
    ctx = {**state["context"], "code_result": state["code_result"]}
    result = await agent.run(ctx)
    return {"test_result": result, "traces": state.get("traces", []) + [{"node": "tester", "summary": result.get("summary", {})}]}

async def debugger_node(state: SWEState):
    agent = DebuggerAgent("debugger")
    ctx = {**state["context"], "test_result": state["test_result"]}
    result = await agent.run(ctx)
    retries_total.inc()
    return {"debug_result": result, "retries": state["retries"] + 1, "traces": state.get("traces", []) + [{"node": "debugger", "retry": state["retries"] + 1}]}

async def reviewer_node(state: SWEState):
    agent = ReviewerAgent("reviewer")
    ctx = {
        **state["context"],
        "code_result": state["code_result"],
        "test_result": state["test_result"],
    }
    result = await agent.run(ctx)
    return {"review_result": result, "traces": state.get("traces", []) + [{"node": "reviewer", "approval": result.get("approval", False)}]}

async def eval_node(state: SWEState):
    agent = EvaluatorAgent("evaluator")
    result = await agent.run(state["context"])
    traces = state.get("traces", []) + [{"node": "eval", "score": result.get("score", 0)}]
    await set_json(f"task:{state['task_id']}:events", traces)
    await set_json(f"task:{state['task_id']}:result", {"eval": result, "traces": traces})
    return {"eval_result": result, "traces": traces}

def route_after_test(state: SWEState):
    if state["test_result"]["summary"]["tests_failed"] == 0:
        return "reviewer"
    if state["retries"] < state["max_retries"]:
        return "debugger"
    return "reviewer"

def route_after_review(state: SWEState):
    if state["review_result"].get("approval"):
        return "eval"
    if state["retries"] < state["max_retries"]:
        return "debugger"
    return "eval"

builder = StateGraph(SWEState)
builder.add_node("repo_context", repo_context_node)
builder.add_node("planner", planner_node)
builder.add_node("coder", coder_node)
builder.add_node("tester", tester_node)
builder.add_node("debugger", debugger_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("eval", eval_node)

builder.set_entry_point("repo_context")
builder.add_edge("repo_context", "planner")
builder.add_edge("planner", "coder")
builder.add_edge("coder", "tester")
builder.add_conditional_edges("tester", route_after_test, {"reviewer": "reviewer", "debugger": "debugger"})
builder.add_conditional_edges("reviewer", route_after_review, {"eval": "eval", "debugger": "debugger"})
builder.add_edge("debugger", "coder")
builder.add_edge("eval", END)

swe_graph = builder.compile()
