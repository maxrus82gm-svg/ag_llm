"""Fresh-process re-open for CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001 (no fault patches at all).

Reads the disposable TEMP storage twice: as raw bytes (independent oracle: JSON files, the TASK history
split on the physical LF, the workspace target) and through the server's own views (OperationStore,
ProjectionService, checkpoint validation, closeout inspect). Then runs the requested follow-up steps
in order, each recorded with its outcome, and re-reads the raw state. Never patches production code.
Usage: reopen_inspector.py <repo-root> <cfg.json>; prints one JSON document.
cfg: storage, task, project, followups: [{"kind": ..., ...}]
"""
import hashlib
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, sys.argv[1])
CFG = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))


def chain(exc):
    out, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        out.append({"type": type(exc).__name__, "message": str(exc)[:300]})
        exc = exc.__cause__ or exc.__context__
    return out


def attempt(fn):
    try:
        return {"ok": fn()}
    except Exception as exc:  # recorded, the parent decides
        return {"error": chain(exc)}


def raw_state(storage: Path, task: str, project: Path) -> dict:
    active, completed = storage / "tasks" / "active" / task, storage / "tasks" / "completed" / task
    task_dir = active if active.is_dir() else completed
    events_bytes = (task_dir / "events.jsonl").read_bytes() if (task_dir / "events.jsonl").is_file() else b""
    events, invalid = [], 0
    for chunk in events_bytes.split(b"\n")[:-1]:
        try:
            item = json.loads(chunk)
        except ValueError:
            invalid += 1
            continue
        payload = item.get("payload") or {}
        events.append([item["event_type"], item.get("microtask_id"), item.get("operation_id"),
                       payload.get("from"), payload.get("to"),
                       bool(payload.get("verification_evidence"))])
    micro = {p.stem: json.loads(p.read_bytes())["status"] for p in sorted((task_dir / "microtasks").glob("*.json"))}
    ops = {}
    for p in sorted((task_dir / "operations").glob("*.json")) if (task_dir / "operations").is_dir() else []:
        rec = json.loads(p.read_bytes())
        ops[p.stem] = {"status": rec["status"], "revision": rec.get("revision"),
                       "settlement": (rec.get("recovery_settlement") or {}).get("action")}
    checkpoint = (json.loads((task_dir / "checkpoint.json").read_bytes()).get("current_status")
                  if (task_dir / "checkpoint.json").is_file() else None)
    payload_files = sorted(p.name for p in (task_dir / "payloads").rglob("*") if p.is_file()) \
        if (task_dir / "payloads").is_dir() else []
    return {
        "location": "active" if task_dir == active else "completed",
        "task_status": json.loads((task_dir / "task.json").read_bytes())["status"],
        "plan_current": json.loads((task_dir / "plan.json").read_bytes()).get("current_microtask_id"),
        "microtasks": micro, "operations": ops, "checkpoint_status": checkpoint,
        "events": events, "events_invalid_lines": invalid,
        "events_sha256": hashlib.sha256(events_bytes).hexdigest(),
        "events_terminated": events_bytes == b"" or events_bytes.endswith(b"\n"),
        "payload_files": payload_files,
        "target_sha256": hashlib.sha256((project / "data.bin").read_bytes()).hexdigest(),
    }


def views(storage: Path, task: str) -> dict:
    from web_alarm.closeout import CloseoutService
    from web_alarm.operation_store import OperationStore
    from web_alarm.projection import ProjectionService
    out = {}
    out["operations_list"] = attempt(lambda: [r.operation_id for r in OperationStore(storage).list(task)])
    projection = attempt(lambda: ProjectionService(storage).build(task))
    if "ok" in projection:
        p = projection["ok"]
        out["projection"] = {"blockers": [b["code"] for b in p["blockers"]],
                             "diagnostics": [d["code"] for d in p["diagnostics"]],
                             "current_status": p["position"]["current_status"],
                             "authority_source": p["authority_source"],
                             "recovery_state": p["recovery"]["state"],
                             "next_safe_action": p["next_safe_action"][:240]}
        out["checkpoint_validation"] = attempt(
            lambda: ProjectionService(storage).validate_checkpoint(task, p)["status"])
    else:
        out["projection"] = projection
    inspect = attempt(lambda: CloseoutService(storage).inspect(task))
    out["closeout_inspect"] = ({"eligible": inspect["ok"]["eligible"],
                                "blockers": [b["code"] for b in inspect["ok"]["blockers"]]}
                               if "ok" in inspect else inspect)
    return out


def follow(step: dict, storage: Path, task: str) -> dict:
    from web_alarm.closeout import CloseoutService
    from web_alarm.operation_store import OperationStore
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    from web_alarm.resolver_service import ResolverService
    from web_alarm.server import ApiError, WebAlarmApi
    kind = step["kind"]

    def http(method, path, body):
        try:
            status, reply = WebAlarmApi(storage).dispatch(method, path, body)
            return {"http": status, "result": reply.get("result"), "result_code": reply.get("result_code"),
                    "event_recorded": reply.get("event_recorded"),
                    "status": (reply.get("microtask") or {}).get("status")}
        except ApiError as exc:
            return {"http": exc.status, "code": exc.code, "message": str(exc)[:300]}

    if kind == "transition":
        return http("POST", f"/microtasks/{step['microtask']}/transition",
                    dict({"task_id": task, "target_status": step["target"]}, **step.get("extra", {})))
    if kind == "mutate":
        return http("POST", f"/tasks/{task}/mutations", step["body"])
    if kind == "closeout":
        return attempt(lambda: {k: v for k, v in CloseoutService(storage).complete(task).items()
                                if k in ("result", "completed", "event_recorded", "resumed")}
                       | {"blockers": [b["code"] for b in (CloseoutService(storage).inspect(task)["blockers"])]})
    if kind == "recover":
        return attempt(lambda: {k: (v if isinstance(v, (str, int, bool, type(None))) else str(v)[:300])
                                for k, v in RecoveryCoordinator(storage).recover(task).items()})
    if kind == "get_operation":
        return attempt(lambda: OperationStore(storage).get(task, step["operation"]).status.value)
    if kind == "resolve":
        return attempt(lambda: {k: (v.to_dict() if hasattr(v, "to_dict") else v)
                                for k, v in ResolverService(storage).apply(
                                    task, step["microtask"], step["operation"], step["action"],
                                    evidence_fingerprint=step.get("evidence_fingerprint", "probe"),
                                    operation_revision=step.get("revision")).items()
                                if k in ("accepted", "created")})
    raise ValueError(kind)


def main():
    storage, task, project = Path(CFG["storage"]), CFG["task"], Path(CFG["project"])
    report = {"before": {"raw": raw_state(storage, task, project), "views": views(storage, task)},
              "followups": []}
    for step in CFG.get("followups", []):
        try:
            outcome = follow(step, storage, task)
        except Exception as exc:
            outcome = {"error": chain(exc), "tb": traceback.format_exc()[-600:]}
        report["followups"].append({"step": step["kind"], "args": {k: v for k, v in step.items()
                                                                    if k not in ("kind", "body")},
                                    "outcome": outcome, "raw_after": raw_state(storage, task, project)})
    report["after"] = {"views": views(storage, task)}
    print(json.dumps(report, ensure_ascii=True, default=str))


main()
