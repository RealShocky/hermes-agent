"""Local workspace bridge for Leonor launcher invocations."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


DOC_CANDIDATES = ("PRD.md", "HERMES_TASKS.md", "ROADMAP.md", "README.md")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _workspace_from_env() -> tuple[Path, str]:
    caller = os.environ.get("LEONOR_CALLER_CWD", "").strip()
    if caller:
        return Path(caller).expanduser(), "LEONOR_CALLER_CWD"
    return Path.cwd(), "cwd"


def _audit_path() -> Path:
    return get_hermes_home() / "runtime" / "leonor_workspace_actions.jsonl"


def _write_audit(payload: dict[str, Any]) -> None:
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": _utc_now(), **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def inspect_workspace() -> dict[str, Any]:
    workspace, source = _workspace_from_env()
    workspace = workspace.resolve()
    exists = workspace.exists() and workspace.is_dir()
    docs = [
        name
        for name in DOC_CANDIDATES
        if exists and (workspace / name).is_file()
    ]
    return {
        "workspace": str(workspace),
        "source": source,
        "editable": exists,
        "error": None if exists else "workspace_not_found",
        "docs": docs,
        "git": {"present": exists and (workspace / ".git").exists()},
    }


def workspace_inspect(args: Any) -> int:
    payload = inspect_workspace()
    should_audit = getattr(args, "audit", True)
    if should_audit:
        _write_audit({"action": "workspace.inspect", **payload})

    if getattr(args, "json", False):
        print(json.dumps(payload, sort_keys=True))
    else:
        print("Leonor Workspace")
        print(f"workspace: {payload['workspace']}")
        print(f"source: {payload['source']}")
        print(f"editable: {payload['editable']}")
        print(f"docs: {', '.join(payload['docs']) if payload['docs'] else '(none)'}")
        print(f"git: {'yes' if payload['git']['present'] else 'no'}")
        if payload["error"]:
            print(f"error: {payload['error']}")
    return 0 if payload["editable"] else 2


def workspace_dispatch(args: Any) -> int:
    sub = getattr(args, "workspace_command", None) or "inspect"
    if sub == "inspect":
        return workspace_inspect(args)
    print("usage: hermes workspace inspect [--json] [--no-audit]")
    return 1
