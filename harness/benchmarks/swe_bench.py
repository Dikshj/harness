
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict
from harness.workflows.swe_graph import swe_graph, SWEState

class SWEBenchRunner:
    def __init__(self, dataset_path: str, report_dir: str = "reports"):
        with open(dataset_path) as f:
            self.dataset = json.load(f)
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    async def run(self, limit: int = 10) -> List[Dict]:
        results = []
        for item in self.dataset[:limit]:
            state: SWEState = {
                "task_id": item["instance_id"],
                "context": {
                    "title": item.get("problem_statement", "")[:200],
                    "description": item.get("problem_statement", ""),
                    "repo_path": item.get("repo", ""),
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
                "max_retries": 3,
            }
            try:
                out = await swe_graph.ainvoke(state)
                evaluation = out.get("eval_result", {})
                results.append({
                    "id": item["instance_id"],
                    "status": "completed",
                    "score": evaluation.get("score", 0),
                    "max_score": evaluation.get("max_score", 100),
                    "eval": evaluation,
                    "retries": out.get("retries", 0),
                    "trace_nodes": [trace.get("node") for trace in out.get("traces", [])],
                })
            except Exception as e:
                results.append({"id": item["instance_id"], "status": "failed", "score": 0, "error": str(e)})
        self.write_report(results)
        return results

    def summarize(self, results: List[Dict]) -> Dict:
        scores = [item.get("score", 0) for item in results]
        completed = [item for item in results if item["status"] == "completed"]
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(results),
            "completed": len(completed),
            "failed": len(results) - len(completed),
            "success_rate": round(len(completed) / len(results), 4) if results else 0,
            "mean_score": round(statistics.mean(scores), 2) if scores else 0,
            "median_score": round(statistics.median(scores), 2) if scores else 0,
            "leaderboard": sorted(
                [{"id": item["id"], "score": item.get("score", 0), "status": item["status"]} for item in results],
                key=lambda item: item["score"],
                reverse=True,
            ),
        }

    def write_report(self, results: List[Dict]) -> Dict[str, str]:
        summary = self.summarize(results)
        json_path = self.report_dir / "swe_bench_report.json"
        md_path = self.report_dir / "swe_bench_report.md"
        json_path.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
        lines = [
            "# SWE-bench Harness Report",
            "",
            f"- Total: {summary['total']}",
            f"- Completed: {summary['completed']}",
            f"- Failed: {summary['failed']}",
            f"- Success rate: {summary['success_rate']}",
            f"- Mean score: {summary['mean_score']}",
            "",
            "## Leaderboard",
            "",
            "| Rank | Instance | Score | Status |",
            "| --- | --- | ---: | --- |",
        ]
        for rank, item in enumerate(summary["leaderboard"], 1):
            lines.append(f"| {rank} | `{item['id']}` | {item['score']} | {item['status']} |")
        md_path.write_text("\n".join(lines))
        return {"json": str(json_path), "markdown": str(md_path)}
