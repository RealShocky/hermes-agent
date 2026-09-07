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

    plan_parser = workspace_subparsers.add_parser(
        "plan",
        help="Create an auditable plan from the caller workspace docs",
    )
    plan_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    plan_parser.add_argument("--request", default="", help="Optional user request to attach to the plan")
    plan_parser.add_argument(
        "--no-audit",
        dest="audit",
        action="store_false",
        default=True,
        help="Do not write the workspace plan audit event",
    )
    plan_parser.set_defaults(func=cmd_workspace)

    build_parser = workspace_subparsers.add_parser(
        "build",
        help="Queue a bounded local build lane request for the caller workspace",
    )
    build_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    build_parser.add_argument("--request", default="", help="User request to attach to the local build lane")
    build_parser.add_argument(
        "--no-audit",
        dest="audit",
        action="store_false",
        default=True,
        help="Do not write the global workspace audit event",
    )
    build_parser.set_defaults(func=cmd_workspace)

    workspace_parser.set_defaults(func=cmd_workspace)
