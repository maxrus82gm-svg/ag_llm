"""Basic command-line interface for Web Alarm Workspace WA-1.6."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .closeout import CloseoutError, CloseoutService
from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .manifest_store import ManifestSnapshotStore, ManifestStoreError
from .models import MicrotaskStatus, record_to_dict
from .mutation_executor import EXECUTED, REPLAYED, MutationExecutor, MutationExecutorError
from .projection import ProjectionError, ProjectionService
from .recovery_coordinator import (
    FAIL_CLOSED,
    RECOVERY_BLOCKED,
    RecoveryCoordinator,
    RecoveryCoordinatorError,
)
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

    complete = task_sub.add_parser("complete", help="complete a TASK through the RC-5 closeout gate")
    complete.add_argument("--task-id", required=True)

    closeout = task_sub.add_parser("closeout", help="pure closeout inspection (eligibility + blockers)")
    closeout.add_argument("--task-id", required=True)

    recover = task_sub.add_parser("recover", help="RC-6 bounded project-level recovery/resume")
    recover.add_argument("--task-id", required=True)
    recover.add_argument("--max-recovery-steps", type=int)

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

    # RC-5: retired. Kept in the parser only to fail with an explicit message:
    # a caller can no longer write checkpoint "truth" (use `checkpoint rebuild`).
    cp_write = checkpoint_sub.add_parser("write", help="retired in RC-5: use `checkpoint rebuild`")
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

    cp_validate = checkpoint_sub.add_parser("validate", help="pure: persisted checkpoint vs current projection")
    cp_validate.add_argument("--task-id", required=True)

    cp_rebuild = checkpoint_sub.add_parser("rebuild", help="rebuild checkpoint.json/.md from authoritative state")
    cp_rebuild.add_argument("--task-id", required=True)

    enter = root.add_parser("enter")
    enter.add_argument("--task-id")

    status = root.add_parser("status")
    status_target = status.add_mutually_exclusive_group(required=True)
    status_target.add_argument("--task-id")
    status_target.add_argument("--active", action="store_true")

    report = root.add_parser("report")
    report.add_argument("--task-id", required=True)

    mutate = root.add_parser("mutate", help="WA4-E: the server performs one tracked mutation (replay-safe)")
    mutate.add_argument("--task-id", required=True)
    mutate.add_argument("--microtask-id", required=True)
    mutate.add_argument("--operation-id", required=True, help="idempotency key: a replay names the same id")
    mutate.add_argument("--action", required=True, help="write | edit | create | delete | move | rename")
    mutate.add_argument("--target", required=True)
    mutate.add_argument("--destination", help="move/rename only")
    mutate.add_argument("--payload-file", help="exact new bytes for write/edit/create")

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
            outcome = CloseoutService(args.storage_root).complete(args.task_id)
            _json({
                "result": outcome["result"],
                "task": record_to_dict(outcome["task"]) if outcome["task"] is not None else None,
                "closeout": outcome["closeout"],
            })
            return 0 if outcome["completed"] else 3
        if args.task_command == "closeout":
            _json(CloseoutService(args.storage_root).inspect(args.task_id))
            return 0
        if args.task_command == "recover":
            outcome = RecoveryCoordinator(args.storage_root).recover(
                args.task_id,
                max_recovery_steps=args.max_recovery_steps,
            )
            _json(outcome)
            return 3 if outcome["state"] in {FAIL_CLOSED, RECOVERY_BLOCKED} else 0

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
            print(
                "ERROR: `checkpoint write` is retired (RC-5): a checkpoint is a projection of "
                "authoritative state, never caller-supplied truth; use `checkpoint rebuild`",
                file=sys.stderr,
            )
            return 2
        if args.checkpoint_command == "show":
            _json(record_to_dict(state.read_checkpoint(args.task_id)))
            return 0
        if args.checkpoint_command == "validate":
            _json(ProjectionService(args.storage_root).validate_checkpoint(args.task_id))
            return 0
        if args.checkpoint_command == "rebuild":
            rebuilt = ProjectionService(args.storage_root).rebuild_checkpoint(args.task_id)
            _json({"checkpoint": record_to_dict(rebuilt["checkpoint"]), "validation": rebuilt["validation"]})
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
        projections = ProjectionService(args.storage_root)
        projection = projections.build(args.task_id)
        payload = {
            "task": record_to_dict(task),
            "plan": record_to_dict(plan),
            "microtasks": [record_to_dict(item) for item in tasks.list_microtasks(args.task_id)],
            "checkpoint": None,
            "checkpoint_validation": projections.validate_checkpoint(args.task_id, projection),
            "projection": projection,
        }
        try:
            payload["checkpoint"] = record_to_dict(state.read_checkpoint(args.task_id))
        except EventCheckpointStoreError as exc:
            if "checkpoint is missing" not in str(exc):
                payload["checkpoint"] = None  # corrupt: reported by checkpoint_validation
        _json(payload)
        return 0

    if args.command == "report":
        task = tasks.open_task(args.task_id)
        plan = tasks.open_plan(args.task_id)
        projections = ProjectionService(args.storage_root)
        projection = projections.build(args.task_id)
        validation = projections.validate_checkpoint(args.task_id, projection)
        position = projection["position"]
        print(f"TASK: {task.task_id}")
        print(f"STATUS: {task.status.value}")
        print(f"WORKSPACE: {task.workspace_id}")
        print(f"MICROTASKS: {len(plan.microtask_ids)}")
        print(f"CURRENT MICROTASK: {position['current_microtask_id'] or '-'}")
        print(f"CURRENT STATUS: {position['current_status']}")
        print(f"SNAPSHOT STATUS: {projection['restore_point']['status']}")
        print(f"CHECKPOINT: {validation['status']} (never authority)")
        print(f"NEXT SAFE ACTION: {projection['next_safe_action']}")
        print(f"NEXT SOURCE: {projection['authority_source']}")
        return 0

    if args.command == "mutate":
        outcome = MutationExecutor(args.storage_root).execute(
            args.task_id,
            args.microtask_id,
            args.operation_id,
            args.action,
            args.target,
            destination=args.destination,
            payload=Path(args.payload_file).read_bytes() if args.payload_file else None,
        )
        _json(outcome)
        return 0 if outcome["result"] in (EXECUTED, REPLAYED) else 3

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
        ProjectionError,
        RecoveryCoordinatorError,
        CloseoutError,
        MutationExecutorError,
        ValueError,
        OSError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
