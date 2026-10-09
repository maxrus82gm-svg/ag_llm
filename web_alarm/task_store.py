"""Persistent TASK and microtask storage for Web Alarm Workspace WA-1.3."""

from __future__ import annotations

import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout
from .models import (
    SCHEMA_VERSION,
    MicrotaskRecord,
    MicrotaskStatus,
    TaskPlanRecord,
    TaskRecord,
    TaskStatus,
    new_id,
    record_to_dict,
    utc_now_iso,
)
from .workspace_registry import default_storage_root

_CLOSED = frozenset({TaskStatus.COMPLETED, TaskStatus.ARCHIVED})

# F-5 (CLAUDE-WA-017): where a TASK stands relative to its completion (completion_state)
COMPLETION_ACTIVE = "ACTIVE"
COMPLETION_DONE = "COMPLETED"
# the directory move (the commit point) happened, the COMPLETED status write did not
COMPLETION_MOVED_STATUS_PENDING = "MOVED_STATUS_PENDING"
# the pre-WA-017 order wrote COMPLETED, then died before the directory move
COMPLETION_STATUS_WRITTEN_NOT_MOVED = "STATUS_WRITTEN_NOT_MOVED"
INTERRUPTED_COMPLETION = frozenset({COMPLETION_MOVED_STATUS_PENDING, COMPLETION_STATUS_WRITTEN_NOT_MOVED})


class TaskStoreError(RuntimeError):
    """Raised when persisted TASK state is missing, inconsistent or unsafe."""


class MicrotaskStatusConflict(TaskStoreError):
    """A compare-and-set lifecycle write found another current status; nothing was written."""

    def __init__(
        self,
        task_id: str,
        microtask_id: str,
        expected: Iterable[MicrotaskStatus],
        actual: MicrotaskStatus,
        reason: str | None = None,
    ) -> None:
        self.task_id = task_id
        self.microtask_id = microtask_id
        self.expected = tuple(sorted(status.value for status in expected))
        self.actual = actual
        super().__init__(
            reason
            or (
                f"microtask {task_id}/{microtask_id} is {actual.value}, not "
                f"{' / '.join(self.expected)}; the newer status was not overwritten"
            )
        )


