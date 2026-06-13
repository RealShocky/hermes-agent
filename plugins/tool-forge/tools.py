"""Bounded native-tool assessment and proposal tools."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from tools.registry import tool_error, tool_result


def _proposal_dir() -> Path:
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    return home / "tool-forge" / "proposals"


def assess(capability: str, evidence: list[str], existing_alternatives: list[str] | None = None) -> str:
    evidence = [str(item).strip() for item in evidence if str(item).strip()]
    alternatives = [str(item).strip() for item in (existing_alternatives or []) if str(item).strip()]
    recurring = len(evidence) >= 2
    recommendation = "native-tool" if recurring and not alternatives else "reuse-or-skill"
    return tool_result(
        recommendation=recommendation,
        recurring_evidence=recurring,
        evidence_count=len(evidence),
        existing_alternatives=alternatives,
        reason=(
            "Repeated evidence and no viable existing alternative justify a reusable native tool."
            if recommendation == "native-tool"
            else "Prefer an existing tool or reusable skill until the capability gap is repeated and distinct."
        ),
    )


def propose(
    name: str,
    capability: str,
    inputs: dict,
    expected_output: str,
    evidence: list[str],
    existing_alternatives: list[str] | None = None,
) -> str:
    assessment = json.loads(assess(capability, evidence, existing_alternatives))
    if assessment.get("recommendation") != "native-tool":
        return tool_error(assessment.get("reason", "Native tool threshold not met."), assessment=assessment)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        return tool_error("name must contain letters or numbers")
    proposal_dir = _proposal_dir()
    proposal_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = proposal_dir / f"{timestamp}-{slug}.json"
    payload = {
        "timestamp": timestamp,
        "status": "proposed",
        "task_type": "tool",
        "workspace": "HERMES_CORE_FORK",
        "summary": f"Create native tool: {name}",
        "capability": capability,
        "inputs": inputs,
        "expected_output": expected_output,
        "evidence": evidence,
        "existing_alternatives": existing_alternatives or [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return tool_result(proposal=payload, path=str(path))


ASSESS_SCHEMA = {
    "name": "tool_forge_assess",
    "description": "Decide whether a recurring missing capability should become a native Hermes tool.",
    "parameters": {
        "type": "object",
        "properties": {
            "capability": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "existing_alternatives": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["capability", "evidence"],
    },
}

PROPOSE_SCHEMA = {
    "name": "tool_forge_propose",
    "description": "Create an auditable native-tool proposal after the assessment threshold is met.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "capability": {"type": "string"},
            "inputs": {"type": "object"},
            "expected_output": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "existing_alternatives": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["name", "capability", "inputs", "expected_output", "evidence"],
    },
}
