"""Bridge from the Hermes CLI to Hermes Prime Operator Brain state."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_FILES = {
    "watchdog": "operator_watchdog.json",
    "proving": "overwatch_proving_ground.json",
    "intelligence": "operator_intelligence.json",
    "lanes": "parallel_coding_lanes.json",
    "kanban": "operator_brain_kanban_sync.json",
    "revenue": "revenue_agent_state.json",
    "prime_intake": "prime_task_intake.json",
}


def _candidate_roots(start: Path | None = None) -> list[Path]:
    roots: list[Path] = []
    env_root = os.environ.get("HERMES_PRIME_ROOT") or os.environ.get("HERMES_OPERATOR_ROOT")
    if env_root:
        roots.append(Path(env_root).expanduser())
    if start is None:
        start = Path.cwd()
    try:
        resolved = start.resolve()
    except OSError:
        resolved = start
    roots.extend([resolved, *resolved.parents])
    roots.extend([Path("P:/Hermes"), Path.home() / "Hermes"])
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).casefold()
        if key not in seen:
            unique.append(root)
            seen.add(key)
    return unique


def find_prime_root(start: Path | None = None) -> Path | None:
    """Return the Hermes umbrella root that contains hermes-wrapper/runtime."""
    for root in _candidate_roots(start):
        runtime = root / "hermes-wrapper" / "runtime"
        if runtime.exists():
            return root
    return None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_operator_brain_state(root: Path | None = None) -> dict[str, Any]:
    """Load current Operator Brain runtime snapshots without mutating state."""
    prime_root = root or find_prime_root()
    if prime_root is None:
        return {
            "available": False,
            "reason": "Hermes Prime root not found. Set HERMES_PRIME_ROOT or run from P:/Hermes.",
        }
    runtime = prime_root / "hermes-wrapper" / "runtime"
    if not runtime.exists():
        return {
            "available": False,
            "root": str(prime_root),
            "reason": f"Operator Brain runtime not found at {runtime}.",
        }
    files: dict[str, Any] = {}
    for key, name in RUNTIME_FILES.items():
        path = runtime / name
        payload = _read_json(path)
        files[key] = {
            "path": str(path),
            "exists": path.exists(),
            "payload": payload if isinstance(payload, dict) else payload,
        }
    return {
        "available": True,
        "root": str(prime_root),
        "runtime": str(runtime),
        "files": files,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _audit_path(root: Path) -> Path:
    return root / "hermes-wrapper" / "runtime" / "operator_cli_actions.jsonl"


def _write_audit(root: Path, action: str, status: str, details: dict[str, Any] | None = None) -> None:
    path = _audit_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": _utc_now(),
        "source": "hermes-cli",
        "action": action,
        "status": status,
        "root": str(root),
        "details": details or {},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def operator_pause(reason: str | None = None, root: Path | None = None) -> dict[str, Any]:
    """Pause future operator cycles by creating the existing pause marker."""
    prime_root = root or find_prime_root()
    if prime_root is None:
        return {"ok": False, "status": "unavailable", "message": "Hermes Prime root not found."}
    marker = prime_root / "hermes-wrapper" / ".pause_operator"
    marker.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": _utc_now(),
        "source": "hermes-cli",
        "reason": reason or "paused from hermes operator pause",
    }
    marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_audit(prime_root, "operator.pause", "paused", {"pause_marker": str(marker), "reason": payload["reason"]})
    return {"ok": True, "status": "paused", "pause_marker": str(marker)}


def operator_resume(root: Path | None = None) -> dict[str, Any]:
    """Resume future operator cycles by removing the pause marker."""
    prime_root = root or find_prime_root()
    if prime_root is None:
        return {"ok": False, "status": "unavailable", "message": "Hermes Prime root not found."}
    marker = prime_root / "hermes-wrapper" / ".pause_operator"
    existed = marker.exists()
    if existed:
        marker.unlink()
    _write_audit(prime_root, "operator.resume", "resumed", {"pause_marker": str(marker), "marker_existed": existed})
    return {"ok": True, "status": "resumed", "pause_marker": str(marker), "marker_existed": existed}


def operator_refresh(root: Path | None = None) -> dict[str, Any]:
    """Refresh Operator Intelligence and the Operator Brain Kanban mirror."""
    prime_root = root or find_prime_root()
    if prime_root is None:
        return {"ok": False, "status": "unavailable", "message": "Hermes Prime root not found."}

    wrapper = prime_root / "hermes-wrapper"
    scripts = [
        wrapper / "scripts" / "update_operator_intelligence.py",
        wrapper / "scripts" / "sync_operator_brain_kanban.py",
    ]
    results: list[dict[str, Any]] = []
    for script in scripts:
        if not script.exists():
            results.append({"script": str(script), "status": "missing", "returncode": None})
            continue
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(wrapper),
            text=True,
            capture_output=True,
            timeout=120,
        )
        results.append(
            {
                "script": str(script),
                "status": "passed" if completed.returncode == 0 else "failed",
                "returncode": completed.returncode,
                "stdout_preview": completed.stdout[-1000:],
                "stderr_preview": completed.stderr[-1000:],
            }
        )
        if completed.returncode != 0:
            _write_audit(prime_root, "operator.refresh", "failed", {"results": results})
            return {"ok": False, "status": "failed", "results": results}

    _write_audit(prime_root, "operator.refresh", "refreshed", {"results": results})
    return {"ok": True, "status": "refreshed", "results": results}


def operator_command(args: Any) -> int:
    """Dispatch `hermes operator ...` actions."""
    action = getattr(args, "operator_action", None) or "status"
    if action == "status":
        print(format_operator_brain_summary())
        return 0
    if action == "approvals":
        from hermes_cli.prime_approvals import format_approvals, list_approvals

        print(format_approvals(list_approvals(limit=getattr(args, "limit", 25))))
        return 0
    if action == "pause":
        result = operator_pause(reason=getattr(args, "reason", None))
    elif action == "resume":
        result = operator_resume()
    elif action == "refresh":
        result = operator_refresh()
    elif action == "task":
        from hermes_cli.prime_intake import create_prime_task, list_prime_tasks

        task_action = getattr(args, "operator_task_action", None)
        if task_action == "create":
            result = create_prime_task(
                workspace_name=getattr(args, "workspace"),
                summary=getattr(args, "summary"),
                reason=getattr(args, "reason", None),
                task_type=getattr(args, "task_type", "feature"),
                refresh=getattr(args, "refresh", True),
                dispatch=getattr(args, "dispatch", False),
            )
        elif task_action == "list":
            result = list_prime_tasks(limit=getattr(args, "limit", 10))
        else:
            print("Usage: hermes operator task [create|list]", file=sys.stderr)
            return 2
    else:
        print(f"Unknown operator action: {action}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    if result.get("ok"):
        if action in {"pause", "resume", "refresh"}:
            print()
            print(format_operator_brain_summary())
        return 0
    return 1


def _payload(state: dict[str, Any], key: str) -> dict[str, Any]:
    item = state.get("files", {}).get(key, {})
    payload = item.get("payload")
    return payload if isinstance(payload, dict) else {}


def _count_running_lanes(lanes: dict[str, Any]) -> int:
    values: list[Any] = []
    for key in ("lanes", "children", "workers", "active_lanes"):
        item = lanes.get(key)
        if isinstance(item, list):
            values.extend(item)
        elif isinstance(item, dict):
            values.extend(item.values())
    return sum(
        1
        for lane in values
        if isinstance(lane, dict)
        and str(lane.get("status") or lane.get("state") or "").lower()
        in {"running", "in_progress", "claimed", "active"}
    )


def build_operator_brain_summary(state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a compact structured summary suitable for CLI/chat display."""
    state = state or load_operator_brain_state()
    if not state.get("available"):
        return {"available": False, "reason": state.get("reason", "Operator Brain state unavailable.")}

    watchdog = _payload(state, "watchdog")
    proving = _payload(state, "proving")
    intelligence = _payload(state, "intelligence")
    lanes = _payload(state, "lanes")
    kanban = _payload(state, "kanban")
    prime_intake = _payload(state, "prime_intake")
    council = intelligence.get("council") if isinstance(intelligence.get("council"), dict) else {}
    ratings = council.get("ratings") if isinstance(council.get("ratings"), dict) else {}
    latest_pr = proving.get("latest_pull_request") if isinstance(proving.get("latest_pull_request"), dict) else {}
    latest_validation = proving.get("latest_validation") if isinstance(proving.get("latest_validation"), dict) else {}
    latest_deployment = proving.get("latest_deployment") if isinstance(proving.get("latest_deployment"), dict) else {}
    contract = proving.get("failure_improvement_contract") if isinstance(proving.get("failure_improvement_contract"), dict) else {}

    return {
        "available": True,
        "root": state.get("root"),
        "runtime": state.get("runtime"),
        "timestamp": intelligence.get("timestamp") or proving.get("timestamp") or watchdog.get("timestamp"),
        "operator_status": watchdog.get("status") or "unknown",
        "operator_pids": watchdog.get("pids") or [],
        "pause_file": watchdog.get("pause_file"),
        "overwatch": {
            "successful_attempts": proving.get("successful_attempts"),
            "target_attempts": proving.get("target_attempts") or proving.get("target_successes") or 10,
            "ready_for_more_repos": bool(proving.get("ready_for_more_repos")),
            "current_phase": proving.get("current_phase"),
            "pending_total": proving.get("pending_total"),
            "latest_pr": latest_pr,
            "latest_validation_status": latest_validation.get("status"),
            "latest_deployment_status": latest_deployment.get("status") or latest_deployment.get("conclusion"),
        },
        "council": {
            "status": council.get("status"),
            "consensus": council.get("consensus"),
            "roles": council.get("roles") or [],
        },
        "ratings": ratings,
        "lanes": {
            "running": _count_running_lanes(lanes),
            "timestamp": lanes.get("timestamp"),
        },
        "contracts": {
            "pending": contract.get("pending_count"),
            "satisfied": contract.get("satisfied_count"),
            "required": contract.get("required_count"),
        },
        "kanban": {
            "timestamp": kanban.get("timestamp"),
            "board": kanban.get("board"),
            "task_count": kanban.get("task_count"),
            "status_counts": kanban.get("status_counts"),
        },
        "prime_intake": {
            "timestamp": prime_intake.get("timestamp"),
            "task_count": prime_intake.get("task_count"),
            "latest": prime_intake.get("latest") if isinstance(prime_intake.get("latest"), dict) else {},
        },
    }


