"""AUD-01T-R: offline operator recovery of a torn global transport log tail.

Oracles read raw bytes and hashes: the exact original and tail must be archived before the log
changes, the log must end as the exact valid prefix, nothing else may be written, and every refusal
must leave the storage tree byte-identical. Process death is real (``os._exit`` in a child at a named
phase) and the outcome is judged by a fresh process. Synthetic data in TEMP only.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from web_alarm import transport_event_recovery as rec
from web_alarm.store_lock import InterProcessLock
from web_alarm.transport_event_store import (
    TransportEventConflictError,
    TransportEventStore,
    TransportEventStoreError,
)

ROOT = Path(__file__).resolve().parent
MARKER = "PAYLOAD-MARKER-ЖЖ"  # must never leave the log/archive (stdout, plan, receipt)
REASON = "synthetic torn tail after a simulated crash"

CHILD = r'''
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
cfg = json.loads(open(sys.argv[2], encoding="utf-8").read())
from web_alarm import transport_event_recovery as rec
from web_alarm.store_lock import InterProcessLock
from web_alarm.transport_event_store import TransportEventStore, TransportEventStoreError
root, base = cfg["root"], cfg["base"]

def mark(name, **facts):
    with open(os.path.join(base, name), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(facts))

def wait_for(name, limit=60.0):
    deadline = time.monotonic() + limit
    while not os.path.exists(os.path.join(base, name)):
        if time.monotonic() > deadline:
            os._exit(91)
        time.sleep(0.01)

kind = cfg["kind"]
if kind == "apply":
    def hook(phase):
        if phase == cfg.get("die_at"):
            mark("died", phase=phase)
            os._exit(77)
        if phase == cfg.get("pause_at"):
            mark("paused", phase=phase)
            wait_for("go")
    rec._PHASE_HOOK = hook
    if cfg.get("start_flag"):
        wait_for(cfg["start_flag"])
    try:
        result = rec.apply(root, cfg["fingerprint"], cfg["reason"], lock_timeout=cfg.get("lock_timeout", 10.0))
        out = {"outcome": result["outcome"], "attempt": result.get("attempt_id"),
               "step": result.get("step"), "proven": result.get("proven_by_attempts")}
    except rec.TransportRecoveryRefused as exc:
        out = {"outcome": "REFUSED", "code": exc.code}
    mark(cfg["out"], **out)
elif kind == "hold_lock":
    lock = InterProcessLock(os.path.join(root, "locks", "transport", "transport_events.lock"))
    lock.acquire()
    mark("held")
    wait_for("release")
    lock.release()
elif kind == "writer":
    store = TransportEventStore(root)
    mark("attempting")
    errors = 0
    deadline = time.monotonic() + 30
    while True:
        try:
            store.append("REMOTE_ONLINE", event_id=cfg["event_id"], payload={"n": "writer"})
            break
        except TransportEventStoreError:
            errors += 1
            if time.monotonic() > deadline:
                mark("writer_done", ok=False, errors=errors)
                sys.exit(0)
            time.sleep(0.02)
    mark("writer_done", ok=True, errors=errors)
elif kind == "reader":
    store = TransportEventStore(root)
    seen = {}
    while not os.path.exists(os.path.join(base, "stop_reader")):
        try:
            ids = [r.event_id for r in store.read_events()]
            key = "ids:" + str(len(ids)) + ":" + "|".join(ids)
        except TransportEventStoreError as exc:
            key = "error:" + str(exc).split(":")[0]
        seen[key] = seen.get(key, 0) + 1
        if sum(seen.values()) == 1:
            mark("reading", first=key[:40])
    mark("reader_done", seen=seen)
'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree(root: Path) -> dict[str, str]:
    """Raw census of every file under root (relative path -> SHA-256).

    Lock files are recorded by size: another process may hold a byte-range lock on them.
    """
    return {p.relative_to(root).as_posix(): (f"lock:{p.stat().st_size}" if p.suffix == ".lock" else sha(p.read_bytes()))
            for p in sorted(root.rglob("*")) if p.is_file()}


def dirs(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_dir())


def _force_remove(function, path, _exc):
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    function(path)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_tailrec_"))
        self.addCleanup(self._cleanup, self.base)  # bound: subTests call setUp again for a fresh tree
        self.root = self.base / "state"
        self.root.mkdir()
        self.log = self.root / "transport" / "transport_events.jsonl"
        if not hasattr(self, "facts"):  # subTests call setUp again: keep every subTest's facts
            self.facts = [{"task": "CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001", "test": self.id()}]
        self.calls = 0

    @staticmethod
    def _cleanup(base: Path):
        for path in base.rglob("*"):
            if path.is_junction():
                os.rmdir(path)
        shutil.rmtree(base, onerror=_force_remove)

    def healthy(self, rows: int = 3) -> bytes:
        store = TransportEventStore(self.root)
        for index in range(rows):
            store.append("REMOTE_ONLINE", event_id=f"t{index}", task_id="task_x",
                         payload={"secret": MARKER, "line": "a" + chr(0x2028) + "b", "i": index})
        return self.log.read_bytes()

    def torn(self, tail: bytes, rows: int = 3) -> tuple[bytes, bytes]:
        prefix = self.healthy(rows)
        with self.log.open("ab") as handle:
            handle.write(tail)
        return prefix, self.log.read_bytes()

    def torn_record(self, rows: int = 3, keep: int = 40) -> tuple[bytes, bytes, bytes]:
        """A real record the writer would write, cut after ``keep`` bytes (no LF)."""
        record = (json.dumps({"event_id": "lost", "event_type": "PROCESS_RESTARTED", "task_id": None,
                              "microtask_id": None, "operation_id": None, "remote_call_kind": None,
                              "error_class": None, "process_id": 7, "process_start_time": None,
                              "payload": {"secret": MARKER}, "recorded_at": "2026-10-20T00:00:00+00:00",
                              "schema_version": 1}, ensure_ascii=False, separators=(",", ":"))).encode("utf-8")
        tail = record[:keep]
        prefix, original = self.torn(tail, rows)
        return prefix, tail, original

    def inspect(self) -> dict:
        return rec.inspect(self.root)

    def attempts(self) -> list[Path]:
        base = self.root / "transport_recovery"
        return sorted(p for p in base.rglob("*") if p.is_dir() and p.parent.parent == base) if base.exists() else []

    def assert_fail_closed(self, expected: bytes):
        self.assertEqual(self.log.read_bytes(), expected, "the original torn log was changed")
        with self.assertRaises(TransportEventStoreError):
            TransportEventStore(self.root).read_events()

    def child(self, cfg: dict, wait: bool = True):
        self.calls += 1
        path = self.base / f"cfg_{self.calls}.json"
        path.write_text(json.dumps(dict(cfg, root=str(self.root), base=str(self.base))), encoding="utf-8")
        proc = subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(ROOT), str(path)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not wait:
            return proc
        out, err = proc.communicate(timeout=120)
        return proc.returncode, err.decode(errors="replace")[-800:]

    def wait_marker(self, name: str, limit: float = 30.0) -> dict:
        deadline = time.monotonic() + limit
        path = self.base / name
        while not path.exists():
            if time.monotonic() > deadline:
                self.fail(f"marker {name} not reached")
            time.sleep(0.01)
        time.sleep(0.02)
        return json.loads(path.read_text(encoding="utf-8"))

    def plan_fp(self) -> str:
        plan = self.inspect()
        self.assertEqual(plan["verdict"], "TORN_TAIL", plan)
        return plan["plan_fingerprint"]


class BaselineFailClosedTests(Fixture):
    """Gate A control: the store itself refuses a torn tail and never repairs it (true before and after)."""

    def test_store_refuses_reads_and_appends_on_a_torn_tail_and_changes_nothing(self):
        _, _, original = self.torn_record()
        with self.assertRaises(TransportEventStoreError):
            TransportEventStore(self.root).read_events()
        with self.assertRaises(TransportEventStoreError):
            TransportEventStore(self.root).append("REMOTE_ONLINE", event_id="after")
        self.assertEqual(self.log.read_bytes(), original)


class InspectTests(Fixture):
    """Direction 1-3: diagnosis without mutation; tail vs middle; refusals."""

    def test_missing_log_and_missing_root_parts_are_never_created(self):
        before = tree(self.root), dirs(self.root)
        self.assertEqual(self.inspect()["verdict"], "BAD_TARGET")  # no transport directory: not a storage root
        self.assertEqual((tree(self.root), dirs(self.root)), before)
        (self.root / "transport").mkdir()
        before = tree(self.root), dirs(self.root)
        self.assertEqual(self.inspect()["verdict"], "NO_LOG")
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, "0" * 64, REASON)
        self.assertEqual(caught.exception.code, "NO_LOG")
        self.assertEqual(tree(self.root), before[0])
        self.assertNotIn("transport_recovery", dirs(self.root))

    def test_empty_and_healthy_logs_are_noop_and_apply_changes_nothing(self):
        (self.root / "transport").mkdir()
        self.log.write_bytes(b"")
        self.assertEqual(self.inspect()["verdict"], "HEALTHY")
        data = self.healthy()
        plan = self.inspect()
        self.assertEqual((plan["verdict"], plan["prefix"]["rows"], plan["source"]["sha256"]), ("HEALTHY", 3, sha(data)))
        before = tree(self.root)
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, "0" * 64, REASON)
        self.assertEqual(caught.exception.code, "HEALTHY")
        self.assertEqual(tree(self.root), before)
        self.assertEqual(self.attempts(), [])

    def test_truncated_record_plan_is_byte_exact_and_shows_no_content(self):
        prefix, tail, original = self.torn_record(keep=55)
        before = tree(self.root), dirs(self.root)
        plan = self.inspect()
        self.facts.append({"plan": plan})
        self.assertEqual(plan["verdict"], "TORN_TAIL")
        self.assertEqual(plan["source"], {"bytes": len(original), "sha256": sha(original)})
        self.assertEqual((plan["prefix"]["bytes"], plan["prefix"]["rows"], plan["prefix"]["sha256"]),
                         (len(prefix), 3, sha(prefix)))
        self.assertEqual(plan["tail"], {"bytes": len(tail), "sha256": sha(tail), "starts_at_offset": len(prefix),
                                        "kind": "TRUNCATED_JSON"})
        self.assertNotIn(MARKER, json.dumps(plan, ensure_ascii=False))
        self.assertEqual((tree(self.root), dirs(self.root)), before, "inspect wrote something")

    def test_every_tail_kind_is_classified_and_recovered_byte_exactly(self):
        record = b'{"event_id":"lost","event_type":"REMOTE_ONLINE","payload":{"s":"\xd0\x96'
        cases = {
            "TRUNCATED_JSON": b'{"event_id":"lost","event_ty',
            "COMPLETE_JSON_WITHOUT_LF": b'{"event_id":"lost","schema_version":1}',
            "COMPLETE_JSON_WITHOUT_LF_CR": b'{"event_id":"lost","schema_version":1}\r',
            "TRUNCATED_UTF8": record[:-1],
            "INVALID_UTF8": b'{"event_id":"\xff\xfe","x":1',
        }
        for name, tail in cases.items():
            with self.subTest(name):
                self.setUp()
                prefix, original = self.torn(tail)
                plan = self.inspect()
                self.assertEqual(plan["tail"]["kind"], name.removesuffix("_CR"))
                result = rec.apply(self.root, plan["plan_fingerprint"], REASON)
                self.assertEqual(result["outcome"], "APPLIED")
                self.assertEqual(self.log.read_bytes(), prefix)
                attempt = self.root / result["archive"]["original.bin"]["path"]
                self.assertEqual(attempt.read_bytes(), original)
                self.assertEqual(attempt.with_name("tail.bin").read_bytes(), tail)
                self.assertEqual(original[len(prefix):], tail)

    def test_crlf_framed_history_keeps_its_exact_prefix(self):
        (self.root / "transport").mkdir()
        rows = [json.dumps({"event_id": f"c{i}", "event_type": "REMOTE_OFFLINE", "payload": {"secret": MARKER},
                            "schema_version": 1}).encode() + b"\r\n" for i in range(3)]
        prefix = b"".join(rows)
        tail = rows[0][:-1].replace(b"c0", b"c9")  # complete record torn between CR and LF
        self.log.write_bytes(prefix + tail)
        plan = self.inspect()
        self.assertEqual((plan["verdict"], plan["tail"]["kind"], plan["prefix"]["rows"]),
                         ("TORN_TAIL", "COMPLETE_JSON_WITHOUT_LF", 3))
        rec.apply(self.root, plan["plan_fingerprint"], REASON)
        self.assertEqual(self.log.read_bytes(), prefix)
        self.assertEqual([r.event_id for r in TransportEventStore(self.root).read_events()], ["c0", "c1", "c2"])

    def test_torn_first_record_leaves_an_empty_log(self):
        (self.root / "transport").mkdir()
        self.log.write_bytes(b'{"event_id":"only","event_t')
        plan = self.inspect()
        self.assertEqual((plan["verdict"], plan["prefix"]["rows"], plan["prefix"]["bytes"]), ("TORN_TAIL", 0, 0))
        rec.apply(self.root, plan["plan_fingerprint"], REASON)
        self.assertEqual(self.log.read_bytes(), b"")
        self.assertEqual(TransportEventStore(self.root).read_events(), [])

    def test_corrupt_middle_is_refused_even_with_a_torn_tail(self):
        prefix = self.healthy(4)
        lines = prefix.split(b"\n")
        variants = {
            "INVALID_JSON": lines[1][:-5],
            "UNKNOWN_SCHEMA": lines[1].replace(b'"schema_version":1', b'"schema_version":99'),
            "UNKNOWN_EVENT_TYPE": lines[1].replace(b'"REMOTE_ONLINE"', b'"REMOTE_MAYBE"'),
            "INVALID_RECORD": lines[1].replace(b'"event_id":"t1"', b'"event_id":""'),
            "INVALID_UTF8": lines[1].replace(b'"task_x"', b'"\xff"'),
            "BLANK_LINE": b"   ",
        }
        for problem, bad in variants.items():
            with self.subTest(problem):
                data = b"\n".join([lines[0], bad, *lines[2:-1]]) + b"\n" + b'{"event_id":"x'
                self.log.write_bytes(data)
                plan = self.inspect()
                self.assertEqual((plan["verdict"], plan["problem"], plan["line"]), ("CORRUPT_MIDDLE", problem, 2))
                with self.assertRaises(rec.TransportRecoveryRefused) as caught:
                    rec.apply(self.root, "0" * 64, REASON)
                self.assertEqual(caught.exception.code, "CORRUPT_MIDDLE")
                self.assertEqual(self.log.read_bytes(), data)
        self.assertEqual(self.attempts(), [])

    def test_event_id_conflict_is_ambiguous_but_an_identical_duplicate_is_tolerated(self):
        prefix = self.healthy(2)
        first = prefix.split(b"\n")[0] + b"\n"
        self.log.write_bytes(prefix + first)
        plan = self.inspect()
        self.assertEqual((plan["verdict"], plan["identical_duplicate_rows"]), ("HEALTHY", 1))
        self.log.write_bytes(prefix + first.replace(b'"i":0', b'"i":5') + b'{"event_id":"x')
        plan = self.inspect()
        self.assertEqual((plan["verdict"], plan["problem"], plan["first_line"]), ("AMBIGUOUS", "EVENT_ID_CONFLICT", 1))

    def test_tails_not_left_by_one_interrupted_write_are_ambiguous(self):
        for name, tail in {"NUL_IN_TAIL": b'{"event_id":"x"' + b"\x00" * 16, "NUL_ONLY": b"\x00" * 64,
                           "TAIL_IS_NOT_A_RECORD_START": b'garbage"}', "CR_ONLY": b"\r"}.items():
            with self.subTest(name):
                self.setUp()
                _, original = self.torn(tail)
                plan = self.inspect()
                self.assertEqual(plan["verdict"], "AMBIGUOUS")
                self.assertIn(plan["problem"], ("NUL_IN_TAIL", "TAIL_IS_NOT_A_RECORD_START"))
                self.assertNotIn("plan_fingerprint", plan)
                self.assert_fail_closed(original)


class ApplyTests(Fixture):
    """Direction 2/4/E: archive before change, exact prefix, receipt, stale/foreign plans, idempotence."""

    def test_apply_archives_original_and_tail_before_keeping_the_exact_prefix(self):
        prefix, tail, original = self.torn_record()
        plan = self.inspect()
        result = rec.apply(self.root, plan["plan_fingerprint"], REASON)
        self.facts.append({"receipt": result})
        self.assertEqual(result["outcome"], "APPLIED")
        self.assertIs(result["receipt_recorded"], True)
        self.assertEqual(self.log.read_bytes(), prefix)
        [attempt] = self.attempts()
        files = {p.name: p.read_bytes() for p in attempt.iterdir()}
        self.assertEqual(sorted(files), ["original.bin", "plan.json", "receipt.json", "tail.bin"])
        self.assertEqual((files["original.bin"], files["tail.bin"]), (original, tail))
        self.assertEqual(sha(files["original.bin"]), plan["source"]["sha256"])
        for name in files:
            self.assertFalse(os.access(attempt / name, os.W_OK), f"{name} is writable")
        receipt = json.loads(files["receipt.json"])
        self.assertEqual(receipt["result"], {"bytes": len(prefix), "sha256": sha(prefix), "rows": 3,
                                             "read_events": "OK"})
        self.assertEqual(receipt["operator_reason"], REASON)
        for name in ("plan.json", "receipt.json"):
            self.assertNotIn(MARKER.encode("utf-8"), files[name])
            self.assertNotIn(MARKER, json.loads(files[name]).__repr__())
        # nothing else: no TASK/operation state, only the log, the lock and the archive
        self.assertEqual({p.split("/")[0] for p in tree(self.root)}, {"transport", "locks", "transport_recovery"})
        self.assertEqual(sorted(p.name for p in self.log.parent.iterdir()), ["transport_events.jsonl"])

    def test_new_appends_work_and_the_lost_event_is_not_resumed(self):
        prefix, _, _ = self.torn_record()
        rec.apply(self.root, self.plan_fp(), REASON)
        store = TransportEventStore(self.root)
        ids = [r.event_id for r in store.read_events()]
        self.assertEqual(ids, ["t0", "t1", "t2"])
        self.assertNotIn("lost", ids)
        replay = store.append("REMOTE_ONLINE", event_id="t0", task_id="task_x",
                              payload={"secret": MARKER, "line": "a" + chr(0x2028) + "b", "i": 0})
        self.assertEqual(replay.event_id, "t0")
        with self.assertRaises(TransportEventConflictError):
            store.append("REMOTE_ONLINE", event_id="t1", payload={"other": True})
        store.append("REMOTE_RECOVERED", event_id="after")
        self.assertEqual([r.event_id for r in store.read_events()], ["t0", "t1", "t2", "after"])
        self.assertTrue(self.log.read_bytes().startswith(prefix))

    def test_stale_foreign_and_malformed_plans_are_refused_without_any_write(self):
        _, _, original = self.torn_record()
        fingerprint = self.plan_fp()
        other = self.base / "other"
        shutil.copytree(self.root, other)
        self.assertNotEqual(rec.inspect(other)["plan_fingerprint"], fingerprint, "plan must bind the storage root")
        before = tree(self.root)
        flipped = fingerprint[:-1] + ("1" if fingerprint[-1] == "0" else "0")
        for args, code in (((flipped, REASON), "PLAN_MISMATCH"), ((fingerprint, " "), "REFUSED"),
                           ((fingerprint[:20], REASON), "REFUSED"), ((fingerprint, "x" * 501), "REFUSED"),
                           ((fingerprint, "bad \ud800"), "REFUSED"),
                           (("..\\..\\" + fingerprint[6:], REASON), "REFUSED"),
                           ((fingerprint.upper(), REASON), "REFUSED")):
            with self.subTest(code=code, args=args[1][:5]):
                with self.assertRaises(rec.TransportRecoveryRefused) as caught:
                    rec.apply(self.root, *args)
                self.assertEqual(caught.exception.code, code)
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(other, fingerprint, REASON)  # foreign plan, identical bytes elsewhere
        self.assertEqual(caught.exception.code, "PLAN_MISMATCH")
        with self.log.open("ab") as handle:  # the log changes after inspect
            handle.write(b'"x')
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(caught.exception.code, "PLAN_MISMATCH")
        self.assertEqual(self.log.read_bytes(), original + b'"x')
        self.assertEqual({k: v for k, v in tree(self.root).items() if k != "transport/transport_events.jsonl"},
                         {k: v for k, v in before.items() if k != "transport/transport_events.jsonl"})
        self.assertEqual(self.attempts(), [])

    def test_repeat_is_already_applied_and_after_new_appends_is_stale(self):
        prefix, _, _ = self.torn_record()
        fingerprint = self.plan_fp()
        first = rec.apply(self.root, fingerprint, REASON)
        census = tree(self.root)
        again = rec.apply(self.root, fingerprint, REASON)
        self.assertEqual((again["outcome"], again["proven_by_attempts"], again["transport_log_changed"]),
                         ("ALREADY_APPLIED", [first["attempt_id"]], False))
        self.assertEqual(tree(self.root), census, "a repeated confirmation wrote something")
        TransportEventStore(self.root).append("REMOTE_ONLINE", event_id="new")
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(caught.exception.code, "HEALTHY")
        self.assertTrue(self.log.read_bytes().startswith(prefix))

    def test_damaged_or_forged_archive_is_never_taken_as_proof(self):
        self.torn_record()
        fingerprint = self.plan_fp()
        rec.apply(self.root, fingerprint, REASON)
        [attempt] = self.attempts()
        plan_file = attempt / "plan.json"
        os.chmod(plan_file, stat.S_IWRITE | stat.S_IREAD)
        good = json.loads(plan_file.read_bytes())
        for name, content in {"garbage": b"{not json", "missing_keys": b'{"plan_fingerprint": "%s"}' % fingerprint.encode(),
                              "wrong_types": json.dumps(dict(good, source=[1])).encode(),
                              "forged_prefix": json.dumps(dict(good, prefix=dict(good["prefix"], bytes=1))).encode()}.items():
            with self.subTest(name):
                plan_file.write_bytes(content)
                census = tree(self.root)
                with self.assertRaises(rec.TransportRecoveryRefused) as caught:
                    rec.apply(self.root, fingerprint, REASON)
                self.assertEqual(caught.exception.code, "HEALTHY")
                self.assertEqual(tree(self.root), census)

    def test_cli_has_two_steps_no_force_and_prints_no_content(self):
        _, _, original = self.torn_record()

        def cli(*args):
            proc = subprocess.run([sys.executable, "-B", "-m", "web_alarm.transport_event_recovery", *args],
                                  cwd=ROOT, capture_output=True, timeout=60)
            return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode(errors="replace")

        code, out, _ = cli("inspect", "--storage-root", str(self.root))
        plan = json.loads(out)
        self.assertEqual((code, plan["verdict"]), (10, "TORN_TAIL"))
        code, _, err = cli("apply", "--storage-root", str(self.root), "--plan-fingerprint", plan["plan_fingerprint"],
                           "--reason", REASON, "--force")
        self.assertEqual(code, 2, err)  # no such option
        code, out, _ = cli("apply", "--storage-root", str(self.root), "--plan-fingerprint", "0" * 64,
                           "--reason", REASON)
        self.assertEqual((code, json.loads(out)["code"]), (20, "PLAN_MISMATCH"))
        self.assertEqual(self.log.read_bytes(), original)
        code, out, _ = cli("apply", "--storage-root", str(self.root), "--plan-fingerprint", plan["plan_fingerprint"],
                           "--reason", REASON)
        self.assertEqual((code, json.loads(out)["outcome"]), (0, "APPLIED"))
        code, out, _ = cli("inspect", "--storage-root", str(self.root))
        self.assertEqual((code, json.loads(out)["verdict"]), (0, "HEALTHY"))
        self.assertNotIn(MARKER, out)
        code, out, _ = cli("inspect", "--storage-root", "relative/path")
        self.assertEqual((code, json.loads(out)["verdict"]), (20, "BAD_TARGET"))


class ArchiveRetryProofTests(Fixture):
    """FT1-ARCHIVE-RETRY: ALREADY_APPLIED needs a complete, consistent archive, not just plan.json + original.bin.

    Every damaged case must refuse (log HEALTHY, code HEALTHY) without writing anything; the intact control after the
    loop must still be ALREADY_APPLIED, so the damage alone decides. A missing receipt stays accepted: a death right
    after the replace leaves none (CrashTests).
    """

    def applied(self):
        prefix, tail, original = self.torn_record()
        fingerprint = self.plan_fp()
        first = rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(first["outcome"], "APPLIED")
        [attempt] = self.attempts()
        return prefix, tail, original, fingerprint, first, attempt

    @staticmethod
    def writable(path: Path):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)

    @staticmethod
    def remove(path: Path):
        if path.is_dir():
            os.rmdir(path)
        elif path.exists():
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            path.unlink()

    def assert_not_proof(self, fingerprint: str):
        census, log = tree(self.root), self.log.read_bytes()
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(caught.exception.code, "HEALTHY")
        self.assertEqual(tree(self.root), census, "a refused retry wrote something")
        self.assertEqual(self.log.read_bytes(), log)

    def assert_proof(self, fingerprint: str, attempts: list[str]):
        census = tree(self.root)
        again = rec.apply(self.root, fingerprint, REASON)
        self.assertEqual((again["outcome"], again["proven_by_attempts"], again["transport_log_changed"]),
                         ("ALREADY_APPLIED", attempts, False))
        self.assertEqual(tree(self.root), census, "a repeated confirmation wrote something")

    def test_retry_proof_requires_the_archived_tail(self):
        _, tail, _, fingerprint, first, attempt = self.applied()
        path, receipt = attempt / "tail.bin", attempt / "receipt.json"
        receipt_bytes = receipt.read_bytes()
        other = bytes([tail[0] ^ 1]) + tail[1:]
        cases = {"missing": None, "empty": b"", "truncated": tail[:-1], "extended": tail + b"x",
                 "one_byte_changed": other, "directory": "dir"}
        # without a receipt (a death right after the replace) only tail.bin itself can contradict the archive
        for with_receipt in (True, False):
            if not with_receipt:
                self.remove(receipt)
            for name, content in cases.items():
                with self.subTest(name, receipt=with_receipt):
                    self.remove(path)
                    if content == "dir":
                        path.mkdir()
                    elif content is not None:
                        path.write_bytes(content)
                    self.assert_not_proof(fingerprint)
                    self.remove(path)
                    path.write_bytes(tail)
            self.assert_proof(fingerprint, [first["attempt_id"]])
        receipt.write_bytes(receipt_bytes)
        self.assert_proof(fingerprint, [first["attempt_id"]])

    def test_retry_proof_rejects_a_damaged_or_foreign_receipt(self):
        prefix, _, _, fingerprint, first, attempt = self.applied()
        path = attempt / "receipt.json"
        good_bytes = path.read_bytes()
        good = json.loads(good_bytes)
        other_sha = "0" * 64
        cases = {
            "empty_as_left_by_a_death_inside_the_write": b"",
            "garbage": b"{not json",
            "not_an_object": b"[]\n",
            "other_attempt": json.dumps(dict(good, attempt_id="20261024T000000-deadbeef")).encode(),
            "other_plan": json.dumps(dict(good, plan_fingerprint=other_sha)).encode(),
            "other_source": json.dumps(dict(good, source_before=dict(good["source_before"], sha256=other_sha))).encode(),
            "other_prefix": json.dumps(dict(good, prefix=dict(good["prefix"], bytes=1))).encode(),
            "archive_hash_mismatch": json.dumps(dict(good, archive=dict(good["archive"], **{
                "tail.bin": dict(good["archive"]["tail.bin"], sha256=other_sha)}))).encode(),
            "archive_entry_missing": json.dumps(dict(good, archive={k: v for k, v in good["archive"].items()
                                                                    if k != "tail.bin"})).encode(),
            "applied_with_other_result": json.dumps(dict(good, result=dict(good["result"], sha256=other_sha))).encode(),
            "unknown_outcome": json.dumps(dict(good, outcome="REFUSED")).encode(),
            "failed_post_check": json.dumps(dict(good, outcome="FAILED", step="POST_CHECK_FAILED",
                                                 transport_log_changed=True)).encode(),
            "directory": "dir",
        }
        self.assertEqual((good["outcome"], good["result"]["sha256"]), ("APPLIED", sha(prefix)))
        for name, content in cases.items():
            with self.subTest(name):
                self.remove(path)
                if content == "dir":
                    path.mkdir()
                else:
                    path.write_bytes(content)
                self.assert_not_proof(fingerprint)
                self.remove(path)
                path.write_bytes(good_bytes)
        self.assert_proof(fingerprint, [first["attempt_id"]])
        self.remove(path)  # no receipt at all: the state a death right after the replace leaves
        self.assert_proof(fingerprint, [first["attempt_id"]])

    def test_a_replace_failure_archive_still_proves_and_a_damaged_one_never_does(self):
        prefix, _, original = self.torn_record()
        fingerprint = self.plan_fp()
        with mock.patch.object(rec, "_replace", side_effect=PermissionError("injected replace failure")):
            failed = rec.apply(self.root, fingerprint, REASON)
        self.assertEqual((failed["outcome"], failed["step"], failed["transport_log_changed"]),
                         ("FAILED", "REPLACE_FAILED", False))
        self.assert_fail_closed(original)
        applied = rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(applied["outcome"], "APPLIED")
        self.assertEqual(self.log.read_bytes(), prefix)
        self.assert_proof(fingerprint, sorted([failed["attempt_id"], applied["attempt_id"]]))
        damaged = self.root / "transport_recovery" / fingerprint[:16] / failed["attempt_id"] / "tail.bin"
        self.remove(damaged)
        damaged.write_bytes(b"{")
        self.assert_proof(fingerprint, [applied["attempt_id"]])

    def test_damaged_archive_after_death_after_replace_is_refused_by_a_fresh_process(self):
        prefix, _, _ = self.torn_record()
        fingerprint = self.plan_fp()
        code, err = self.child({"kind": "apply", "fingerprint": fingerprint, "reason": REASON,
                                "die_at": "after_replace", "out": "never"})
        self.assertEqual(code, 77, err)
        self.assertEqual(self.log.read_bytes(), prefix)
        [attempt] = self.attempts()
        self.assertFalse((attempt / "receipt.json").exists(), "the death must leave no receipt")
        self.remove(attempt / "tail.bin")
        census = tree(self.root)
        self.child({"kind": "apply", "fingerprint": fingerprint, "reason": REASON, "out": "r_missing"})
        result = self.wait_marker("r_missing")
        self.facts.append({"fresh_process_retry_without_tail": result})
        self.assertEqual((result["outcome"], result.get("code")), ("REFUSED", "HEALTHY"))
        self.assertEqual(tree(self.root), census)
        (attempt / "tail.bin").write_bytes((attempt / "original.bin").read_bytes()[len(prefix):])
        self.child({"kind": "apply", "fingerprint": fingerprint, "reason": REASON, "out": "r_restored"})
        restored = self.wait_marker("r_restored")
        self.assertEqual((restored["outcome"], restored["proven"]), ("ALREADY_APPLIED", [attempt.name]))


class FaultTests(Fixture):
    """Direction 6: injected exceptions (in process) — distinct from real process death below."""

    def run_with(self, patch_target: str, side_effect, expect: str):
        prefix, tail, original = self.torn_record()
        fingerprint = self.plan_fp()
        with mock.patch.object(rec, patch_target, side_effect=side_effect):
            try:
                result = rec.apply(self.root, fingerprint, REASON)
                outcome = result["outcome"], str(result.get("step"))
            except rec.TransportRecoveryRefused as exc:
                result, outcome = None, ("REFUSED", exc.code)
        self.facts.append({"outcome": outcome})
        self.assertEqual(outcome, tuple(expect.split("/")))
        return prefix, tail, original, fingerprint, result

    def test_archive_write_failure_refuses_and_keeps_the_log(self):
        real = rec._write_new

        def failing(path, data):
            if path.name == "tail.bin":
                raise OSError("injected archive write failure")
            return real(path, data)
        _, _, original, fingerprint, _ = self.run_with("_write_new", failing, "REFUSED/ARCHIVE_FAILED")
        self.assert_fail_closed(original)
        [attempt] = self.attempts()
        self.assertEqual((attempt / "original.bin").read_bytes(), original, "partial archive must stay as written")
        self.assertEqual(rec.apply(self.root, fingerprint, REASON)["outcome"], "APPLIED")
        self.assertEqual(len(self.attempts()), 2, "a retry must use a new attempt directory")

    def test_fsync_failure_refuses_before_any_change(self):
        _, _, original, _, _ = self.run_with("_fsync", OSError("injected fsync failure"), "REFUSED/ARCHIVE_FAILED")
        self.assert_fail_closed(original)

    def test_replace_failure_reports_failed_and_keeps_the_log(self):
        prefix, _, original, fingerprint, result = self.run_with(
            "_replace", PermissionError("injected replace failure"), "FAILED/REPLACE_FAILED")
        self.assertIs(result["transport_log_changed"], False)
        self.assertIs(result["receipt_recorded"], True)
        self.assert_fail_closed(original)
        self.assertEqual(sorted(p.name for p in self.log.parent.iterdir()), ["transport_events.jsonl"])
        self.assertEqual(rec.apply(self.root, fingerprint, REASON)["outcome"], "APPLIED")
        self.assertEqual(self.log.read_bytes(), prefix)

    def test_receipt_failure_is_reported_not_hidden(self):
        real = rec._write_new

        def failing(path, data):
            if path.name == "receipt.json":
                raise OSError("injected receipt failure")
            return real(path, data)
        prefix, _, _, _, result = self.run_with("_write_new", failing, "APPLIED/None")
        self.assertEqual((result["receipt_recorded"], result["receipt_error"]), (False, "OSError"))
        self.assertEqual(self.log.read_bytes(), prefix)

    def test_wrong_bytes_after_replace_restore_the_original(self):
        real = rec._replace

        def corrupting(source, target):
            if source.name.endswith(".restore.tmp"):
                return real(source, target)
            Path(source).unlink()
            Path(target).write_bytes(b'{"broken')  # a disk/foreign fault: the replaced log is not the prefix
        _, _, original, _, result = self.run_with("_replace", corrupting, "FAILED/POST_CHECK_FAILED")
        self.assertIn("restored", result["state"])
        self.assert_fail_closed(original)

    def test_foreign_write_ignoring_the_lock_before_replace_is_detected(self):
        _, _, original = self.torn_record()
        fingerprint = self.plan_fp()

        def foreign_writer(phase):
            if phase == "temp_written":  # a process that does not take the transport lock writes meanwhile
                with self.log.open("ab") as handle:
                    handle.write(b"Z")
        with mock.patch.object(rec, "_PHASE_HOOK", foreign_writer):
            with self.assertRaises(rec.TransportRecoveryRefused) as caught:
                rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(caught.exception.code, "SOURCE_CHANGED")
        self.assertEqual(self.log.read_bytes(), original + b"Z", "the log was replaced over a foreign write")
        self.assertEqual(sorted(p.name for p in self.log.parent.iterdir()), ["transport_events.jsonl"])

    def test_silently_corrupted_archive_write_is_caught_by_read_back(self):
        _, _, original = self.torn_record()
        fingerprint = self.plan_fp()
        real_write, calls = os.write, []

        def lossy(fd, data):
            calls.append(len(data))
            if len(calls) == 1:  # the first archive file loses its last byte but reports success
                real_write(fd, bytes(data)[:-1])
                return len(data)
            return real_write(fd, data)
        with mock.patch.object(rec.os, "write", side_effect=lossy):
            with self.assertRaises(rec.TransportRecoveryRefused) as caught:
                rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(caught.exception.code, "ARCHIVE_FAILED")
        self.assert_fail_closed(original)

    def test_readonly_log_file_fails_replace_for_real(self):
        _, _, original = self.torn_record()
        fingerprint = self.plan_fp()
        os.chmod(self.log, stat.S_IREAD)
        self.addCleanup(os.chmod, self.log, stat.S_IWRITE | stat.S_IREAD)
        result = rec.apply(self.root, fingerprint, REASON)
        self.assertEqual((result["outcome"], result["step"]), ("FAILED", "REPLACE_FAILED"))
        self.assertEqual(self.log.read_bytes(), original)


class CrashTests(Fixture):
    """Direction 6: real death of a child process at each phase; a fresh process judges and retries."""

    PHASES = ("locked", "archive_original_written", "archive_written", "archive_verified", "temp_written",
              "before_replace", "after_replace", "receipt_written")

    def test_death_at_every_phase_leaves_original_or_exact_prefix_and_retry_is_safe(self):
        for phase in self.PHASES:
            with self.subTest(phase):
                self.setUp()
                prefix, _, original = self.torn_record()
                fingerprint = self.plan_fp()
                code, err = self.child({"kind": "apply", "fingerprint": fingerprint, "reason": REASON,
                                        "die_at": phase, "out": "never"})
                self.assertEqual(code, 77, err)
                replaced = phase in ("after_replace", "receipt_written")
                if replaced:
                    self.assertEqual(self.log.read_bytes(), prefix)
                else:
                    self.assert_fail_closed(original)
                reopened = self.inspect()  # fresh judgement in this process
                self.facts.append({phase: {"verdict": reopened["verdict"],
                                           "leftover": reopened.get("leftover_recovery_temp_files", 0)}})
                code, err = self.child({"kind": "apply", "fingerprint": fingerprint, "reason": REASON, "out": "r2"})
                second = self.wait_marker("r2")
                self.assertEqual(second["outcome"], "ALREADY_APPLIED" if replaced else "APPLIED", (phase, second))
                self.assertEqual(self.log.read_bytes(), prefix)
                for attempt in self.attempts():  # no archive file was ever altered
                    if (attempt / "original.bin").exists() and phase != "locked":
                        self.assertEqual((attempt / "original.bin").read_bytes()[:len(original)],
                                         original[:(attempt / "original.bin").stat().st_size])
                complete = [a for a in self.attempts() if (a / "original.bin").exists()
                            and (a / "original.bin").read_bytes() == original]
                self.assertTrue(complete, "no complete archive of the original survived")


class ConcurrencyTests(Fixture):
    """Direction 5: other processes holding the lock, appending, applying and reading meanwhile."""

    def test_lock_held_by_another_process_times_out_without_any_change(self):
        _, _, original = self.torn_record()
        fingerprint = self.plan_fp()
        holder = self.child({"kind": "hold_lock"}, wait=False)
        try:
            self.wait_marker("held")
            census = tree(self.root)
            with self.assertRaises(rec.TransportRecoveryRefused) as caught:
                rec.apply(self.root, fingerprint, REASON, lock_timeout=0.3)
        finally:
            (self.base / "release").write_text("1")
            holder.communicate(timeout=60)
        self.assertEqual(caught.exception.code, "LOCK_TIMEOUT")
        self.assertEqual(tree(self.root), census)
        self.assert_fail_closed(original)

    def test_writer_waits_for_the_repair_and_then_appends_after_the_prefix(self):
        prefix, _, _ = self.torn_record()
        fingerprint = self.plan_fp()
        applier = self.child({"kind": "apply", "fingerprint": fingerprint, "reason": REASON,
                              "pause_at": "temp_written", "out": "applied"}, wait=False)
        self.wait_marker("paused")
        writer = self.child({"kind": "writer", "event_id": "w1"}, wait=False)
        self.wait_marker("attempting")
        time.sleep(0.5)
        blocked = not (self.base / "writer_done").exists()
        (self.base / "go").write_text("1")
        applier.communicate(timeout=60)
        writer.communicate(timeout=60)
        done, applied = self.wait_marker("writer_done"), self.wait_marker("applied")
        self.facts.append({"blocked_while_repairing": blocked, "writer": done, "apply": applied})
        self.assertTrue(blocked, "a writer got past the recovery lock")
        self.assertEqual((applied["outcome"], done["ok"]), ("APPLIED", True))
        # it waited on the lock and never even saw the torn log: no refused attempt before success
        self.assertEqual(done["errors"], 0, "the writer read the log while the recovery was in progress")
        data = self.log.read_bytes()
        self.assertTrue(data.startswith(prefix))
        self.assertEqual([r.event_id for r in TransportEventStore(self.root).read_events()], ["t0", "t1", "t2", "w1"])

    def test_two_concurrent_confirmations_apply_exactly_once(self):
        prefix, _, _ = self.torn_record()
        fingerprint = self.plan_fp()
        procs = [self.child({"kind": "apply", "fingerprint": fingerprint, "reason": REASON, "start_flag": "start",
                             "out": f"a{i}"}, wait=False) for i in range(2)]
        (self.base / "start").write_text("1")
        for proc in procs:
            proc.communicate(timeout=60)
        outcomes = sorted(self.wait_marker(f"a{i}")["outcome"] for i in range(2))
        self.facts.append({"outcomes": outcomes})
        self.assertEqual(outcomes, ["ALREADY_APPLIED", "APPLIED"])
        self.assertEqual(self.log.read_bytes(), prefix)
        self.assertEqual(len(self.attempts()), 1)

    def test_lock_free_readers_never_see_a_half_cut_log(self):
        prefix, tail, _ = self.torn_record(rows=40)
        expected_ids = [f"t{i}" for i in range(40)]
        reader = self.child({"kind": "reader"}, wait=False)
        first = self.wait_marker("reading")  # the reader really runs before the first repair
        outcomes = []
        for round_no in range(20):  # tear and repair again and again while the reader keeps reading
            if round_no:
                with self.log.open("ab") as handle:
                    handle.write(tail)
            fingerprint = self.plan_fp()
            for _ in range(200):
                try:
                    result = rec.apply(self.root, fingerprint, REASON)
                except rec.TransportRecoveryRefused as exc:
                    self.fail(f"refused while a reader was active: {exc}")
                outcomes.append(result.get("step") or result["outcome"])
                if result["outcome"] == "APPLIED":
                    break
            self.assertEqual(self.log.read_bytes(), prefix)
        (self.base / "stop_reader").write_text("1")
        reader.communicate(timeout=60)
        seen = self.wait_marker("reader_done")["seen"]
        counts = {k: outcomes.count(k) for k in set(outcomes)}
        self.facts.append({"reader_first": first, "apply_outcomes": counts,
                           "reader_observations": {k[:40]: v for k, v in seen.items()}})
        self.assertEqual(counts.get("APPLIED"), 20)
        self.assertGreater(seen.get("error:unterminated transport event log", 0), 0, "the reader never saw a torn log")
        allowed_ids = "ids:40:" + "|".join(expected_ids)
        # a reader may also hit the store's own fail-closed "cannot read" while the name is being replaced
        allowed = {allowed_ids, "error:unterminated transport event log", "error:cannot read transport events"}
        self.assertEqual(set(seen) - allowed, set(),
                         "a reader observed a state that is neither the torn original nor the exact prefix")
        self.assertEqual(self.log.read_bytes(), prefix)


class TargetTests(Fixture):
    """Direction 7: wrong roots, junctions, path swaps, hard links, symlinks (privilege permitting)."""

    def junction(self, target: Path, link: Path):
        import _winapi
        _winapi.CreateJunction(str(target), str(link))

    def test_bad_roots_are_refused(self):
        self.torn_record()
        cases = {"relative": "state", "missing": str(self.base / "nope"), "file": str(self.log),
                 "dotdot": str(self.root / ".." / "state")}
        for name, root in cases.items():
            with self.subTest(name):
                result = rec.inspect(root)
                self.assertEqual(result["verdict"], "BAD_TARGET", result)
                with self.assertRaises(rec.TransportRecoveryRefused):
                    rec.apply(root, "0" * 64, REASON)

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_junctions_anywhere_in_the_tree_are_refused_before_any_write(self):
        _, _, original = self.torn_record()
        fingerprint = self.plan_fp()
        alias = self.base / "alias"
        self.junction(self.root, alias)
        self.assertEqual(rec.inspect(alias)["verdict"], "BAD_TARGET")
        # transport_recovery redirected elsewhere: refused before an archive byte is written
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        self.junction(elsewhere, self.root / "transport_recovery")
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(caught.exception.code, "BAD_TARGET")
        self.assertEqual(list(elsewhere.iterdir()), [])
        os.rmdir(self.root / "transport_recovery")
        # locks redirected
        lock_target = self.base / "locks_elsewhere"
        lock_target.mkdir()
        shutil.rmtree(self.root / "locks", ignore_errors=True)
        self.junction(lock_target, self.root / "locks")
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(caught.exception.code, "BAD_TARGET")
        os.rmdir(self.root / "locks")
        self.assert_fail_closed(original)

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_path_swap_to_an_identical_copy_after_inspect_is_refused(self):
        _, _, original = self.torn_record()
        fingerprint = self.plan_fp()
        decoy = self.base / "decoy"
        shutil.copytree(self.root / "transport", decoy)
        os.rename(self.root / "transport", self.base / "moved")
        self.junction(decoy, self.root / "transport")
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, fingerprint, REASON)
        self.assertEqual(caught.exception.code, "BAD_TARGET")
        self.assertEqual((decoy / "transport_events.jsonl").read_bytes(), original)
        self.assertEqual((self.base / "moved" / "transport_events.jsonl").read_bytes(), original)

    def test_hard_linked_log_is_ambiguous(self):
        _, _, original = self.torn_record()
        os.link(self.log, self.base / "second_name.jsonl")
        self.assertEqual(self.inspect()["verdict"], "AMBIGUOUS")
        with self.assertRaises(rec.TransportRecoveryRefused) as caught:
            rec.apply(self.root, "0" * 64, REASON)
        self.assertEqual(caught.exception.code, "AMBIGUOUS")
        self.assertEqual(self.log.read_bytes(), original)

    def test_symlinked_log_is_refused(self):
        _, _, original = self.torn_record()
        real = self.base / "real.jsonl"
        os.replace(self.log, real)
        try:
            os.symlink(real, self.log)
        except OSError as exc:
            self.skipTest(f"symlink creation not permitted on this host ({exc.__class__.__name__} "
                          f"winerror={getattr(exc, 'winerror', None)}): NOT RUN, see report")
        self.assertEqual(self.inspect()["verdict"], "BAD_TARGET")
        self.assertEqual(real.read_bytes(), original)


class DifferentialTests(Fixture):
    """Gate C: the classifier agrees with the store's own reader on seeded random damage."""

    def test_classifier_matches_the_store_reader_on_random_damage(self):
        prefix = self.healthy(6)
        rng = random.Random(20261020)
        store = TransportEventStore(self.root)
        disagreements, verdicts = [], {}
        for case in range(400):
            data = bytearray(prefix)
            action = rng.choice(["cut", "flip", "insert", "cut", "append"])
            if action == "cut":
                data = data[:rng.randrange(0, len(data) + 1)]
            elif action == "flip":
                index = rng.randrange(len(data))
                data[index] = rng.randrange(256)
            elif action == "insert":
                index = rng.randrange(len(data))
                data[index:index] = bytes([rng.choice([0, 10, 13, 34, 123, 125, 0xFF])])
            else:
                data += bytes(rng.randrange(256) for _ in range(rng.randrange(1, 30)))
            data = bytes(data)
            self.log.write_bytes(data)
            result = rec.classify(data)
            verdict = result["verdict"]
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
            try:
                store.read_events()
                readable = True
            except TransportEventStoreError:
                readable = False
            # the store tolerates an event-id conflict on read (only append checks it); the classifier refuses it
            expected = verdict == "HEALTHY" or (result.get("problem") == "EVENT_ID_CONFLICT"
                                                and (not data or data.endswith(b"\n")))
            if readable != expected:
                disagreements.append((case, action, verdict))
            if verdict == "TORN_TAIL":  # the planned prefix must itself be readable by the store
                cut = rec.classify(data)["prefix"]["bytes"]
                self.log.write_bytes(data[:cut])
                store.read_events()
        self.facts.append({"verdicts": verdicts, "disagreements": disagreements[:5]})
        self.assertEqual(disagreements, [])
        self.assertGreater(verdicts.get("TORN_TAIL", 0), 20)
        self.assertGreater(verdicts.get("CORRUPT_MIDDLE", 0), 20)


if __name__ == "__main__":
    unittest.main()
