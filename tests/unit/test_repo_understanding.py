from harness.memory.repo_understanding import RepositoryUnderstandingEngine


def test_repo_understanding_indexes_python_symbols(tmp_path):
    source = tmp_path / "app.py"
    source.write_text(
        "import json\n\n"
        "class Service:\n"
        "    def run(self):\n"
        "        return json.dumps({'ok': True})\n"
    )

    engine = RepositoryUnderstandingEngine(str(tmp_path))
    context = engine.build_context()

    assert context["file_count"] == 1
    assert any(symbol["name"] == "Service" for symbol in context["symbols"])
    assert any(symbol["name"] == "run" for symbol in context["symbols"])
    assert context["dependencies"]["app.py"] == ["json"]
    assert engine.search("json service", top_k=1)[0]["path"] == "app.py"
