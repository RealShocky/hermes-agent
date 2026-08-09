"""Hermes Prime task intake helpers for the CLI operator bridge."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hermes_cli.operator_brain import find_prime_root, operator_refresh


TASK_TYPES = {"feature", "fix", "self-improve", "infra", "tool"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "task"


def _registry_path(root: Path) -> Path:
    return root / "hermes-wrapper" / "workspace-registry" / "workspaces.yaml"


def _runtime_path(root: Path, name: str) -> Path:
    return root / "hermes-wrapper" / "runtime" / name


def _load_workspaces(root: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(_registry_path(root).read_text(encoding="utf-8")) or {}
    workspaces = payload.get("workspaces")
    return workspaces if isinstance(workspaces, list) else []


def _find_workspace(root: Path, name: str) -> dict[str, Any]:
    wanted = name.strip().casefold()
    for workspace in _load_workspaces(root):
        if str(workspace.get("name", "")).casefold() == wanted:
            return workspace
    raise KeyError(f"unknown workspace: {name}")


def _backlog_path(workspace: dict[str, Any]) -> Path:
    workspace_root = Path(str(workspace["path"]))
    backlog_files = workspace.get("backlog_files") or ["HERMES_TASKS.md"]
    for candidate in backlog_files:
        path = workspace_root / str(candidate)
        if path.name == "HERMES_TASKS.md":
            return path
    return workspace_root / str(backlog_files[0])


def _ensure_backlog(path: Path, workspace_name: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"# {workspace_name} Task Queue",
                "",
                "Unchecked items in this file are eligible for Hermes autonomous coding.",
                "",
                "## Ready",
                "",
                "## Completed",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _append_ready_item(path: Path, summary: str) -> None:
    _ensure_backlog(path, path.parent.name.upper())
    text = path.read_text(encoding="utf-8")
    line = f"- [ ] {summary.strip()}"
    if line in text:
        return
    lines = text.splitlines()
    for index, existing in enumerate(lines):
        if existing.strip().lower() == "## ready":
            insert_at = index + 1
            while insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            lines.insert(insert_at, line)
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            return
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend(["## Ready", "", line])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _write_state(root: Path, record: dict[str, Any]) -> None:
    state_path = _runtime_path(root, "prime_task_intake.json")
    previous: list[dict[str, Any]] = []
    if state_path.exists():
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            items = payload.get("tasks")
            previous = items if isinstance(items, list) else []
        except (OSError, json.JSONDecodeError):
            previous = []
    tasks = [record, *previous]
    state_path.write_text(
        json.dumps(
            {
                "schema": "prime_task_intake.v1",
                "timestamp": record["timestamp"],
                "task_count": len(tasks),
                "latest": record,
                "tasks": tasks[:50],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def create_prime_task(
    *,
    workspace_name: str,
    summary: str,
    reason: str | None = None,
    task_type: str = "feature",
    refresh: bool = True,
    dispatch: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """Add a user-approved task to a registered workspace backlog."""
    if task_type not in TASK_TYPES:
        raise ValueError(f"unsupported task type: {task_type}")
    prime_root = root or find_prime_root()
    if prime_root is None:
        return {"ok": False, "status": "unavailable", "message": "Hermes Prime root not found."}

    workspace = _find_workspace(prime_root, workspace_name)
    backlog = _backlog_path(workspace)
    _append_ready_item(backlog, summary)

    timestamp = _utc_now()
    record = {
        "timestamp": timestamp,
        "source": "hermes-cli",
        "status": "queued",
        "task_id": f"{workspace['name'].lower()}-{_slug(summary)}-{timestamp.replace(':', '').replace('-', '')}",
        "workspace": workspace["name"],
        "workspace_path": workspace["path"],
        "task_type": task_type,
        "summary": summary.strip(),
        "reason": reason or "User approved autonomous implementation from Hermes CLI.",
        "backlog_path": str(backlog),
        "dispatch_requested": dispatch,
    }
    _append_jsonl(_runtime_path(prime_root, "prime_task_intake.jsonl"), record)
    _write_state(prime_root, record)

    refresh_result: dict[str, Any] | None = None
    if refresh:
        refresh_result = operator_refresh(prime_root)
        record["refresh_status"] = refresh_result.get("status")

    dispatch_result: dict[str, Any] | None = None
    if dispatch:
        script = prime_root / "hermes-wrapper" / "scripts" / "run_parallel_coding_lanes.py"
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(prime_root / "hermes-wrapper"),
            text=True,
            capture_output=True,
            timeout=180,
        )
        dispatch_result = {
            "status": "passed" if completed.returncode == 0 else "failed",
            "returncode": completed.returncode,
            "stdout_preview": completed.stdout[-1000:],
            "stderr_preview": completed.stderr[-1000:],
        }
        record["dispatch_status"] = dispatch_result["status"]
        _append_jsonl(_runtime_path(prime_root, "prime_task_intake.jsonl"), {**record, "event": "dispatch"})
        _write_state(prime_root, record)

    return {
        "ok": True,
        "status": "queued",
        "task": record,
        "refresh": refresh_result,
        "dispatch": dispatch_result,
    }


def list_prime_tasks(root: Path | None = None, limit: int = 10) -> dict[str, Any]:
    prime_root = root or find_prime_root()
    if prime_root is None:
        return {"ok": False, "status": "unavailable", "message": "Hermes Prime root not found."}
    state_path = _runtime_path(prime_root, "prime_task_intake.json")
    if not state_path.exists():
        return {"ok": True, "status": "empty", "tasks": []}
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks") if isinstance(payload.get("tasks"), list) else []
    return {"ok": True, "status": "listed", "tasks": tasks[:limit]}
