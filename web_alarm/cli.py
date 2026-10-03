"""Basic command-line interface for Web Alarm Workspace WA-1.6."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .manifest_store import ManifestSnapshotStore, ManifestStoreError
from .models import CheckpointRecord, MicrotaskStatus, record_to_dict
from .remote_entry import RemoteEntry, RemoteEntryError
from .task_store import TaskStore, TaskStoreError
from .workspace_registry import WorkspaceRegistryError


def _json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _target_spec(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("target must use PATH=EXPECTED_CHANGE")
    path, change = value.split("=", 1)
    if not path.strip() or not change.strip():
        raise argparse.ArgumentTypeError("target must use non-empty PATH=EXPECTED_CHANGE")
    return path.strip(), change.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="webalarm")
    parser.add_argument("--storage-root", help="Web Alarm state root; defaults to machine-local root")
    root = parser.add_subparsers(dest="command", required=True)

    task = root.add_parser("task")
    task_sub = task.add_subparsers(dest="task_command", required=True)

    create = task_sub.add_parser("create")
    create.add_argument("--workspace-id", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--raw-task", required=True)
    create.add_argument("--goal", required=True)
    create.add_argument("--task-id")

    open_p = task_sub.add_parser("open")
    open_p.add_argument("--task-id", required=True)

    complete = task_sub.add_parser("complete")
    complete.add_argument("--task-id", required=True)

    micro = root.add_parser("microtask")
    micro_sub = micro.add_subparsers(dest="micro_command", required=True)

    micro_create = micro_sub.add_parser("create")
    micro_create.add_argument("--task-id", required=True)
    micro_create.add_argument("--title", required=True)
    micro_create.add_argument("--goal", required=True)
    micro_create.add_argument("--microtask-id")

    prepare = micro_sub.add_parser("prepare")
    prepare.add_argument("--task-id", required=True)
    prepare.add_argument("--microtask-id", required=True)
    prepare.add_argument("--target", action="append", type=_target_spec, required=True)

    snapshot = root.add_parser("snapshot")
    snapshot_sub = snapshot.add_subparsers(dest="snapshot_command", required=True)
    for name in ("verify", "restore"):
        cmd = snapshot_sub.add_parser(name)
        cmd.add_argument("--task-id", required=True)
        cmd.add_argument("--microtask-id", required=True)

    checkpoint = root.add_parser("checkpoint")
    checkpoint_sub = checkpoint.add_subparsers(dest="checkpoint_command", required=True)

    cp_write = checkpoint_sub.add_parser("write")
    cp_write.add_argument("--task-id", required=True)
    cp_write.add_argument("--current-microtask")
    cp_write.add_argument("--last-verified-microtask")
    cp_write.add_argument(
        "--current-status",
        choices=[status.value for status in MicrotaskStatus],
        default=MicrotaskStatus.PLANNED.value,
    )
    cp_write.add_argument("--snapshot-status", required=True)
    cp_write.add_argument("--last-operation-id")
    cp_write.add_argument("--next-safe-action", required=True)

    cp_show = checkpoint_sub.add_parser("show")
    cp_show.add_argument("--task-id", required=True)

    enter = root.add_parser("enter")
    enter.add_argument("--task-id")

    status = root.add_parser("status")
    status_target = status.add_mutually_exclusive_group(required=True)
    status_target.add_argument("--task-id")
    status_target.add_argument("--active", action="store_true")

    report = root.add_parser("report")
    report.add_argument("--task-id", required=True)

    return parser


def _stores(storage_root: str | None):
    return (
        TaskStore(storage_root),
        ManifestSnapshotStore(storage_root),
        EventCheckpointStore(storage_root),
    )


def _handle(args: argparse.Namespace) -> int:
    tasks, manifests, state = _stores(args.storage_root)

    if args.command == "task":
        if args.task_command == "create":
            record = tasks.create_task(
                args.workspace_id,
                args.title,
                args.raw_task,
                args.goal,
                task_id=args.task_id,
            )
            _json(record_to_dict(record))
            return 0
        if args.task_command == "open":
            _json(record_to_dict(tasks.open_task(args.task_id)))
            return 0
        if args.task_command == "complete":
            _json(record_to_dict(tasks.complete_task(args.task_id)))
            return 0

    if args.command == "microtask":
        if args.micro_command == "create":
            record = tasks.create_microtask(
                args.task_id,
                args.title,
                args.goal,
                microtask_id=args.microtask_id,
            )
            _json(record_to_dict(record))
            return 0
        if args.micro_command == "prepare":
            record = manifests.prepare_microtask(
                args.task_id,
                args.microtask_id,
                args.target,
            )
            _json(record_to_dict(record))
            return 0

    if args.command == "snapshot":
        if args.snapshot_command == "verify":
            _json(record_to_dict(manifests.verify_restore_point(args.task_id, args.microtask_id)))
            return 0
        if args.snapshot_command == "restore":
            _json(record_to_dict(manifests.restore_microtask(args.task_id, args.microtask_id)))
            return 0

    if args.command == "checkpoint":
        if args.checkpoint_command == "write":
            task = tasks.open_task(args.task_id)
            record = CheckpointRecord(
                task_id=task.task_id,
                workspace_id=task.workspace_id,
                last_verified_microtask_id=args.last_verified_microtask,
                current_microtask_id=args.current_microtask,
                current_status=MicrotaskStatus(args.current_status),
                snapshot_status=args.snapshot_status,
                last_operation_id=args.last_operation_id,
                next_safe_action=args.next_safe_action,
            )
            _json(record_to_dict(state.write_checkpoint(record)))
            return 0
        if args.checkpoint_command == "show":
            _json(record_to_dict(state.read_checkpoint(args.task_id)))
            return 0

    if args.command == "enter":
        _json(RemoteEntry(args.storage_root).enter(args.task_id))
        return 0

    if args.command == "status":
        if args.active:
            _json(RemoteEntry(args.storage_root).enter())
            return 0
        task = tasks.open_task(args.task_id)
        plan = tasks.open_plan(args.task_id)
        payload = {
            "task": record_to_dict(task),
            "plan": record_to_dict(plan),
            "microtasks": [record_to_dict(item) for item in tasks.list_microtasks(args.task_id)],
            "checkpoint": None,
        }
        try:
            payload["checkpoint"] = record_to_dict(state.read_checkpoint(args.task_id))
        except EventCheckpointStoreError as exc:
            if "checkpoint is missing" not in str(exc):
                raise
        _json(payload)
        return 0

    if args.command == "report":
        task = tasks.open_task(args.task_id)
        plan = tasks.open_plan(args.task_id)
        print(f"TASK: {task.task_id}")
        print(f"STATUS: {task.status.value}")
        print(f"WORKSPACE: {task.workspace_id}")
        print(f"MICROTASKS: {len(plan.microtask_ids)}")
        print(f"CURRENT MICROTASK: {plan.current_microtask_id or '-'}")
        try:
            checkpoint = state.read_checkpoint(args.task_id)
        except EventCheckpointStoreError as exc:
            if "checkpoint is missing" in str(exc):
                print("CHECKPOINT: MISSING")
                return 0
            raise
        print(f"CHECKPOINT STATUS: {checkpoint.current_status.value}")
        print(f"SNAPSHOT STATUS: {checkpoint.snapshot_status}")
        print(f"NEXT SAFE ACTION: {checkpoint.next_safe_action}")
        return 0

    raise RuntimeError("unreachable CLI branch")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return _handle(args)
    except (
        TaskStoreError,
        ManifestStoreError,
        EventCheckpointStoreError,
        WorkspaceRegistryError,
        RemoteEntryError,
        ValueError,
        OSError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