def _safe_id(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskStoreError(f"{name} must be a non-empty string")
    if Path(value).name != value or "/" in value or "\\" in value:
        raise TaskStoreError(f"{name} must not contain path separators")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskStoreError(f"cannot read JSON record: {path}") from exc
    if not isinstance(value, dict):
        raise TaskStoreError(f"JSON record is not an object: {path}")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise TaskStoreError(
            f"unsupported schema_version in {path}: {value.get('schema_version')!r}"
        )
    return value


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise TaskStoreError(f"cannot persist JSON record: {path}") from exc


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
    try:
        with temp.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise TaskStoreError(f"cannot persist text record: {path}") from exc


class TaskStore:
    """Disk-backed lifecycle storage for TASK and ordered microtasks.

    RC-5: every plan/microtask mutation and the completion of a TASK hold the
    per-TASK mutation lock, so the closeout gate can prove "nothing open" and
    complete without a new microtask/status change slipping in between. The
    lock is not re-entrant; ``*_locked`` variants serve a caller that holds it.
    """

    def __init__(
        self,
        storage_root: str | os.PathLike[str] | None = None,
        *,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        root = Path(storage_root) if storage_root is not None else default_storage_root()
        self.storage_root = root.expanduser().resolve(strict=False)
        self.tasks_root = self.storage_root / "tasks"
        self.active_dir = self.tasks_root / "active"
        self.completed_dir = self.tasks_root / "completed"
        self.staging_dir = self.tasks_root / ".staging"
        self.lock_timeout = lock_timeout
        for path in (self.active_dir, self.completed_dir, self.staging_dir):
            path.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def mutation_lock(self, task_id: str) -> Iterator[None]:
        """Per-TASK lock for plan/microtask writes and completion (not re-entrant)."""
        task_id = _safe_id("task_id", task_id)
        lock = InterProcessLock(
            self.storage_root / "locks" / "tasks" / f"{task_id}.lock",
            timeout=self.lock_timeout,
        )
        try:
            lock.acquire()
        except StoreLockTimeout as exc:
            raise TaskStoreError(str(exc)) from exc
        try:
            yield
        finally:
            lock.release()

    def _task_path(self, task_id: str, *, active_only: bool = False) -> Path:
        task_id = _safe_id("task_id", task_id)
        active = self.active_dir / task_id
        completed = self.completed_dir / task_id
        if active.is_dir() and completed.is_dir():
            raise TaskStoreError(f"task exists in active and completed: {task_id}")
        if active.is_dir():
            return active
        if not active_only and completed.is_dir():
            return completed
        raise TaskStoreError(f"unknown {'active ' if active_only else ''}task_id: {task_id}")

    def _load_task_from(self, task_dir: Path) -> TaskRecord:
        raw = _read_json(task_dir / "task.json")
        try:
            raw["status"] = TaskStatus(raw["status"])
            record = TaskRecord(**raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise TaskStoreError(f"invalid task record: {task_dir}") from exc
        source_path = task_dir / "task.md"
        try:
            source = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise TaskStoreError(f"cannot read RAW TASK: {source_path}") from exc
        if source != record.raw_task:
            raise TaskStoreError(f"RAW TASK drift detected for {record.task_id}")
        return record

    def _load_plan_from(self, task_dir: Path) -> TaskPlanRecord:
        raw = _read_json(task_dir / "plan.json")
        try:
            return TaskPlanRecord(**raw)
        except (TypeError, ValueError) as exc:
            raise TaskStoreError(f"invalid task plan: {task_dir}") from exc

    def _microtask_path(self, task_dir: Path, microtask_id: str) -> Path:
        return task_dir / "microtasks" / f"{_safe_id('microtask_id', microtask_id)}.json"

    def _microtask_dir_path(self, task_dir: Path, microtask_id: str) -> Path:
        return task_dir / "microtasks" / _safe_id("microtask_id", microtask_id)

    def _load_microtask_from(
        self, task_dir: Path, microtask_id: str
    ) -> MicrotaskRecord:
        path = self._microtask_path(task_dir, microtask_id)
        if not path.is_file():
            raise TaskStoreError(f"unknown microtask_id: {microtask_id}")
        raw = _read_json(path)
        try:
            raw["status"] = MicrotaskStatus(raw["status"])
            return MicrotaskRecord(**raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise TaskStoreError(f"invalid microtask record: {path}") from exc

    def _write_task(self, task_dir: Path, record: TaskRecord) -> None:
        _atomic_write_json(task_dir / "task.json", record_to_dict(record))

    def _write_plan(self, task_dir: Path, plan: TaskPlanRecord) -> None:
        _atomic_write_json(task_dir / "plan.json", record_to_dict(plan))

    def _write_microtask(self, task_dir: Path, record: MicrotaskRecord) -> None:
        _atomic_write_json(
            self._microtask_path(task_dir, record.microtask_id),
            record_to_dict(record),
        )

    def _require_mutable(self, task_dir: Path) -> TaskRecord:
        task = self._load_task_from(task_dir)
        if task.status in _CLOSED:
            raise TaskStoreError(f"task is not mutable: {task.task_id}")
        return task

    def _active_task_dir(self, task_id: str) -> Path:
        """The directory of a TASK every writer may still change (``active_only``).

        F-5: in active/ *and* not closed by its status. A COMPLETED status left in
        active/ by an interrupted pre-WA-017 completion is a closed TASK: no store
        writes into it (finish it with the gated ``task complete``).
        """
        task_dir = self._task_path(task_id, active_only=True)
        task = self._load_task_from(task_dir)
        if task.status in _CLOSED:
            raise TaskStoreError(
                f"task {task.task_id} is {task.status.value} (interrupted completion): it is not active"
            )
        return task_dir

    def create_task(
        self,
        workspace_id: str,
        title: str,
        raw_task: str,
        goal: str,
        *,
        task_id: str | None = None,
    ) -> TaskRecord:
        chosen_id = _safe_id("task_id", task_id) if task_id else new_id("task")
        if (self.active_dir / chosen_id).exists() or (self.completed_dir / chosen_id).exists():
            raise TaskStoreError(f"task_id already exists: {chosen_id}")

        record = TaskRecord(
            task_id=chosen_id,
            workspace_id=workspace_id,
            title=title,
            raw_task=raw_task,
            goal=goal,
            status=TaskStatus.PLANNED,
            plan_revision=1,
        )
        plan = TaskPlanRecord(task_id=chosen_id, revision=1)
        stage = self.staging_dir / f"{chosen_id}.{new_id('stage')}"
        final = self.active_dir / chosen_id
        try:
            (stage / "microtasks").mkdir(parents=True, exist_ok=False)
            _atomic_write_json(stage / "task.json", record_to_dict(record))
            _atomic_write_text(stage / "task.md", raw_task)
            _atomic_write_json(stage / "plan.json", record_to_dict(plan))
            os.replace(stage, final)
        except OSError as exc:
            shutil.rmtree(stage, ignore_errors=True)
            raise TaskStoreError(f"cannot publish task: {chosen_id}") from exc
        return record
    def open_task(self, task_id: str) -> TaskRecord:
        return self._load_task_from(self._task_path(task_id))

    def open_plan(self, task_id: str) -> TaskPlanRecord:
        task_dir = self._task_path(task_id)
        self._load_task_from(task_dir)
        return self._load_plan_from(task_dir)

    def save_raw_task(self, task_id: str, raw_task: str) -> TaskRecord:
        task_dir = self._task_path(task_id)
        task = self._load_task_from(task_dir)
        if raw_task != task.raw_task:
            raise TaskStoreError("RAW TASK is immutable after task creation")
        return task

    def task_directory(self, task_id: str, *, active_only: bool = False) -> Path:
        if active_only:
            return self._active_task_dir(task_id)
        task_dir = self._task_path(task_id)
        self._load_task_from(task_dir)
        return task_dir

    def open_microtask(self, task_id: str, microtask_id: str) -> MicrotaskRecord:
        task_dir = self._task_path(task_id)
        self._load_task_from(task_dir)
        return self._load_microtask_from(task_dir, microtask_id)

    def microtask_directory(
        self, task_id: str, microtask_id: str, *, active_only: bool = False
    ) -> Path:
        task_dir = self._active_task_dir(task_id) if active_only else self._task_path(task_id)
        self._load_microtask_from(task_dir, microtask_id)
        work_dir = self._microtask_dir_path(task_dir, microtask_id)
        if not work_dir.is_dir():
            raise TaskStoreError(f"microtask work directory is missing: {microtask_id}")
        return work_dir

    def set_microtask_status(
        self, task_id: str, microtask_id: str, status: MicrotaskStatus
    ) -> MicrotaskRecord:
        with self.mutation_lock(task_id):
            return self.set_microtask_status_locked(task_id, microtask_id, status)

    def set_microtask_status_locked(
        self, task_id: str, microtask_id: str, status: MicrotaskStatus
    ) -> MicrotaskRecord:
        """Storage primitive for a caller already holding ``mutation_lock``.

        The caller owns lifecycle policy. This method performs the same
        fail-closed active-TASK write as ``set_microtask_status`` without
        acquiring the non-reentrant TASK lock again.
        """
        task_dir = self._task_path(task_id, active_only=True)
        self._require_mutable(task_dir)
        microtask = self._load_microtask_from(task_dir, microtask_id)
        microtask.status = MicrotaskStatus(status)
        microtask.updated_at = utc_now_iso()
        self._write_microtask(task_dir, microtask)
        return microtask

    def compare_and_set_microtask_status(
        self,
        task_id: str,
        microtask_id: str,
        *,
        expected: MicrotaskStatus | str | Iterable[MicrotaskStatus | str],
        status: MicrotaskStatus | str,
        activate: bool = False,
    ) -> MicrotaskRecord:
        """Lifecycle write that never overwrites a status it did not observe.

        Under the per-TASK mutation lock the authoritative status is re-read;
        unless it is still one of ``expected`` (the basis the caller decided
        on) nothing is written and MicrotaskStatusConflict is raised. With
        ``activate`` the "every earlier microtask is VERIFIED" and "no other
        ACTIVE microtask" rules and the plan's current pointer are handled
        inside the same locked section, so an activation is all-or-nothing
        against concurrent writers.
        """
        with self.mutation_lock(task_id):
            return self.compare_and_set_microtask_status_locked(
                task_id, microtask_id, expected=expected, status=status, activate=activate
            )

    def compare_and_set_microtask_status_locked(
        self,
        task_id: str,
        microtask_id: str,
        *,
        expected: MicrotaskStatus | str | Iterable[MicrotaskStatus | str],
        status: MicrotaskStatus | str,
        activate: bool = False,
    ) -> MicrotaskRecord:
        """``compare_and_set_microtask_status`` for a caller holding ``mutation_lock``.

        Activation crash semantics (Repair #3): the plan pointer is written
        before the status. A crash between the two leaves the pointer on the
        microtask that is still READY: the pointer is never authority (RC-5
        lifecycle is), it corroborates the lifecycle-current microtask, and
        repeating the activation completes it idempotently.
        """
        if isinstance(expected, (str, MicrotaskStatus)):
            expected_set = {MicrotaskStatus(expected)}
        else:
            expected_set = {MicrotaskStatus(item) for item in expected}
        target = MicrotaskStatus(status)
        task_dir = self._task_path(task_id, active_only=True)
        self._require_mutable(task_dir)
        microtask = self._load_microtask_from(task_dir, microtask_id)
        if microtask.status not in expected_set:
            raise MicrotaskStatusConflict(task_id, microtask_id, expected_set, microtask.status)
        if activate:
            plan = self._load_plan_from(task_dir)
            if microtask_id not in plan.microtask_ids:
                raise TaskStoreError("current microtask must belong to the task plan")
            index = plan.microtask_ids.index(microtask_id)
            for position, other_id in enumerate(plan.microtask_ids):
                if other_id == microtask_id:
                    continue
                other = self._load_microtask_from(task_dir, other_id)
                if position < index and other.status is not MicrotaskStatus.VERIFIED:
                    raise MicrotaskStatusConflict(
                        task_id,
                        microtask_id,
                        expected_set,
                        microtask.status,
                        reason=(
                            f"previous microtask {other_id} is {other.status.value}, not VERIFIED; "
                            "nothing was written"
                        ),
                    )
                if other.status is MicrotaskStatus.ACTIVE:
                    raise MicrotaskStatusConflict(
                        task_id,
                        microtask_id,
                        expected_set,
                        microtask.status,
                        reason=f"another microtask {other_id} is already ACTIVE; nothing was written",
                    )
            plan.current_microtask_id = microtask_id
            plan.updated_at = utc_now_iso()
            self._write_plan(task_dir, plan)
        microtask.status = target
        microtask.updated_at = utc_now_iso()
        self._write_microtask(task_dir, microtask)
        return microtask

    def list_microtasks(self, task_id: str) -> list[MicrotaskRecord]:
        task_dir = self._task_path(task_id)
        self._load_task_from(task_dir)
        plan = self._load_plan_from(task_dir)
        return [
            self._load_microtask_from(task_dir, microtask_id)
            for microtask_id in plan.microtask_ids
        ]

    def create_microtask(
        self,
        task_id: str,
        title: str,
        goal: str,
        *,
        microtask_id: str | None = None,
    ) -> MicrotaskRecord:
        with self.mutation_lock(task_id):
            task_dir = self._task_path(task_id, active_only=True)
            task = self._require_mutable(task_dir)
            plan = self._load_plan_from(task_dir)
            chosen_id = (
                _safe_id("microtask_id", microtask_id)
                if microtask_id
                else new_id("micro")
            )
            path = self._microtask_path(task_dir, chosen_id)
            work_dir = self._microtask_dir_path(task_dir, chosen_id)
            if path.exists() or work_dir.exists():
                raise TaskStoreError(f"microtask_id already exists: {chosen_id}")

            record = MicrotaskRecord(
                microtask_id=chosen_id,
                task_id=task_id,
                sequence=len(plan.microtask_ids) + 1,
                title=title,
                goal=goal,
            )
            try:
                work_dir.mkdir(parents=False, exist_ok=False)
                self._write_microtask(task_dir, record)
            except (OSError, TaskStoreError) as exc:
                path.unlink(missing_ok=True)
                shutil.rmtree(work_dir, ignore_errors=True)
                raise TaskStoreError(f"cannot create microtask: {chosen_id}") from exc
            plan.microtask_ids.append(chosen_id)
            plan.revision += 1
            plan.updated_at = utc_now_iso()
            task.plan_revision = plan.revision
            task.updated_at = utc_now_iso()
            self._write_plan(task_dir, plan)
            self._write_task(task_dir, task)
            return record

    def set_plan(self, task_id: str, microtask_ids: Iterable[str]) -> TaskPlanRecord:
        with self.mutation_lock(task_id):
            task_dir = self._task_path(task_id, active_only=True)
            task = self._require_mutable(task_dir)
            plan = self._load_plan_from(task_dir)
            ordered = [_safe_id("microtask_id", value) for value in microtask_ids]
            if len(ordered) != len(set(ordered)):
                raise TaskStoreError("plan must not contain duplicate microtask IDs")
            if set(ordered) != set(plan.microtask_ids):
                raise TaskStoreError("plan must contain exactly the task's microtasks")

            for sequence, microtask_id in enumerate(ordered, start=1):
                micro = self._load_microtask_from(task_dir, microtask_id)
                micro.sequence = sequence
                micro.updated_at = utc_now_iso()
                self._write_microtask(task_dir, micro)

            plan.microtask_ids = ordered
            plan.revision += 1
            plan.updated_at = utc_now_iso()
            task.plan_revision = plan.revision
            task.updated_at = utc_now_iso()
            self._write_plan(task_dir, plan)
            self._write_task(task_dir, task)
            return plan

    def set_current_microtask(
        self, task_id: str, microtask_id: str
    ) -> TaskPlanRecord:
        with self.mutation_lock(task_id):
            task_dir = self._task_path(task_id, active_only=True)
            self._require_mutable(task_dir)
            plan = self._load_plan_from(task_dir)
            microtask_id = _safe_id("microtask_id", microtask_id)
            if microtask_id not in plan.microtask_ids:
                raise TaskStoreError("current microtask must belong to the task plan")
            self._load_microtask_from(task_dir, microtask_id)
            plan.current_microtask_id = microtask_id
            plan.updated_at = utc_now_iso()
            self._write_plan(task_dir, plan)
            return plan

    def complete_task(self, task_id: str) -> TaskRecord:
        """Storage primitive: no closeout gate. Public workflows use CloseoutService."""
        with self.mutation_lock(task_id):
            return self.complete_task_locked(task_id)

    def completion_state(self, task_id: str) -> str:
        """Pure: ACTIVE, COMPLETED, or an interrupted completion (``INTERRUPTED_COMPLETION``)."""
        task_dir = self._task_path(task_id)
        closed = self._load_task_from(task_dir).status in _CLOSED
        if task_dir.parent == self.active_dir:
            return COMPLETION_STATUS_WRITTEN_NOT_MOVED if closed else COMPLETION_ACTIVE
        return COMPLETION_DONE if closed else COMPLETION_MOVED_STATUS_PENDING

    def complete_task_locked(self, task_id: str) -> TaskRecord:
        """``complete_task`` for a caller that already holds ``mutation_lock``.

        F-5 (CLAUDE-WA-017): the directory move active/ -> completed/ is the one
        commit point, and the COMPLETED status is written after it. No store
        writes into a TASK outside active/ (or one closed by its status), so a
        process death leaves either the untouched active TASK (before the move)
        or a closed one (after it), never a closed TASK that still accepts
        writes. A failed move changes nothing. An interrupted completion is
        finished idempotently here: MOVED_STATUS_PENDING writes the status,
        STATUS_WRITTEN_NOT_MOVED (a pre-WA-017 crash) performs the move.
        """
        state = self.completion_state(task_id)
        if state == COMPLETION_DONE:
            raise TaskStoreError(f"task is already completed: {task_id}")
        destination = self.completed_dir / _safe_id("task_id", task_id)
        if state != COMPLETION_MOVED_STATUS_PENDING:
            task_dir = self.active_dir / task_id
            if state == COMPLETION_ACTIVE:
                self._require_mutable(task_dir)
            try:
                os.replace(task_dir, destination)
            except OSError as exc:
                raise TaskStoreError(f"cannot move task to completed: {task_id}") from exc
        task = self._load_task_from(destination)
        if task.status not in _CLOSED:
            task.status = TaskStatus.COMPLETED
            task.updated_at = utc_now_iso()
            self._write_task(destination, task)
        return self._load_task_from(destination)

    def archive_task(self, task_id: str) -> TaskRecord:
        task_id = _safe_id("task_id", task_id)
        task_dir = self.completed_dir / task_id
        if not task_dir.is_dir():
            raise TaskStoreError(f"task must be completed before archive: {task_id}")
        task = self._load_task_from(task_dir)
        if task.status == TaskStatus.ARCHIVED:
            return task
        if task.status != TaskStatus.COMPLETED:
            raise TaskStoreError(f"task is not in completed state: {task_id}")
        task.status = TaskStatus.ARCHIVED
        task.updated_at = utc_now_iso()
        self._write_task(task_dir, task)
        return task
