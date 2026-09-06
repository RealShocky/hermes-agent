"""``hermes operator`` parser for Leonor runtime controls."""

from __future__ import annotations

from typing import Callable


def build_operator_parser(subparsers, *, cmd_operator: Callable) -> None:
    operator_parser = subparsers.add_parser(
        "operator",
        help="Read or control the bounded Leonor operator runtime",
        description="Read Operator Brain state or pause/resume/refresh the wrapper runtime.",
    )
    operator_subparsers = operator_parser.add_subparsers(dest="operator_command")

    status_parser = operator_subparsers.add_parser("status", help="Show Operator Brain status")
    status_parser.set_defaults(func=cmd_operator)

    pause_parser = operator_subparsers.add_parser("pause", help="Pause autonomous operator cycles")
    pause_parser.add_argument("--reason", default="", help="Reason written to the pause marker")
    pause_parser.set_defaults(func=cmd_operator)

    resume_parser = operator_subparsers.add_parser("resume", help="Resume autonomous operator cycles")
    resume_parser.set_defaults(func=cmd_operator)

    refresh_parser = operator_subparsers.add_parser(
        "refresh",
        help="Refresh Operator Brain/Kanban runtime state",
    )
    refresh_parser.set_defaults(func=cmd_operator)

    operator_parser.set_defaults(func=cmd_operator)
