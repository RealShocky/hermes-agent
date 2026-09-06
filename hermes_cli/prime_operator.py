"""Leonor operator bridge for the repo-local Hermes CLI.

This module intentionally keeps a thin boundary around the wrapper runtime.
The core CLI can read and control the bounded operator state without importing
wrapper code or taking a dependency on the wrapper package layout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(os.environ.get("LEONOR_ROOT", "P:/Hermes"))


def _root() -> Path:
    return Path(os.environ.get("LEONOR_ROOT", str(DEFAULT_ROOT))).expanduser()


def _wrapper_runtime() -> Path:
    return _root() / "hermes-wrapper" / "runtime"


def _pause_marker() -> Path:
    return _root() / "hermes-wrapper" / ".pause_operator"


def _audit_path() -> Path:
    return _wrapper_runtime() / "operator_cli_actions.jsonl"


def _json_path(name: str) -> Path:
    return _wrapper_runtime() / name


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001 - status should degrade cleanly
        return {"error": f"{type(exc).__name__}: {exc}"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_audit(action: str, **fields: Any) -> None:
    runtime = _wrapper_runtime()
    runtime.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": _utc_now(),
        "action": action,
        "source": "leonor-cli",
        **fields,
    }
    with _audit_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _print_kv(label: str, value: Any) -> None:
    print(f"{label}: {value}")


def print_brain_status(*, concise: bool = False) -> int:
    """Print a bounded Operator Brain snapshot from wrapper runtime files."""
    root = _root()
    proving = _read_json(_json_path("overwatch_proving_ground.json"))
    watchdog = _read_json(_json_path("operator_watchdog.json"))
    brain = _read_json(_json_path("operator_brain.json"))
    paused = _pause_marker().exists()

    if not concise:
        print("Leonor Operator Brain")
        _print_kv("root", root)
    _print_kv("paused", "yes" if paused else "no")

    if proving:
        _print_kv("workspace", proving.get("workspace", "(unknown)"))
        successes = proving.get("successful_attempts", 0)
        target = proving.get("target_attempts", 10)
        observed = proving.get("attempts_observed", 0)
        _print_kv("proofrail", f"{successes}/{target} successful ({observed} observed)")
        _print_kv("ready_for_more_repos", proving.get("ready_for_more_repos", False))
        latest_validation = proving.get("latest_validation") or {}
        if latest_validation:
            _print_kv("latest_validation", latest_validation.get("status", "(unknown)"))
    else:
        _print_kv("proofrail", "missing runtime snapshot")

    if watchdog:
        watchdog_status = watchdog.get("status", "(unknown)")
        if paused and watchdog_status == "running":
            watchdog_status = "paused (snapshot was running)"
        _print_kv("watchdog_status", watchdog_status)
        if watchdog.get("timestamp"):
            _print_kv("watchdog_timestamp", watchdog.get("timestamp"))

    if brain:
        if brain.get("timestamp"):
            _print_kv("brain_timestamp", brain.get("timestamp"))
        if brain.get("status"):
            _print_kv("brain_status", brain.get("status"))

    return 0


def operator_status(_args: Any) -> int:
    return print_brain_status(concise=False)


def operator_dispatch(args: Any) -> int:
    sub = getattr(args, "operator_command", None) or "status"
    if sub == "status":
        return operator_status(args)
    if sub == "pause":
        return operator_pause(args)
    if sub == "resume":
        return operator_resume(args)
    if sub == "refresh":
        return operator_refresh(args)
    print("usage: hermes operator <status|pause|resume|refresh>", file=sys.stderr)
    return 1


def operator_pause(args: Any) -> int:
    reason = getattr(args, "reason", None) or "paused from leonor operator pause"
    marker = _pause_marker()
    marker.write_text(f"{reason}\n", encoding="utf-8")
    _append_audit("pause", reason=reason, marker=str(marker))
    print(f"paused: {marker}")
    return 0


def operator_resume(args: Any) -> int:
    marker = _pause_marker()
    existed = marker.exists()
    if existed:
        marker.unlink()
    _append_audit("resume", removed=existed, marker=str(marker))
    print("resumed" if existed else "already unpaused")
    return 0


def operator_refresh(_args: Any) -> int:
    script = _root() / "hermes-wrapper" / "scripts" / "sync_operator_brain_kanban.py"
    if not script.exists():
        print(f"refresh script missing: {script}", file=sys.stderr)
        return 1
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_root() / "hermes-wrapper"),
        text=True,
        capture_output=True,
        timeout=60,
    )
    _append_audit("refresh", exit_code=result.returncode)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode
