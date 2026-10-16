"""Content-addressed immutable payload storage for operation contracts (RC-1).

Blobs live inside the machine-local TASK directory (``payloads/<sha256>.bin``)
and therefore move with the TASK from active to completed. A blob is written
once and never overwritten; every read verifies size and SHA-256 and fails
closed on any mismatch. Payload bytes are never copied into events or reports.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import new_id
from .storage_policy import MAX_PAYLOAD_BYTES, PAYLOAD_RETENTION, is_within
from .task_store import TaskStore, TaskStoreError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PayloadStoreError(RuntimeError):
    """Raised when a payload cannot be stored or addressed safely."""


class PayloadIntegrityError(PayloadStoreError):
    """Raised when stored payload bytes do not match their reference."""


class PayloadScopeError(PayloadStoreError):
    """Raised when a payload violates the size or storage-location policy."""


def validate_payload_ref(ref: Any) -> dict[str, Any]:
    if not isinstance(ref, Mapping):
        raise PayloadStoreError("payload_ref must be an object")
    sha = ref.get("sha256")
    size = ref.get("size")
    if not isinstance(sha, str) or not _SHA256_RE.match(sha):
        raise PayloadStoreError("payload_ref.sha256 must be lowercase hex SHA-256")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise PayloadStoreError("payload_ref.size must be a non-negative integer")
    return {"sha256": sha, "size": size}


class PayloadStore:
    DIRECTORY = "payloads"

    def __init__(
        self,
        storage_root: str | os.PathLike[str] | None = None,
        *,
        max_bytes: int = MAX_PAYLOAD_BYTES,
    ) -> None:
        self.tasks = TaskStore(storage_root)
        self.max_bytes = max_bytes

    def _directory(self, task_id: str, *, active_only: bool) -> Path:
        try:
            task_dir = self.tasks.task_directory(task_id, active_only=active_only)
        except TaskStoreError as exc:
            raise PayloadStoreError(str(exc)) from exc
        return task_dir / self.DIRECTORY

    def _blob_path(self, task_id: str, sha256: str, *, active_only: bool) -> Path:
        return self._directory(task_id, active_only=active_only) / f"{sha256}.bin"

    def _verify_blob(self, path: Path, ref: Mapping[str, Any]) -> bytes:
        if not path.is_file():
            raise PayloadIntegrityError(f"payload blob is missing: {ref['sha256']}")
        try:
            size = path.stat().st_size
            if size != ref["size"] or size > self.max_bytes:
                raise PayloadIntegrityError(
                    f"payload blob size mismatch: {ref['sha256']}"
                )
            data = path.read_bytes()
        except OSError as exc:
            raise PayloadIntegrityError(
                f"payload blob is unreadable: {ref['sha256']}"
            ) from exc
        if len(data) != ref["size"] or hashlib.sha256(data).hexdigest() != ref["sha256"]:
            raise PayloadIntegrityError(f"payload blob hash mismatch: {ref['sha256']}")
        return data

    def put(
        self,
        task_id: str,
        data: bytes,
        *,
        forbidden_roots: Iterable[Path] = (),
    ) -> dict[str, Any]:
        if not isinstance(data, (bytes, bytearray)):
            raise PayloadStoreError("payload must be bytes")
        data = bytes(data)
        if len(data) > self.max_bytes:
            raise PayloadScopeError(
                f"payload exceeds size limit: {len(data)} > {self.max_bytes} bytes"
            )
        directory = self._directory(task_id, active_only=True)
        for root in forbidden_roots:
            if is_within(directory, Path(root)):
                raise PayloadScopeError(
                    "payload storage must be outside the workspace/vault"
                )
        ref = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
        path = directory / f"{ref['sha256']}.bin"
        if path.exists():
            self._verify_blob(path, ref)
            return self.reference(ref["sha256"], ref["size"])
        directory.mkdir(parents=True, exist_ok=True)
        temp = directory / f".{ref['sha256']}.{new_id('tmp')}.tmp"
        try:
            with temp.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            if not path.exists():
                raise PayloadStoreError(
                    f"cannot persist payload blob: {ref['sha256']}"
                ) from exc
        self._verify_blob(path, ref)
        return self.reference(ref["sha256"], ref["size"])

    @staticmethod
    def reference(sha256: str, size: int) -> dict[str, Any]:
        """The durable reference stored in an operation contract."""
        return {
            "sha256": sha256,
            "size": size,
            "store": "task_payloads",
            "retention": PAYLOAD_RETENTION,
        }

    def read(self, task_id: str, ref: Any) -> bytes:
        checked = validate_payload_ref(ref)
        path = self._blob_path(task_id, checked["sha256"], active_only=False)
        return self._verify_blob(path, checked)

    def verify(self, task_id: str, ref: Any) -> None:
        self.read(task_id, ref)
