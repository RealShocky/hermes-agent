import importlib.util
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "dashboard" / "plugin_api.py"
SPEC = importlib.util.spec_from_file_location("operator_brain_api", MODULE)
plugin_api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plugin_api)


def test_json_returns_empty_for_missing_file(tmp_path) -> None:
    assert plugin_api._json(tmp_path / "missing.json") == {}


def test_json_reads_object(tmp_path) -> None:
    path = tmp_path / "value.json"
    path.write_text('{"status":"passed"}', encoding="utf-8")
    assert plugin_api._json(path)["status"] == "passed"


def test_snapshot_exposes_proving_ground(tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "overwatch_proving_ground.json").write_text('{"current_phase":1}', encoding="utf-8")
    (runtime / "workspace_cleanup.json").write_text('{"results":[{"workspace":"DEMO"}]}', encoding="utf-8")
    (runtime / "branch_lifecycle.json").write_text('{"pruned_branches":[{"branch":"auto/demo"}]}', encoding="utf-8")
    (runtime / "native_tool_lifecycle.json").write_text('{"gate":"overwatch_proving_ground"}', encoding="utf-8")
    (runtime / "expansion_readiness.json").write_text('{"ready_for_more_repos":false}', encoding="utf-8")
    (runtime / "operator_council.json").write_text('{"consensus":"proceed_with_overwatch"}', encoding="utf-8")
    (runtime / "online_research_policy.json").write_text('{"default":"offline_first"}', encoding="utf-8")
    (runtime / "agent_skill_ratings.json").write_text('{"ratings":{"overall_system":{"score":7.1}}}', encoding="utf-8")
    (runtime / "operator_intelligence.json").write_text('{"timestamp":"now"}', encoding="utf-8")
    machine_ops = tmp_path / "machine-ops" / "pending"
    machine_ops.mkdir(parents=True)
    (machine_ops / "request.json").write_text(
        '{"id":"req-1","status":"approved","action":"qwen.restart","risk":"medium","reason":"test"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_OPERATOR_ROOT", str(tmp_path))
    monkeypatch.setenv("HERMES_MACHINE_OPS_ROOT", str(tmp_path / "machine-ops"))

    import asyncio
    payload = asyncio.run(plugin_api.snapshot())

    assert payload["proving_ground"]["current_phase"] == 1
    assert payload["workspace_cleanup"]["results"][0]["workspace"] == "DEMO"
    assert payload["branch_lifecycle"]["pruned_branches"][0]["branch"] == "auto/demo"
    assert payload["native_tool_lifecycle"]["gate"] == "overwatch_proving_ground"
    assert payload["expansion_readiness"]["ready_for_more_repos"] is False
    assert payload["operator_council"]["consensus"] == "proceed_with_overwatch"
    assert payload["online_research_policy"]["default"] == "offline_first"
    assert payload["agent_skill_ratings"]["ratings"]["overall_system"]["score"] == 7.1
    assert payload["operator_intelligence"]["timestamp"] == "now"
    assert payload["machine_ops"]["total"] == 1
    assert payload["machine_ops"]["by_action"]["qwen.restart"] == 1
    assert payload["machine_ops"]["latest_requests"][0]["reason"] == "test"
