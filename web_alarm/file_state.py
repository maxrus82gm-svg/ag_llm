"""Physical byte-state observation for Web Alarm operation contracts (RC-1).

Authority is SHA-256 over the exact on-disk bytes plus size. Line-ending style,
BOM presence and the EOL-normalized hash are diagnostic metadata only: they may
explain a mismatch but never turn a byte mismatch into a match.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

UTF8_BOM = b"\xef\xbb\xbf"
_CHUNK_SIZE = 64 * 1024
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400

AUTHORITY_FIELDS = ("exists", "size", "sha256")


class FileStateError(RuntimeError):
    """Raised when a target cannot be observed as a regular file."""


@dataclass(frozen=True, slots=True)
class FileState:
    exists: bool
    size: int | None = None
    sha256: str | None = None
    eol: str | None = None
    bom: bool | None = None
    normalized_sha256: str | None = None

    def authority(self) -> dict[str, Any]:
        return {"exists": self.exists, "size": self.size, "sha256": self.sha256}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _Digest:
    """Streaming raw + diagnostic digest; CRLF pairs are never split across chunks."""

    def __init__(self) -> None:
        self.raw = hashlib.sha256()
        self.normalized = hashlib.sha256()
        self.size = 0
        self.crlf = 0
        self.lf = 0
        self.cr = 0
        self.bom: bool | None = None
        self._carry = b""

    def update(self, chunk: bytes) -> None:
        self.raw.update(chunk)
        self.size += len(chunk)
        data = self._carry + chunk
        if self.bom is None:
            if len(data) < len(UTF8_BOM) and UTF8_BOM.startswith(data):
                self._carry = data
                return
            self.bom = data.startswith(UTF8_BOM)
            if self.bom:
                data = data[len(UTF8_BOM):]
        if data.endswith(b"\r"):
            self._carry = b"\r"
            data = data[:-1]
        else:
            self._carry = b""
        self._consume(data)

    def _consume(self, data: bytes) -> None:
        self.crlf += data.count(b"\r\n")
        self.lf += data.count(b"\n")
        self.cr += data.count(b"\r")
        self.normalized.update(data.replace(b"\r\n", b"\n"))

    def finish(self) -> FileState:
        if self.bom is None:
            self.bom = False
        self._consume(self._carry)
        self._carry = b""
        lone_lf = self.lf - self.crlf
        lone_cr = self.cr - self.crlf
        if self.crlf == 0 and lone_lf == 0 and lone_cr == 0:
            eol = "none"
        elif lone_lf == 0 and lone_cr == 0:
            eol = "crlf"
        elif self.crlf == 0 and lone_cr == 0:
            eol = "lf"
        else:
            eol = "mixed"
        return FileState(
            exists=True,
            size=self.size,
            sha256=self.raw.hexdigest(),
            eol=eol,
            bom=self.bom,
            normalized_sha256=self.normalized.hexdigest(),
        )


def observe_bytes(data: bytes) -> FileState:
    """State that a file would have if it contained exactly ``data``."""
    if not isinstance(data, (bytes, bytearray)):
        raise FileStateError("payload must be bytes")
    digest = _Digest()
    digest.update(bytes(data))
    return digest.finish()


def is_link_or_reparse_point(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def observe_path(path: str | os.PathLike[str]) -> FileState:
    """Read the current physical state of one file target without following links."""
    target = Path(path)
    try:
        info = os.lstat(target)
    except FileNotFoundError:
        return FileState(exists=False)
    except OSError as exc:
        raise FileStateError(f"cannot stat target: {target}") from exc
    if is_link_or_reparse_point(target):
        raise FileStateError(f"target is a link or reparse point: {target}")
    if not stat.S_ISREG(info.st_mode):
        raise FileStateError(f"target is not a regular file: {target}")
    digest = _Digest()
    try:
        with target.open("rb") as handle:
            while True:
                chunk = handle.read(_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise FileStateError(f"cannot read target: {target}") from exc
    return digest.finish()


def authority_of(state: Mapping[str, Any] | FileState | None) -> dict[str, Any] | None:
    """Return only the authority fields of a state mapping."""
    if state is None:
        return None
    if isinstance(state, FileState):
        return state.authority()
    return {name: state.get(name) for name in AUTHORITY_FIELDS}


def same_authority(
    left: Mapping[str, Any] | FileState | None,
    right: Mapping[str, Any] | FileState | None,
) -> bool:
    if left is None or right is None:
        return False
    return authority_of(left) == authority_of(right)


def eol_only_drift(
    expected: Mapping[str, Any] | FileState | None,
    observed: Mapping[str, Any] | FileState | None,
) -> bool:
    """Diagnostic: bytes differ but match after CRLF/BOM normalization."""
    if expected is None or observed is None:
        return False
    if same_authority(expected, observed):
        return False

    def _get(state: Any, name: str) -> Any:
        return getattr(state, name) if isinstance(state, FileState) else state.get(name)

    left = _get(expected, "normalized_sha256")
    right = _get(observed, "normalized_sha256")
    return (
        _get(expected, "exists") is True
        and _get(observed, "exists") is True
        and left is not None
        and left == right
    )
