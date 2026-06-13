"""Native tool lifecycle entrypoint."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("hermes_tool_forge_tools", Path(__file__).with_name("tools.py"))
_TOOLS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_TOOLS)
ASSESS_SCHEMA = _TOOLS.ASSESS_SCHEMA
PROPOSE_SCHEMA = _TOOLS.PROPOSE_SCHEMA
assess = _TOOLS.assess
propose = _TOOLS.propose


def register(ctx) -> None:
    ctx.register_tool(
        name="tool_forge_assess",
        toolset="tool-forge",
        schema=ASSESS_SCHEMA,
        handler=lambda args, **_: assess(**args),
    )
    ctx.register_tool(
        name="tool_forge_propose",
        toolset="tool-forge",
        schema=PROPOSE_SCHEMA,
        handler=lambda args, **_: propose(**args),
    )
