from types import SimpleNamespace


def test_status_parser_accepts_brain_flags():
    import argparse

    from hermes_cli.subcommands.status import build_status_parser

    parser = argparse.ArgumentParser(prog="hermes")
    subparsers = parser.add_subparsers(dest="command")
    build_status_parser(subparsers, cmd_status=lambda args: 0)

    args = parser.parse_args(["status", "--brain-only"])
    assert args.command == "status"
    assert args.brain_only is True
    assert args.brain is False

    args = parser.parse_args(["status", "--brain"])
    assert args.brain is True
    assert args.brain_only is False


def test_operator_parser_accepts_pause_resume_status_refresh():
    import argparse

    from hermes_cli.subcommands.operator import build_operator_parser

    parser = argparse.ArgumentParser(prog="hermes")
    subparsers = parser.add_subparsers(dest="command")
    build_operator_parser(subparsers, cmd_operator=lambda args: 0)

    args = parser.parse_args(["operator", "pause", "--reason", "cooldown"])
    assert args.command == "operator"
    assert args.operator_command == "pause"
    assert args.reason == "cooldown"

    for subcommand in ("status", "resume", "refresh"):
        args = parser.parse_args(["operator", subcommand])
        assert args.operator_command == subcommand


def test_brain_status_reads_wrapper_runtime(monkeypatch, tmp_path, capsys):
    from hermes_cli import prime_operator

    root = tmp_path / "Hermes"
    runtime = root / "hermes-wrapper" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "overwatch_proving_ground.json").write_text(
        '{"workspace":"PROOFRAIL_TRUST_CENTER","target_attempts":10,'
        '"attempts_observed":10,"successful_attempts":10,'
        '"ready_for_more_repos":true,'
        '"latest_validation":{"status":"passed"}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LEONOR_ROOT", str(root))

    assert prime_operator.print_brain_status(concise=True) == 0

    output = capsys.readouterr().out
    assert "paused: no" in output
    assert "workspace: PROOFRAIL_TRUST_CENTER" in output
    assert "proofrail: 10/10 successful (10 observed)" in output
    assert "ready_for_more_repos: True" in output
    assert "latest_validation: passed" in output


def test_operator_pause_resume_writes_marker_and_audit(monkeypatch, tmp_path):
    from hermes_cli import prime_operator

    root = tmp_path / "Hermes"
    runtime = root / "hermes-wrapper" / "runtime"
    runtime.mkdir(parents=True)
    monkeypatch.setenv("LEONOR_ROOT", str(root))

    assert prime_operator.operator_pause(SimpleNamespace(reason="cool down")) == 0
    marker = root / "hermes-wrapper" / ".pause_operator"
    assert marker.read_text(encoding="utf-8") == "cool down\n"

    assert prime_operator.operator_resume(SimpleNamespace()) == 0
    assert not marker.exists()

    audit = runtime / "operator_cli_actions.jsonl"
    text = audit.read_text(encoding="utf-8")
    assert '"action": "pause"' in text
    assert '"action": "resume"' in text
    assert "cool down" in text


def test_pause_marker_overrides_stale_running_watchdog(monkeypatch, tmp_path, capsys):
    from hermes_cli import prime_operator

    root = tmp_path / "Hermes"
    wrapper = root / "hermes-wrapper"
    runtime = wrapper / "runtime"
    runtime.mkdir(parents=True)
    (wrapper / ".pause_operator").write_text("cooling\n", encoding="utf-8")
    (runtime / "operator_watchdog.json").write_text(
        '{"status":"running","timestamp":"2026-08-31T08:40:12Z"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LEONOR_ROOT", str(root))

    assert prime_operator.print_brain_status(concise=True) == 0

    output = capsys.readouterr().out
    assert "paused: yes" in output
    assert "watchdog_status: paused (snapshot was running)" in output