def format_operator_brain_summary(summary: dict[str, Any] | None = None) -> str:
    """Format Operator Brain status for terminal output and slash commands."""
    summary = summary or build_operator_brain_summary()
    if not summary.get("available"):
        return f"Operator Brain: unavailable\nReason: {summary.get('reason', 'unknown')}"

    overwatch = summary.get("overwatch", {})
    council = summary.get("council", {})
    lanes = summary.get("lanes", {})
    contracts = summary.get("contracts", {})
    kanban = summary.get("kanban", {})
    prime_intake = summary.get("prime_intake", {})
    ratings = summary.get("ratings", {})
    lines = [
        "Operator Brain",
        f"  Root: {summary.get('root')}",
        f"  Snapshot: {summary.get('timestamp') or 'unknown'}",
        f"  Operator: {summary.get('operator_status')} pids={summary.get('operator_pids') or []}",
        (
            "  Overwatch: "
            f"{overwatch.get('successful_attempts')}/{overwatch.get('target_attempts')} "
            f"phase={overwatch.get('current_phase') or 'unknown'} "
            f"pending={overwatch.get('pending_total') if overwatch.get('pending_total') is not None else 'unknown'} "
            f"ready_for_more_repos={overwatch.get('ready_for_more_repos')}"
        ),
        (
            "  Latest PR: "
            f"{overwatch.get('latest_pr', {}).get('number') or 'none'} "
            f"{overwatch.get('latest_pr', {}).get('status') or ''}".rstrip()
        ),
        (
            "  Validation/deploy: "
            f"{overwatch.get('latest_validation_status') or 'unknown'} / "
            f"{overwatch.get('latest_deployment_status') or 'unknown'}"
        ),
        (
            "  Improvement contracts: "
            f"pending={contracts.get('pending') if contracts.get('pending') is not None else 'unknown'} "
            f"satisfied={contracts.get('satisfied') if contracts.get('satisfied') is not None else 'unknown'}"
        ),
        f"  Lanes running: {lanes.get('running')}",
        f"  Council: {council.get('consensus') or council.get('status') or 'unknown'}",
        f"  Kanban: board={kanban.get('board') or 'unknown'} tasks={kanban.get('task_count') if kanban.get('task_count') is not None else 'unknown'}",
    ]
    if prime_intake.get("task_count"):
        latest_task = prime_intake.get("latest") or {}
        lines.append(
            "  Prime intake: "
            f"{prime_intake.get('task_count')} queued, latest={latest_task.get('workspace', 'unknown')} "
            f"{latest_task.get('summary', '')}".rstrip()
        )
    overall = ratings.get("overall_system") if isinstance(ratings.get("overall_system"), dict) else {}
    if overall:
        lines.append(
            f"  Overall rating: {overall.get('score', 'unknown')}/10 {overall.get('title', '')}".rstrip()
        )
    return "\n".join(lines)


def build_chat_context(max_chars: int = 2400) -> str:
    """Return concise Operator Brain context for injection into chat sessions."""
    text = format_operator_brain_summary()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."
