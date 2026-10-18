"""WA4-R repair CLAUDE-WA4-R-AUD01T02B-REPAIR-001: global transport evidence framing and
concurrency (AUD-01T) and microtask lifecycle steps that must not persist state their history
cannot record (AUD-02b).

Oracles read raw bytes: every storage file outside ``locks/``, JSONL logs split on the physical
LF only, the workspace target. Separator characters are real code points (chr()), never escape
sequences. Concurrency cases use separate Python processes that start on a file barrier.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
TASK = "task_t02b"
PRE = b"T02B-PRE\r\n\x01"
SEPARATORS = (chr(0x85), chr(0x2028), chr(0x2029))
LONE_SURROGATE = chr(0xD800)

CHILD = r'''
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from web_alarm.server import ApiError, WebAlarmApi
storage, go, mode, wid, count, task = Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
api = WebAlarmApi(storage)
deadline = time.monotonic() + 60
while not go.exists():
    if time.monotonic() > deadline:
        sys.exit(5)
    time.sleep(0.001)
errors, replies = [], []
for n in range(count):
    try:
        if mode == "transport":
            api.dispatch("POST", "/transport/events", {"event_type": "REMOTE_OFFLINE", "event_id": f"t_{wid}_{n}",
                         "payload": {"w": wid, "n": n, "note": "x" + chr(0x2028) * (n % 3)}})
        elif mode == "same_id":
            _, reply = api.dispatch("POST", "/transport/events", {"event_type": "REMOTE_RECOVERED", "event_id": "t_same",
                                    "payload": {"note": "same" + chr(0x2029)}})
            replies.append(reply["event"]["recorded_at"])
        elif mode == "report":
            api.dispatch("POST", "/microtasks/m1/report", {"task_id": task, "report": f"r_{wid}" + chr(0x85) + f"_{n}"})
        elif mode == "cycle":
            for status in ("DONE", "FAILED_VERIFICATION", "ACTIVE"):
                api.dispatch("POST", "/microtasks/m1/transition", {"task_id": task, "target_status": status})
    except ApiError as exc:
        errors.append([exc.status, exc.code, str(exc)[:200]])
print(json.dumps({"wid": wid, "errors": errors, "replies": sorted(set(replies))}))
'''

HOLD_LOCK = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from web_alarm.store_lock import InterProcessLock
lock = InterProcessLock(Path(sys.argv[2]), timeout=5)
lock.acquire()
Path(sys.argv[3]).write_text("held")
deadline = time.monotonic() + 30
while not Path(sys.argv[4]).exists() and time.monotonic() < deadline:
    time.sleep(0.01)
lock.release()
'''

WRITE_THEN_READ = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from web_alarm.transport_event_store import TransportEventStore
store = TransportEventStore(Path(sys.argv[2]))
if sys.argv[3] == "write":
    for index, ch in enumerate([chr(0x85), chr(0x2028), chr(0x2029)]):
        store.append("REMOTE_OFFLINE", event_id=f"fresh_{index}", error_class=f"e{ch}", payload={"note": f"a{ch}b"})
else:
    print(json.dumps([[e.event_id, e.error_class, e.payload] for e in store.read_events()], ensure_ascii=True))
'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lf_records(data: bytes) -> list[dict]:
    """Independent framing oracle: one physical LF ends one record."""
    assert data == b"" or data.endswith(b"\n"), "unterminated"
    return [json.loads(chunk) for chunk in data.split(b"\n")[:-1]]


def tolerant_records(data: bytes) -> tuple[list[dict], int, int]:
    """Raw census of a log written by racing writers: (parsed records, unparsable lines, tail bytes)."""
    chunks = data.split(b"\n")
    tail = chunks.pop()
    records, invalid = [], 0
    for chunk in chunks:
        try:
            records.append(json.loads(chunk))
        except ValueError:
            invalid += 1
    return records, invalid, len(tail)


def storage_files(storage: Path) -> dict[str, str]:
    return {p.relative_to(storage).as_posix(): sha(p.read_bytes())
            for p in sorted(storage.rglob("*"))
            if p.is_file() and p.relative_to(storage).parts[0] != "locks"}


def call(storage: Path, method: str, path: str, body=None) -> list:
    from web_alarm.server import ApiError, WebAlarmApi
    try:
        status, reply = WebAlarmApi(storage).dispatch(method, path, body)
        return [status, reply]
    except ApiError as exc:
        return [exc.status, exc.code, str(exc)]


def run_children(storage: Path, mode: str, workers: int, count: int, task: str = TASK) -> list[dict]:
    go = storage.parent / f"go_{mode}"
    procs = [subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(ROOT), str(storage), str(go), mode, str(w),
                               str(count), task], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
             for w in range(workers)]
    time.sleep(0.4)
    go.write_text("go")
    results = []
    for proc in procs:
        out, err = proc.communicate(timeout=180)
        if proc.returncode != 0:
            raise AssertionError(f"child exit {proc.returncode}: {err.decode(errors='replace')[-800:]}")
        results.append(json.loads(out.decode().strip().splitlines()[-1]))
    return results


class TransportFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wa_aud01t_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.storage = self.base / "state"
        self.facts = [{"task": "CLAUDE-WA4-R-AUD01T02B-REPAIR-001", "finding": "AUD-01T", "test": self.id()}]

    @property
    def log(self) -> Path:
        return self.storage / "transport" / "transport_events.jsonl"

    def store(self, **kwargs):
        from web_alarm.transport_event_store import TransportEventStore
        return TransportEventStore(self.storage, **kwargs)

    def seed(self, count: int = 2) -> bytes:
        store = self.store()
        for n in range(count):
            store.append("REMOTE_ONLINE", event_id=f"seed_{n}", payload={"n": n})
        return self.log.read_bytes()

    def assert_refused_unchanged(self, broken: bytes, name: str):
        """Read and append fail closed (store error, HTTP 409) and never touch the bytes."""
        from web_alarm.transport_event_store import TransportEventStoreError
        self.log.write_bytes(broken)
        with self.assertRaises(TransportEventStoreError, msg=f"{name}: read"):
            self.store().read_events()
        with self.assertRaises(TransportEventStoreError, msg=f"{name}: append"):
            self.store().append("REMOTE_OFFLINE", event_id=f"must_not_{name}")
        get = call(self.storage, "GET", "/transport/events")
        post = call(self.storage, "POST", "/transport/events", {"event_type": "REMOTE_OFFLINE"})
        self.facts.append({name: {"get": get[:2], "post": post[:2]}})
        self.assertEqual(get[:2], [409, "transport_evidence_error"], name)
        self.assertEqual(post[:2], [409, "transport_evidence_error"], name)
        self.assertEqual(self.log.read_bytes(), broken, f"{name}: refused access changed or repaired the log")


class TransportFramingTests(TransportFixture):
    """AUD-01T: one physical LF is one transport record; separators inside JSON strings are data."""

    def test_http_separator_text_keeps_transport_evidence_readable_and_appendable(self):
        first = call(self.storage, "POST", "/transport/events", {
            # text fields are stripped by the API (U+2028 is whitespace): keep the separator inside
            "event_type": "REMOTE_OFFLINE", "event_id": "sep_1", "error_class": "dr" + SEPARATORS[1] + "op",
            "payload": {"note": "a" + "".join(SEPARATORS) + "b", "key" + SEPARATORS[2]: SEPARATORS[0]}})
        listing = call(self.storage, "GET", "/transport/events")
        second = call(self.storage, "POST", "/transport/events",
                      {"event_type": "REMOTE_RECOVERED", "event_id": "sep_2", "payload": {"note": "plain"}})
        again = call(self.storage, "GET", "/transport/events")
        data = self.log.read_bytes()
        self.facts.append({"first": first[:2] if first[0] != 201 else 201, "get": listing[0],
                           "second": second[0], "lf_records": data.count(b"\n")})
        self.assertEqual(first[0], 201)
        self.assertEqual(listing[0], 200, "one accepted transport event made all transport evidence unreadable")
        self.assertEqual(second[0], 201, "one accepted transport event blocked every later transport append")
        self.assertEqual(again[0], 200)
        events = again[1]["events"]
        self.assertEqual([e["event_id"] for e in events], ["sep_1", "sep_2"])
        self.assertEqual(events[0]["error_class"], "dr" + SEPARATORS[1] + "op")
        self.assertEqual(events[0]["payload"], {"note": "a" + "".join(SEPARATORS) + "b",
                                                "key" + SEPARATORS[2]: SEPARATORS[0]})
        raw = lf_records(data)
        self.assertEqual([r["event_id"] for r in raw], ["sep_1", "sep_2"])
        self.assertEqual(raw[0]["payload"], events[0]["payload"])
        for ch in SEPARATORS:
            self.assertNotIn(ch.encode("utf-8"), data, "raw line separator written into the transport log")

    def test_pre_repair_raw_separator_and_crlf_records_stay_readable_and_appendable(self):
        from web_alarm.models import SCHEMA_VERSION
        legacy = []
        for index, ch in enumerate(SEPARATORS):
            record = {"event_id": f"legacy_{index}", "event_type": "REMOTE_OFFLINE", "task_id": None,
                      "microtask_id": None, "operation_id": None, "remote_call_kind": None, "error_class": None,
                      "process_id": None, "process_start_time": None, "payload": {"note": f"x{ch}y"},
                      "recorded_at": "2026-10-16T00:00:00+00:00", "schema_version": SCHEMA_VERSION}
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            legacy.append(line + (b"\r\n" if index == 1 else b"\n"))  # one CRLF record (hand-edited log)
        self.storage.mkdir(parents=True)
        self.store()
        prefix = b"".join(legacy)
        self.log.write_bytes(prefix)
        events = self.store().read_events()
        self.assertEqual([e.payload["note"] for e in events], [f"x{ch}y" for ch in SEPARATORS],
                         "a valid pre-repair record (raw separator, CRLF) became unreadable")
        self.assertEqual(self.log.read_bytes(), prefix, "reading changed bytes")
        self.store().append("REMOTE_RECOVERED", event_id="after_legacy", payload={"note": "n" + SEPARATORS[1]})
        after = self.log.read_bytes()
        self.assertTrue(after.startswith(prefix), "append rewrote the existing prefix")
        self.assertEqual(lf_records(after[len(prefix):])[0]["payload"], {"note": "n" + SEPARATORS[1]})
        self.assertEqual([e.event_id for e in self.store().read_events()][-1], "after_legacy")

    def test_unterminated_tail_is_refused_never_spliced(self):
        good = self.seed()
        self.assert_refused_unchanged(good[:-1], "complete_record_without_lf")
        self.assert_refused_unchanged(good[:-20], "partial_json_tail")

    def test_corrupt_log_fails_closed_without_writes(self):
        good = self.seed()
        first = good.index(b"\n") + 1
        cases = {
            "invalid_json_line": good[:first] + b"{not json\n" + good[first:],
            "blank_line": good[:first] + b"\n" + good[first:],
            "invalid_utf8": good[:first] + b"\xff\xfe\n" + good[first:],
            "two_records_on_one_line": good[:first - 1] + b"\r" + good[first:],
            "utf8_bom": b"\xef\xbb\xbf" + good,
        }
        for name, broken in cases.items():
            with self.subTest(name):
                self.assert_refused_unchanged(broken, name)

    def test_replay_identity_and_conflict_survive_reopen(self):
        from web_alarm.transport_event_store import TransportEventConflictError
        payload = {"note": "r" + SEPARATORS[0] + SEPARATORS[1]}
        first = self.store().append("REMOTE_OFFLINE", event_id="replay_1", error_class="c" + SEPARATORS[2],
                                    payload=payload)
        before = self.log.read_bytes()
        again = self.store().append("REMOTE_OFFLINE", event_id="replay_1", error_class="c" + SEPARATORS[2],
                                    payload=payload)
        self.assertEqual(again.recorded_at, first.recorded_at, "same-evidence replay was not recognized")
        self.assertEqual(self.log.read_bytes(), before, "replay appended a duplicate")
        with self.assertRaises(TransportEventConflictError):
            self.store().append("REMOTE_OFFLINE", event_id="replay_1", payload={"note": "different"})
        http = call(self.storage, "POST", "/transport/events",
                    {"event_type": "REMOTE_OFFLINE", "event_id": "replay_1", "payload": {"note": "other"}})
        self.assertEqual(http[:2], [409, "transport_evidence_error"])
        self.assertEqual(self.log.read_bytes(), before, "a conflicting reuse changed the log")

    def test_fresh_processes_write_and_read_separator_events(self):
        self.storage.mkdir(parents=True)
        for mode in ("write", "read"):
            proc = subprocess.run([sys.executable, "-B", "-c", WRITE_THEN_READ, str(ROOT), str(self.storage), mode],
                                  capture_output=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode(errors="replace")[-800:])
        got = json.loads(proc.stdout.decode().strip().splitlines()[-1])
        self.assertEqual(got, [[f"fresh_{i}", f"e{ch}", {"note": f"a{ch}b"}] for i, ch in enumerate(SEPARATORS)])

    def test_unencodable_text_is_refused_before_any_write(self):
        self.storage.mkdir(parents=True)
        reply = call(self.storage, "POST", "/transport/events",
                     {"event_type": "REMOTE_OFFLINE", "payload": {"note": "bad" + LONE_SURROGATE}})
        self.facts.append({"http": reply[:2]})
        self.assertEqual(reply[:2], [400, "invalid_value"])
        self.assertFalse(self.log.exists(), "a refused event created or touched the transport log")
        good = self.seed(1)
        reply = call(self.storage, "POST", "/transport/events",
                     {"event_type": "REMOTE_OFFLINE", "error_class": "e" + LONE_SURROGATE})
        self.assertEqual(reply[:2], [400, "invalid_value"])
        self.assertEqual(self.log.read_bytes(), good)

    def test_read_on_fresh_storage_creates_nothing(self):
        reply = call(self.storage, "GET", "/transport/events")
        self.assertEqual(reply[0], 200)
        self.assertEqual(reply[1]["events"], [])
        self.assertFalse(self.log.exists())
        self.assertFalse((self.storage / "locks" / "transport").exists(), "a read created a lock file")


class TransportDurabilityTests(TransportFixture):
    """AUD-01T: concurrent writers, failed durable append and lock refusal."""

    def test_concurrent_processes_lose_no_transport_event(self):
        self.storage.mkdir(parents=True)
        workers, count = 6, 40
        results = run_children(self.storage, "transport", workers, count)
        errors = [e for r in results for e in r["errors"]]
        data = self.log.read_bytes()
        records, invalid, tail = tolerant_records(data)  # raw oracle: every line one complete JSON record
        self.facts.append({"errors": len(errors), "first_errors": errors[:3], "lf_lines": data.count(b"\n"),
                           "parsed": len(records), "invalid_lines": invalid, "tail_bytes": tail})
        self.assertEqual((invalid, tail), (0, 0), "racing appends tore or spliced transport records")
        self.assertEqual(errors, [])
        ids = [r["event_id"] for r in records]
        self.assertEqual(len(ids), len(set(ids)), "an event was written twice")
        self.assertEqual(sorted(ids), sorted(f"t_{w}_{n}" for w in range(workers) for n in range(count)),
                         "concurrent appends lost or overwrote transport evidence")
        for w in range(workers):  # each writer's own order is preserved
            self.assertEqual([r["payload"]["n"] for r in records if r["payload"]["w"] == w], list(range(count)))

    def test_concurrent_replay_of_one_event_id_is_stored_once(self):
        self.storage.mkdir(parents=True)
        results = run_children(self.storage, "same_id", 5, 6)
        errors = [e for r in results for e in r["errors"]]
        replies = sorted({stamp for r in results for stamp in r["replies"]})
        records, invalid, tail = tolerant_records(self.log.read_bytes())
        self.facts.append({"errors": len(errors), "first_errors": errors[:3], "records": len(records),
                           "invalid_lines": invalid, "tail_bytes": tail, "distinct_replies": replies})
        self.assertEqual((invalid, tail), (0, 0), "racing replays tore or spliced transport records")
        self.assertEqual(errors, [])
        self.assertEqual([r["event_id"] for r in records], ["t_same"], "one event_id stored more than once")
        self.assertEqual(replies, [records[0]["recorded_at"]], "a replay returned a record that is not stored")

    def test_failed_durable_append_is_rolled_back_and_reported(self):
        from web_alarm.transport_event_store import TransportEventStoreError
        good = self.seed()
        real = os.fsync
        calls = []

        def failing_once(fd):
            calls.append(fd)
            if len(calls) == 1:
                raise OSError(28, "injected: no space left on device")
            return real(fd)

        with mock.patch("web_alarm.transport_event_store.os.fsync", side_effect=failing_once):
            with self.assertRaises(TransportEventStoreError) as caught:
                self.store().append("REMOTE_OFFLINE", event_id="lost_fsync", payload={"n": 9})
        self.facts.append({"error": str(caught.exception), "fsync_calls": len(calls)})
        self.assertEqual(self.log.read_bytes(), good, "a failed durable append left its bytes in the log")
        self.assertNotIn("lost_fsync", [e.event_id for e in self.store().read_events()])
        self.store().append("REMOTE_OFFLINE", event_id="after_failure")
        self.assertEqual([r["event_id"] for r in lf_records(self.log.read_bytes())],
                         ["seed_0", "seed_1", "after_failure"])

    def test_lock_held_by_another_process_refuses_without_writing(self):
        from web_alarm.transport_event_store import TransportEventStoreError
        good = self.seed(1)
        store = self.store(lock_timeout=0.3)
        lock_path = getattr(store, "lock_path", self.storage / "locks" / "transport" / "transport_events.lock")
        held, release = self.base / "held", self.base / "release"
        holder = subprocess.Popen([sys.executable, "-B", "-c", HOLD_LOCK, str(ROOT), str(lock_path), str(held),
                                   str(release)])
        try:
            deadline = time.monotonic() + 30
            while not held.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(held.exists())
            with self.assertRaises(TransportEventStoreError):
                store.append("REMOTE_OFFLINE", event_id="blocked")
            self.assertEqual(self.log.read_bytes(), good, "an append wrote while another process held the lock")
        finally:
            release.write_text("go")
            holder.wait(timeout=60)
        store.append("REMOTE_OFFLINE", event_id="after_release")
        self.assertEqual([r["event_id"] for r in lf_records(self.log.read_bytes())], ["seed_0", "after_release"])


class MicrotaskFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wa_aud02b_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.facts = [{"task": "CLAUDE-WA4-R-AUD01T02B-REPAIR-001", "finding": "AUD-02b", "test": self.id()}]
        self.storage = self.build("main", "ACTIVE")

    def build(self, name: str, upto: str) -> Path:
        """A fresh disposable fixture whose m1 stands at ``upto`` (healthy history)."""
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        storage, project = self.base / name / "state", self.base / name / "project"
        project.mkdir(parents=True)
        (project / "data.bin").write_bytes(PRE)
        WorkspaceRegistry(storage).register("t02b", project, workspace_id="ws_t02b")
        tasks = TaskStore(storage)
        tasks.create_task("ws_t02b", "t02b", "synthetic RAW TASK for AUD-02b", "repair", task_id=TASK)
        tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
        if upto == "PLANNED":
            from web_alarm.event_checkpoint_store import EventCheckpointStore
            EventCheckpointStore(storage).append_event(TASK, "FIXTURE_SEED")  # a history to damage
            return storage
        machine = ServerStateMachine(storage)
        machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        steps = {"BACKUP_VERIFIED": [], "READY": ["READY"], "ACTIVE": ["READY", "ACTIVE"],
                 "DONE": ["READY", "ACTIVE", "DONE"],
                 "FAILED_VERIFICATION": ["READY", "ACTIVE", "DONE", "FAILED_VERIFICATION"],
                 "UNKNOWN_AFTER_DISCONNECT": ["READY", "ACTIVE", "UNKNOWN_AFTER_DISCONNECT"]}[upto]
        for step in steps:
            machine.transition(TASK, "m1", step)
        return storage

    @staticmethod
    def task_dir(storage: Path) -> Path:
        active = storage / "tasks" / "active" / TASK
        return active if active.is_dir() else storage / "tasks" / "completed" / TASK

    def events(self, storage: Path) -> list[dict]:
        return lf_records((self.task_dir(storage) / "events.jsonl").read_bytes())

    def status(self, storage: Path) -> str:
        return json.loads((self.task_dir(storage) / "microtasks" / "m1.json").read_bytes())["status"]

    def tear_tail(self, storage: Path) -> None:
        path = self.task_dir(storage) / "events.jsonl"
        path.write_bytes(path.read_bytes()[:-1])

    def insert_invalid_line(self, storage: Path) -> None:
        path = self.task_dir(storage) / "events.jsonl"
        data = path.read_bytes()
        first = data.index(b"\n") + 1
        path.write_bytes(data[:first] + b"{not json\n" + data[first:])

    def transition(self, storage: Path, target: str, **extra) -> list:
        return call(storage, "POST", "/microtasks/m1/transition", dict({"task_id": TASK, "target_status": target}, **extra))

    def assert_refused_without_writes(self, storage: Path, outcome: list, before: dict, label: str,
                                      expected_status: str, code=(409, "state_machine_error")):
        after = storage_files(storage)
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        self.facts.append({label: {"http": outcome[:2], "message": str(outcome[-1])[:240], "changed": changed}})
        self.assertEqual(outcome[:2], list(code), f"{label}: {outcome}")
        self.assertEqual(changed, [], f"{label}: a refused lifecycle step persisted state")
        self.assertEqual(self.status(storage), expected_status)
        self.assertEqual((storage.parent / "project" / "data.bin").read_bytes(), PRE)


class MicrotaskHistoryTests(MicrotaskFixture):
    """AUD-02b: a lifecycle step refused for unreadable history persists nothing."""

    def test_torn_history_refuses_ACTIVE_to_DONE_without_writes(self):
        self.tear_tail(self.storage)
        before = storage_files(self.storage)
        outcome = self.transition(self.storage, "DONE")
        self.assert_refused_without_writes(self.storage, outcome, before, "ACTIVE->DONE", "ACTIVE")
        self.assertIn("history", outcome[2])
        self.assertIn("nothing was written", outcome[2])

    def test_every_public_transition_is_refused_on_torn_history(self):
        cases = [
            ("BACKUP_VERIFIED", "READY", {}),
            ("READY", "ACTIVE", {}),
            ("ACTIVE", "UNKNOWN_AFTER_DISCONNECT", {}),
            ("DONE", "VERIFIED", {"verification_evidence": "checked"}),
            ("DONE", "FAILED_VERIFICATION", {}),
            ("FAILED_VERIFICATION", "ACTIVE", {}),
            ("UNKNOWN_AFTER_DISCONNECT", "RECOVERY_REQUIRED", {}),
        ]
        for start, target, extra in cases:
            with self.subTest(f"{start}->{target}"):
                storage = self.build(f"{start}_{target}", start)
                self.tear_tail(storage)
                before = storage_files(storage)
                outcome = self.transition(storage, target, **extra)
                self.assert_refused_without_writes(storage, outcome, before, f"{start}->{target}", start)

    def test_invalid_line_history_refuses_steps_and_rejections_without_writes(self):
        cases = [("allowed ACTIVE->DONE", "DONE", {}),
                 ("disallowed ACTIVE->VERIFIED", "VERIFIED", {"verification_evidence": "x"}),
                 ("stale expected_status", "DONE", {"expected_status": "READY"})]
        for index, (label, target, extra) in enumerate(cases):
            with self.subTest(label):
                storage = self.build(f"invalid_line_{index}", "ACTIVE")
                self.insert_invalid_line(storage)
                before = storage_files(storage)
                outcome = self.transition(storage, target, **extra)
                self.assert_refused_without_writes(storage, outcome, before, label, "ACTIVE")

    def test_prepare_on_unreadable_history_writes_no_restore_point(self):
        storage = self.build("prepare", "PLANNED")
        self.tear_tail(storage)
        before = storage_files(storage)
        outcome = call(storage, "POST", "/microtasks/m1/prepare",
                       {"task_id": TASK, "targets": [{"path": "data.bin", "expected_change": "edit"}]})
        self.assert_refused_without_writes(storage, outcome, before, "prepare", "PLANNED")
        self.assertFalse((self.task_dir(storage) / "microtasks" / "m1" / "restore_point").exists())

    def test_history_turning_unreadable_before_the_commit_lock_is_refused(self):
        """The readability check is repeated under the lock of the compare-and-set (every commit path)."""
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        real = EventCheckpointStore.read_events
        cases = [("ACTIVE", "DONE", {}), ("READY", "ACTIVE", {}),
                 ("DONE", "VERIFIED", {"verification_evidence": "checked"})]
        for start, target, extra in cases:
            with self.subTest(f"{start}->{target}"):
                storage = self.build(f"toctou_{target}", start)
                reads = []

                def tear_after_first_read(store, task_id, storage=storage, reads=reads):
                    result = real(store, task_id)
                    reads.append(task_id)
                    if len(reads) == 1:  # the history breaks between the entry check and the commit
                        self.tear_tail(storage)
                    return result

                before = storage_files(storage)
                with mock.patch.object(EventCheckpointStore, "read_events", tear_after_first_read):
                    outcome = self.transition(storage, target, **extra)
                after = storage_files(storage)
                changed = sorted(k for k in after if before.get(k) != after[k])
                self.facts.append({f"{start}->{target}": {"http": outcome[:2], "reads": len(reads),
                                                          "changed": changed}})
                self.assertEqual(outcome[:2], [409, "state_machine_error"], outcome)
                self.assertEqual(self.status(storage), start, "status persisted over a history known to be torn")
                self.assertEqual(changed, ["tasks/active/task_t02b/events.jsonl"], "only the injected tear may differ")

    def test_unencodable_text_is_refused_before_any_write(self):
        cases = [("ACTIVE", "DONE", {"operation_id": "op" + LONE_SURROGATE}),
                 ("DONE", "VERIFIED", {"verification_evidence": "checked" + LONE_SURROGATE})]
        for start, target, extra in cases:
            with self.subTest(f"{start}->{target}"):
                storage = self.build(f"surrogate_{target}", start)
                before = storage_files(storage)
                outcome = self.transition(storage, target, **extra)
                self.assert_refused_without_writes(storage, outcome, before, f"{start}->{target}", start,
                                                   code=(400, "invalid_value"))


class MicrotaskCommitTests(MicrotaskFixture):
    """AUD-02b: the event of a committed step is written with it; failures after commit are honest."""

    def test_healthy_steps_record_their_events(self):
        evidence = "verified" + SEPARATORS[1] + "ok"
        done = self.transition(self.storage, "DONE")
        verified = self.transition(self.storage, "VERIFIED", verification_evidence=evidence)
        self.assertEqual(done[0], 200)
        self.assertEqual(verified[0], 200)
        self.assertIs(done[1].get("event_recorded"), True)
        self.assertIs(verified[1].get("event_recorded"), True)
        transitions = [(e["payload"]["from"], e["payload"]["to"], e["payload"]["verification_evidence"])
                       for e in self.events(self.storage) if e["event_type"] == "MICROTASK_TRANSITION"]
        self.assertEqual(transitions[-2:], [("ACTIVE", "DONE", None), ("DONE", "VERIFIED", evidence)])
        self.assertEqual(self.status(self.storage), "VERIFIED")
        self.assertEqual(verified[1]["checkpoint"]["current_status"], "VERIFIED")

    def test_stale_compare_and_set_is_still_rejected_with_its_event(self):
        before = self.events(self.storage)
        outcome = self.transition(self.storage, "DONE", expected_status="READY")
        self.assertEqual(outcome[:2], [409, "transition_rejected"])
        after = self.events(self.storage)
        self.assertEqual(after[:len(before)], before)
        self.assertEqual([e["event_type"] for e in after[len(before):]], ["MICROTASK_TRANSITION_REJECTED"])
        self.assertEqual(self.status(self.storage), "ACTIVE")

    def test_plain_step_decided_on_a_stale_status_is_rejected_under_the_lock(self):
        """Deterministic stale write: another writer moves m1 after the decision, before the locked commit."""
        from web_alarm.models import MicrotaskStatus
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        real = ServerStateMachine._commit

        def newer_status_meanwhile(machine, task_id, microtask_id, *args, **kwargs):
            TaskStore(self.storage).set_microtask_status(task_id, microtask_id, MicrotaskStatus.RECOVERY_REQUIRED)
            return real(machine, task_id, microtask_id, *args, **kwargs)

        before = self.events(self.storage)
        with mock.patch.object(ServerStateMachine, "_commit", newer_status_meanwhile):
            outcome = self.transition(self.storage, "DONE")
        after = self.events(self.storage)
        self.facts.append({"http": outcome[:2], "message": str(outcome[-1])[:200]})
        self.assertEqual(outcome[:2], [409, "transition_rejected"], outcome)
        self.assertEqual(self.status(self.storage), "RECOVERY_REQUIRED", "a stale step overwrote a newer status")
        self.assertEqual([e["event_type"] for e in after[len(before):]], ["MICROTASK_TRANSITION_REJECTED"])

    def test_history_failure_after_commit_is_reported_as_committed(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
        real = EventCheckpointStore.append_event

        def refuse_transition_event(store, task_id, event_type, **kwargs):
            if event_type == "MICROTASK_TRANSITION":
                raise EventCheckpointStoreError("injected: cannot append event")
            return real(store, task_id, event_type, **kwargs)

        before = self.events(self.storage)
        with mock.patch.object(EventCheckpointStore, "append_event", refuse_transition_event):
            outcome = self.transition(self.storage, "DONE")
        self.facts.append({"http": outcome[0], "reply": {k: outcome[1].get(k) for k in
                           ("event_recorded", "history_error", "next_safe_action")} if outcome[0] == 200 else outcome})
        self.assertEqual(outcome[0], 200, f"a committed step was reported as refused: {outcome}")
        self.assertIs(outcome[1]["event_recorded"], False)
        self.assertIn("injected", outcome[1]["history_error"])
        self.assertIn("persisted", outcome[1]["next_safe_action"])
        self.assertEqual(outcome[1]["microtask"]["status"], "DONE")
        self.assertEqual(self.status(self.storage), "DONE")
        self.assertEqual(self.events(self.storage), before, "the history gained an event although append failed")

    def test_prepare_history_failure_after_commit_is_reported_as_committed(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
        storage = self.build("prepare_commit", "PLANNED")
        real = EventCheckpointStore.append_event

        def refuse_prepared_event(store, task_id, event_type, **kwargs):
            if event_type == "MICROTASK_PREPARED":
                raise EventCheckpointStoreError("injected: cannot append event")
            return real(store, task_id, event_type, **kwargs)

        before = self.events(storage)
        with mock.patch.object(EventCheckpointStore, "append_event", refuse_prepared_event):
            outcome = call(storage, "POST", "/microtasks/m1/prepare",
                           {"task_id": TASK, "targets": [{"path": "data.bin", "expected_change": "edit"}]})
        self.facts.append({"http": outcome[0], "event_recorded": outcome[1].get("event_recorded")
                           if outcome[0] == 200 else outcome})
        self.assertEqual(outcome[0], 200, f"a persisted restore point was reported as refused: {outcome}")
        self.assertIs(outcome[1]["event_recorded"], False)
        self.assertIn("injected", outcome[1]["history_error"])
        self.assertEqual(self.status(storage), "BACKUP_VERIFIED")
        self.assertTrue((self.task_dir(storage) / "microtasks" / "m1" / "restore_point" / "manifest.json").is_file())
        self.assertEqual(self.events(storage), before)

    def test_events_lock_held_elsewhere_refuses_the_append_without_writing(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
        store = EventCheckpointStore(self.storage)
        store.task_store.lock_timeout = 0.3
        path = self.task_dir(self.storage) / "events.jsonl"
        good = path.read_bytes()
        lock_path = self.storage / "locks" / "events" / f"{TASK}.lock"
        held, release = self.base / "events_held", self.base / "events_release"
        holder = subprocess.Popen([sys.executable, "-B", "-c", HOLD_LOCK, str(ROOT), str(lock_path), str(held),
                                   str(release)])
        try:
            deadline = time.monotonic() + 30
            while not held.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(held.exists())
            with self.assertRaises(EventCheckpointStoreError):
                store.append_event(TASK, "MUST_WAIT")
            self.assertEqual(path.read_bytes(), good, "an append wrote while another process held the events lock")
        finally:
            release.write_text("go")
            holder.wait(timeout=60)
        store.append_event(TASK, "AFTER_RELEASE")
        self.assertEqual(self.events(self.storage)[-1]["event_type"], "AFTER_RELEASE")

    def test_closeout_cannot_interleave_between_status_and_its_event(self):
        """VERIFIED of the last microtask: closeout must not complete the TASK in between."""
        from web_alarm.closeout import CloseoutService
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.state_machine import ServerStateMachine
        ServerStateMachine(self.storage).transition(TASK, "m1", "DONE")
        real = EventCheckpointStore.append_event
        entered, release = threading.Event(), threading.Event()

        def pausing(store, task_id, event_type, **kwargs):
            if event_type == "MICROTASK_TRANSITION" and (kwargs.get("payload") or {}).get("to") == "VERIFIED":
                entered.set()
                release.wait(20)
            return real(store, task_id, event_type, **kwargs)

        outcomes = {}

        def verify():
            outcomes["verify"] = ServerStateMachine(self.storage).transition(
                TASK, "m1", "VERIFIED", verification_evidence="checked")

        def close():
            outcomes["close"] = CloseoutService(self.storage).complete(TASK)

        with mock.patch.object(EventCheckpointStore, "append_event", pausing):
            first = threading.Thread(target=verify)
            first.start()
            self.assertTrue(entered.wait(20), "the transition never reached its event")
            second = threading.Thread(target=close)
            second.start()
            second.join(1.0)
            closed_while_paused = not second.is_alive()
            release.set()
            first.join(30)
            second.join(30)
        kinds = [(e["event_type"], (e["payload"] or {}).get("to")) for e in self.events(self.storage)]
        self.facts.append({"closed_while_paused": closed_while_paused, "tail": kinds[-3:],
                           "close": (outcomes.get("close") or {}).get("result")})
        self.assertFalse(closed_while_paused, "closeout completed the TASK between a status and its event")
        self.assertEqual(outcomes["close"]["result"], "COMPLETED")
        self.assertEqual(kinds[-2:], [("MICROTASK_TRANSITION", "VERIFIED"), ("TASK_COMPLETED", None)])


class HistoryConcurrencyTests(MicrotaskFixture):
    """AUD-02b: concurrent writers of one TASK history lose no event (status <=> event)."""

    def test_concurrent_reports_from_processes_lose_no_event(self):
        before = self.events(self.storage)
        workers, count = 6, 30
        results = run_children(self.storage, "report", workers, count)
        errors = [e for r in results for e in r["errors"]]
        data = (self.task_dir(self.storage) / "events.jsonl").read_bytes()
        records, invalid, tail = tolerant_records(data)
        self.facts.append({"errors": len(errors), "first_errors": errors[:3], "lf_lines": data.count(b"\n"),
                           "parsed": len(records), "invalid_lines": invalid, "tail_bytes": tail})
        self.assertEqual((invalid, tail), (0, 0), "racing appends tore or spliced TASK history records")
        self.assertEqual(errors, [])
        self.assertEqual(records[:len(before)], before)
        reports = sorted(r["payload"]["report"] for r in records if r["event_type"] == "REPORT")
        self.assertEqual(reports, sorted(f"r_{w}" + SEPARATORS[0] + f"_{n}" for w in range(workers) for n in range(count)),
                         "concurrent appends lost or overwrote TASK history events")

    def test_transitions_racing_with_reports_keep_every_transition_event(self):
        before = self.events(self.storage)
        cycles = 6
        go = self.storage.parent / "go_report"
        reporters = [subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(ROOT), str(self.storage), str(go),
                                       "report", str(w), "25", TASK], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for w in range(4)]
        cycler = subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(ROOT), str(self.storage), str(go), "cycle",
                                   "9", str(cycles), TASK], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(0.4)
        go.write_text("go")
        outputs = []
        for proc in reporters + [cycler]:
            out, err = proc.communicate(timeout=240)
            self.assertEqual(proc.returncode, 0, err.decode(errors="replace")[-800:])
            outputs.append(json.loads(out.decode().strip().splitlines()[-1]))
        errors = [e for o in outputs for e in o["errors"]]
        records, invalid, tail = tolerant_records((self.task_dir(self.storage) / "events.jsonl").read_bytes())
        transitions = [(r["payload"]["from"], r["payload"]["to"]) for r in records[len(before):]
                       if r["event_type"] == "MICROTASK_TRANSITION"]
        self.facts.append({"errors": len(errors), "first_errors": errors[:3], "transition_events": len(transitions),
                           "records": len(records), "invalid_lines": invalid, "tail_bytes": tail})
        self.assertEqual((invalid, tail), (0, 0), "racing appends tore or spliced TASK history records")
        self.assertEqual(errors, [])
        self.assertEqual(records[:len(before)], before)
        self.assertEqual(transitions, [("ACTIVE", "DONE"), ("DONE", "FAILED_VERIFICATION"),
                                       ("FAILED_VERIFICATION", "ACTIVE")] * cycles,
                         "a persisted status lost its history event under concurrent writers")
        self.assertEqual(sum(1 for r in records if r["event_type"] == "REPORT"), 4 * 25)
        self.assertEqual(self.status(self.storage), "ACTIVE")


if __name__ == "__main__":
    unittest.main()
