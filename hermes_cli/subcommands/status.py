"""``hermes status`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_status_parser(subparsers, *, cmd_status: Callable) -> None:
    """Attach the ``status`` subcommand to ``subparsers``."""
    status_parser = subparsers.add_parser(
        "status", help="Show status of all components",
        description="Display status of Hermes Agent components")
    status_parser.add_argument(
        "--all", action="store_true", help="Show all details (redacted for sharing)")
    status_parser.add_argument(
        "--deep", action="store_true", help="Run deep checks (may take longer)")
    status_parser.add_argument(
        "--brain",
        action="store_true",
        help="Include Leonor Operator Brain runtime status",
    )
    status_parser.add_argument(
        "--brain-only",
        action="store_true",
        help="Only show Leonor Operator Brain runtime status",
    )
    status_parser.set_defaults(func=cmd_status)
