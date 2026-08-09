import json

from hermes_cli.operator_brain import (
    build_operator_brain_summary,
    find_prime_root,
    format_operator_brain_summary,
    load_operator_brain_state,
)


def test_find_prime_root_detects_wrapper_runtime(tmp_path):
    root = tmp_path / "Hermes"
    runtime = root / "hermes-wrapper" / "runtime"
    runtime.mkdir(parents=True)

    assert find_prime_root(root / "hermes-core-fork") == root


def test_operator_brain_summary_reads_live_runtime(tmp_path):
    root = tmp_path / "Hermes"
    runtime = root / "hermes-wrapper" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "operator_watchdog.json").write_text(
        json.dumps({"timestamp": "2026-08-09T00:00:00Z", "status": "running", "pids": [123]}),
        encoding="utf-8",
    )
    (runtime / "overwatch_proving_ground.json").write_text(
        json.dumps(
            {
                "timestamp": "2026-08-09T00:01:00Z",
                "successful_attempts": 8,
                "target_attempts": 10,
                "current_phase": 2,
                "pending_total": 6,
                "latest_pull_request": {"number": 14, "status": "merged"},
                "latest_validation": {"status": "passed"},
                "latest_deployment": {"status": "completed"},
                "failure_improvement_contract": {"pending_count": 2, "satisfied_count": 8},
            }
        ),
        encoding="utf-8",
    )
    (runtime / "operator_intelligence.json").write_text(
        json.dumps(
            {
                "timestamp": "2026-08-09T00:02:00Z",
                "council": {
                    "status": "active",
                    "consensus": "proceed_with_overwatch",
                    "ratings": {"overall_system": {"score": 7.5, "title": "mid-level"}},
                },
            }
        ),
        encoding="utf-8",
    )
    (runtime / "operator_brain_kanban_sync.json").write_text(
        json.dumps({"board": "operator-brain", "task_count": 23}),
        encoding="utf-8",
    )

    state = load_operator_brain_state(root)
    summary = build_operator_brain_summary(state)
    text = format_operator_brain_summary(summary)

    assert summary["operator_status"] == "running"
    assert summary["overwatch"]["successful_attempts"] == 8
    assert "Overwatch: 8/10" in text
    assert "Latest PR: 14 merged" in text
    assert "Council: proceed_with_overwatch" in text


def test_operator_brain_unavailable_message(tmp_path):
    state = load_operator_brain_state(tmp_path / "missing")
    text = format_operator_brain_summary(build_operator_brain_summary(state))

    assert "Operator Brain: unavailable" in text


def test_status_brain_only_prints_just_operator_brain(monkeypatch, capsys, tmp_path):
    from types import SimpleNamespace

    from hermes_cli import status as status_mod

    root = tmp_path / "Hermes"
    runtime = root / "hermes-wrapper" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "operator_watchdog.json").write_text(
        json.dumps({"status": "running", "pids": [123]}),
        encoding="utf-8",
    )
    (runtime / "overwatch_proving_ground.json").write_text(
        json.dumps({"successful_attempts": 8, "target_attempts": 10}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_PRIME_ROOT", str(root))

    status_mod.show_status(SimpleNamespace(all=False, deep=False, brain_only=True))
    output = capsys.readouterr().out

    assert output.startswith("Operator Brain")
    assert "API Keys" not in output
    assert "Overwatch: 8/10" in output


def test_operator_pause_resume_write_marker_and_audit(tmp_path):
    root = tmp_path / "Hermes"
    runtime = root / "hermes-wrapper" / "runtime"
    runtime.mkdir(parents=True)

    from hermes_cli.operator_brain import operator_pause, operator_resume

    paused = operator_pause("cool down", root=root)
    marker = root / "hermes-wrapper" / ".pause_operator"

    assert paused["ok"] is True
    assert marker.exists()
    assert "cool down" in marker.read_text(encoding="utf-8")

    resumed = operator_resume(root=root)

    assert resumed["ok"] is True
    assert resumed["marker_existed"] is True
    assert not marker.exists()
    audit = runtime / "operator_cli_actions.jsonl"
    audit_text = audit.read_text(encoding="utf-8")
    assert '"action": "operator.pause"' in audit_text
    assert '"action": "operator.resume"' in audit_text


def test_create_prime_task_appends_ready_item_and_audit(monkeypatch, tmp_path):
    root = tmp_path / "Hermes"
    wrapper = root / "hermes-wrapper"
    runtime = wrapper / "runtime"
    registry = wrapper / "workspace-registry"
    workspace = root / "demo"
    registry.mkdir(parents=True)
    runtime.mkdir(parents=True)
    workspace.mkdir()
    (registry / "workspaces.yaml").write_text(
        "\n".join(
            [
                "workspaces:",
                "- name: DEMO",
                f"  path: {workspace.as_posix()}",
                "  backlog_files:",
                "  - HERMES_TASKS.md",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "HERMES_TASKS.md").write_text("# Demo\n\n## Ready\n\n## Completed\n", encoding="utf-8")

    from hermes_cli import prime_intake

    monkeypatch.setattr(prime_intake, "operator_refresh", lambda root: {"ok": True, "status": "refreshed"})

    result = prime_intake.create_prime_task(
        workspace_name="DEMO",
        summary="Add useful self-analysis report",
        task_type="self-improve",
        root=root,
    )

    assert result["ok"] is True
    backlog = (workspace / "HERMES_TASKS.md").read_text(encoding="utf-8")
    assert "- [ ] Add useful self-analysis report" in backlog
    intake = runtime / "prime_task_intake.json"
    assert '"workspace": "DEMO"' in intake.read_text(encoding="utf-8")
    audit = runtime / "prime_task_intake.jsonl"
    assert "Add useful self-analysis report" in audit.read_text(encoding="utf-8")


def test_list_approvals_reads_runtime_queue(tmp_path):
    root = tmp_path / "Hermes"
    runtime = root / "hermes-wrapper" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "approval_queue.json").write_text(
        json.dumps(
            {
                "approval_requests": [
                    {
                        "id": "ap-1",
                        "title": "Approve public post",
                        "status": "pending",
                        "risk_level": "medium",
                        "reason": "External-facing action",
                    },
                    {"id": "ap-2", "title": "Already approved", "status": "approved"},
                    {
                        "id": "ap-3",
                        "title": "Dataset intake mentions approval but is autonomous",
                        "status": "pending",
                        "approval_required": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    from hermes_cli.prime_approvals import format_approvals, list_approvals

    payload = list_approvals(root=root)
    text = format_approvals(payload)

    assert payload["approval_count"] == 1
    assert "Approve public post" in text
    assert "Already approved" not in text
    assert "Dataset intake" not in text
