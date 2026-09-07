import json
import subprocess
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


def test_workspace_parser_accepts_positional_build_request():
    import argparse

    from hermes_cli.subcommands.workspace import build_workspace_parser

    parser = argparse.ArgumentParser(prog="hermes")
    subparsers = parser.add_subparsers(dest="command")
    build_workspace_parser(subparsers, cmd_workspace=lambda args: 0)

    args = parser.parse_args(["workspace", "build", "build PRD", "--json"])

    assert args.command == "workspace"
    assert args.workspace_command == "build"
    assert args.request_text == "build PRD"
    assert args.json is True


def test_workspace_parser_accepts_execute_once_json():
    import argparse

    from hermes_cli.subcommands.workspace import build_workspace_parser

    parser = argparse.ArgumentParser(prog="hermes")
    subparsers = parser.add_subparsers(dest="command")
    build_workspace_parser(subparsers, cmd_workspace=lambda args: 0)

    args = parser.parse_args(["workspace", "execute", "--once", "--json"])

    assert args.command == "workspace"
    assert args.workspace_command == "execute"
    assert args.once is True
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
    assert local_row["request_id"]


def test_workspace_execute_runs_queued_request_inside_workspace(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    root = tmp_path / "HermesHome"
    workspace = tmp_path / "CustomerProject"
    workspace.mkdir()
    (workspace / "PRD.md").write_text("# PRD\nBuild a dashboard.\n", encoding="utf-8")

    monkeypatch.setenv("LEONOR_CALLER_CWD", str(workspace))
    monkeypatch.setenv("HERMES_HOME", str(root))
    assert leonor_workspace.workspace_build(SimpleNamespace(json=True, audit=True, request="build PRD")) == 0
    capsys.readouterr()

    def fake_run(command, cwd, env, timeout, capture_output, text):
        assert cwd == str(workspace)
        assert "--toolsets" in command
        assert "file,terminal" in command
        assert "--ignore-rules" in command
        assert "--reasoning" in command
        assert "minimal" in command
        assert env["LEONOR_TARGET_WORKSPACE"] == str(workspace)
        assert "build PRD" in env["LEONOR_WORKSPACE_REQUEST"]
        assert env["HERMES_MAX_TOKENS"] == "2048"
        (workspace / "built.txt").write_text("ok", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="built", stderr="")

    monkeypatch.setattr(leonor_workspace.subprocess, "run", fake_run)

    assert leonor_workspace.workspace_execute(SimpleNamespace(json=True, audit=True, once=True, timeout=30)) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "completed"
    assert payload["processed"] == 1
    assert (workspace / "built.txt").read_text(encoding="utf-8") == "ok"
    run_rows = [
        json.loads(line)
        for line in (workspace / ".leonor" / "runtime" / "build_runs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert run_rows[-1]["status"] == "completed"
    assert run_rows[-1]["exit_code"] == 0


def test_workspace_execute_blocks_queue_item_outside_allowed_root(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    root = tmp_path / "HermesHome"
    workspace = tmp_path / "CustomerProject"
    workspace.mkdir()
    outside = tmp_path / "OutsideProject"
    outside.mkdir()
    monkeypatch.setenv("LEONOR_CALLER_CWD", str(workspace))
    monkeypatch.setenv("HERMES_HOME", str(root))

    request_path = workspace / ".leonor" / "runtime" / "build_requests.jsonl"
    request_path.parent.mkdir(parents=True)
    request_path.write_text(
        json.dumps(
            {
                "schema": "leonor_workspace_build_request.v1",
                "status": "queued",
                "request_id": "bad",
                "request": "escape",
                "workspace": str(outside),
                "safety": {"allowed_root": str(workspace)},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert leonor_workspace.workspace_execute(SimpleNamespace(json=True, audit=True, once=True, timeout=30)) == 3

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "blocked"
    assert payload["runs"][0]["reason"] == "workspace_outside_allowed_root"


def test_workspace_execute_treats_agent_api_failure_text_as_failed(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    root = tmp_path / "HermesHome"
    workspace = tmp_path / "CustomerProject"
    workspace.mkdir()
    (workspace / "PRD.md").write_text("# PRD\nBuild a dashboard.\n", encoding="utf-8")

    monkeypatch.setenv("LEONOR_CALLER_CWD", str(workspace))
    monkeypatch.setenv("HERMES_HOME", str(root))
    assert leonor_workspace.workspace_build(SimpleNamespace(json=True, audit=True, request="build PRD")) == 0
    capsys.readouterr()

    def fake_run(command, cwd, env, timeout, capture_output, text):
        return subprocess.CompletedProcess(command, 0, stdout="API call failed after 3 retries", stderr="")

    monkeypatch.setattr(leonor_workspace.subprocess, "run", fake_run)

    assert leonor_workspace.workspace_execute(SimpleNamespace(json=True, audit=True, once=True, timeout=30)) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["runs"][0]["reason"] == "agent_reported_failure"


def test_workspace_execute_treats_auth_error_text_as_failed(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    root = tmp_path / "HermesHome"
    workspace = tmp_path / "CustomerProject"
    workspace.mkdir()
    (workspace / "PRD.md").write_text("# PRD\nCreate LEONOR_SMOKE.txt.\n", encoding="utf-8")

    monkeypatch.setenv("LEONOR_CALLER_CWD", str(workspace))
    monkeypatch.setenv("HERMES_HOME", str(root))
    assert leonor_workspace.workspace_build(SimpleNamespace(json=True, audit=True, request="build PRD")) == 0
    capsys.readouterr()

    def fake_run(command, cwd, env, timeout, capture_output, text):
        return subprocess.CompletedProcess(command, 0, stdout='HTTP 401: {"error":"Unauthorized"}', stderr="")

    monkeypatch.setattr(leonor_workspace.subprocess, "run", fake_run)

    assert leonor_workspace.workspace_execute(SimpleNamespace(json=True, audit=True, once=True, timeout=30)) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["runs"][0]["reason"] == "agent_reported_failure"


def test_workspace_execution_prompt_is_bounded_for_small_context_routes(tmp_path):
    from hermes_cli import leonor_workspace

    request = {
        "workspace": str(tmp_path),
        "request": "build",
        "plan": {
            "documents": [
                {"name": "PRD.md", "preview": "a" * 20_000},
                {"name": "README.md", "preview": "b" * 20_000},
            ]
        },
    }

    prompt = leonor_workspace._execution_prompt(request)

    assert len(prompt) <= 3000
    assert "LEONOR WORKSPACE EXECUTION" in prompt
    assert "aaa" in prompt


def test_workspace_executor_args_are_configurable(monkeypatch):
    from hermes_cli import leonor_workspace

    monkeypatch.setenv("LEONOR_WORKSPACE_EXECUTOR_TOOLSETS", "file,terminal")
    monkeypatch.setenv("LEONOR_WORKSPACE_EXECUTOR_REASONING", "low")

    command = leonor_workspace._executor_command("hi")

    assert command[-1] == "hi"
    assert command[command.index("--toolsets") + 1] == "file,terminal"
    assert command[command.index("--reasoning") + 1] == "low"


def test_workspace_executor_seeds_allowlisted_root_env_without_overriding_process_env(monkeypatch, tmp_path):
    from hermes_cli import leonor_workspace

    root = tmp_path / "HermesRoot"
    (root / "hermes-wrapper").mkdir(parents=True)
    (root / ".env").write_text(
        "HERMES_QWEN_API_KEY=root-secret\nHERMES_AUTONOMOUS_MODEL=qwen3.8-27b\nIGNORED_SECRET=do-not-load\n",
        encoding="utf-8",
    )
    (root / "hermes-wrapper" / ".env").write_text(
        "OPENAI_BASE_URL=http://example.invalid/v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LEONOR_ROOT", str(root))
    monkeypatch.delenv("HERMES_QWEN_API_KEY", raising=False)
    monkeypatch.delenv("HERMES_AUTONOMOUS_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    env = {"HERMES_QWEN_API_KEY": "existing-secret"}
    leonor_workspace._seed_executor_env(env)

    assert env["HERMES_QWEN_API_KEY"] == "existing-secret"
    assert env["HERMES_AUTONOMOUS_MODEL"] == "qwen3.8-27b"
    assert env["OPENAI_BASE_URL"] == "http://example.invalid/v1"
    assert "IGNORED_SECRET" not in env


def test_workspace_inspect_rejects_missing_workspace(monkeypatch, tmp_path, capsys):
    from hermes_cli import leonor_workspace

    missing = tmp_path / "missing"
    monkeypatch.setenv("LEONOR_CALLER_CWD", str(missing))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))

    assert leonor_workspace.workspace_inspect(SimpleNamespace(json=True, audit=True)) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["editable"] is False
    assert payload["error"] == "workspace_not_found"
