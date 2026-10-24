"""Offline operator recovery of a torn global transport event log tail (AUD-01T-R).

`TransportEventStore` fails closed when a process dies inside an append and leaves
an unterminated last record: every later read and append is refused, and nothing
repairs the log automatically. This module is the separate, explicit, two-step
operator procedure for that one situation. It is never called by the server or
the store; it runs only as ``python -m web_alarm.transport_event_recovery`` with
an explicit storage root.

1. ``inspect`` is a dry run: no write, no lock, no directory creation. It
   classifies the log and, for a torn tail only, prints a plan: source size and
   SHA-256, the valid prefix (offset, rows, SHA-256) and the excluded tail (size,
   SHA-256, kind), sealed by ``plan_fingerprint``. Event content is never shown.
2. ``apply`` needs that fingerprint and an operator reason (no force mode). Under
   the transport writer lock it re-inspects and refuses a stale or foreign plan,
   archives the exact original bytes and the tail in a new attempt directory
   (exclusive create, fsync, read-back check, read-only), writes the prefix to a
   temporary file checked by the store's own reader, re-checks the source and
   atomically replaces the log. A receipt is written next to the archive, never
   into the transport log. A repeated ``apply`` on the repaired log is
   ALREADY_APPLIED only if an attempt's archive (original, tail, plan) and its
   receipt - when there is one - agree with the current bytes; otherwise refused.

The excluded tail is never restored or re-appended: whether that event was
delivered stays unknown. A corrupt middle line, an event-id conflict, NUL bytes
in the tail or a tail that does not start a JSON object is refused, not salvaged.
Windows cannot fsync a directory, so power-loss durability is not claimed
(PWR-01): the replacement is atomic against process death, not against power loss.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
import stat
import sys
import uuid
from pathlib import Path
from typing import Any, Callable

from .models import SCHEMA_VERSION, utc_now_iso
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout
from .transport_event_store import (
    TransportEventRecord,
    TransportEventStore,
    TransportEventStoreError,
    TransportEventType,
    _request_identity,
)

PLAN_FORMAT = 1
ARCHIVE_RELATIVE_PATH = Path("transport_recovery")
TEMP_PREFIX = ".transport_events.jsonl.recovery-"
MAX_REASON_CHARS = 500

# inspect verdicts
NO_LOG = "NO_LOG"
HEALTHY = "HEALTHY"
TORN_TAIL = "TORN_TAIL"
CORRUPT_MIDDLE = "CORRUPT_MIDDLE"
AMBIGUOUS = "AMBIGUOUS"
BAD_TARGET = "BAD_TARGET"
# apply outcomes
APPLIED = "APPLIED"
ALREADY_APPLIED = "ALREADY_APPLIED"
REFUSED = "REFUSED"
FAILED = "FAILED"

_EVENT_TYPES = frozenset(item.value for item in TransportEventType)
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_PHASE_HOOK: Callable[[str], None] | None = None  # test seam only: crash/fault injection at named phases


class TransportRecoveryRefused(RuntimeError):
    """The recovery was refused before the transport log was changed."""

    def __init__(self, code: str, reason: str, **details: Any) -> None:
        super().__init__(f"{code}: {reason}")
        self.code = code
        self.reason = reason
        self.details = details


def _phase(name: str) -> None:
    if _PHASE_HOOK is not None:
        _PHASE_HOOK(name)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync(fd: int) -> None:
    os.fsync(fd)


def _replace(source: Path, target: Path) -> None:
    os.replace(source, target)


# --- target validation -----------------------------------------------------------------

def _is_reparse(path: Path) -> bool:
    info = os.lstat(path)
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & _REPARSE)


def _canonical_root(storage_root: str | os.PathLike[str]) -> Path:
    """The storage root exactly as given, refused unless it is already canonical."""
    raw = Path(storage_root)
    if not raw.is_absolute():
        raise TransportRecoveryRefused(BAD_TARGET, "storage root must be an absolute path")
    absolute = Path(os.path.abspath(raw))
    if os.path.normcase(str(raw)) != os.path.normcase(str(absolute)):
        raise TransportRecoveryRefused(BAD_TARGET, "storage root must be given in normalized form (no '.' or '..')")
    try:
        resolved = absolute.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise TransportRecoveryRefused(BAD_TARGET, f"storage root is not accessible: {type(exc).__name__}") from exc
    if os.path.normcase(str(resolved)) != os.path.normcase(str(absolute)):
        raise TransportRecoveryRefused(
            BAD_TARGET, "storage root is not canonical (junction, symlink, alias or relative part in its path)")
    if not resolved.is_dir() or _is_reparse(resolved):
        raise TransportRecoveryRefused(BAD_TARGET, "storage root is not a plain directory")
    return resolved


def _require_plain_dir(path: Path, what: str) -> None:
    if _is_reparse(path) or not path.is_dir():
        raise TransportRecoveryRefused(BAD_TARGET, f"{what} is not a plain directory")


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_ino, info.st_dev


def _read_log(events_path: Path) -> tuple[bytes, tuple[int, int]] | None:
    """Bytes and file identity of the log, or None when it does not exist."""
    try:
        before = os.lstat(events_path)
    except FileNotFoundError:
        return None
    if _is_reparse(events_path) or not stat.S_ISREG(before.st_mode):
        raise TransportRecoveryRefused(BAD_TARGET, "transport log is not a regular file")
    if before.st_nlink != 1:
        raise TransportRecoveryRefused(AMBIGUOUS, "transport log has more than one hard link")
    with events_path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        data = handle.read()
    after = os.lstat(events_path)
    if not (_identity(before) == _identity(opened) == _identity(after)) or after.st_size != len(data):
        raise TransportRecoveryRefused(BAD_TARGET, "transport log changed identity or size while it was read")
    return data, _identity(after)


# --- classification (mirrors TransportEventStore.read_events) ---------------------------

def _line_problem(chunk: bytes) -> tuple[str | None, TransportEventRecord | None]:
    """The store's per-record validation, with the reason it would refuse."""
    try:
        line = chunk.removesuffix(b"\r").decode("utf-8")
    except UnicodeDecodeError:
        return "INVALID_UTF8", None
    if not line.strip():
        return "BLANK_LINE", None
    try:
        raw = json.loads(line)
    except json.JSONDecodeError:
        return "INVALID_JSON", None
    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        return "UNKNOWN_SCHEMA", None
    if raw.get("event_type") not in _EVENT_TYPES:
        return "UNKNOWN_EVENT_TYPE", None
    try:
        raw["event_type"] = TransportEventType(raw["event_type"])
        return None, TransportEventRecord(**raw)
    except (KeyError, TypeError, ValueError):
        return "INVALID_RECORD", None


