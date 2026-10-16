"""Exploration probe (before repair): which microtask lifecycle paths persist state with a refused event.

Each case builds a fresh disposable TEMP fixture, damages or perturbs the TASK history, calls the real
HTTP handler (WebAlarmApi.dispatch) and records HTTP outcome + raw byte changes of every storage file
outside locks/. Prints one JSON document. Usage: explore_aud02b_paths.py <repo-root>
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from web_alarm.server import ApiError, WebAlarmApi  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_x"


def fixture(base: Path, upto: str):
    storage, project = base / "state", base / "project"
    project.mkdir()
    (project / "data.bin").write_bytes(b"pre")
    WorkspaceRegistry(storage).register("x", project, workspace_id="ws_x")
    tasks = TaskStore(storage)
    tasks.create_task("ws_x", "x", "RAW", "explore", task_id=TASK)
    tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
    machine = ServerStateMachine(storage)
    if upto == "PLANNED":
        return storage
    machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
    for step in {"BACKUP_VERIFIED": [], "READY": ["READY"], "ACTIVE": ["READY", "ACTIVE"],
                 "DONE": ["READY", "ACTIVE", "DONE"]}[upto]:
        machine.transition(TASK, "m1", step)
    return storage


def files(storage: Path):
    return {p.relative_to(storage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(storage.rglob("*")) if p.is_file() and p.relative_to(storage).parts[0] != "locks"}


def damage(storage: Path, kind: str):
    path = storage / "tasks" / "active" / TASK / "events.jsonl"
    data = path.read_bytes()
    if kind == "torn":
        path.write_bytes(data[:-1])
    elif kind == "middle":
        first = data.index(b"\n") + 1
        path.write_bytes(data[:first] + b"{not json\n" + data[first:])


def call(storage, method, path, body):
    try:
        status, reply = WebAlarmApi(storage).dispatch(method, path, body)
        return [status, (reply.get("microtask") or {}).get("status")]
    except ApiError as exc:
        return [exc.status, exc.code, str(exc)[:160]]
    except Exception as exc:  # noqa: BLE001 - exploration records the raw type
        return ["RAISED", type(exc).__name__, str(exc)[:160]]


CASES = [
    ("ACTIVE->DONE torn", "ACTIVE", "torn", "POST", "/microtasks/m1/transition", {"target_status": "DONE"}),
    ("ACTIVE->DONE middle", "ACTIVE", "middle", "POST", "/microtasks/m1/transition", {"target_status": "DONE"}),
    ("READY->ACTIVE torn", "READY", "torn", "POST", "/microtasks/m1/transition", {"target_status": "ACTIVE"}),
    ("DONE->VERIFIED torn", "DONE", "torn", "POST", "/microtasks/m1/transition",
     {"target_status": "VERIFIED", "verification_evidence": "ok"}),
    ("BACKUP_VERIFIED->READY torn", "BACKUP_VERIFIED", "torn", "POST", "/microtasks/m1/transition",
     {"target_status": "READY"}),
    ("ACTIVE->VERIFIED (disallowed) middle", "ACTIVE", "middle", "POST", "/microtasks/m1/transition",
     {"target_status": "VERIFIED", "verification_evidence": "x"}),
    ("DONE->VERIFIED lone surrogate evidence", "DONE", None, "POST", "/microtasks/m1/transition",
     {"target_status": "VERIFIED", "verification_evidence": "ok" + chr(0xD800)}),
    ("ACTIVE->DONE lone surrogate operation_id", "ACTIVE", None, "POST", "/microtasks/m1/transition",
     {"target_status": "DONE", "operation_id": "op" + chr(0xDC00)}),
    ("prepare torn", "PLANNED", "torn_after_report", "POST", "/microtasks/m1/prepare",
     {"targets": [{"path": "data.bin", "expected_change": "edit"}]}),
    ("report middle", "ACTIVE", "middle", "POST", "/microtasks/m1/report", {"report": "r"}),
]

out = []
for name, upto, kind, method, path, body in CASES:
    base = Path(tempfile.mkdtemp(prefix="aud02b-explore-"))
    storage = fixture(base, upto)
    if kind == "torn_after_report":  # PLANNED has no events yet: create one, then tear it
        WebAlarmApi(storage).dispatch("POST", "/microtasks/m1/report", {"task_id": TASK, "report": "seed"})
        kind = "torn"
    if kind:
        damage(storage, kind)
    before = files(storage)
    outcome = call(storage, method, path, dict(body, task_id=TASK))
    after = files(storage)
    micro = json.loads((storage / "tasks/active" / TASK / "microtasks/m1.json").read_bytes())["status"]
    out.append({"case": name, "http": outcome, "m1_status_after": micro,
                "changed": sorted(k for k in after if before.get(k) != after[k]),
                "added": sorted(set(after) - set(before))})
print(json.dumps(out, ensure_ascii=True, indent=1))
