"""Minimal inter-process lock for Web Alarm persistent stores (RC-1).

This protects storage integrity (read-check-write of one store), not physical
targets: it is not the RC-3 canonical-target conflict gate or mutation CAS.
The OS releases the byte-range lock when the owning process dies, so a crashed
writer never leaves a stale lock behind.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

DEFAULT_LOCK_TIMEOUT_SECONDS = 10.0


class StoreLockTimeout(RuntimeError):
    """Raised when the store lock cannot be acquired in time."""


class InterProcessLock:
    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
        poll_interval: float = 0.005,
    ) -> None:
        self.path = Path(path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._handle = None

    def _try_lock(self) -> bool:
        assert self._handle is not None
        try:
            if os.name == "nt":
                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def acquire(self) -> None:
        if self._handle is not None:
            raise RuntimeError(f"lock is already held by this object: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+b")
        deadline = time.monotonic() + self.timeout
        while not self._try_lock():
            if time.monotonic() >= deadline:
                self._handle.close()
                self._handle = None
                raise StoreLockTimeout(f"store lock timeout: {self.path}")
            time.sleep(self.poll_interval)

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            if os.name == "nt":
                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "InterProcessLock":
        self.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()
