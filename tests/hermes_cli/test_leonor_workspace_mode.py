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


def test_workspace_inspect_rejects_missing_workspace(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    missing = tmp_path / "missing"
    monkeypatch.setenv("LEONOR_CALLER_CWD", str(missing))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))

    assert leonor_workspace.workspace_inspect(SimpleNamespace(json=True, audit=True)) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["editable"] is False
    assert payload["error"] == "workspace_not_found"
