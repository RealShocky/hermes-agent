"""Local workspace bridge for Leonor launcher invocations."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


DOC_CANDIDATES = ("PRD.md", "HERMES_TASKS.md", "ROADMAP.md", "README.md")
DOC_PREVIEW_CHARS = 4000
EXECUTION_PROMPT_MAX_CHARS = 3000
EXECUTION_DOC_PREVIEW_CHARS = 700
EXECUTION_DEFAULT_TOOLSETS = "file,terminal"
EXECUTION_DEFAULT_REASONING = "minimal"
EXECUTION_DEFAULT_MAX_TOKENS = "2048"
AGENT_FAILURE_MARKERS = (
    "api call failed",
    "error code:",
    "authenticationerror",
    "connection error",
    "exceeds the maximum allowed length",
    "http 401",
    "unauthorized",
)
EXECUTOR_ENV_NAMES = (
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "HERMES_DGX_API_KEY",
    "HERMES_QWEN_API_KEY",
    "HERMES_AUTONOMOUS_API_KEY",
    "OPENAI_BASE_URL",
    "HERMES_AUTONOMOUS_BASE_URL",
    "HERMES_AUTONOMOUS_MODEL",
    "HERMES_AUTONOMOUS_PROVIDER",
)


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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _write_audit(payload: dict[str, Any]) -> None:
    _write_jsonl(_audit_path(), {"timestamp": _utc_now(), **payload})


def _workspace_runtime_path(workspace: Path, filename: str) -> Path:
    return workspace / ".leonor" / "runtime" / filename


def _global_build_requests_path() -> Path:
    return get_hermes_home() / "runtime" / "leonor_workspace_build_requests.jsonl"


def _global_build_runs_path() -> Path:
    return get_hermes_home() / "runtime" / "leonor_workspace_build_runs.jsonl"


def _request_id(payload: dict[str, Any]) -> str:
    existing = str(payload.get("request_id") or "").strip()
    if existing:
        return existing
    seed = json.dumps(
        {
            "timestamp": payload.get("timestamp"),
            "workspace": payload.get("workspace"),
            "request": payload.get("request"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _resolve_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _inside_or_same(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return path == root


def _completed_request_ids(workspace: Path) -> set[str]:
    completed: set[str] = set()
    for path in (_workspace_runtime_path(workspace, "build_runs.jsonl"), _global_build_runs_path()):
        for row in _read_jsonl(path):
            if row.get("status") == "completed":
                request_id = str(row.get("request_id") or "").strip()
                if request_id:
                    completed.add(request_id)
    return completed


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


def _execution_prompt(request: dict[str, Any]) -> str:
    plan = request.get("plan") if isinstance(request.get("plan"), dict) else {}
    documents = plan.get("documents") if isinstance(plan.get("documents"), list) else []
    doc_blocks = []
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        doc_blocks.append(
            f"## {doc.get('name', 'document')}\n{str(doc.get('preview') or '')[:EXECUTION_DOC_PREVIEW_CHARS]}"
        )
    docs_text = "\n\n".join(doc_blocks) if doc_blocks else "(no docs captured)"
    prompt = (
        "LEONOR WORKSPACE EXECUTION\n"
        "You are Leonor, the local bounded autonomous coding operator.\n\n"
        f"Workspace: {request.get('workspace')}\n"
        f"Request: {request.get('request')}\n\n"
        "Rules: inspect first; write only inside workspace; preserve unrelated changes; "
        "implement the smallest complete testable slice; run discovered validation; do not print secrets.\n\n"
        f"Captured docs:\n{docs_text}\n"
    )
    if len(prompt) <= EXECUTION_PROMPT_MAX_CHARS:
        return prompt
    return prompt[: EXECUTION_PROMPT_MAX_CHARS - 80] + "\n...[execution prompt truncated]\n"


def _executor_setting(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _executor_command(prompt: str) -> list[str]:
    command = [sys.executable, "-m", "hermes_cli.main", "--cli", "--ignore-rules"]
    toolsets = _executor_setting("LEONOR_WORKSPACE_EXECUTOR_TOOLSETS", EXECUTION_DEFAULT_TOOLSETS)
    reasoning = _executor_setting("LEONOR_WORKSPACE_EXECUTOR_REASONING", EXECUTION_DEFAULT_REASONING)
    if toolsets:
        command.extend(["--toolsets", toolsets])
    if reasoning:
        command.extend(["--reasoning", reasoning])
    command.extend(["-z", prompt])
    return command


def _read_env_file_value(path: Path, name: str) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None
    prefix = f"{name}="
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        value = stripped[len(prefix) :].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        return value
    return None


def _executor_root() -> Path | None:
    configured = os.environ.get("LEONOR_ROOT") or os.environ.get("HERMES_ROOT")
    if configured:
        return _resolve_path(configured)
    core_root = Path(__file__).resolve().parents[1]
    for candidate in (core_root.parent, core_root.parent.parent):
        if (candidate / ".env").is_file() or (candidate / "hermes-wrapper" / ".env").is_file():
            return candidate
    return None


def _seed_executor_env(env: dict[str, str]) -> None:
    root = _executor_root()
    if root is None:
        return
    env_files = (root / ".env", root / "hermes-wrapper" / ".env")
    for name in EXECUTOR_ENV_NAMES:
        if env.get(name):
            continue
        for env_file in env_files:
            value = _read_env_file_value(env_file, name)
            if value:
                env[name] = value
                break
    if not env.get("HERMES_QWEN_API_KEY"):
        env["HERMES_QWEN_API_KEY"] = env.get("HERMES_DGX_API_KEY", "") or env.get("OPENAI_API_KEY", "")


def _run_build_request(request: dict[str, Any], timeout: int) -> dict[str, Any]:
    workspace = _resolve_path(str(request.get("workspace") or ""))
    safety = request.get("safety") if isinstance(request.get("safety"), dict) else {}
    allowed_root = _resolve_path(str(safety.get("allowed_root") or workspace))
    request_id = _request_id(request)
    base_run = {
        "timestamp": _utc_now(),
        "schema": "leonor_workspace_build_run.v1",
        "request_id": request_id,
        "workspace": str(workspace),
        "request": str(request.get("request") or ""),
    }
    if not workspace.is_dir():
        return {**base_run, "status": "blocked", "reason": "workspace_not_found", "exit_code": None}
    if not _inside_or_same(workspace, allowed_root):
        return {**base_run, "status": "blocked", "reason": "workspace_outside_allowed_root", "exit_code": None}

    prompt = _execution_prompt({**request, "request_id": request_id, "workspace": str(workspace)})
    env = os.environ.copy()
    _seed_executor_env(env)
    env["LEONOR_TARGET_WORKSPACE"] = str(workspace)
    env["LEONOR_WORKSPACE_REQUEST"] = str(request.get("request") or "")
    env["LEONOR_WORKSPACE_REQUEST_ID"] = request_id
    env["HERMES_DISABLE_STREAMING"] = "1"
    env["LEONOR_WORKSPACE_EXECUTION"] = "1"
    env.setdefault(
        "HERMES_MAX_TOKENS",
        _executor_setting("LEONOR_WORKSPACE_EXECUTOR_MAX_TOKENS", EXECUTION_DEFAULT_MAX_TOKENS),
    )
    command = _executor_command(prompt)
    try:
        completed = subprocess.run(
            command,
            cwd=str(workspace),
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            **base_run,
            "status": "failed",
            "reason": "executor_timeout",
            "exit_code": None,
            "stdout_tail": str(exc.stdout or "")[-8000:],
            "stderr_tail": str(exc.stderr or "")[-4000:],
            "command": _executor_command("<prompt>"),
        }
    except OSError as exc:
        return {
            **base_run,
            "status": "failed",
            "reason": "executor_launch_error",
            "exit_code": None,
            "stdout_tail": "",
            "stderr_tail": str(exc)[-4000:],
            "command": _executor_command("<prompt>"),
        }
    stdout = (completed.stdout or "")[-8000:]
    stderr = (completed.stderr or "")[-4000:]
    combined_output = f"{stdout}\n{stderr}".lower()
    agent_reported_failure = any(marker in combined_output for marker in AGENT_FAILURE_MARKERS)
    status = "completed" if completed.returncode == 0 and not agent_reported_failure else "failed"
    reason = "command_completed"
    if agent_reported_failure:
        reason = "agent_reported_failure"
    elif status == "failed":
        reason = "command_failed"
    return {
        **base_run,
        "status": status,
        "reason": reason,
        "exit_code": completed.returncode,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
        "command": _executor_command("<prompt>"),
    }


def execute_queued_builds(*, once: bool = False, timeout: int = 900) -> dict[str, Any]:
    inspected = inspect_workspace()
    workspace = Path(inspected["workspace"])
    if not inspected["editable"]:
        return {
            "timestamp": _utc_now(),
            "schema": "leonor_workspace_execute.v1",
            "status": "blocked",
            "reason": inspected["error"],
            "processed": 0,
            "workspace": inspected["workspace"],
            "runs": [],
        }
    request_path = _workspace_runtime_path(workspace, "build_requests.jsonl")
    requests = _read_jsonl(request_path)
    completed = _completed_request_ids(workspace)
    runs = []
    for request in requests:
        request_id = _request_id(request)
        if request.get("status") != "queued" or request_id in completed:
            continue
        run = _run_build_request({**request, "request_id": request_id}, timeout)
        _write_jsonl(_workspace_runtime_path(workspace, "build_runs.jsonl"), run)
        _write_jsonl(_global_build_runs_path(), run)
        runs.append(run)
        if once:
            break
    statuses = {run["status"] for run in runs}
    if not runs:
        status = "idle"
    elif statuses == {"completed"}:
        status = "completed"
    elif "blocked" in statuses:
        status = "blocked"
    else:
        status = "failed"
    return {
        "timestamp": _utc_now(),
        "schema": "leonor_workspace_execute.v1",
        "status": status,
        "processed": len(runs),
        "workspace": inspected["workspace"],
        "runs": runs,
    }


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
    request = getattr(args, "request", None) or getattr(args, "request_text", None)
    payload = build_workspace_plan(request)
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
    request = getattr(args, "request", None) or getattr(args, "request_text", None)
    plan = build_workspace_plan(request)
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
        "request_id": _request_id({"timestamp": plan["timestamp"], "workspace": plan["workspace"], "request": plan["request"]}),
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


def workspace_execute(args: Any) -> int:
    payload = execute_queued_builds(
        once=bool(getattr(args, "once", False)),
        timeout=int(getattr(args, "timeout", 900) or 900),
    )
    if getattr(args, "audit", True):
        _write_audit({"action": "workspace.execute", **payload})

    if getattr(args, "json", False):
        print(json.dumps(payload, sort_keys=True))
    else:
        print("Leonor workspace execute")
        print(f"workspace: {payload['workspace']}")
        print(f"status: {payload['status']}")
        print(f"processed: {payload['processed']}")
        for run in payload["runs"]:
            print(f"- {run['request_id']}: {run['status']} ({run.get('reason')})")
    if payload["status"] in {"completed", "idle"}:
        return 0
    if payload["status"] == "blocked":
        return 3
    return 1


def workspace_dispatch(args: Any) -> int:
    sub = getattr(args, "workspace_command", None) or "inspect"
    if sub == "inspect":
        return workspace_inspect(args)
    if sub == "plan":
        return workspace_plan(args)
    if sub == "build":
        return workspace_build(args)
    if sub == "execute":
        return workspace_execute(args)
    print("usage: hermes workspace inspect|plan|build|execute [--json] [--no-audit]")
    return 1
