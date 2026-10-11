"""Offline WA4-A test infrastructure; never a production mutation entry point.

The worker exercises the real HTTP handler with an in-memory wire. Losing that
wire happens AFTER dispatch and durable DONE, not by pretending execution failed.
Each invocation owns a new Python process/API/store. All fixture data is temporary.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent
TASK = "wa4a_task"
BEFORE = b"before\n"
AFTER = b"after\r\n\x00binary\xff"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def append(path, value):
    with Path(path).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def lines(path):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines()]


def request(action="write", target="a.txt", operation_id="op_a", **extra):
    import base64
    body = dict(microtask_id="m1", operation_id=operation_id, action=action, target=target)
    if action in {"write", "edit", "create"}:
        body["payload"] = {"encoding": "base64", "data": base64.b64encode(AFTER).decode("ascii")}
    body.update(extra)
    return body


class DisposableWorkspace:
    """Mixin with no inherited tests (unittest discovery must not duplicate WA4-E)."""
    manifest = [("a.txt", "edit")]

    def setUp(self):
        from web_alarm.workspace_registry import WorkspaceRegistry
        from web_alarm.task_store import TaskStore
        from web_alarm.state_machine import ServerStateMachine
        self.temp = tempfile.TemporaryDirectory(prefix="wa4a_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.storage = self.base / "state"
        self.project = self.base / "project"
        self.project.mkdir()
        for name, data in {"a.txt": BEFORE, "src.txt": BEFORE, "outside.txt": b"outside\n"}.items():
            (self.project / name).write_bytes(data)
        WorkspaceRegistry(self.storage).register("disposable WA4-A", self.project, workspace_id="wa4a_ws")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("wa4a_ws", "acceptance", "disposable", "WA4-A", task_id=TASK)
        self.tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
        self.tasks.create_microtask(TASK, "two", "two", microtask_id="m2")
        self.machine = ServerStateMachine(self.storage)
        self.machine.prepare_microtask(TASK, "m1", self.manifest)
        self.machine.transition(TASK, "m1", "READY")
        self.machine.transition(TASK, "m1", "ACTIVE")
        self.facts = []

    def note(self, **facts):
        self.facts.append(facts)

    def op(self, operation_id="op_a"):
        from web_alarm.operation_store import OperationStore
        return OperationStore(self.storage).get(TASK, operation_id)

    def operation_path(self, operation_id="op_a"):
        return self.tasks.task_directory(TASK) / "operations" / (operation_id + ".json")

    def events(self, event_type=None):
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        events = EventCheckpointStore(self.storage).read_events(TASK)
        return [e for e in events if event_type is None or e.event_type == event_type]

    def history(self, operation_id="op_a"):
        from web_alarm.models import record_to_dict
        return [record_to_dict(e) for e in self.events() if e.operation_id == operation_id]

    def apply_count(self):
        path = self.base / "physical.jsonl"
        return sum(v["event"] == "APPLY_ENTER" for v in lines(path)) if path.exists() else 0

    def dispatch(self, body=None):
        from web_alarm.server import ApiError, WebAlarmApi
        try:
            return WebAlarmApi(self.storage).dispatch("POST", f"/tasks/{TASK}/mutations", body or request())
        except ApiError as exc:
            return exc.status, {"error": exc.code, "details": exc.details}

    def worker_args(self, mode="deliver", body=None, name="worker", barrier=None):
        args = [sys.executable, "-B", str(ROOT / "wa4a_acceptance.py"), "worker",
                str(self.base), mode, name, json.dumps(body or request())]
        if barrier:
            args.append(str(barrier))
        return args

    def child(self, mode="deliver", body=None, name="worker"):
        done = subprocess.run(self.worker_args(mode, body, name), cwd=ROOT, capture_output=True,
                              text=True, timeout=90)
        if mode in {"before_started", "after_started", "after_write", "after_receipt", "receipt_before_event", "move_partial"}:
            self.assertEqual(done.returncode, 91, done.stderr)
            self.assertEqual(done.stdout, "")
            result = {"client": {"state": "UNKNOWN", "received_bytes": 0}, "exit": 91}
        else:
            self.assertEqual(done.returncode, 0, done.stderr)
            result = json.loads(done.stdout)
        self.note(worker=name, mode=mode, observed=result)
        return result

    def decision(self, operation_id="op_a"):
        from web_alarm.reconciliation_service import ReconciliationService
        return ReconciliationService(self.storage).reconcile(TASK, "m1", operation_id)

    def resolve(self, action, operation_id="op_a"):
        from web_alarm.resolver_service import ResolverService
        dec = self.decision(operation_id)["DECISION"]
        result = ResolverService(self.storage).apply(
            TASK, "m1", operation_id, action, evidence_fingerprint=dec["evidence_fingerprint"],
            operation_revision=self.op(operation_id).revision)
        self.assertTrue(result["accepted"], result)
        return result


def worker(base, mode, name, body, barrier=None):
    from web_alarm.event_checkpoint_store import EventCheckpointStore
    from web_alarm.models import OperationStatus
    from web_alarm.mutation_executor import MutationExecutor
    from web_alarm.operation_store import OperationStore
    from web_alarm.server import WebAlarmApi, _JsonHandler
    base = Path(base)
    trace = base / (name + ".jsonl")
    storage = base / "state"

    def mark(event, **extra):
        append(trace, dict(event=event, pid=os.getpid(), **extra))

    mark("PROCESS_START")
    real_transition = OperationStore._transition_locked
    real_apply = MutationExecutor._apply
    real_send = _JsonHandler._send_json
    real_event = EventCheckpointStore.append_event

    def event(store, task, event_type, **kw):
        if mode == "receipt_before_event" and event_type == "OPERATION_TRANSITION" and kw.get("payload", {}).get("to") == "DONE":
            mark("FAULT_STOP", point=mode, receipt=OperationStore(storage).get(TASK, body["operation_id"]).receipt)
            os._exit(91)
        return real_event(store, task, event_type, **kw)

    def transition(store, task, op, status, **kw):
        if OperationStatus(status) is OperationStatus.STARTED and (
            mode == "before_started" or (mode == "move_partial" and op.endswith("delete-source"))
        ):
            mark("FAULT_STOP", point=mode)
            os._exit(91)
        result = real_transition(store, task, op, status, **kw)
        if mode == "after_receipt" and OperationStatus(status) is OperationStatus.DONE:
            mark("FAULT_STOP", point=mode, receipt=result["operation"].receipt)
            os._exit(91)
        return result

    def apply(kind, path, data):
        if mode == "after_started":
            mark("FAULT_STOP", point=mode)
            os._exit(91)
        append(base / "physical.jsonl", {"event": "APPLY_ENTER", "target": path.name,
                                        "kind": kind.value, "pid": os.getpid()})
        real_apply(kind, path, data)
        append(base / "physical.jsonl", {"event": "APPLY_RETURN", "target": path.name,
                                        "pid": os.getpid()})
        if mode == "after_write":
            mark("FAULT_STOP", point=mode)
            os._exit(91)

    def send(handler, status, payload):
        # This is server-side evidence, never a response received by the client.
        mark("RESPONSE_READY", status=status, result=payload.get("result"), receipt=payload.get("receipt"))
        return real_send(handler, status, payload)

    class Wire(io.BytesIO):
        def write(self, data):
            if mode == "drop_response":
                mark("DELIVERY_DROPPED", bytes_attempted=len(data))
                raise BrokenPipeError("deterministic lost response (no bytes delivered)")
            return super().write(data)

    api = WebAlarmApi(storage)
    if barrier:
        barrier = Path(barrier)
        (barrier / (name + ".ready")).touch()
        deadline = time.monotonic() + 30
        while not (barrier / "go").exists():
            if time.monotonic() > deadline:
                raise TimeoutError("acceptance barrier did not open")
            time.sleep(0.005)
    raw = json.dumps(body).encode("utf-8")
    handler = _JsonHandler.__new__(_JsonHandler)
    handler.server = SimpleNamespace(web_alarm_api=api)
    handler.command = "POST"
    handler.path = f"/tasks/{TASK}/mutations"
    handler.request_version = "HTTP/1.1"
    handler.requestline = "POST " + handler.path + " HTTP/1.1"
    handler.headers = Message()
    handler.headers["Content-Type"] = "application/json"
    handler.headers["Content-Length"] = str(len(raw))
    handler.rfile = io.BytesIO(raw)
    handler.wfile = Wire()
    with mock.patch.object(OperationStore, "_transition_locked", transition), \
         mock.patch.object(MutationExecutor, "_apply", staticmethod(apply)), \
         mock.patch.object(EventCheckpointStore, "append_event", event), \
         mock.patch.object(_JsonHandler, "_send_json", send):
        try:
            handler._run()
        except BrokenPipeError:
            if mode != "drop_response":
                raise
    delivered = handler.wfile.getvalue()
    if delivered:
        headers, raw_body = delivered.split(b"\r\n\r\n", 1)
        client = {"state": "RECEIVED", "status": int(headers.split(b" ")[1]),
                  "body": json.loads(raw_body), "received_bytes": len(delivered)}
    else:
        client = {"state": "UNKNOWN", "received_bytes": 0, "body": None}
    mark("CLIENT_OBSERVATION", **client)
    print(json.dumps({"pid": os.getpid(), "client": client}))


# Installed as sitecustomize for this runner AND every Python child. The full
# suite uses loopback HTTP; external networking and all non-Python subprocesses
# are refused. Writes are confined to the system temp directory, never live data.
GUARD = r'''
import ipaddress, json, os, sys, tempfile
from pathlib import Path
_audit_temp = Path(tempfile.gettempdir()).resolve()
_audit_log = Path(os.environ["WA4A_GUARD_LOG"]).resolve()
if not _audit_log.is_relative_to(_audit_temp):
    raise RuntimeError("WA4-A audit log must be inside disposable temp")
# Open once before the audit hook. A denied write must never re-enter
# the hook while recording the denial (especially on Windows runners).
_audit_fd = os.open(_audit_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
def _violation(event, reason):
    os.write(_audit_fd, (json.dumps({"event":event,"reason":reason,"pid":os.getpid()})+"\n").encode("utf-8"))
    raise PermissionError("WA4-A isolation: "+reason)
def _path(value, write=False):
    if value is None or isinstance(value, int): return
    p = Path(os.fsdecode(value)).resolve()
    if ".git" in {s.lower() for s in p.parts}: _violation("filesystem", "Git metadata access")
    if write and not p.is_relative_to(_audit_temp): _violation("filesystem", "write outside disposable temp: "+str(p))
def _local(host):
    if host == "localhost": return True
    try: return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError): return False
def _audit(event, args):
    if event == "open":
        path, mode, flags = args
        _path(path, (isinstance(mode,str) and any(c in mode for c in "wax+")) or
              (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))))
    elif event in {"os.remove","os.rmdir","os.mkdir","os.chmod","os.truncate","os.utime"}: _path(args[0], True)
    elif event in {"os.rename","os.replace","os.link","os.symlink"}:
        _path(args[0], True); _path(args[1], True)
    elif event in {"os.listdir","os.scandir"}: _path(args[0])
    elif event == "subprocess.Popen":
        exe, argv = args[:2]
        # Windows audits the already quoted command line, with executable=None.
        if exe is None and isinstance(argv,str):
            prefix = '"'+sys.executable+'"' if ' ' in sys.executable else sys.executable
            if not argv.startswith(prefix+' '): _violation(event,"non-Python command line")
            exe = sys.executable
        elif exe is None and isinstance(argv,(list,tuple)):
            exe = argv[0]
        if exe is None or Path(exe).resolve() != Path(sys.executable).resolve():
            _violation(event, "only controlled Python subprocesses allowed")
    elif event in {"os.system","os.exec","os.posix_spawn"}: _violation(event,"shell/native execution forbidden")
    elif event in {"socket.connect","socket.bind"}:
        address = args[1]
        if not isinstance(address,tuple) or not _local(address[0]): _violation(event,"external socket forbidden")
    elif event == "socket.getaddrinfo" and not _local(args[0]): _violation(event,"external DNS forbidden")
sys.addaudithook(_audit)
'''


def run_tests(targets, output):
    output = Path(output).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not output.is_relative_to(temp_root):
        raise ValueError("WA4-A test evidence must stay inside the disposable Python temp directory")
    output.mkdir(parents=True, exist_ok=True)
    guard_dir = Path(tempfile.mkdtemp(prefix="wa4a_guard_"))
    guard_log = output / "isolation.jsonl"
    guard_log.write_text("", encoding="utf-8")
    (guard_dir / "sitecustomize.py").write_text(GUARD, encoding="utf-8")
    os.environ["WA4A_GUARD_LOG"] = str(guard_log)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONPATH"] = str(guard_dir) + os.pathsep + str(ROOT)
    # Children import sitecustomize; install the same guard in this process now.
    exec(compile(GUARD, str(guard_dir / "sitecustomize.py"), "exec"), {})
    captured = []

    class Result(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test)
            captured.append({"test": test.id(), "status": "PASS", "facts": getattr(test, "facts", [])})

        def addFailure(self, test, err):
            super().addFailure(test, err)
            captured.append({"test": test.id(), "status": "FAIL", "error": self._exc_info_to_string(err, test),
                             "facts": getattr(test, "facts", [])})

        def addError(self, test, err):
            super().addError(test, err)
            captured.append({"test": test.id(), "status": "ERROR", "error": self._exc_info_to_string(err, test),
                             "facts": getattr(test, "facts", [])})

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            captured.append({"test": test.id(), "status": "SKIP", "reason": reason})

        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            if err:
                captured.append({"test": subtest.id(), "status": "FAIL", "error": self._exc_info_to_string(err, test)})

    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT), pattern="test_web_alarm*.py") if targets == ["all"] else loader.loadTestsFromNames(targets)
    started = time.time()
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    hashes = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted((ROOT / "web_alarm").glob("*.py"))}
    for p in sorted(ROOT.glob("test_web_alarm*.py")):
        hashes[p.name] = sha(p.read_bytes())
    hashes["wa4a_acceptance.py"] = sha(Path(__file__).read_bytes())
    summary = {"task": "CODEX-WA4-A-001", "targets": targets, "python": sys.version,
               "platform": sys.platform, "started_unix": started, "elapsed_seconds": round(time.time()-started, 3),
               "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "skips": len(result.skipped), "passed": result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
               "successful": result.wasSuccessful(), "isolation_violations": lines(guard_log),
               "source_sha256": hashes, "tests": captured}
    (output / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    # Remove only our guard directory, checked by TemporaryDirectory-equivalent prefix.
    import shutil
    shutil.rmtree(guard_dir)
    return 0 if result.wasSuccessful() and not summary["isolation_violations"] else 1


if __name__ == "__main__":
    if sys.argv[1:2] == ["worker"]:
        worker(sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5]), *sys.argv[6:])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--output", required=True)
        parser.add_argument("targets", nargs="+", help="unittest names, or all for Web Alarm discovery")
        ns = parser.parse_args()
        raise SystemExit(run_tests(ns.targets, ns.output))
