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
    monkeypatch.setenv("HERMES_OPERATOR_ROOT", str(tmp_path))

    import asyncio
    payload = asyncio.run(plugin_api.snapshot())

    assert payload["proving_ground"]["current_phase"] == 1
    assert payload["workspace_cleanup"]["results"][0]["workspace"] == "DEMO"
    assert payload["branch_lifecycle"]["pruned_branches"][0]["branch"] == "auto/demo"