def _tail_kind(tail: bytes) -> str:
    try:
        text = tail.removesuffix(b"\r").decode("utf-8")
    except UnicodeDecodeError:
        try:
            codecs.getincrementaldecoder("utf-8")().decode(tail, final=False)
        except UnicodeDecodeError:
            return "INVALID_UTF8"
        return "TRUNCATED_UTF8"
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return "TRUNCATED_JSON"
    return "COMPLETE_JSON_WITHOUT_LF"


def classify(data: bytes) -> dict[str, Any]:
    """Pure classification of transport log bytes; never returns event content."""
    cut = data.rfind(b"\n") + 1
    prefix, tail = data[:cut], data[cut:]
    seen: dict[str, tuple[int, dict[str, Any]]] = {}
    duplicates = 0
    ids: list[str] = []
    for index, chunk in enumerate(prefix.split(b"\n")[:-1], start=1):
        problem, record = _line_problem(chunk)
        if problem is not None:
            return {"verdict": CORRUPT_MIDDLE, "line": index, "problem": problem,
                    "reason": "a complete record before the end is invalid: the log is not repairable by tail recovery"}
        identity = _request_identity(record)
        if record.event_id in seen:
            if seen[record.event_id][1] != identity:
                return {"verdict": AMBIGUOUS, "line": index, "problem": "EVENT_ID_CONFLICT",
                        "first_line": seen[record.event_id][0],
                        "reason": "one event_id has two different records: forensic review required"}
            duplicates += 1
        else:
            seen[record.event_id] = (index, identity)
        ids.append(record.event_id)
    result: dict[str, Any] = {
        "prefix": {"bytes": len(prefix), "rows": len(ids), "sha256": _sha(prefix),
                   "event_ids_sha256": _sha("\n".join(ids).encode("utf-8"))},
        "identical_duplicate_rows": duplicates,
    }
    if not tail:
        return dict(result, verdict=HEALTHY)
    tail_info = {"bytes": len(tail), "sha256": _sha(tail), "starts_at_offset": len(prefix)}
    if b"\x00" in tail:
        return dict(result, verdict=AMBIGUOUS, problem="NUL_IN_TAIL", tail=tail_info,
                    reason="NUL bytes are not left by a process dying inside one write (power loss or storage "
                           "fault suspected, PWR-01): forensic review required")
    if not tail.lstrip(b" \t").startswith(b"{"):
        return dict(result, verdict=AMBIGUOUS, problem="TAIL_IS_NOT_A_RECORD_START", tail=tail_info,
                    reason="the bytes after the last record do not start a JSON object: not a torn append")
    tail_info["kind"] = _tail_kind(tail)
    return dict(result, verdict=TORN_TAIL, tail=tail_info,
                risk="the excluded tail is an append that never completed; whether its event was delivered is "
                     "unknown and it is NOT restored; its exact bytes are kept in the archive")


