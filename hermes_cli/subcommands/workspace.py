"""``hermes workspace`` parser for Leonor caller-workspace awareness."""

from __future__ import annotations

from typing import Callable


def build_workspace_parser(subparsers, *, cmd_workspace: Callable) -> None:
    workspace_parser = subparsers.add_parser(
        "workspace",
        help="Inspect the current Leonor caller workspace",
        description="Inspect docs, git state, and audit context for the caller workspace.",
    )
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command")

    inspect_parser = workspace_subparsers.add_parser(
        "inspect",
        help="Inspect the caller workspace without editing files",
    )
    inspect_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    inspect_parser.add_argument(
        "--no-audit",
        dest="audit",
        action="store_false",
        default=True,
        help="Do not write the workspace inspection audit event",
    )
    inspect_parser.set_defaults(func=cmd_workspace)

    workspace_parser.set_defaults(func=cmd_workspace)
