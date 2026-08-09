"""Prime-wide approval queue aggregation for the Hermes CLI bridge."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from hermes_cli.operator_brain import find_prime_root


APPROVAL_FILES = (
    "approval_queue.json",
    "prime_approval_queue.json",
    "operator_approval_queue.json",
    "revenue_approval_queue.json",
    "machine_approval_queue.json",
    "revenue_agent_state.json",
)

APPROVAL_TERMS = re.compile(
    r"\b(approval request|pending approval|needs approval|requires approval|human approval)\b",
    re.IGNORECASE,
)


def _runtime(root: Path) -> Path:
    return root / "hermes-wrapper" / "runtime"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _queue_items_from_payload(payload: Any, source: str) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = []
        for key in ("approvals", "approval_requests", "queue", "items", "requests"):
            value = payload.get(key)
            if isinstance(value, list):
                raw_items.extend(value)
        if not raw_items and payload.get("approval_required"):
            raw_items = [payload]
    else:
        return []

    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        if item.get("human_approval_required") is False or item.get("approval_required") is False:
            continue
        status = str(item.get("status") or item.get("approval_status") or "pending").lower()
        if status in {"approved", "rejected", "denied", "done", "completed", "closed", "archived"}:
            continue
        items.append(
            {
                "id": str(item.get("id") or item.get("approval_id") or f"{Path(source).stem}-{index}"),
                "source": source,
                "title": str(item.get("title") or item.get("action") or item.get("summary") or "Approval request"),
                "status": status,
                "risk": item.get("risk") or item.get("risk_level"),
                "reason": item.get("reason") or item.get("why") or item.get("notes"),
                "raw": item,
            }
        )
    return items


def _kanban_approval_items(root: Path) -> list[dict[str, Any]]:
    try:
        from hermes_cli import kanban_db
    except Exception:
        return []

    items: list[dict[str, Any]] = []
    for board in ("operator-brain", None):
        try:
            db_path = kanban_db.kanban_db_path(board=board)
            if not db_path.exists():
                continue
            with kanban_db.connect(db_path=db_path, board=board) as conn:
                rows = conn.execute(
                    """
                    SELECT id, title, body, status, priority
                    FROM tasks
                    WHERE status IN ('blocked', 'review', 'ready')
                    ORDER BY priority DESC, created_at DESC
                    """
                ).fetchall()
        except Exception:
            continue
        for row in rows:
            haystack = f"{row['title']}\n{row['body'] or ''}"
            if not APPROVAL_TERMS.search(haystack):
                continue
            normalized = haystack.lower().replace(" ", "")
            if '"human_approval_required":false' in normalized or '"approval_required":false' in normalized:
                continue
            items.append(
                {
                    "id": str(row["id"]),
                    "source": f"kanban:{board or 'current'}",
                    "title": str(row["title"]),
                    "status": str(row["status"]),
                    "risk": None,
                    "reason": (row["body"] or "")[:500],
                    "raw": {"priority": row["priority"]},
                }
            )
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = (item["id"], item["title"])
        if key in seen:
            continue
        unique.append(item)
        seen.add(key)
    return unique


def list_approvals(root: Path | None = None, limit: int = 25) -> dict[str, Any]:
    prime_root = root or find_prime_root()
    if prime_root is None:
        return {"ok": False, "status": "unavailable", "message": "Hermes Prime root not found.", "approvals": []}

    approvals: list[dict[str, Any]] = []
    runtime = _runtime(prime_root)
    for filename in APPROVAL_FILES:
        path = runtime / filename
        approvals.extend(_queue_items_from_payload(_read_json(path), str(path)))
    approvals.extend(_kanban_approval_items(prime_root))

    return {
        "ok": True,
        "status": "pending" if approvals else "empty",
        "approval_count": len(approvals),
        "approvals": approvals[:limit],
    }


def format_approvals(payload: dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"Approvals unavailable: {payload.get('message', 'unknown')}"
    approvals = payload.get("approvals") or []
    if not approvals:
        return "No pending approval requests found in runtime queues or Operator Brain Kanban."
    lines = [f"Pending approvals: {payload.get('approval_count', len(approvals))}"]
    for item in approvals:
        risk = f" risk={item.get('risk')}" if item.get("risk") else ""
        lines.append(f"- {item.get('id')} [{item.get('status')}] {item.get('title')}{risk}")
        lines.append(f"  source: {item.get('source')}")
        if item.get("reason"):
            reason = " ".join(str(item["reason"]).split())
            lines.append(f"  reason: {reason[:240]}")
    return "\n".join(lines)
