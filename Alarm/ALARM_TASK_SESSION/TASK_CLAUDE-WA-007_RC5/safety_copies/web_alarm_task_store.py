"""Persistent TASK and microtask storage for Web Alarm Workspace WA-1.3."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable

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


class TaskStoreError(RuntimeError):
    """Raised when persisted TASK state is missing, inconsistent or unsafe."""


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
    """Disk-backed lifecycle storage for TASK and ordered microtasks."""

    def __init__(self, storage_root: str | os.PathLike[str] | None = None) -> None:
        root = Path(storage_root) if storage_root is not None else default_storage_root()
        self.storage_root = root.expanduser().resolve(strict=False)
        self.tasks_root = self.storage_root / "tasks"
        self.active_dir = self.tasks_root / "active"
        self.completed_dir = self.tasks_root / "completed"
        self.staging_dir = self.tasks_root / ".staging"
        for path in (self.active_dir, self.completed_dir, self.staging_dir):
            path.mkdir(parents=True, exist_ok=True)

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
        if task.status in {TaskStatus.COMPLETED, TaskStatus.ARCHIVED}:
            raise TaskStoreError(f"task is not mutable: {task.task_id}")
        return task

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
        task_dir = self._task_path(task_id, active_only=active_only)
        self._load_task_from(task_dir)
        return task_dir

    def open_microtask(self, task_id: str, microtask_id: str) -> MicrotaskRecord:
        task_dir = self._task_path(task_id)
        self._load_task_from(task_dir)
        return self._load_microtask_from(task_dir, microtask_id)

    def microtask_directory(
        self, task_id: str, microtask_id: str, *, active_only: bool = False
    ) -> Path:
        task_dir = self._task_path(task_id, active_only=active_only)
        self._load_microtask_from(task_dir, microtask_id)
        work_dir = self._microtask_dir_path(task_dir, microtask_id)
        if not work_dir.is_dir():
            raise TaskStoreError(f"microtask work directory is missing: {microtask_id}")
        return work_dir

    def set_microtask_status(
        self, task_id: str, microtask_id: str, status: MicrotaskStatus
    ) -> MicrotaskRecord:
        task_dir = self._task_path(task_id, active_only=True)
        self._require_mutable(task_dir)
        microtask = self._load_microtask_from(task_dir, microtask_id)
        microtask.status = MicrotaskStatus(status)
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
        task_dir = self._task_path(task_id, active_only=True)
        task = self._require_mutable(task_dir)
        destination = self.completed_dir / task.task_id
        if destination.exists():
            raise TaskStoreError(f"completed task already exists: {task.task_id}")
        task.status = TaskStatus.COMPLETED
        task.updated_at = utc_now_iso()
        self._write_task(task_dir, task)
        try:
            os.replace(task_dir, destination)
        except OSError as exc:
            raise TaskStoreError(f"cannot move task to completed: {task.task_id}") from exc
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
