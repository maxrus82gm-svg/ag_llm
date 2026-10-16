"""Persistent Workspace Registry for Web Alarm Workspace WA-1.2."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from .models import (
    SCHEMA_VERSION,
    WorkspaceRegistration,
    new_id,
    record_to_dict,
)


class WorkspaceRegistryError(RuntimeError):
    """Raised when workspace registry state is invalid or unsafe."""


def default_storage_root() -> Path:
    """Return the default machine-local Web Alarm storage root."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "WebAlarmWorkspace"
    return Path.home() / ".web_alarm_workspace"


def _safe_workspace_id(workspace_id: str) -> str:
    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise WorkspaceRegistryError("workspace_id must be a non-empty string")
    if Path(workspace_id).name != workspace_id or "/" in workspace_id or "\\" in workspace_id:
        raise WorkspaceRegistryError("workspace_id must not contain path separators")
    return workspace_id


def _normalize_existing_directory(path: str | os.PathLike[str]) -> Path:
    try:
        resolved = Path(path).expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise WorkspaceRegistryError(f"workspace_root does not exist: {path}") from exc
    if not resolved.is_dir():
        raise WorkspaceRegistryError(f"workspace_root is not a directory: {resolved}")
    return resolved


def _root_key(path: str | os.PathLike[str]) -> str:
    return os.path.normcase(str(Path(path).expanduser().resolve(strict=False)))


class WorkspaceRegistry:
    """Disk-backed registry of external project roots."""

    def __init__(self, storage_root: str | os.PathLike[str] | None = None) -> None:
        root = Path(storage_root) if storage_root is not None else default_storage_root()
        self.storage_root = root.expanduser().resolve(strict=False)
        self.workspaces_dir = self.storage_root / "workspaces"
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)

    def _record_path(self, workspace_id: str) -> Path:
        safe_id = _safe_workspace_id(workspace_id)
        return self.workspaces_dir / f"{safe_id}.json"

    def _load_path(self, path: Path) -> WorkspaceRegistration:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceRegistryError(f"cannot read workspace record: {path}") from exc
        if not isinstance(raw, dict):
            raise WorkspaceRegistryError(f"workspace record is not an object: {path}")
        if raw.get("schema_version") != SCHEMA_VERSION:
            raise WorkspaceRegistryError(
                f"unsupported workspace schema_version in {path}: "
                f"{raw.get('schema_version')!r}"
            )
        try:
            return WorkspaceRegistration(**raw)
        except (TypeError, ValueError) as exc:
            raise WorkspaceRegistryError(f"invalid workspace record: {path}") from exc

    def _write(self, record: WorkspaceRegistration) -> None:
        path = self._record_path(record.workspace_id)
        temp = self.workspaces_dir / f".{record.workspace_id}.{new_id('tmp')}.tmp"
        payload = json.dumps(record_to_dict(record), ensure_ascii=False, indent=2)
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise WorkspaceRegistryError(f"cannot persist workspace record: {path}") from exc

    def list(self) -> list[WorkspaceRegistration]:
        return [self._load_path(path) for path in sorted(self.workspaces_dir.glob("*.json"))]

    def get(self, workspace_id: str) -> WorkspaceRegistration:
        path = self._record_path(workspace_id)
        if not path.is_file():
            raise WorkspaceRegistryError(f"unknown workspace_id: {workspace_id}")
        return self._load_path(path)

    def find_by_root(
        self, workspace_root: str | os.PathLike[str]
    ) -> WorkspaceRegistration | None:
        target_key = _root_key(_normalize_existing_directory(workspace_root))
        for record in self.list():
            if _root_key(record.workspace_root) == target_key:
                return record
        return None
    def register(
        self,
        display_name: str,
        workspace_root: str | os.PathLike[str],
        *,
        workspace_id: str | None = None,
    ) -> WorkspaceRegistration:
        if not isinstance(display_name, str) or not display_name.strip():
            raise WorkspaceRegistryError("display_name must be a non-empty string")

        resolved_root = _normalize_existing_directory(workspace_root)
        existing = self.find_by_root(resolved_root)
        if existing is not None:
            if workspace_id is not None and workspace_id != existing.workspace_id:
                raise WorkspaceRegistryError(
                    "workspace_root is already registered under another workspace_id"
                )
            return existing

        chosen_id = _safe_workspace_id(workspace_id) if workspace_id else new_id("ws")
        if self._record_path(chosen_id).exists():
            raise WorkspaceRegistryError(f"workspace_id already exists: {chosen_id}")

        record = WorkspaceRegistration(
            workspace_id=chosen_id,
            display_name=display_name.strip(),
            workspace_root=str(resolved_root),
        )
        self._write(record)
        return record
