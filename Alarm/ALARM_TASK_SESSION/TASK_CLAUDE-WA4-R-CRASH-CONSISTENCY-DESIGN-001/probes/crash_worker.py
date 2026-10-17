"""Child actor for CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001 (one fresh Python process per call).

Runs ONE production call against a disposable TEMP storage with an optional fault at one event append:
  crash_after_status  -- MICROTASK_TRANSITION is about to be appended: re-read the microtask record from
                         disk (proves the CAS is durable), write a marker, os._exit(70)
  crash_after_intent  -- OPERATION_INTENT is about to be appended: re-read the operation record from disk
                         (proves INTENT is durable), write a marker, os._exit(78)
  raise_after_status / raise_after_intent -- same phase, but an injected EventCheckpointStoreError (the
                         process survives): to separate an exception from a real process death
  crash_after_op_done -- OPERATION_TRANSITION ...->DONE is about to be appended: re-read the operation record
                         (DONE + receipt durable, the physical apply already happened), os._exit(79)
  none                -- healthy control
Every physical apply of the executor is traced (apply_enter) so the parent counts real applies.
Usage: crash_worker.py <repo-root> <cfg.json>; prints one JSON line (result or error chain).
"""
import json
import os
import sys
import traceback
from pathlib import Path
from unittest import mock

sys.path.insert(0, sys.argv[1])
CFG = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))


def chain(exc):
    out, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        out.append({"type": type(exc).__name__, "message": str(exc)[:400]})
        exc = exc.__cause__ or exc.__context__
    return out


def main():
    from web_alarm.event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
    from web_alarm.mutation_executor import MutationExecutor
    from web_alarm.server import ApiError, WebAlarmApi

    storage, task, mode, base = Path(CFG["storage"]), CFG["task"], CFG["mode"], Path(CFG["base"])
    trace = base / f"{CFG['name']}.trace.jsonl"

    def mark(phase, **facts):
        with trace.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(dict(phase=phase, pid=os.getpid(), **facts)) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    real_event = EventCheckpointStore.append_event
    real_apply = MutationExecutor._apply
    task_dir = storage / "tasks" / "active" / task

    def event(store, task_id, kind, **kw):
        if kind == "MICROTASK_TRANSITION" and mode in ("crash_after_status", "raise_after_status"):
            micro = json.loads((task_dir / "microtasks" / f"{kw['microtask_id']}.json").read_bytes())
            mark("status_persisted_event_pending", persisted_status=micro["status"],
                 event_payload=kw.get("payload"))
            if mode == "crash_after_status":
                os._exit(70)
            raise EventCheckpointStoreError("injected: event append failed after status CAS")
        if kind == "OPERATION_INTENT" and mode in ("crash_after_intent", "raise_after_intent"):
            op = json.loads((task_dir / "operations" / f"{kw['operation_id']}.json").read_bytes())
            mark("intent_persisted_event_pending", persisted_status=op["status"], revision=op["revision"])
            if mode == "crash_after_intent":
                os._exit(78)
            raise EventCheckpointStoreError("injected: OPERATION_INTENT append failed after INTENT record")
        if (kind == "OPERATION_TRANSITION" and mode == "crash_after_op_done"
                and (kw.get("payload") or {}).get("to") == "DONE"):
            op = json.loads((task_dir / "operations" / f"{kw['operation_id']}.json").read_bytes())
            mark("op_done_persisted_event_pending", persisted_status=op["status"], revision=op["revision"],
                 receipt=op.get("receipt") is not None)
            os._exit(79)
        return real_event(store, task_id, kind, **kw)

    def apply(kind, path, data):
        mark("apply_enter", target=Path(path).name)
        return real_apply(kind, path, data)

    mark("actor_enter", action=CFG["action"], mode=mode)
    with mock.patch.object(EventCheckpointStore, "append_event", event), \
         mock.patch.object(MutationExecutor, "_apply", staticmethod(apply)):
        api = WebAlarmApi(storage)
        try:
            if CFG["action"] == "transition":
                status, reply = api.dispatch("POST", f"/microtasks/{CFG['microtask']}/transition",
                                             dict({"task_id": task, "target_status": CFG["target"]},
                                                  **CFG.get("extra", {})))
                result = {"http": status, "event_recorded": reply.get("event_recorded"),
                          "history_error": reply.get("history_error"),
                          "status": (reply.get("microtask") or {}).get("status")}
            elif CFG["action"] == "mutate":
                status, reply = api.dispatch("POST", f"/tasks/{task}/mutations", CFG["body"])
                result = {"http": status, "result": reply.get("result"), "result_code": reply.get("result_code")}
            else:
                raise ValueError("unknown action")
        except ApiError as exc:
            result = {"http": exc.status, "code": exc.code, "message": str(exc)[:400]}
        except Exception as exc:  # the parent asserts the exact chain
            result = {"raised": chain(exc), "tb": traceback.format_exc()[-800:]}
    mark("actor_exit", result=result)
    print(json.dumps(result))


main()
