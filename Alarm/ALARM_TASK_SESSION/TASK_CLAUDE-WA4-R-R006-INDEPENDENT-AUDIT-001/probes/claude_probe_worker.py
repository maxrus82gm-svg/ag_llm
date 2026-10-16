"""Child actor for the Claude R-006 independent probes (one fresh Python process per actor).

Runs ONE production API call in a disposable TEMP storage, optionally with a fault barrier:
  crash_after_move     - os._exit(77) right after the active->completed directory move (F3 commit point)
  pause_after_move     - after the move: touch <name>.moved, wait for <name>.go (F1 native status refusal)
  pause_before_move    - holding both TASK locks, before the move: touch <name>.before_move, wait <name>.go
  pause_in_apply       - inside the RC-3 boundary, before the physical write: touch <name>.in_apply, wait <name>.go
  crash_after_done     - os._exit(79) right after the durable DONE transition (before reply/event)
  crash_before_intent  - os._exit(78) when OPERATION_INTENT is about to be appended (record already persisted)
Every physical apply is traced to <name>.trace (apply_enter) so the parent counts real applies.
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path
from unittest import mock

TASK = "task_cl"


def chain(exc):
    out, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        out.append({"type": type(exc).__name__, "message": str(exc)[:500],
                    "winerror": getattr(exc, "winerror", None), "errno": getattr(exc, "errno", None)})
        exc = exc.__cause__ or exc.__context__
    return out


def main(cfg_path):
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    base, storage, name, mode = Path(cfg["base"]), Path(cfg["storage"]), cfg["name"], cfg["mode"]
    from web_alarm.closeout import CloseoutService
    from web_alarm.event_checkpoint_store import EventCheckpointStore
    from web_alarm.models import OperationStatus
    from web_alarm.mutation_executor import MutationExecutor
    from web_alarm.operation_store import OperationStore
    from web_alarm.task_store import TaskStore

    def mark(phase, **facts):
        with (base / (name + ".trace")).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(phase=phase, pid=os.getpid(), **facts)) + "\n")
        (base / (name + "." + phase)).touch()

    def wait_go():
        deadline = time.monotonic() + 40
        while not (base / (name + ".go")).exists():
            if time.monotonic() > deadline:
                raise TimeoutError("parent never released " + name)
            time.sleep(0.005)

    real_replace = os.replace
    real_apply = MutationExecutor._apply
    real_transition = OperationStore._transition_locked
    real_event = EventCheckpointStore.append_event
    active, completed = storage / "tasks" / "active" / TASK, storage / "tasks" / "completed" / TASK

    def replace(src, dst):
        moving = Path(src) == active and Path(dst) == completed
        if moving and mode == "pause_before_move":
            mark("before_move")
            wait_go()
        result = real_replace(src, dst)
        if moving:
            mark("moved")
            if mode == "crash_after_move":
                os._exit(77)
            if mode == "pause_after_move":
                wait_go()
        return result

    def apply(kind, path, data):
        mark("apply_enter", target=Path(path).name)
        if mode == "pause_in_apply":
            mark("in_apply")
            wait_go()
        return real_apply(kind, path, data)

    def transition(store, task, op, status, **kw):
        result = real_transition(store, task, op, status, **kw)
        if mode == "crash_after_done" and OperationStatus(status) is OperationStatus.DONE:
            mark("done_persisted", receipt=result["operation"].receipt)
            os._exit(79)
        return result

    def event(store, task, kind, **kw):
        if mode == "crash_before_intent" and kind == "OPERATION_INTENT":
            mark("intent_record_persisted_event_pending")
            os._exit(78)
        return real_event(store, task, kind, **kw)

    try:
        with mock.patch.object(os, "replace", replace), \
             mock.patch.object(MutationExecutor, "_apply", staticmethod(apply)), \
             mock.patch.object(OperationStore, "_transition_locked", transition), \
             mock.patch.object(EventCheckpointStore, "append_event", event):
            mark("actor_enter", action=cfg["action"], mode=mode)
            if cfg["action"] == "close":
                value = CloseoutService(storage).complete(TASK)
                result = {k: value.get(k) for k in ("result", "resumed", "event_recorded")}
            elif cfg["action"] == "direct_close":
                result = {"result": "COMPLETED", "status": TaskStore(storage).complete_task(TASK).status.value}
            elif cfg["action"] == "mutate":
                value = MutationExecutor(storage).execute(TASK, "m1", cfg["op"], "write", "data.bin",
                                                          payload=bytes.fromhex(cfg["payload_hex"]))
                result = {k: value.get(k) for k in ("result", "result_code", "receipt")}
            else:
                raise ValueError("unknown action")
        print(json.dumps(result))
    except Exception as exc:  # the parent asserts the exact chain
        print(json.dumps({"error": chain(exc), "tb": traceback.format_exc()[-1500:]}))
        raise SystemExit(2)


if __name__ == "__main__":
    main(sys.argv[1])
