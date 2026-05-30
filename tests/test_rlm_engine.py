import asyncio

from harness.rlm.engine import RLMEngine, RLMRunConfig
from harness.rlm.memory import JsonlMemoryStore
from harness.rlm.repl import SandboxedPythonRepl


def test_rlm_engine_recurses_and_persists_memory(tmp_path):
    memory = JsonlMemoryStore(tmp_path / "memory.jsonl")
    engine = RLMEngine(memory=memory, repl=SandboxedPythonRepl(timeout_seconds=2))
    context = "\n".join(
        f"- module {index} has implementation detail that should be analyzed separately for recursion"
        for index in range(12)
    )

    result = asyncio.run(
        engine.run(
            task_id="test-run",
            goal="Design the implementation",
            context=context,
            config=RLMRunConfig(max_depth=2, branch_factor=3, context_window=220),
        )
    )

    assert result["execution_graph"]["nodes"][0] == "root"
    assert len(result["traces"]) > 1
    assert result["tree"]["children"]
    assert result["score"]["score"] > 55
    assert memory.search("implementation")


def test_sandboxed_repl_captures_output():
    repl = SandboxedPythonRepl(timeout_seconds=2)

    result = repl.run("print(2 + 3)")

    assert result.exit_code == 0
    assert result.stdout == "5"
