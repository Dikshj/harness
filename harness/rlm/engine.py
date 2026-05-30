from __future__ import annotations

import re
import textwrap
from dataclasses import asdict, dataclass

from harness.config import get_settings
from harness.rlm.memory import JsonlMemoryStore
from harness.rlm.repl import SandboxedPythonRepl


@dataclass
class RLMRunConfig:
    max_depth: int = 3
    branch_factor: int = 3
    context_window: int = 1200
    repl_timeout_seconds: int = 5


class RLMEngine:
    def __init__(self, memory: JsonlMemoryStore | None = None, repl: SandboxedPythonRepl | None = None):
        self.memory = memory or JsonlMemoryStore(get_settings().rlm_memory_path)
        self.repl = repl or SandboxedPythonRepl()

    async def run(self, task_id: str, goal: str, context: str = "", config: RLMRunConfig | None = None) -> dict:
        config = config or RLMRunConfig()
        retrieved = self.memory.search(f"{goal} {context}")
        traces: list[dict] = []
        tree = self._solve_node(
            task_id=task_id,
            node_id="root",
            goal=goal,
            context=context,
            depth=0,
            config=config,
            traces=traces,
            retrieved_memory=retrieved,
        )
        summary = self._summarize_tree(tree)
        self.memory.append(task_id, "root", "run_summary", summary, {"node_count": len(traces)})
        return {
            "summary": summary,
            "tree": tree,
            "traces": traces,
            "memory_hits": retrieved,
            "execution_graph": self._graph_from_traces(traces),
            "config": asdict(config),
            "score": self._score(traces),
        }

    def _solve_node(
        self,
        task_id: str,
        node_id: str,
        goal: str,
        context: str,
        depth: int,
        config: RLMRunConfig,
        traces: list[dict],
        retrieved_memory: list[dict],
    ) -> dict:
        compressed = self._compress_context(context, config.context_window)
        should_recurse = depth < config.max_depth and len(context) > config.context_window
        subtasks = self._decompose(goal, context, config.branch_factor) if should_recurse else []
        trace = {
            "node": node_id,
            "depth": depth,
            "goal": goal,
            "context_chars": len(context),
            "compressed_chars": len(compressed),
            "spawned": len(subtasks),
            "memory_hits": len(retrieved_memory) if depth == 0 else 0,
        }
        traces.append(trace)

        children = [
            self._solve_node(
                task_id=task_id,
                node_id=f"{node_id}.{index + 1}",
                goal=subtask,
                context=self._slice_context(context, index, len(subtasks)),
                depth=depth + 1,
                config=config,
                traces=traces,
                retrieved_memory=[],
            )
            for index, subtask in enumerate(subtasks)
        ]
        repl_result = self._repl_probe(goal, compressed, len(children))
        content = self._node_summary(goal, compressed, children, repl_result.stdout)
        self.memory.append(
            task_id,
            node_id,
            "node_summary",
            content,
            {"depth": depth, "children": len(children), "repl_exit_code": repl_result.exit_code},
        )
        return {
            "id": node_id,
            "goal": goal,
            "depth": depth,
            "context_summary": compressed,
            "children": children,
            "repl": asdict(repl_result),
            "summary": content,
        }

    def _decompose(self, goal: str, context: str, branch_factor: int) -> list[str]:
        bullets = [part.strip(" -\t") for part in re.split(r"[\n.;]", context) if len(part.strip()) > 40]
        if not bullets:
            bullets = textwrap.wrap(context, width=max(180, len(context) // max(branch_factor, 1)))
        return [f"{goal}: analyze shard {index + 1} - {item[:140]}" for index, item in enumerate(bullets[:branch_factor])]

    def _compress_context(self, context: str, context_window: int) -> str:
        normalized = " ".join(context.split())
        if len(normalized) <= context_window:
            return normalized
        head = normalized[: context_window // 2].rstrip()
        tail = normalized[-context_window // 2 :].lstrip()
        return f"{head} ... [compressed {len(normalized) - len(head) - len(tail)} chars] ... {tail}"

    def _slice_context(self, context: str, index: int, total: int) -> str:
        if total <= 1:
            return context
        width = max(1, len(context) // total)
        start = index * width
        end = len(context) if index == total - 1 else start + width
        return context[start:end]

    def _repl_probe(self, goal: str, compressed: str, child_count: int):
        code = (
            "import json\n"
            f"goal = {goal!r}\n"
            f"context = {compressed!r}\n"
            f"children = {child_count!r}\n"
            "print(json.dumps({'goal_words': len(goal.split()), 'context_chars': len(context), 'children': children}))\n"
        )
        return self.repl.run(code)

    def _node_summary(self, goal: str, compressed: str, children: list[dict], repl_stdout: str) -> str:
        child_text = "; ".join(child["summary"] for child in children[:3])
        basis = compressed[:260] if compressed else "No external context supplied."
        if child_text:
            return f"{goal} resolved by {len(children)} recursive subcalls. Local basis: {basis}. Child findings: {child_text}"
        return f"{goal} resolved in local REPL. Basis: {basis}. Probe: {repl_stdout or 'no output'}"

    def _summarize_tree(self, tree: dict) -> str:
        return tree["summary"]

    def _graph_from_traces(self, traces: list[dict]) -> dict:
        nodes = [trace["node"] for trace in traces]
        edges = []
        for node in nodes:
            if "." in node:
                parent = node.rsplit(".", 1)[0]
                edges.append([parent, node])
        return {"nodes": nodes, "edges": edges}

    def _score(self, traces: list[dict]) -> dict:
        if not traces:
            return {"score": 0, "max_score": 100}
        recursive_nodes = sum(1 for trace in traces if trace["depth"] > 0)
        score = min(100, 55 + recursive_nodes * 10 + min(len(traces), 5) * 3)
        return {"score": score, "max_score": 100}
