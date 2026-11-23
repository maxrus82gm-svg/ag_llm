"""Cross-process OS-owner guard for disposable Colibri Turn execution/recovery.

A nonblocking OS byte-range lock is held from BEFORE the ATTEMPTING transition
until the final durable outcome. A lost process releases its handle automatically.
The lock does NOT attest remote execution, prove a dead network request stopped,
authorize a retry, or replace the Workspace writer/Run Store integrity checks.
"""
from __future__ import annotations

from contextlib import contextmanager
import errno
import os
import stat

import run_store as runs


class OwnerLeaseBusy(Exception):
    pass


class OwnerLeaseUnavailable(Exception):
    pass


@contextmanager
def claim(root, run_id):
    # Exact existing Run Store path guard: no links/reparse in parent or target.
    path = runs.run_component_path(root, run_id, "colibri-owner.lock")
    fd = None
    acquired = False
    try:
        fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_BINARY", 0)
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        st = os.fstat(fd)
        checked = runs.run_component_path(root, run_id, "colibri-owner.lock")
        visible = checked.stat()
        if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or
                (st.st_dev, st.st_ino) != (visible.st_dev, visible.st_ino)):
            raise OwnerLeaseUnavailable("unsafe_owner_lock")
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as e:
                if e.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise OwnerLeaseBusy("owner_running") from None
                raise OwnerLeaseUnavailable("lock_failed") from None
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as e:
                if e.errno in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
                    raise OwnerLeaseBusy("owner_running") from None
                raise OwnerLeaseUnavailable("lock_failed") from None
        acquired = True
    except (OwnerLeaseBusy, OwnerLeaseUnavailable):
        raise
    except (OSError, ValueError):
        raise OwnerLeaseUnavailable("lock_unavailable") from None
    else:
        # Exceptions raised by the protected Turn body must not be mistaken
        # for an OS-lock acquisition failure.
        yield
    finally:
        if fd is not None:
            try:
                if acquired:
                    if os.name == "nt":
                        import msvcrt
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
