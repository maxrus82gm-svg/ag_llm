"""Server-owned sequential Task Plan and persistence contract state machine."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import time
import uuid

from planner_runtime import validate_plan, validate_readiness

PERSISTENCE_RECOVERY_LIMIT = 2
READINESS_CONTINUE_LIMIT = 2
REPLAN_LIMIT = 2
RUN_LIFECYCLE_CALL_LIMIT = 64
RUN_LIFECYCLE_SECONDS = 1800


class LifecycleBlocked(RuntimeError):
    pass


class PersistencePreflightRejected(RuntimeError):
    def __init__(self, reason_code: str, next_action: str):
        self.reason_code = reason_code
        self.next_action = next_action
        super().__init__(next_action)


class PlanInvalidated(RuntimeError):
    def __init__(self, fact: dict):
        self.fact = fact
        super().__init__(fact["reason"])


def postcondition_holds(artifact: dict, snapshot: dict) -> bool:
    post = artifact["postcondition"]
    kind, value = post["kind"], post["value"]
    if kind == "absent":
        return not snapshot["exists"]
    if not snapshot["exists"]:
        return False
    if kind == "exists":
        return True
    if kind == "sha256":
        return snapshot["sha256"] == value
    if kind == "equals":
        return snapshot["content"] == value
    return value in snapshot["content"]


def atomic_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


class TaskLifecycle:
    def __init__(self, *, path: Path, run_id: str, task_block_id: str | None,
                 raw_task: str, planner_call, emit, snapshot, prepare):
        self.path, self.raw_task = path, raw_task
        self.planner_call, self.emit = planner_call, emit
        self.snapshot, self.prepare = snapshot, prepare
        self.started = time.monotonic()
        self.state = {"schema_version": 1, "run_id": run_id, "task_block_id": task_block_id,
                      "plan_id": "plan_" + uuid.uuid4().hex, "plan_version": 0,
                      "plans": [], "stage_states": {}, "active_stage_id": None,
                      "candidates": {}, "receipts": [], "replans": [], "calls": 0,
                      "recovery_attempts": {}, "readiness_attempts": {}}

    @property
    def plan(self):
        return self.state["plans"][-1]

    @property
    def stage(self):
        if not self.state["plans"]:
            return None
        sid = self.state["active_stage_id"]
        return next((s for s in self.plan["stages"] if s["stage_id"] == sid), None)

    def save(self):
        atomic_state(self.path, self.state)

    def event(self, name, **payload):
        self.emit(name, {"plan_id": self.state["plan_id"], "plan_version": self.state["plan_version"],
                         "stage_id": self.state["active_stage_id"], **payload})

    def tick(self, role):
        self.state["calls"] += 1
        if self.state["calls"] > RUN_LIFECYCLE_CALL_LIMIT or time.monotonic() - self.started > RUN_LIFECYCLE_SECONDS:
            self.block("run_lifecycle_budget_exhausted")
        self.save()

    def block(self, reason):
        if self.stage:
            self.state["stage_states"][self.stage["stage_id"]]["status"] = "BLOCKED"
        self.state["terminal_reason"] = reason
        self.save()
        self.event("stage_blocked", reason=reason)
        self.emit("run_finished", {"status": "BLOCKED", "reason": reason})
        raise LifecycleBlocked(reason)

    async def ask(self, mode, context):
        self.tick("PLANNER")
        name = "planner_readiness_started" if mode == "READINESS" else "planner_started"
        self.event(name, mode=mode)
        try:
            result = await self.planner_call(mode=mode, raw_task=self.raw_task, context=context)
            result = validate_readiness(result) if mode == "READINESS" else validate_plan(result)
        except Exception as exc:
            self.event("planner_failed", mode=mode, reason=type(exc).__name__)
            self.block("planner_protocol_or_runtime_error")
        self.event("planner_readiness_result" if mode == "READINESS" else "planner_completed",
                   mode=mode, status=result.get("status", "VALID"), reason=result.get("reason", ""))
        return result

    async def initialize(self, context):
        result = await self.ask("INITIAL", context)
        if result["obligation_changes"]:
            self.block("initial_plan_cannot_change_obligations")
        self.install(result)
        self.event("plan_created", stages_count=len(self.plan["stages"]))

    def install(self, result):
        previous = self.plan if self.state["plans"] else None
        old_states = copy.deepcopy(self.state["stage_states"])
        self.state["plan_version"] += 1
        plan = {**copy.deepcopy(result), "plan_id": self.state["plan_id"],
                "plan_version": self.state["plan_version"], "run_id": self.state["run_id"],
                "task_block_id": self.state["task_block_id"]}
        self.state["plans"].append(plan)
        states = {}
        old_stages = {s["stage_id"]: s for s in previous["stages"]} if previous else {}
        for stage in plan["stages"]:
            sid = stage["stage_id"]
            if old_stages.get(sid) == stage and old_states.get(sid, {}).get("status") == "SATISFIED":
                states[sid] = old_states[sid]
            else:
                states[sid] = {"status": "PENDING", "obligations": {
                    a["artifact_id"]: {"status": "OPEN"} for a in stage["artifacts"]}, "result": ""}
        self.state["stage_states"] = states
        self.state["active_stage_id"] = None
        self.advance()
        self.save()

    def advance(self):
        stage = next((s for s in self.plan["stages"]
                      if self.state["stage_states"][s["stage_id"]]["status"] != "SATISFIED"), None)
        self.state["active_stage_id"] = stage["stage_id"] if stage else None
        if stage:
            state = self.state["stage_states"][stage["stage_id"]]
            if "baseline" not in state:
                state["baseline"] = {}
                for artifact in stage["artifacts"]:
                    try:
                        observed = self.snapshot(artifact["path"])
                    except (PermissionError, ValueError, OSError):
                        self.block("persistence_target_unreadable_or_out_of_scope")
                    state["baseline"][artifact["artifact_id"]] = {
                        "exists": observed["exists"], "sha256": observed["sha256"],
                        "postcondition_holds": postcondition_holds(artifact, observed)}
            self.set_status("WORKING")
            self.event("stage_started", goal=stage["goal"])
        self.save()

    def set_status(self, status):
        self.state["stage_states"][self.stage["stage_id"]]["status"] = status
        self.save()
        self.event("stage_status_changed", status=status)

    def facts(self):
        stage = self.stage
        return {"plan_id": self.state["plan_id"], "plan_version": self.state["plan_version"],
                "active_stage_id": stage["stage_id"] if stage else None,
                "stage_status": self.state["stage_states"][stage["stage_id"]]["status"] if stage else "SATISFIED",
                "open_persistence_obligations": sum(
                    o["status"] == "OPEN" for s in self.state["stage_states"].values()
                    for o in s["obligations"].values())}

    def executor_context(self):
        return {**self.facts(), "current_stage": self.stage,
                "completed_results": [{"stage_id": sid, "result": s["result"][:2000]}
                                      for sid, s in self.state["stage_states"].items() if s["status"] == "SATISFIED"]}

    def artifact(self, path):
        if self.stage:
            return next((a for a in self.stage["artifacts"] if a["path"] == path), None)
        return None

    def candidate_summary(self, candidate, *, material=False):
        summary = {key: candidate[key] for key in ("run_id", "plan_id", "plan_version",
                                                  "stage_id", "artifact_id", "path", "operation", "expected")}
        summary["function_name"] = candidate["call"]["name"]
        if material:
            summary["payload"] = candidate["call"]["arguments"]
        return summary

    def new_candidate(self, call):
        if not isinstance(call, dict) or not isinstance(call.get("arguments"), dict):
            raise ValueError("Candidate must contain a concrete function and arguments")
        artifact = self.artifact(call["arguments"].get("path"))
        if artifact is None:
            raise ValueError("Mutation target is not an active stage obligation")
        state = self.state["stage_states"][self.stage["stage_id"]]
        prepared = self.prepare(call, artifact, self.can_update_created_target(artifact, state))
        cid = "candidate_" + uuid.uuid4().hex
        candidate = {"candidate_id": cid, "run_id": self.state["run_id"], "plan_id": self.state["plan_id"],
                     "plan_version": self.state["plan_version"], "stage_id": self.stage["stage_id"],
                     "artifact_id": artifact["artifact_id"], "path": artifact["path"],
                     "operation": artifact["operation"], "call": copy.deepcopy(call),
                     "before": prepared["before"], "expected": prepared["expected"],
                     "authorized": False}
        # Bounded by the shared lifecycle/tool budgets, with no duplicate material on retries.
        for old in self.state["candidates"].values():
            if not old.get("superseded") and not old.get("executed") and all(
                    old.get(k) == candidate[k] for k in ("plan_version", "stage_id", "call", "before")):
                return old
        self.state["candidates"][cid] = candidate
        self.save()
        return candidate

    def can_update_created_target(self, artifact, state):
        return state.get("repair", False) or any(
            r["stage_id"] == self.stage["stage_id"] and r["plan_version"] == self.state["plan_version"]
            and r["artifact_id"] == artifact["artifact_id"] and not r["before"]["exists"]
            and r["after"]["exists"] for r in self.state["receipts"])

    async def readiness(self, result, candidates):
        state = self.state["stage_states"][self.stage["stage_id"]]
        if state.get("repair"):
            # Execution-defect correction uses the existing contract, never replans.
            response = {"status": "READY_TO_PERSIST", "reason": "targeted execution repair",
                        "unresolved_requirements": [], "next_action": "",
                        "candidate_ids": [c["candidate_id"] for c in candidates]}
        else:
            response = await self.ask("READINESS", {
                "plan_version": self.state["plan_version"], "stage": self.stage,
                "executor_result": result[:12000], "open_persistence_obligations": [
                    aid for aid, ob in state["obligations"].items() if ob["status"] == "OPEN"],
                "candidates": [self.candidate_summary(c, material=True) for c in candidates],
                "server_facts": self.facts(),
            })
        if response["status"] == "BLOCKED":
            self.block(response["reason"])
        if response["status"] != "READY_TO_PERSIST":
            return self.readiness_continue("planner_continue", response["next_action"])
        if response["unresolved_requirements"]:
            return self.readiness_continue("ready_with_unresolved_requirements",
                                           "Resolve the listed stage requirements before persistence.")
        if self.stage["persistence_required"] and not candidates:
            return self.readiness_continue("candidate_missing", "Prepare a concrete file operation.")

        # The model's optional legacy candidate_ids are deliberately ignored. Bind only
        # the concrete objects supplied by Server to this exact readiness call.
        selected = {}
        artifacts = {a["artifact_id"]: a for a in self.stage["artifacts"]}
        for candidate in candidates:
            aid = candidate.get("artifact_id")
            artifact = artifacts.get(aid)
            if (candidate.get("run_id") != self.state["run_id"]
                    or candidate.get("plan_id") != self.state["plan_id"]
                    or candidate.get("plan_version") != self.state["plan_version"]
                    or candidate.get("stage_id") != self.stage["stage_id"]
                    or artifact is None or candidate.get("path") != artifact["path"]
                    or candidate.get("operation") != artifact["operation"]
                    or candidate.get("superseded") or candidate.get("executed")
                    or (state["obligations"][aid]["status"] != "OPEN" and not state.get("repair"))):
                return self.readiness_continue("candidate_binding_invalid",
                                               "Prepare a candidate for an open obligation in the active stage.")
            prior = selected.get(aid)
            if prior is not None and prior["candidate_id"] != candidate["candidate_id"]:
                return self.readiness_continue("candidate_ambiguous",
                                               "Provide one concrete operation per artifact obligation.")
            selected[aid] = candidate

        selected_ids = [c["candidate_id"] for c in selected.values()]
        if self.stage["persistence_required"]:
            # Prepare again immediately before acquiring the latch: no stale capability/state.
            for candidate in selected.values():
                artifact = artifacts[candidate["artifact_id"]]
                refreshed = self.prepare(candidate["call"], artifact, self.can_update_created_target(artifact, state))
                if refreshed["before"] != candidate["before"] or refreshed["expected"] != candidate["expected"]:
                    raise PlanInvalidated({"reason": "candidate_precondition_changed", "path": candidate["path"]})
                candidate["authorized"] = True
            self.set_status("READY_TO_PERSIST")
            self.set_status("PERSIST_REQUIRED")
            self.event("persistence_required", candidate_ids=selected_ids)
        return {"action": "ready", "candidate_ids": selected_ids}

    def readiness_continue(self, reason_code, next_action):
        if self.stage:
            key = f'{self.state["plan_version"]}:{self.stage["stage_id"]}'
            count = self.state["readiness_attempts"].get(key, 0) + 1
            self.state["readiness_attempts"][key] = count
            self.save()
            self.event("planner_readiness_rejected", reason_code=reason_code, executed=False)
            if count > READINESS_CONTINUE_LIMIT:
                self.block("readiness_no_progress")
        return {"action": "continue", "reason_code": reason_code, "reason": next_action}

    async def before_mutation(self, call):
        candidate = self.new_candidate(call)
        if not candidate["authorized"]:
            decision = await self.readiness("Proposed concrete tool operation", [candidate])
            if decision["action"] != "ready":
                raise PersistencePreflightRejected(decision["reason_code"], decision["reason"])
        # The caller must still run its ordinary permission/backup/tool dispatcher.
        return candidate["candidate_id"]

    def after_mutation(self, candidate_id, result):
        candidate = self.state["candidates"][candidate_id]
        if result.get("path") != candidate["path"]:
            self.block("mutation_receipt_target_mismatch")
        if candidate["plan_version"] != self.state["plan_version"] or candidate["stage_id"] != self.stage["stage_id"]:
            self.block("mutation_candidate_identity_mismatch")
        actual = self.snapshot(candidate["path"])
        expected = candidate["expected"]
        if {k: actual[k] for k in ("exists", "sha256")} != expected:
            self.block("mutation_readback_mismatch")
        if actual["exists"] and result.get("content_sha256") != actual["sha256"]:
            self.block("mutation_receipt_hash_mismatch")
        artifact = self.artifact(candidate["path"])
        satisfied = postcondition_holds(artifact, actual)
        receipt = {"candidate_id": candidate_id, "plan_version": candidate["plan_version"],
                   "stage_id": candidate["stage_id"], "artifact_id": artifact["artifact_id"],
                   "path": candidate["path"], "operation": candidate["operation"],
                   "before": candidate["before"], "after": expected, "executed": True}
        self.state["receipts"].append(receipt)
        candidate["executed"] = True
        self.state["stage_states"][self.stage["stage_id"]]["obligations"][artifact["artifact_id"]] = {
            "status": "SATISFIED" if satisfied else "OPEN", "receipt": receipt}
        self.save()
        self.event("persistence_satisfied" if satisfied else "persistence_unsatisfied", artifact_id=artifact["artifact_id"], path=artifact["path"],
                   content_sha256=actual["sha256"], outcome="MUTATED")

    def check_obligations(self, stage=None):
        stage = stage or self.stage
        state = self.state["stage_states"][stage["stage_id"]]
        for artifact in stage["artifacts"]:
            ob = state["obligations"][artifact["artifact_id"]]
            actual = self.snapshot(artifact["path"])
            if ob["status"] != "OPEN":
                expected = ob.get("receipt", {}).get("after", ob.get("observed"))
                if expected != {k: actual[k] for k in ("exists", "sha256")} or not postcondition_holds(artifact, actual):
                    raise PlanInvalidated({"reason": "satisfied_target_changed", "path": artifact["path"]})
            elif (artifact["allow_already_satisfied"]
                  and not state.get("repair")
                  and state["baseline"][artifact["artifact_id"]]["postcondition_holds"]
                  and state["baseline"][artifact["artifact_id"]]["sha256"] == actual["sha256"]
                  and state["baseline"][artifact["artifact_id"]]["exists"] == actual["exists"]
                  and postcondition_holds(artifact, actual)):
                state["obligations"][artifact["artifact_id"]] = {
                    "status": "ALREADY_SATISFIED", "observed": {k: actual[k] for k in ("exists", "sha256")}}
                self.event("persistence_satisfied", artifact_id=artifact["artifact_id"], path=artifact["path"],
                           outcome="ALREADY_SATISFIED", executed=False)
        self.save()
        return all(ob["status"] != "OPEN" for ob in state["obligations"].values())

    def recovery(self):
        key = f'{self.state["plan_version"]}:{self.stage["stage_id"]}'
        count = self.state["recovery_attempts"].get(key, 0) + 1
        self.state["recovery_attempts"][key] = count
        self.event("persistence_unsatisfied", **self.facts())
        if count > PERSISTENCE_RECOVERY_LIMIT:
            self.event("persistence_recovery_exhausted", attempts=count - 1)
            self.block("persistence_recovery_exhausted")
        self.save()
        self.event("persistence_recovery_started", attempt=count)

    def next_prepared_call(self):
        if not self.stage:
            return None
        state = self.state["stage_states"][self.stage["stage_id"]]
        for candidate in self.state["candidates"].values():
            if (candidate["plan_version"] != self.state["plan_version"]
                    or candidate["stage_id"] != self.stage["stage_id"]
                    or not candidate["authorized"] or candidate.get("superseded") or candidate.get("executed")
                    or state["obligations"][candidate["artifact_id"]]["status"] != "OPEN"):
                continue
            artifact = self.artifact(candidate["path"])
            prepared = self.prepare(candidate["call"], artifact, self.can_update_created_target(artifact, state))
            if prepared["before"] != candidate["before"]:
                raise PlanInvalidated({"reason": "prepared_operation_became_stale", "path": candidate["path"]})
            return copy.deepcopy(candidate["call"])
        return None

    async def on_stop(self, content):
        if not self.stage:
            self.assert_satisfied()
            return {"action": "final"}
        if self.stage["persistence_required"]:
            if self.check_obligations():
                return self.complete(content)
            self.recovery()
            prepared = self.next_prepared_call()
            if prepared:
                return {"action": "dispatch", "call": prepared}
            candidates = []
            try:
                envelope = json.loads(content)
            except (ValueError, TypeError):
                envelope = None
            if isinstance(envelope, dict) and isinstance(envelope.get("candidates"), list):
                if len(envelope["candidates"]) > 16:
                    self.block("too_many_candidates")
                for call in envelope["candidates"]:
                    candidates.append(self.new_candidate(call))
            if not candidates:
                candidates = [c for c in self.state["candidates"].values()
                              if not c.get("superseded") and not c.get("executed")
                              and c["stage_id"] == self.stage["stage_id"]
                              and c["plan_version"] == self.state["plan_version"]
                              and self.state["stage_states"][self.stage["stage_id"]]["obligations"][c["artifact_id"]]["status"] == "OPEN"]
            response = await self.readiness(content, candidates)
            if response["action"] == "ready":
                return {"action": "dispatch", "call": self.state["candidates"][response["candidate_ids"][0]]["call"]}
            return response
        response = await self.readiness(content, [])
        if response["action"] == "ready":
            if not content.strip():
                self.block("empty_stage_result")
            return self.complete(content)
        return response

    def complete(self, content):
        sid = self.stage["stage_id"]
        self.state["stage_states"][sid]["result"] = content[:4000]
        self.set_status("SATISFIED")
        self.event("stage_satisfied")
        self.advance()
        if self.stage:
            return {"action": "next_stage"}
        self.assert_satisfied()
        return {"action": "final"}

    def assert_satisfied(self):
        for stage in self.plan["stages"]:
            if self.state["stage_states"][stage["stage_id"]]["status"] != "SATISFIED" or not self.check_obligations(stage):
                self.state["active_stage_id"] = stage["stage_id"]
                self.block("open_obligations_before_final")

    async def replan(self, fact):
        if len(self.state["replans"]) >= REPLAN_LIMIT:
            self.block("replan_budget_exhausted")
        fact = {**fact, "fact_id": "fact_" + uuid.uuid4().hex[:12]}
        self.event("replan_started", reason=fact["reason"], fact_id=fact["fact_id"])
        response = await self.ask("REPLAN", {"current_plan": self.plan,
            "stage_states": self.state["stage_states"], "authoritative_facts": [fact]})
        old = {a["artifact_id"]: a for s in self.plan["stages"] for a in s["artifacts"]}
        new = {a["artifact_id"]: a for s in response["stages"] for a in s["artifacts"]}
        changes = {c["old_artifact_id"]: c for c in response["obligation_changes"]}
        if len(changes) != len(response["obligation_changes"]):
            self.block("duplicate_obligation_change")
        for aid, artifact in old.items():
            if new.get(aid) != artifact and aid not in changes:
                self.block("replan_dropped_obligation")
        if set(changes) - set(old) or any(c["fact_id"] != fact["fact_id"] for c in changes.values()):
            self.block("replan_unproven_obligation_change")
        for aid, change in changes.items():
            if change["action"] == "cancel" and aid in new:
                self.block("cancelled_obligation_still_in_plan")
        self.state["replans"].append({"from_version": self.state["plan_version"],
                                      "fact": fact, "obligation_changes": response["obligation_changes"],
                                      "prior_stage_states": copy.deepcopy(self.state["stage_states"])})
        self.install(response)
        self.event("plan_revised", fact_id=fact["fact_id"])
        self.event("replan_completed")

    def execution_defect(self, affected_stage_ids):
        ids = set(affected_stage_ids)
        known = {s["stage_id"] for s in self.plan["stages"]}
        if ids - known:
            self.block("unknown_audit_stage")
        # Backwards-compatible UNKNOWN routing repairs the last stage, never infers prose.
        if not ids:
            ids = {self.plan["stages"][-1]["stage_id"]}
        for sid in ids:
            state = self.state["stage_states"][sid]
            state["status"] = "PENDING"
            state["repair"] = True
            # Reopen the stage, retaining verified persistence receipts. The defect may
            # concern only one artifact, verification, or the final response. Requiring
            # every artifact to mutate again would manufacture meaningless writes.
            # Repaired targets receive new receipts; all targets are rechecked on stop.
        for candidate in self.state["candidates"].values():
            if candidate["stage_id"] in ids:
                candidate["authorized"] = False
                candidate["superseded"] = True
        self.advance()

    def evidence(self):
        return {"plan_id": self.state["plan_id"], "plan_version": self.state["plan_version"],
                "stages": self.plan["stages"], "stage_states": self.state["stage_states"],
                "replans": [{k: r[k] for k in ("from_version", "fact", "obligation_changes")}
                            for r in self.state["replans"]]}
