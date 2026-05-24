from harness.benchmarks.swe_bench import SWEBenchRunner


def test_benchmark_summary_and_report(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text('[{"instance_id":"case-1","problem_statement":"Fix issue","repo":"."}]')
    runner = SWEBenchRunner(str(dataset), report_dir=str(tmp_path / "reports"))
    results = [{"id": "case-1", "status": "completed", "score": 88}]

    summary = runner.summarize(results)
    paths = runner.write_report(results)

    assert summary["success_rate"] == 1
    assert summary["leaderboard"][0]["id"] == "case-1"
    assert (tmp_path / "reports" / "swe_bench_report.json").exists()
    assert (tmp_path / "reports" / "swe_bench_report.md").exists()
    assert paths["json"].endswith("swe_bench_report.json")
