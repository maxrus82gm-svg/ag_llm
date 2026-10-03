"""Server-owned sequential Task Plan and persistence contract state machine."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from planner_runtime import PlannerError, validate_plan, validate_readiness

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


def evidence_arguments_fingerprint(arguments: dict) -> str:
    encoded = json.dumps(
        arguments,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evidence_target_state_fingerprint(snapshot: dict) -> str:
    payload = {
        "exists": bool(snapshot.get("exists")),
        "sha256": snapshot.get("sha256"),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evidence_dependency_targets(tool: str, arguments: dict) -> list[str]:
    targets = []
    path = arguments.get("path")
    if isinstance(path, str) and path:
        targets.append(path)
    paths = arguments.get("paths")
    if isinstance(paths, list):
        targets.extend(
            item for item in paths
            if isinstance(item, str) and item
        )
    if tool == "ui_smoke_test":
        targets.append("ultra_ui.py")
    return list(dict.fromkeys(targets))


def evidence_dependency_state_fingerprint(
    snapshot_fn,
    tool: str,
    arguments: dict,
) -> str | None:
    targets = evidence_dependency_targets(tool, arguments)
    if not targets:
        return None
    payload = []
    for target in targets:
        snapshot = snapshot_fn(target)
        payload.append({
            "target": target,
            "exists": bool(snapshot.get("exists")),
            "sha256": snapshot.get("sha256"),
        })
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_replan_against_fact(previous_plan: dict, candidate: dict, fact: dict) -> None:
    """Reject a candidate plan that demonstrably preserves a server-known conflict."""
    if fact.get("reason") != "create_target_already_exists":
        return
    path = fact.get("path")
    if not isinstance(path, str) or not path:
        return
    old_conflicts = [
        artifact
        for stage in previous_plan["stages"]
        for artifact in stage["artifacts"]
        if artifact["path"] == path and artifact["operation"] == "create"
    ]
    if not old_conflicts:
        return
    for stage in candidate["stages"]:
        for artifact in stage["artifacts"]:
            if artifact["path"] != path:
                continue
            if (artifact["operation"] == "create"
                    and artifact["allow_already_satisfied"] is False):
                raise PlannerError(
                    "Replan did not resolve authoritative fact: "
                    f"create_target_already_exists for {path}"
                )
            if (fact.get("postcondition_holds") is True
                    and any(
                        artifact["postcondition"] == old["postcondition"]
                        for old in old_conflicts
                    )
                    and artifact["allow_already_satisfied"] is False):
                raise PlannerError(
                    "Existing target already satisfies the unchanged postcondition; "
                    "REPLAN must explicitly set allow_already_satisfied=true "
                    "or define a genuinely different required state."
                )


def validate_replan_transition(previous_plan: dict, candidate: dict, fact: dict) -> None:
    validate_replan_against_fact(previous_plan, candidate, fact)
    old = {
        artifact["artifact_id"]: artifact
        for stage in previous_plan["stages"]
        for artifact in stage["artifacts"]
    }
    new = {
        artifact["artifact_id"]: artifact
        for stage in candidate["stages"]
        for artifact in stage["artifacts"]
    }
    changes_list = candidate["obligation_changes"]
    changes = {change["old_artifact_id"]: change for change in changes_list}
    if len(changes) != len(changes_list):
        raise PlannerError("REPLAN contains duplicate obligation_changes old_artifact_id")
    for artifact_id, artifact in old.items():
        if new.get(artifact_id) != artifact and artifact_id not in changes:
            raise PlannerError(
                f"REPLAN changed or dropped obligation {artifact_id!r} without obligation_changes"
            )
    unknown = set(changes) - set(old)
    if unknown:
        raise PlannerError(
            "REPLAN obligation_changes reference unknown old_artifact_id: "
            + ", ".join(sorted(unknown))
        )
    if any(change["fact_id"] != fact["fact_id"] for change in changes.values()):
        raise PlannerError("REPLAN obligation_changes must reference the supplied authoritative fact_id")
    for artifact_id, change in changes.items():
        if change["action"] == "cancel" and artifact_id in new:
            raise PlannerError(
                f"REPLAN cannot cancel obligation {artifact_id!r} while keeping it in the new plan"
            )


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
                 raw_task: str, planner_call, emit, snapshot, prepare,
                 planner_session_id: str | None = None, planner_feedback=None,
                 planner_review=None, dredd_enabled: bool = True):
        self.path, self.raw_task = path, raw_task
        self.planner_call, self.emit = planner_call, emit
        self.snapshot, self.prepare = snapshot, prepare
        self.planner_session_id = planner_session_id or "ps_" + uuid.uuid4().hex
        self.planner_feedback = planner_feedback
        self.planner_review = planner_review
        self.dredd_enabled = dredd_enabled
        self.available_tools: set[str] | None = None
        self._planner_session_started = False
        self._planner_session_terminal = False
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
        if not self._planner_session_terminal:
            self._planner_session_terminal = True
            self.event("planner_session_blocked", session_id=self.planner_session_id,
                       task_block_id=self.state["task_block_id"], reason=reason)
        self.event("stage_blocked", reason=reason)
        self.emit("run_finished", {"status": "BLOCKED", "reason": reason})
        raise LifecycleBlocked(reason)

    def _session_feedback(self, *, speaker, mode, attempt, text):
        if self.planner_feedback is not None:
            self.planner_feedback(speaker=speaker, mode=mode, attempt=attempt, text=text)

    def validate_evidence_tools_available(self, result: dict) -> None:
        if self.available_tools is None:
            return
        for stage in result["stages"]:
            for requirement in stage.get("evidence_requirements") or []:
                if requirement["tool"] not in self.available_tools:
                    raise PlannerError(
                        "Evidence requirement uses unavailable tool: "
                        f"{requirement['tool']}"
                    )

    async def ask(self, mode, context, candidate_validator=None):
        name = "planner_readiness_started" if mode == "READINESS" else "planner_started"
        self.event(name, mode=mode)
        max_attempts = 3 if self.dredd_enabled and self.planner_review is not None else 2
        for attempt in range(1, max_attempts + 1):
            self.tick("PLANNER")
            try:
                result = await self.planner_call(
                    mode=mode, raw_task=self.raw_task, context=context, attempt=attempt,
                )
                result = (
                    validate_readiness(result)
                    if mode == "READINESS"
                    else validate_plan(result, raw_task=self.raw_task)
                )
                if candidate_validator is not None:
                    candidate_validator(result)
            except Exception as exc:
                error_type = type(exc).__name__
                error_message = str(exc) if isinstance(exc, PlannerError) else error_type
                self.event("planner_attempt_rejected", session_id=self.planner_session_id,
                           task_block_id=self.state["task_block_id"], mode=mode,
                           attempt=attempt, error_type=error_type,
                           error_message=error_message)
                if attempt == 1:
                    self._session_feedback(
                        speaker="SERVER", mode=mode, attempt=attempt,
                        text=("SERVER VALIDATION\n\nPrevious Planner response is invalid.\n"
                              f"Mode: {mode}\nValidation error: {error_message}\n\n"
                              "Correct the previous response.\n"
                              "Return the FULL corrected structured response required for this mode.\n"
                              "Do not omit required fields.\n"
                              "Do not return prose outside the required JSON."),
                    )
                    continue
                if attempt == 2 and max_attempts == 3:
                    self.event("planner_dredd_review_started", session_id=self.planner_session_id,
                               task_block_id=self.state["task_block_id"], mode=mode)
                    try:
                        review = await self.planner_review(mode=mode, validation_error=error_message)
                    except Exception as review_exc:
                        review_error_message = str(review_exc)[:1000]
                        planner_error_message = error_message
                        self.event(
                            "planner_dredd_review_failed",
                            session_id=self.planner_session_id,
                            task_block_id=self.state["task_block_id"],
                            mode=mode,
                            planner_validation_error=planner_error_message,
                            review_error_type=type(review_exc).__name__,
                            review_error_message=review_error_message,
                        )
                        self.event(
                            "planner_failed",
                            mode=mode,
                            reason="planner_dredd_review_error",
                            error_type=type(review_exc).__name__,
                            error_message=review_error_message,
                            planner_error_type=error_type,
                            planner_error_message=planner_error_message,
                        )
                        self.block("planner_protocol_or_runtime_error")
                    review_payload = (review if isinstance(review, dict)
                                      else {key: getattr(review, key) for key in (
                                          "diagnosis", "required_action", "verifier_run_id",
                                          "model_id", "model_display_name", "provider_model_id",
                                          "usage")})
                    self.event("planner_dredd_review_completed",
                               session_id=self.planner_session_id,
                               task_block_id=self.state["task_block_id"], mode=mode,
                               **review_payload)
                    self._session_feedback(
                        speaker="DREDD", mode=mode, attempt=attempt,
                        text=("DREDD REVIEW\n\nDiagnosis:\n"
                              f"{review_payload['diagnosis']}\n\nRequired action:\n"
                              f"{review_payload['required_action']}\n\n"
                              "This is the final Planner retry.\n"
                              f"Return the FULL corrected structured response for mode {mode}."),
                    )
                    continue
                failure = {"mode": mode, "reason": error_type, "error_type": error_type}
                if isinstance(exc, PlannerError):
                    failure["error_message"] = str(exc)
                self.event("planner_failed", **failure)
                self.block("planner_protocol_or_runtime_error")
            self.event("planner_readiness_result" if mode == "READINESS" else "planner_completed",
                       mode=mode, status=result.get("status", "VALID"), reason=result.get("reason", ""))
            return result
        raise AssertionError("unreachable Planner attempt loop")

    async def initialize(self, context):
        if "tools" in context:
            self.available_tools = {
                item["name"]
                for item in (context.get("tools") or [])
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
        if not self._planner_session_started:
            self._planner_session_started = True
            self.event("planner_session_started", session_id=self.planner_session_id,
                       task_block_id=self.state["task_block_id"], status="ACTIVE")
        def validate_initial(result):
            if result["obligation_changes"]:
                raise PlannerError(
                    "INITIAL plan must return obligation_changes=[] because no previous plan exists."
                )
            self.validate_evidence_tools_available(result)
        result = await self.ask("INITIAL", context, validate_initial)
        self.install(result)
        self.event("plan_created", stages_count=len(self.plan["stages"]))
        self._session_feedback(speaker="SERVER", mode="INITIAL", attempt=None,
                               text=f"PLAN VALID · v{self.state['plan_version']}")

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
            old_state = old_states.get(sid, {})
            can_preserve = (
                stage["persistence_required"]
                and old_stages.get(sid) == stage
                and old_state.get("status") == "SATISFIED"
            )
            if can_preserve:
                states[sid] = old_state
                states[sid].setdefault("evidence_generation", 0)
            else:
                prior_generation = int(old_state.get("evidence_generation", 0))
                states[sid] = {
                    "status": "PENDING",
                    "obligations": {
                        a["artifact_id"]: {"status": "OPEN"}
                        for a in stage["artifacts"]
                    },
                    "result": "",
                    "evidence_generation": (
                        prior_generation + 1 if previous is not None else 0
                    ),
                }
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
            if (stage["persistence_required"]
                    and not state.get("repair")
                    and self.check_obligations(stage)):
                state["result"] = "Persistence obligations already satisfied at stage baseline."
                self.save()
                self.set_status("SATISFIED")
                self.event("stage_satisfied")
                return self.advance()
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
        if satisfied and self.check_obligations():
            return self.complete("Persistence obligations satisfied by server readback.")
        return None

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

    def _matched_evidence_requirement_ids_for_stage(
        self,
        stage: dict,
        stage_evidence,
    ):
        if stage["persistence_required"]:
            return []
        matched = []
        state = self.state["stage_states"][stage["stage_id"]]
        current_generation = int(state.get("evidence_generation", 0))
        facts = [
            item
            for item in (stage_evidence or [])
            if item.get("task_block_id") == self.state["task_block_id"]
            and item.get("run_id") == self.state["run_id"]
            and item.get("plan_version") == self.state["plan_version"]
            and item.get("stage_id") == stage["stage_id"]
            and int(item.get("evidence_generation", -1)) == current_generation
            and isinstance(item.get("source_record_id"), str)
            and item.get("source_record_id")
            and item.get("status") == "OK"
            and item.get("executed") is True
        ]
        for requirement in stage.get("evidence_requirements") or []:
            expected_fingerprint = evidence_arguments_fingerprint(
                requirement["arguments"]
            )
            dependency_targets = evidence_dependency_targets(
                requirement["tool"],
                requirement["arguments"],
            )
            current_state_fingerprint = None
            if dependency_targets:
                try:
                    current_state_fingerprint = (
                        evidence_dependency_state_fingerprint(
                            self.snapshot,
                            requirement["tool"],
                            requirement["arguments"],
                        )
                    )
                except (PermissionError, ValueError, OSError):
                    current_state_fingerprint = None
            if any(
                item.get("tool") == requirement["tool"]
                and item.get("arguments_sha256") == expected_fingerprint
                and requirement["evidence_id"] in (
                    item.get("requirement_ids") or []
                )
                and (
                    not dependency_targets
                    or (
                        current_state_fingerprint is not None
                        and item.get("observed_state_sha256")
                        == current_state_fingerprint
                    )
                )
                for item in facts
            ):
                matched.append(requirement["evidence_id"])
        return matched

    def matched_evidence_requirement_ids(self, stage_evidence):
        if not self.stage:
            return []
        return self._matched_evidence_requirement_ids_for_stage(
            self.stage,
            stage_evidence,
        )

    def remaining_evidence_requirements_for_stage(
        self,
        stage: dict,
        stage_evidence,
    ) -> list[dict]:
        matched = set(
            self._matched_evidence_requirement_ids_for_stage(
                stage,
                stage_evidence,
            )
        )
        return [
            copy.deepcopy(requirement)
            for requirement in stage.get("evidence_requirements") or []
            if requirement["evidence_id"] not in matched
        ]

    def invalidate_stale_satisfied_evidence(self, stage_evidence) -> list[str]:
        stale = []
        for stage in self.plan["stages"]:
            state = self.state["stage_states"][stage["stage_id"]]
            requirements = stage.get("evidence_requirements") or []
            if (
                state.get("status") != "SATISFIED"
                or stage["persistence_required"]
                or not requirements
            ):
                continue
            matched = set(
                self._matched_evidence_requirement_ids_for_stage(
                    stage,
                    stage_evidence,
                )
            )
            required = {
                item["evidence_id"]
                for item in requirements
            }
            if required.issubset(matched):
                continue
            state["status"] = "PENDING"
            state["repair"] = True
            state["result"] = ""
            state["evidence_generation"] = int(
                state.get("evidence_generation", 0)
            ) + 1
            stale.append(stage["stage_id"])
            self.event(
                "evidence_invalidated",
                stale_stage_id=stage["stage_id"],
                previous_generation=state["evidence_generation"] - 1,
                new_generation=state["evidence_generation"],
                reason="evidence_snapshot_or_identity_stale",
            )
        if stale:
            self.state["active_stage_id"] = None
            self.advance()
            self.save()
        return stale

    def evidence_freshness_snapshot(self, stage_evidence) -> dict:
        """Return the authoritative identity/coverage payload used by freshness binding."""
        stages = []
        for stage in self.plan["stages"]:
            state = self.state["stage_states"][stage["stage_id"]]
            if stage["persistence_required"]:
                artifacts = []
                for artifact in stage["artifacts"]:
                    snapshot = self.snapshot(artifact["path"])
                    obligation = state["obligations"][
                        artifact["artifact_id"]
                    ]
                    artifacts.append({
                        "artifact_id": artifact["artifact_id"],
                        "path": artifact["path"],
                        "operation": artifact["operation"],
                        "obligation_status": obligation["status"],
                        "observed_state_sha256": (
                            evidence_target_state_fingerprint(snapshot)
                        ),
                    })
                stages.append({
                    "stage_id": stage["stage_id"],
                    "persistence_required": True,
                    "artifacts": artifacts,
                })
                continue
            requirements = stage.get("evidence_requirements") or []
            if not requirements:
                continue
            stage_item = {
                "stage_id": stage["stage_id"],
                "persistence_required": False,
                "evidence_generation": int(
                    state.get("evidence_generation", 0)
                ),
                "requirements": [],
            }
            for requirement in requirements:
                dependency_targets = evidence_dependency_targets(
                    requirement["tool"],
                    requirement["arguments"],
                )
                target_state = None
                if dependency_targets:
                    try:
                        target_state = evidence_dependency_state_fingerprint(
                            self.snapshot,
                            requirement["tool"],
                            requirement["arguments"],
                        )
                    except (PermissionError, ValueError, OSError):
                        target_state = "UNRESOLVED"
                expected_args = evidence_arguments_fingerprint(
                    requirement["arguments"]
                )
                source_records = sorted(
                    [
                        {
                            "source_record_id": item["source_record_id"],
                            "sequence": item.get("sequence"),
                            "result_sha256": (
                                item.get("result") or {}
                            ).get("sha256"),
                            "observed_state_sha256": item.get(
                                "observed_state_sha256"
                            ),
                        }
                        for item in (stage_evidence or [])
                        if item.get("task_block_id")
                        == self.state["task_block_id"]
                        and item.get("run_id") == self.state["run_id"]
                        and item.get("plan_version")
                        == self.state["plan_version"]
                        and item.get("stage_id") == stage["stage_id"]
                        and int(item.get("evidence_generation", -1))
                        == int(state.get("evidence_generation", 0))
                        and requirement["evidence_id"] in (
                            item.get("requirement_ids") or []
                        )
                        and item.get("tool") == requirement["tool"]
                        and item.get("arguments_sha256") == expected_args
                        and item.get("status") == "OK"
                        and item.get("executed") is True
                        and isinstance(item.get("source_record_id"), str)
                        and item.get("source_record_id")
                    ],
                    key=lambda item: item["source_record_id"],
                )
                stage_item["requirements"].append({
                    "evidence_id": requirement["evidence_id"],
                    "tool": requirement["tool"],
                    "arguments_sha256": expected_args,
                    "target_identity": list(dependency_targets),
                    "target_state_sha256": target_state,
                    "source_records": source_records,
                })
            stages.append(stage_item)
        return {
            "task_block_id": self.state["task_block_id"],
            "run_id": self.state["run_id"],
            "plan_id": self.state["plan_id"],
            "plan_version": self.state["plan_version"],
            "stages": stages,
        }

    def evidence_freshness_snapshot_sha256(self, stage_evidence) -> str:
        payload = self.evidence_freshness_snapshot(stage_evidence)
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def minimum_remaining_tool_calls(self, stage_evidence) -> int:
        minimum = 0
        for stage in self.plan["stages"]:
            state = self.state["stage_states"][stage["stage_id"]]
            if state["status"] == "SATISFIED":
                continue
            if stage["persistence_required"]:
                minimum += sum(
                    obligation["status"] == "OPEN"
                    for obligation in state["obligations"].values()
                )
            else:
                minimum += len(
                    self.remaining_evidence_requirements_for_stage(
                        stage,
                        stage_evidence,
                    )
                )
        return minimum

    def current_reserved_tool_names(self, stage_evidence) -> set[str]:
        if not self.stage:
            return set()
        state = self.state["stage_states"][self.stage["stage_id"]]
        if self.stage["persistence_required"]:
            names = set()
            artifacts = {
                artifact["artifact_id"]: artifact
                for artifact in self.stage["artifacts"]
            }
            for artifact_id, obligation in state["obligations"].items():
                if obligation["status"] != "OPEN":
                    continue
                operation = artifacts[artifact_id]["operation"]
                if operation == "delete":
                    names.add("delete_file")
                elif operation == "create":
                    names.add("write_file")
                else:
                    names.update({
                        "write_file",
                        "replace_text",
                        "insert_before",
                        "insert_after",
                    })
            return names
        return {
            requirement["tool"]
            for requirement in self.remaining_evidence_requirements_for_stage(
                self.stage,
                stage_evidence,
            )
        }

    def non_persistence_evidence_satisfied(self, stage_evidence):
        if not self.stage or self.stage["persistence_required"]:
            return False
        requirements = self.stage.get("evidence_requirements") or []
        if not requirements:
            return False
        matched = set(self.matched_evidence_requirement_ids(stage_evidence))
        return all(item["evidence_id"] in matched for item in requirements)

    def _complete_server_evidence_stage(self, stage_evidence):
        requirements = self.stage.get("evidence_requirements") or []
        evidence_ids = self.matched_evidence_requirement_ids(stage_evidence)
        self.event(
            "non_persistence_evidence_satisfied",
            completion_mode="server_evidence",
            evidence_ids=evidence_ids,
            tools=[item["tool"] for item in requirements],
            evidence_count=len(stage_evidence or []),
        )
        result = json.dumps(
            {
                "completion": "server_evidence",
                "evidence_ids": evidence_ids,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return self.complete(result)

    def after_non_persistence_evidence(self, stage_evidence):
        if (
            not self.stage
            or self.stage["persistence_required"]
            or self.stage.get("completion_mode") != "server_evidence"
        ):
            return None
        if not self.non_persistence_evidence_satisfied(stage_evidence):
            return None
        return self._complete_server_evidence_stage(stage_evidence)

    async def on_stop(self, content, stage_evidence=None):
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
        if self.stage.get("completion_mode") == "server_evidence":
            if self.non_persistence_evidence_satisfied(stage_evidence):
                return self._complete_server_evidence_stage(stage_evidence)
            return {
                "action": "evidence_required",
                "reason": "Exact server evidence requirements are not yet satisfied.",
                "requirements": copy.deepcopy(
                    self.stage.get("evidence_requirements") or []
                ),
            }

        requirements = self.stage.get("evidence_requirements") or []
        if requirements and not self.non_persistence_evidence_satisfied(stage_evidence):
            return {
                "action": "evidence_required",
                "reason": "Required server evidence must be collected before model result completion.",
                "requirements": copy.deepcopy(requirements),
            }

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

    def complete_planner_session(self):
        if not self._planner_session_terminal:
            self._planner_session_terminal = True
            self.event("planner_session_completed", session_id=self.planner_session_id,
                       task_block_id=self.state["task_block_id"], status="VALID")

    async def replan(self, fact):
        if len(self.state["replans"]) >= REPLAN_LIMIT:
            self.block("replan_budget_exhausted")
        fact = {**fact, "fact_id": "fact_" + uuid.uuid4().hex[:12]}
        self.event("replan_started", reason=fact["reason"], fact_id=fact["fact_id"])
        previous_plan = self.plan
        def validate_replan_candidate(candidate):
            validate_replan_transition(previous_plan, candidate, fact)
            self.validate_evidence_tools_available(candidate)

        response = await self.ask(
            "REPLAN", {"current_plan": previous_plan,
                       "stage_states": self.state["stage_states"],
                       "authoritative_facts": [fact]},
            validate_replan_candidate,
        )
        self.state["replans"].append({"from_version": self.state["plan_version"],
                                      "fact": fact, "obligation_changes": response["obligation_changes"],
                                      "prior_stage_states": copy.deepcopy(self.state["stage_states"])})
        self.install(response)
        self._session_feedback(speaker="SERVER", mode="REPLAN", attempt=None,
                               text=f"PLAN VALID · v{self.state['plan_version']}")
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
            state["evidence_generation"] = int(
                state.get("evidence_generation", 0)
            ) + 1
            state["result"] = ""
            # Reopen the stage, retaining verified persistence receipts. The defect may
            # concern only one artifact, verification, or the final response. Requiring
            # every artifact to mutate again would manufacture meaningless writes.
            # Repaired targets receive new receipts; all targets are rechecked on stop.
            # Non-persistence evidence from an older repair generation is stale.
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
