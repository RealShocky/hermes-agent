import importlib.util
import json
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "tools.py"
SPEC = importlib.util.spec_from_file_location("tool_forge_tools", MODULE)
tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tools)


def test_assess_requires_repeated_evidence() -> None:
    payload = json.loads(tools.assess("demo", ["once"]))
    assert payload["recommendation"] == "reuse-or-skill"


def test_propose_persists_qualified_tool(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(tools, "_proposal_dir", lambda: tmp_path)
    payload = json.loads(
        tools.propose("Repo Inspector", "inspect repos", {"path": "string"}, "report", ["failure one", "failure two"])
    )
    assert payload["proposal"]["task_type"] == "tool"
    assert Path(payload["path"]).exists()
