import json
from types import SimpleNamespace


def test_workspace_parser_accepts_inspect_json():
    import argparse

    from hermes_cli.subcommands.workspace import build_workspace_parser

    parser = argparse.ArgumentParser(prog="hermes")
    subparsers = parser.add_subparsers(dest="command")
    build_workspace_parser(subparsers, cmd_workspace=lambda args: 0)

    args = parser.parse_args(["workspace", "inspect", "--json"])

    assert args.command == "workspace"
    assert args.workspace_command == "inspect"
    assert args.json is True


def test_workspace_parser_accepts_build_request():
    import argparse

    from hermes_cli.subcommands.workspace import build_workspace_parser

    parser = argparse.ArgumentParser(prog="hermes")
    subparsers = parser.add_subparsers(dest="command")
    build_workspace_parser(subparsers, cmd_workspace=lambda args: 0)

    args = parser.parse_args(["workspace", "build", "--request", "implement PRD", "--json"])

    assert args.command == "workspace"
    assert args.workspace_command == "build"
    assert args.request == "implement PRD"
    assert args.json is True


def test_workspace_inspect_prefers_leonor_caller_cwd(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    root = tmp_path / "Hermes"
    workspace = tmp_path / "CustomerProject"
    workspace.mkdir()
    (workspace / "PRD.md").write_text("# Build this\n", encoding="utf-8")
    (workspace / "README.md").write_text("# Customer Project\n", encoding="utf-8")
    (workspace / ".git").mkdir()
    runtime = root / "runtime"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEONOR_CALLER_CWD", str(workspace))
    monkeypatch.setenv("HERMES_HOME", str(root))

    assert leonor_workspace.workspace_inspect(SimpleNamespace(json=True, audit=True)) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"] == str(workspace)
    assert payload["source"] == "LEONOR_CALLER_CWD"
    assert payload["docs"] == ["PRD.md", "README.md"]
    assert payload["git"]["present"] is True
    assert payload["editable"] is True

    audit = runtime / "leonor_workspace_actions.jsonl"
    rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["action"] == "workspace.inspect"
    assert rows[-1]["workspace"] == str(workspace)


def test_workspace_plan_reads_local_docs_without_editing(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    root = tmp_path / "HermesHome"
    workspace = tmp_path / "CustomerProject"
    workspace.mkdir()
    (workspace / "PRD.md").write_text("# PRD\nBuild a dashboard.\n", encoding="utf-8")
    (workspace / "README.md").write_text("# Customer Project\n", encoding="utf-8")

    monkeypatch.setenv("LEONOR_CALLER_CWD", str(workspace))
    monkeypatch.setenv("HERMES_HOME", str(root))

    assert leonor_workspace.workspace_plan(SimpleNamespace(json=True, audit=True, request="build it")) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready_for_local_lane"
    assert payload["request"] == "build it"
    assert [doc["name"] for doc in payload["documents"]] == ["PRD.md", "README.md"]
    assert payload["safety"]["allowed_root"] == str(workspace)
    assert not (workspace / ".leonor").exists()


def test_workspace_build_queues_local_lane_request(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    root = tmp_path / "HermesHome"
    workspace = tmp_path / "CustomerProject"
    workspace.mkdir()
    (workspace / "PRD.md").write_text("# PRD\nBuild a dashboard.\n", encoding="utf-8")

    monkeypatch.setenv("LEONOR_CALLER_CWD", str(workspace))
    monkeypatch.setenv("HERMES_HOME", str(root))

    assert leonor_workspace.workspace_build(SimpleNamespace(json=True, audit=True, request="build PRD")) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "queued"
    assert payload["request"] == "build PRD"
    assert payload["workspace"] == str(workspace)

    local_log = workspace / ".leonor" / "runtime" / "build_requests.jsonl"
    global_log = root / "runtime" / "leonor_workspace_build_requests.jsonl"
    assert local_log.exists()
    assert global_log.exists()
    local_row = json.loads(local_log.read_text(encoding="utf-8").splitlines()[-1])
    global_row = json.loads(global_log.read_text(encoding="utf-8").splitlines()[-1])
    assert local_row["request"] == "build PRD"
    assert global_row["workspace"] == str(workspace)


def test_workspace_inspect_rejects_missing_workspace(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    missing = tmp_path / "missing"
    monkeypatch.setenv("LEONOR_CALLER_CWD", str(missing))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))

    assert leonor_workspace.workspace_inspect(SimpleNamespace(json=True, audit=True)) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["editable"] is False
    assert payload["error"] == "workspace_not_found"
