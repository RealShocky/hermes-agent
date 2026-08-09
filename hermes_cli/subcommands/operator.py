"""``hermes operator`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_operator_parser(subparsers, *, cmd_operator: Callable) -> None:
    """Attach Hermes Prime operator bridge commands."""
    operator_parser = subparsers.add_parser(
        "operator",
        help="Inspect or control the Hermes Prime operator bridge",
        description="Read Operator Brain state and perform audited local operator actions",
    )
    operator_subparsers = operator_parser.add_subparsers(dest="operator_action")

    status_parser = operator_subparsers.add_parser(
        "status",
        help="Show live Operator Brain state",
    )
    status_parser.set_defaults(func=cmd_operator)

    pause_parser = operator_subparsers.add_parser(
        "pause",
        help="Pause future autonomous operator cycles",
    )
    pause_parser.add_argument(
        "--reason",
        default=None,
        help="Optional pause reason written to the pause marker and audit log",
    )
    pause_parser.set_defaults(func=cmd_operator)

    resume_parser = operator_subparsers.add_parser(
        "resume",
        help="Resume future autonomous operator cycles",
    )
    resume_parser.set_defaults(func=cmd_operator)

    refresh_parser = operator_subparsers.add_parser(
        "refresh",
        help="Refresh Operator Intelligence and the Operator Brain Kanban mirror",
    )
    refresh_parser.set_defaults(func=cmd_operator)

    approvals_parser = operator_subparsers.add_parser(
        "approvals",
        help="List pending approval requests from runtime queues and Operator Brain Kanban",
    )
    approvals_parser.add_argument("--limit", type=int, default=25)
    approvals_parser.set_defaults(func=cmd_operator)

    task_parser = operator_subparsers.add_parser(
        "task",
        help="Queue user-approved work for a registered Hermes Prime workspace",
    )
    task_subparsers = task_parser.add_subparsers(dest="operator_task_action")

    task_create = task_subparsers.add_parser(
        "create",
        help="Append an unchecked item to a workspace HERMES_TASKS.md queue",
    )
    task_create.add_argument("--workspace", required=True, help="Registered workspace name")
    task_create.add_argument("--summary", required=True, help="Task summary to add as a checklist item")
    task_create.add_argument(
        "--type",
        dest="task_type",
        default="feature",
        choices=["feature", "fix", "self-improve", "infra", "tool"],
        help="Autonomous task type",
    )
    task_create.add_argument(
        "--reason",
        default=None,
        help="Reason recorded in the intake audit log",
    )
    task_create.add_argument(
        "--no-refresh",
        dest="refresh",
        action="store_false",
        help="Do not refresh Operator Brain/Kanban after creating the task",
    )
    task_create.add_argument(
        "--dispatch",
        action="store_true",
        help="Run one side-lane scheduler pass after queueing the task",
    )
    task_create.set_defaults(func=cmd_operator, operator_action="task")

    task_list = task_subparsers.add_parser(
        "list",
        help="List recent CLI-created Hermes Prime tasks",
    )
    task_list.add_argument("--limit", type=int, default=10)
    task_list.set_defaults(func=cmd_operator, operator_action="task")

    operator_parser.set_defaults(func=cmd_operator, operator_action="status")