# --- plan --------------------------------------------------------------------------------

def _fingerprint(plan: dict[str, Any]) -> str:
    sealed = {key: plan[key] for key in ("plan_format", "storage_root", "relative_path", "source", "prefix", "tail")}
    return _sha(json.dumps(sealed, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _inspect_root(root: Path) -> tuple[dict[str, Any], bytes | None, tuple[int, int] | None]:
    events_path = root / TransportEventStore.RELATIVE_PATH
    transport_dir = events_path.parent
    if not transport_dir.exists():
        raise TransportRecoveryRefused(BAD_TARGET, "not a Web Alarm storage root: no transport directory")
    _require_plain_dir(transport_dir, "transport directory")
    base = {"plan_format": PLAN_FORMAT, "storage_root": str(root),
            "relative_path": TransportEventStore.RELATIVE_PATH.as_posix()}
    leftovers = sorted(p.name for p in transport_dir.glob(TEMP_PREFIX + "*"))
    if leftovers:
        base["leftover_recovery_temp_files"] = len(leftovers)
    read = _read_log(events_path)
    if read is None:
        return dict(base, verdict=NO_LOG), None, None
    data, identity = read
    plan = dict(base, source={"bytes": len(data), "sha256": _sha(data)}, **classify(data))
    if plan["verdict"] == TORN_TAIL:
        plan["plan_fingerprint"] = _fingerprint(plan)
    return plan, data, identity


def inspect(storage_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Dry run: classify the log and describe the only admissible recovery. Writes nothing."""
    try:
        return _inspect_root(_canonical_root(storage_root))[0]
    except TransportRecoveryRefused as exc:
        return {"verdict": exc.code, "reason": exc.reason, **exc.details}


# --- apply -------------------------------------------------------------------------------

def _write_new(path: Path, data: bytes) -> dict[str, Any]:
    """Exclusive create, full write, fsync, read back: never overwrites anything."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
        _fsync(fd)
    finally:
        os.close(fd)
    if path.read_bytes() != data:
        raise OSError(f"read-back of {path.name} does not match the written bytes")
    return {"bytes": len(data), "sha256": _sha(data)}


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=1, sort_keys=True) + "\n").encode("ascii")


def _archive_base(root: Path, fingerprint: str) -> Path:
    base = root / ARCHIVE_RELATIVE_PATH
    for level in (base, base / fingerprint[:16]):
        if level.exists():
            _require_plain_dir(level, f"archive directory {level.name}")
    return base / fingerprint[:16]


def _receipt_agrees(attempt: Path, plan: dict[str, Any], files: dict[str, bytes], current: bytes) -> bool:
    """No receipt (a death right after the replace leaves none), or one written for exactly this attempt.

    A receipt that is present must name this attempt and plan, record the archived bytes, and be either APPLIED
    with ``current`` as its result or a replace failure that left the log unchanged. Anything else - unreadable,
    foreign, or a failed post-check - contradicts the archive and proves nothing.
    """
    path = attempt / "receipt.json"
    if not os.path.lexists(path):
        return True
    receipt = json.loads(path.read_bytes())
    archive = receipt["archive"]
    if not (receipt["receipt_format"] == PLAN_FORMAT and receipt["attempt_id"] == attempt.name
            and receipt["plan_fingerprint"] == plan["plan_fingerprint"] and receipt["storage_root"] == plan["storage_root"]
            and receipt["relative_path"] == plan["relative_path"] and receipt["source_before"] == plan["source"]
            and receipt["prefix"] == plan["prefix"] and receipt["tail"] == plan["tail"]
            and set(archive) == set(files)
            and all(archive[name]["sha256"] == _sha(data) and archive[name]["bytes"] == len(data)
                    for name, data in files.items())):
        return False
    if receipt["outcome"] == APPLIED:
        return receipt["result"]["sha256"] == _sha(current) and receipt["result"]["bytes"] == len(current)
    return (receipt["outcome"] == FAILED and receipt["step"] == "REPLACE_FAILED"
            and receipt["transport_log_changed"] is False)


def _proven_attempts(root: Path, fingerprint: str, current: bytes) -> list[str]:
    """Attempts whose verified archive proves that ``current`` is exactly the plan's prefix."""
    plan_dir = root / ARCHIVE_RELATIVE_PATH / fingerprint[:16]
    proven = []
    if not plan_dir.is_dir() or _is_reparse(plan_dir):
        return proven
    for attempt in sorted(p for p in plan_dir.iterdir() if p.is_dir() and not _is_reparse(p)):
        try:
            files = {name: (attempt / name).read_bytes() for name in ("original.bin", "tail.bin", "plan.json")}
            plan = json.loads(files["plan.json"])
            original, tail, cut = files["original.bin"], files["tail.bin"], plan["prefix"]["bytes"]
            matches = (plan.get("plan_fingerprint") == fingerprint == _fingerprint(plan)
                       and _sha(original) == plan["source"]["sha256"]
                       and original[:cut] == current
                       and _sha(current) == plan["prefix"]["sha256"]
                       and tail == original[cut:]
                       and _sha(tail) == plan["tail"]["sha256"] and len(tail) == plan["tail"]["bytes"]
                       and _receipt_agrees(attempt, plan, files, current))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue  # an unreadable, partial, damaged or foreign attempt proves nothing
        if matches:
            proven.append(attempt.name)
    return proven


def _make_readonly(path: Path) -> None:
    os.chmod(path, stat.S_IREAD)


def apply(
    storage_root: str | os.PathLike[str],
    plan_fingerprint: str,
    reason: str,
    *,
    lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Explicit operator repair of the torn tail described by ``plan_fingerprint``.

    Raises TransportRecoveryRefused before any change of the transport log. Returns
    the receipt (outcome APPLIED or ALREADY_APPLIED) or, when a step after the
    archive failed, a FAILED result that states the exact state left behind.
    """
    if not isinstance(reason, str) or not reason.strip() or len(reason) > MAX_REASON_CHARS:
        raise TransportRecoveryRefused(REFUSED, f"an operator reason of 1..{MAX_REASON_CHARS} characters is required")
    try:
        reason.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise TransportRecoveryRefused(REFUSED, "the operator reason is not valid Unicode") from exc
    if (not isinstance(plan_fingerprint, str) or len(plan_fingerprint) != 64
            or plan_fingerprint.strip("0123456789abcdef")):  # it becomes part of an archive path
        raise TransportRecoveryRefused(REFUSED, "a full 64-character plan fingerprint from inspect is required")
    root = _canonical_root(storage_root)
    _decide(root, plan_fingerprint)  # every refusal happens before the lock file or anything else is touched
    for rel in (Path("locks"), TransportEventStore.LOCK_RELATIVE_PATH.parent):
        if (root / rel).exists():
            _require_plain_dir(root / rel, f"lock directory {rel.as_posix()}")
    lock = InterProcessLock(root / TransportEventStore.LOCK_RELATIVE_PATH, timeout=lock_timeout)
    try:
        lock.acquire()
    except (StoreLockTimeout, OSError) as exc:
        raise TransportRecoveryRefused("LOCK_TIMEOUT", f"transport writer lock not acquired: {type(exc).__name__}") from exc
    try:
        _phase("locked")
        return _apply_locked(root, plan_fingerprint, reason.strip())
    finally:
        lock.release()


def _decide(root: Path, fingerprint: str) -> tuple[dict[str, Any], bytes, tuple[int, int]] | dict[str, Any]:
    """Current plan of a matching torn tail, an ALREADY_APPLIED result, or a refusal (raised)."""
    plan, data, identity = _inspect_root(root)
    if plan["verdict"] == HEALTHY and data is not None:
        proven = _proven_attempts(root, fingerprint, data)
        if proven:
            return {"outcome": ALREADY_APPLIED, "plan_fingerprint": fingerprint, "proven_by_attempts": proven,
                    "log": {"bytes": len(data), "sha256": _sha(data)}, "transport_log_changed": False}
    if plan["verdict"] != TORN_TAIL:
        raise TransportRecoveryRefused(plan["verdict"], plan.get("reason", "the log has no recoverable torn tail"),
                                       verdict=plan["verdict"])
    if plan["plan_fingerprint"] != fingerprint:
        raise TransportRecoveryRefused("PLAN_MISMATCH", "the plan is stale or for another log: inspect again",
                                       current_plan_fingerprint=plan["plan_fingerprint"])
    return plan, data, identity


def _apply_locked(root: Path, fingerprint: str, reason: str) -> dict[str, Any]:
    decided = _decide(root, fingerprint)  # again, now that no writer can interleave
    if isinstance(decided, dict):
        return decided
    plan, data, identity = decided
    events_path = root / TransportEventStore.RELATIVE_PATH
    prefix_len = plan["prefix"]["bytes"]
    prefix, tail = data[:prefix_len], data[prefix_len:]
    attempt_id = f"{utc_now_iso().replace(':', '').replace('-', '')[:15]}-{uuid.uuid4().hex[:8]}"
    archive_base = _archive_base(root, fingerprint)
    attempt = archive_base / attempt_id
    try:
        archive_base.mkdir(parents=True, exist_ok=True)
        _require_plain_dir(archive_base, "archive directory")
        attempt.mkdir()
    except OSError as exc:
        raise TransportRecoveryRefused("ARCHIVE_FAILED", f"the archive directory could not be created "
                                       f"({type(exc).__name__}); the log was not changed") from exc
    receipt: dict[str, Any] = {
        "receipt_format": PLAN_FORMAT, "attempt_id": attempt_id, "plan_fingerprint": fingerprint,
        "storage_root": str(root), "relative_path": plan["relative_path"], "operator_reason": reason,
        "started_at": utc_now_iso(), "source_before": plan["source"], "prefix": plan["prefix"], "tail": plan["tail"],
        "risk": plan["risk"],
        "durability": "file data fsynced; directory entry not fsynced (unsupported on Windows, PWR-01)",
    }
    # 1. archive: the exact original and the tail, verified, before any change of the log
    try:
        archived = {"original.bin": _write_new(attempt / "original.bin", data)}
        _phase("archive_original_written")
        archived["tail.bin"] = _write_new(attempt / "tail.bin", tail)
        archived["plan.json"] = _write_new(attempt / "plan.json", _json_bytes(dict(plan, operator_reason=reason)))
        _phase("archive_written")
        for name, facts in archived.items():
            if _sha((attempt / name).read_bytes()) != facts["sha256"]:
                raise OSError(f"archive {name} does not verify")
            _make_readonly(attempt / name)
    except OSError as exc:
        raise TransportRecoveryRefused("ARCHIVE_FAILED", f"the original could not be archived ({type(exc).__name__}); "
                                       "the log was not changed", attempt_id=attempt_id) from exc
    receipt["archive"] = {name: dict(facts, path=(ARCHIVE_RELATIVE_PATH / fingerprint[:16] / attempt_id / name)
                                     .as_posix()) for name, facts in archived.items()}
    _phase("archive_verified")
    # 2. the prefix as a temporary file, checked by the store's own reader
    temp = events_path.parent / f"{TEMP_PREFIX}{attempt_id}.tmp"
    try:
        _write_new(temp, prefix)
        reader = TransportEventStore.__new__(TransportEventStore)
        reader.events_path = temp
        if len(reader.read_events()) != plan["prefix"]["rows"]:
            raise OSError("temporary prefix row count differs from the plan")
    except (OSError, TransportEventStoreError) as exc:
        _discard(temp)
        raise TransportRecoveryRefused("TEMP_FAILED", f"the repaired log could not be prepared ({type(exc).__name__}); "
                                       "the log was not changed; archive kept", attempt_id=attempt_id) from exc
    _phase("temp_written")
    # 3. the source must still be exactly the planned bytes
    try:
        current = _read_log(events_path)
        _require_plain_dir(events_path.parent, "transport directory")
    except TransportRecoveryRefused:
        _discard(temp)
        raise
    if current is None or current[1] != identity or current[0] != data:
        _discard(temp)
        raise TransportRecoveryRefused("SOURCE_CHANGED", "the log changed after the plan was re-checked; archive kept",
                                       attempt_id=attempt_id)
    _phase("before_replace")
    try:
        _replace(temp, events_path)
    except OSError as exc:
        _discard(temp)
        return _finish(attempt, receipt, FAILED, step="REPLACE_FAILED", error=type(exc).__name__,
                       transport_log_changed=False,
                       state="the original torn log is unchanged and still fails closed; archive kept; retry apply")
    _phase("after_replace")
    # 4. the result must be exactly the prefix and readable by the store
    try:
        result = events_path.read_bytes()
        records = TransportEventStore(root).read_events()
        ok = result == prefix and len(records) == plan["prefix"]["rows"]
        ids_sha = _sha("\n".join(r.event_id for r in records).encode("utf-8"))
        ok = ok and ids_sha == plan["prefix"]["event_ids_sha256"]
    except (OSError, TransportEventStoreError):
        ok = False
    if not ok:
        return _restore(attempt, receipt, events_path, data)
    receipt["result"] = {"bytes": len(prefix), "sha256": _sha(prefix), "rows": plan["prefix"]["rows"],
                         "read_events": "OK"}
    return _finish(attempt, receipt, APPLIED, transport_log_changed=True)


def _discard(temp: Path) -> None:
    try:
        temp.unlink()
    except OSError:
        pass  # a leftover temporary prefix is reported by inspect; it is never read as the log


def _restore(attempt: Path, receipt: dict[str, Any], events_path: Path, original: bytes) -> dict[str, Any]:
    """Post-check failed: put the archived original back so the log fails closed again."""
    back = events_path.parent / f"{TEMP_PREFIX}{receipt['attempt_id']}.restore.tmp"
    try:
        _write_new(back, original)
        _replace(back, events_path)
        state = "post-check failed; the original torn log was restored and fails closed; archive kept"
    except OSError as exc:
        _discard(back)
        state = (f"post-check failed and restoring the original failed ({type(exc).__name__}); the exact original "
                 "is in the archive: manual restore required")
    return _finish(attempt, receipt, FAILED, step="POST_CHECK_FAILED", transport_log_changed=True, state=state)


def _finish(attempt: Path, receipt: dict[str, Any], outcome: str, **facts: Any) -> dict[str, Any]:
    receipt = dict(receipt, outcome=outcome, finished_at=utc_now_iso(), **facts)
    try:
        _write_new(attempt / "receipt.json", _json_bytes(receipt))
        _make_readonly(attempt / "receipt.json")
        receipt["receipt_recorded"] = True
    except OSError as exc:
        receipt["receipt_recorded"] = False
        receipt["receipt_error"] = type(exc).__name__
    _phase("receipt_written")
    return receipt


# --- command line ------------------------------------------------------------------------

EXIT_OK, EXIT_PLAN, EXIT_REFUSED, EXIT_FAILED = 0, 10, 20, 30


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m web_alarm.transport_event_recovery",
        description="Offline operator recovery of a torn transport event log tail (AUD-01T-R). "
                    "Stop Web Alarm first. inspect is a dry run; apply needs its plan fingerprint.")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("inspect", help="dry run: classify the log and print the recovery plan")
    one.add_argument("--storage-root", required=True)
    two = sub.add_parser("apply", help="archive the original, then remove the torn tail")
    two.add_argument("--storage-root", required=True)
    two.add_argument("--plan-fingerprint", required=True)
    two.add_argument("--reason", required=True)
    two.add_argument("--lock-timeout", type=float, default=DEFAULT_LOCK_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    if args.command == "inspect":
        result = inspect(args.storage_root)
        code = {NO_LOG: EXIT_OK, HEALTHY: EXIT_OK, TORN_TAIL: EXIT_PLAN}.get(result["verdict"], EXIT_REFUSED)
    else:
        try:
            result = apply(args.storage_root, args.plan_fingerprint, args.reason, lock_timeout=args.lock_timeout)
            code = EXIT_OK if result["outcome"] in (APPLIED, ALREADY_APPLIED) else EXIT_FAILED
        except TransportRecoveryRefused as exc:
            result = {"outcome": REFUSED, "code": exc.code, "reason": exc.reason, **exc.details}
            code = EXIT_REFUSED
    sys.stdout.write(json.dumps(result, ensure_ascii=True, indent=1, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
