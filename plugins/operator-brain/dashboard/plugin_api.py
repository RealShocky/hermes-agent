"""Read-only Operator Brain dashboard API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter

router = APIRouter()


def _wrapper_root() -> Path:
    return Path(os.environ.get("HERMES_OPERATOR_ROOT", "P:/Hermes/hermes-wrapper"))


def _hermes_root() -> Path:
    return Path(os.environ.get("HERMES_ROOT", str(_wrapper_root().parent)))


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _latest(pattern: str, limit: int = 1) -> list[dict[str, Any]]:
    log_dir = _wrapper_root() / "logs"
    paths = sorted(log_dir.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]
    return [{"file": path.name, **_json(path)} for path in paths]


def _workspaces() -> list[dict[str, Any]]:
    registry = _wrapper_root() / "workspace-registry" / "workspaces.yaml"
    try:
        items = (yaml.safe_load(registry.read_text(encoding="utf-8")) or {}).get("workspaces", [])
    except (OSError, ValueError):
        return []
    cycles = {item.get("workspace"): item for item in _latest("*_cycle.json", 40)}
    result = []
    for item in items:
        cycle = cycles.get(item.get("name"), {})
        result.append(
            {
                "name": item.get("name"),
                "type": item.get("repo_type"),
                "risk": item.get("risk"),
                "path": item.get("path"),
                "cycle_status": cycle.get("status", "unknown"),
                "cycle_timestamp": cycle.get("timestamp"),
            }
        )
    return result


def _skills() -> list[dict[str, Any]]:
    root = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "skills"
    result = []
    if not root.exists():
        return result
    for path in root.rglob("SKILL.md"):
        result.append({"name": path.parent.name, "path": str(path)})
    return result[:100]


def _machine_ops() -> dict[str, Any]:
    root = Path(os.environ.get("HERMES_MACHINE_OPS_ROOT", str(_hermes_root() / "runtime" / "machine-ops")))
    requests: list[dict[str, Any]] = []
    for folder in ("pending", "approved", "executed", "failed"):
        request_dir = root / folder
        if not request_dir.exists():
            continue
        for path in request_dir.glob("*.json"):
            payload = _json(path)
            if not payload:
                continue
            payload = {
                "file": path.name,
                "folder": folder,
                "id": payload.get("id"),
                "created_at": payload.get("created_at"),
                "status": payload.get("status", folder),
                "action": payload.get("action"),
                "risk": payload.get("risk"),
                "approval_required": payload.get("approval_required"),
                "approved_by": payload.get("approved_by"),
                "approved_at": payload.get("approved_at"),
                "executed_at": payload.get("executed_at"),
                "reason": payload.get("reason"),
                "expected_impact": payload.get("expected_impact"),
                "rollback": payload.get("rollback"),
                "execution_status": (payload.get("execution") or {}).get("status"),
                "execution_exit_code": (payload.get("execution") or {}).get("exit_code"),
                "dry_run_status": (payload.get("last_dry_run") or {}).get("status"),
            }
            requests.append(payload)
    requests.sort(key=lambda item: str(item.get("created_at") or item.get("id") or ""), reverse=True)
    by_status: dict[str, int] = {}
    by_action: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    for item in requests:
        status = str(item.get("status") or "unknown")
        action = str(item.get("action") or "unknown")
        risk = str(item.get("risk") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        by_action[action] = by_action.get(action, 0) + 1
        by_risk[risk] = by_risk.get(risk, 0) + 1
    return {
        "root": str(root),
        "total": len(requests),
        "by_status": by_status,
        "by_action": by_action,
        "by_risk": by_risk,
        "latest_requests": requests[:20],
    }


@router.get("/snapshot")
async def snapshot():
    ledger = _json(_wrapper_root() / "runtime" / "planner_hypothesis_ledger.json")
    planner = _latest("*_planner_round.json", 1)
    coding = _latest("*_coding_round.json", 8)
    tasks = _latest("*_task.json", 30)
    reconciles = _latest("*_pr_reconcile.json", 5)
    brain_state = planner[0].get("brain_state", {}) if planner else {}
    active = [item for item in coding if item.get("status") not in {"passed", "idle"}][:1]
    proving_ground = _json(_wrapper_root() / "runtime" / "overwatch_proving_ground.json")
    workspace_cleanup = _json(_wrapper_root() / "runtime" / "workspace_cleanup.json")
    branch_lifecycle = _json(_wrapper_root() / "runtime" / "branch_lifecycle.json")
    native_tool_lifecycle = _json(_wrapper_root() / "runtime" / "native_tool_lifecycle.json")
    expansion_readiness = _json(_wrapper_root() / "runtime" / "expansion_readiness.json")
    machine_ops = _machine_ops()
    return {
        "operator": {
            "paused": (_wrapper_root() / ".pause_operator").exists(),
            "root": str(_wrapper_root()),
            "active_task": active[0].get("task") if active else None,
        },
        "agents": [
            {"name": "Operator", "role": "orchestrator", "status": "paused" if (_wrapper_root() / ".pause_operator").exists() else "running"},
            {"name": "Scout", "role": "planner", "status": "ready"},
            {"name": "Critic", "role": "reviewer", "status": "ready"},
            {"name": "Coding Worker", "role": "worker", "status": "running" if active else "ready"},
            {"name": "PR Reconciler", "role": "release", "status": "ready"},
        ],
        "brain_state": brain_state,
        "hypotheses": ledger.get("entries", [])[:100],
        "tasks": tasks,
        "coding_rounds": coding,
        "pull_requests": reconciles,
        "workspaces": _workspaces(),
        "skills": _skills(),
        "proving_ground": proving_ground,
        "workspace_cleanup": workspace_cleanup,
        "branch_lifecycle": branch_lifecycle,
        "native_tool_lifecycle": native_tool_lifecycle,
        "expansion_readiness": expansion_readiness,
        "machine_ops": machine_ops,
    }
