"""Local workspace bridge for Leonor launcher invocations."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


DOC_CANDIDATES = ("PRD.md", "HERMES_TASKS.md", "ROADMAP.md", "README.md")
DOC_PREVIEW_CHARS = 4000


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _workspace_from_env() -> tuple[Path, str]:
    caller = os.environ.get("LEONOR_CALLER_CWD", "").strip()
    if caller:
        return Path(caller).expanduser(), "LEONOR_CALLER_CWD"
    return Path.cwd(), "cwd"


def _audit_path() -> Path:
    return get_hermes_home() / "runtime" / "leonor_workspace_actions.jsonl"


def _write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_audit(payload: dict[str, Any]) -> None:
    _write_jsonl(_audit_path(), {"timestamp": _utc_now(), **payload})


def _workspace_runtime_path(workspace: Path, filename: str) -> Path:
    return workspace / ".leonor" / "runtime" / filename


def _global_build_requests_path() -> Path:
    return get_hermes_home() / "runtime" / "leonor_workspace_build_requests.jsonl"


def _doc_summaries(workspace: Path, docs: list[str]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for name in docs:
        path = workspace / name
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        summaries.append(
            {
                "name": name,
                "path": str(path),
                "bytes": path.stat().st_size,
                "preview": text[:DOC_PREVIEW_CHARS],
                "truncated": len(text) > DOC_PREVIEW_CHARS,
            }
        )
    return summaries


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


def build_workspace_plan(request: str | None = None) -> dict[str, Any]:
    inspected = inspect_workspace()
    workspace = Path(inspected["workspace"])
    documents = _doc_summaries(workspace, inspected["docs"]) if inspected["editable"] else []
    default_request = "Analyze local project docs and create the smallest safe implementation lane."
    return {
        "timestamp": _utc_now(),
        "schema": "leonor_workspace_plan.v1",
        "status": "ready_for_local_lane" if inspected["editable"] else "blocked",
        "request": (request or default_request).strip() or default_request,
        "workspace": inspected["workspace"],
        "source": inspected["source"],
        "error": inspected["error"],
        "documents": documents,
        "git": inspected["git"],
        "safety": {
            "allowed_root": inspected["workspace"],
            "write_scope": "workspace_only",
            "external_workspace_required": False,
            "secrets_policy": "do_not_print_or_export_secrets",
        },
        "next_actions": [
            "Create an isolated local lane for this workspace.",
            "Implement the smallest testable slice from the detected docs.",
            "Run discovered validation commands and record evidence.",
            "Append follow-up tasks only after verification.",
        ],
    }


def workspace_plan(args: Any) -> int:
    payload = build_workspace_plan(getattr(args, "request", None))
    should_audit = getattr(args, "audit", True)
    if should_audit:
        _write_audit({"action": "workspace.plan", **payload})

    if getattr(args, "json", False):
        print(json.dumps(payload, sort_keys=True))
    else:
        print("Leonor Workspace Plan")
        print(f"workspace: {payload['workspace']}")
        print(f"status: {payload['status']}")
        print(f"request: {payload['request']}")
        print(f"docs: {', '.join(doc['name'] for doc in payload['documents']) if payload['documents'] else '(none)'}")
        if payload["error"]:
            print(f"error: {payload['error']}")
    return 0 if payload["status"] == "ready_for_local_lane" else 2


def workspace_build(args: Any) -> int:
    plan = build_workspace_plan(getattr(args, "request", None))
    if plan["status"] != "ready_for_local_lane":
        payload = {**plan, "status": "blocked", "action": "workspace.build"}
        if getattr(args, "json", False):
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f"Leonor workspace build blocked: {plan['error']}")
        return 2

    workspace = Path(plan["workspace"])
    payload = {
        "timestamp": _utc_now(),
        "schema": "leonor_workspace_build_request.v1",
        "action": "workspace.build",
        "status": "queued",
        "request": plan["request"],
        "workspace": plan["workspace"],
        "source": plan["source"],
        "documents": [doc["name"] for doc in plan["documents"]],
        "safety": plan["safety"],
        "plan": plan,
    }
    _write_jsonl(_workspace_runtime_path(workspace, "build_requests.jsonl"), payload)
    _write_jsonl(_global_build_requests_path(), payload)
    if getattr(args, "audit", True):
        _write_audit(payload)

    if getattr(args, "json", False):
        print(json.dumps(payload, sort_keys=True))
    else:
        print("Leonor workspace build queued")
        print(f"workspace: {payload['workspace']}")
        print(f"request: {payload['request']}")
        print(f"local log: {_workspace_runtime_path(workspace, 'build_requests.jsonl')}")
    return 0


def workspace_dispatch(args: Any) -> int:
    sub = getattr(args, "workspace_command", None) or "inspect"
    if sub == "inspect":
        return workspace_inspect(args)
    if sub == "plan":
        return workspace_plan(args)
    if sub == "build":
        return workspace_build(args)
    print("usage: hermes workspace inspect|plan|build [--json] [--no-audit]")
    return 1
