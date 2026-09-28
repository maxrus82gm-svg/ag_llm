"""Bounded, tool-free Planner role. No Executor or Verifier session is reused."""
from __future__ import annotations

import copy
import json
import uuid

import httpx

from context_registry import resolve_context_text
from gigachat_transport import CHAT_URL, extract_usage, get_access_token
from model_registry import get_model_spec

DEFAULT_PLANNER_MODEL_ID = "gigachat_ultra"
MAX_PLANNING_CONTEXT_BYTES = 128 * 1024
MAX_PLANNER_RESPONSE_BYTES = 96 * 1024
PLANNER_TIMEOUT_SECONDS = 90
MAX_PLAN_STAGES = 8
MAX_PLAN_ARTIFACTS = 16
PLANNER_HARD_PROTOCOL = (
    "Every stage with stage_type='verification' must include VERIFY in "
    "allowed_capabilities. Add READ as well only when raw file inspection is required. "
    "For exact textual file verification prefer verify_file_content with "
    "equals/contains/sha256 over repeated read_file/find_text when the check can be "
    "expressed by that tool."
)


class PlannerError(RuntimeError):
    pass


def strict_json(text: str) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PlannerError("Duplicate JSON key")
            result[key] = value
        return result

    try:
        result = json.loads(text, object_pairs_hook=pairs,
                            parse_constant=lambda value: (_ for _ in ()).throw(PlannerError("Non-finite JSON")))
    except (ValueError, TypeError) as exc:
        raise PlannerError("Planner must return one JSON object without prose") from exc
    if not isinstance(result, dict):
        raise PlannerError("Planner result must be an object")
    return result


def text_field(value, label, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise PlannerError(f"Invalid {label}")
    return value


def keys(value, required, optional=()):
    if not isinstance(value, dict):
        raise PlannerError("Invalid structured fields: expected object")

    actual = set(value)
    required = set(required)
    optional = set(optional)

    missing = sorted(required - actual)
    extra = sorted(actual - required - optional)

    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing={missing[:8]!r}")
        if extra:
            parts.append(f"extra={extra[:8]!r}")

        message = "Invalid structured fields: " + ", ".join(parts)
        if len(message) > 240:
            message = message[:237] + "..."
        raise PlannerError(message)


def string_list(value, label, limit=16):
    if not isinstance(value, list) or len(value) > limit:
        raise PlannerError(f"Invalid {label}")
    for item in value:
        text_field(item, label)
    return value


def validate_plan(value: dict) -> dict:
    keys(value, {"stages", "obligation_changes"})
    stages = value["stages"]
    if not isinstance(stages, list) or not 1 <= len(stages) <= MAX_PLAN_STAGES:
        raise PlannerError("Invalid stages count")
    ids, artifacts = set(), set()
    for stage in stages:
        keys(stage, {"stage_id", "goal", "stage_type", "persistence_required",
                     "allowed_capabilities", "artifacts", "completion_criteria"})
        sid = text_field(stage["stage_id"], "stage_id", 80)
        if sid in ids:
            raise PlannerError("Duplicate stage_id")
        ids.add(sid)
        text_field(stage["goal"], "goal")
        if stage["stage_type"] not in {"analysis", "produce_artifact", "verification"}:
            received = repr(stage["stage_type"])
            if len(received) > 80:
                received = received[:77] + "..."
            raise PlannerError(f"Invalid stage_type: {received}")
        if type(stage["persistence_required"]) is not bool:
            raise PlannerError("persistence_required must be boolean")
        caps = string_list(stage["allowed_capabilities"], "capabilities", 4)
        if set(caps) - {"READ", "WRITE", "DELETE", "VERIFY"} or len(caps) != len(set(caps)):
            raise PlannerError("Invalid capabilities")
        if stage["stage_type"] == "verification" and "VERIFY" not in caps:
            raise PlannerError("verification stage requires VERIFY capability")
        if not string_list(stage["completion_criteria"], "completion criteria"):
            raise PlannerError("Completion criteria required")
        if not isinstance(stage["artifacts"], list):
            raise PlannerError("Invalid artifacts")
        if bool(stage["artifacts"]) != stage["persistence_required"]:
            raise PlannerError("Persistence stages must declare artifacts before execution")
        for artifact in stage["artifacts"]:
            keys(artifact, {"artifact_id", "path", "operation", "postcondition", "allow_already_satisfied"})
            aid = text_field(artifact["artifact_id"], "artifact_id", 80)
            if aid in artifacts:
                raise PlannerError("Duplicate artifact_id")
            artifacts.add(aid)
            path = text_field(artifact["path"], "artifact path", 512)
            if "\\" in path or ":" in path or path.startswith("/") or any(p in {"", ".", ".."} for p in path.split("/")):
                raise PlannerError("Artifact path must be canonical workspace-relative")
            if artifact["operation"] not in {"create", "update", "delete"}:
                raise PlannerError("Invalid operation")
            capability = "DELETE" if artifact["operation"] == "delete" else "WRITE"
            if capability not in caps:
                raise PlannerError("Missing artifact capability")
            if type(artifact["allow_already_satisfied"]) is not bool:
                raise PlannerError("Invalid already-satisfied policy")
            post = artifact["postcondition"]
            keys(post, {"kind", "value"})
            if post["kind"] not in {"exists", "absent", "contains", "equals", "sha256"}:
                raise PlannerError("Unsupported postcondition")
            if not isinstance(post["value"], str) or len(post["value"]) > 8000:
                raise PlannerError("Invalid postcondition value")
            if post["kind"] in {"contains", "sha256"} and not post["value"]:
                raise PlannerError("Empty content postcondition")
            if post["kind"] == "sha256" and (len(post["value"]) != 64 or any(c not in "0123456789abcdef" for c in post["value"])):
                raise PlannerError("Invalid SHA-256 postcondition")
            if post["kind"] in {"exists", "absent"} and post["value"]:
                raise PlannerError("Existence postconditions have an empty value")
            if (artifact["operation"] == "delete") != (post["kind"] == "absent"):
                raise PlannerError("Operation/postcondition mismatch")
    if len(artifacts) > MAX_PLAN_ARTIFACTS:
        raise PlannerError("Too many artifacts")
    if not isinstance(value["obligation_changes"], list) or len(value["obligation_changes"]) > MAX_PLAN_ARTIFACTS:
        raise PlannerError("Invalid obligation_changes")
    for change in value["obligation_changes"]:
        keys(change, {"old_artifact_id", "action", "replacement_ids", "reason", "fact_id"})
        text_field(change["old_artifact_id"], "old artifact", 80)
        text_field(change["reason"], "change reason")
        text_field(change["fact_id"], "fact_id", 80)
        if change["action"] not in {"replace", "cancel"}:
            raise PlannerError("Invalid obligation action")
        string_list(change["replacement_ids"], "replacement ids")
        if (change["action"] == "replace") != bool(change["replacement_ids"]):
            raise PlannerError("Replacement ids required only for replacement")
        if set(change["replacement_ids"]) - artifacts:
            raise PlannerError("Unknown replacement obligation")
    return value


def validate_readiness(value: dict) -> dict:
    keys(value, {"status", "reason", "unresolved_requirements", "next_action"}, {"candidate_ids"})
    if value["status"] not in {"CONTINUE", "READY_TO_PERSIST", "BLOCKED"}:
        raise PlannerError("Invalid readiness status")
    text_field(value["reason"], "reason")
    string_list(value["unresolved_requirements"], "unresolved requirements")
    if "candidate_ids" in value:
        # Legacy advisory metadata. Candidate identity and authorization belong to Server.
        string_list(value["candidate_ids"], "candidate ids")
    if not isinstance(value["next_action"], str):
        raise PlannerError("Invalid next_action")
    if value["status"] == "CONTINUE" and (not value["unresolved_requirements"] or not value["next_action"].strip()):
        raise PlannerError("CONTINUE requires a missing prerequisite and concrete next action")
    return value


PLAN_FORMAT = {
    "stages": [{"stage_id": "stage_1", "goal": "specific requested outcome",
                "stage_type": "produce_artifact", "persistence_required": True,
                "allowed_capabilities": ["READ", "WRITE"],
                "artifacts": [{"artifact_id": "result", "path": "result.md", "operation": "create",
                               "postcondition": {"kind": "contains", "value": "required content"},
                               "allow_already_satisfied": False}],
                "completion_criteria": ["requested result physically exists"]}],
    "obligation_changes": [],
}


def build_planner_body(mode: str, raw_task: str, context: dict, model_id: str) -> dict:
    if mode not in {"INITIAL", "READINESS", "REPLAN"}:
        raise PlannerError("Unknown Planner mode")
    model = get_model_spec(model_id)
    if model.provider != "gigachat":
        raise PlannerError("Unsupported Planner provider")
    mode_context_id = {
        "INITIAL": "planner.initial",
        "READINESS": "planner.readiness",
        "REPLAN": "planner.replan",
    }[mode]
    variables = ({"plan_format": json.dumps(PLAN_FORMAT)}
                 if mode in {"INITIAL", "REPLAN"} else None)
    base_context = resolve_context_text("planner.base")
    mode_context = resolve_context_text(mode_context_id, variables)
    system = (
        base_context.rstrip() + " " + PLANNER_HARD_PROTOCOL + " "
        + mode_context.lstrip()
    )
    serialized = json.dumps({"mode": mode, "raw_task": raw_task, "context": context}, ensure_ascii=False)
    if len(serialized.encode("utf-8")) > MAX_PLANNING_CONTEXT_BYTES:
        raise PlannerError("Planning context exceeds bounded limit")
    return {"model": model.provider_model_id, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": serialized}],
        "temperature": 0.0, "max_tokens": 8192, "stream": False, "function_call": "none"}


def _planner_session_system() -> str:
    plan_variables = {"plan_format": json.dumps(PLAN_FORMAT)}
    parts = [
        resolve_context_text("planner.base").strip(),
        PLANNER_HARD_PROTOCOL,
        "===== INITIAL PROTOCOL =====\n"
        + resolve_context_text("planner.initial", plan_variables).strip(),
        "===== READINESS PROTOCOL =====\n"
        + resolve_context_text("planner.readiness").strip(),
        "===== REPLAN PROTOCOL =====\n"
        + resolve_context_text("planner.replan", plan_variables).strip(),
    ]
    return "\n\n".join(parts)


class PlannerSession:
    """One bounded, local, stateless-provider conversation for one task RUN."""

    MAX_MESSAGES = 32

    def __init__(self, *, raw_task: str,
                 planner_model_id: str = DEFAULT_PLANNER_MODEL_ID,
                 diagnostic_callback=None, message_callback=None) -> None:
        self.session_id = "ps_" + uuid.uuid4().hex
        self.raw_task = raw_task
        self.planner_model_id = planner_model_id
        self.diagnostic_callback = diagnostic_callback
        self.message_callback = message_callback
        self.turn_count = 0
        self._initial_added = False
        self.messages = [{"role": "system", "content": _planner_session_system()}]
        self._check_bounds()

    def _diagnostic(self, kind: str, payload: dict) -> None:
        if self.diagnostic_callback is None:
            return
        try:
            self.diagnostic_callback(kind, payload)
        except Exception:
            pass

    def _notify(self, speaker: str, mode: str, attempt: int | None,
                text: str) -> None:
        if self.message_callback is None:
            return
        try:
            self.message_callback(speaker, mode, attempt, text)
        except Exception:
            pass

    def _check_bounds(self) -> None:
        if len(self.messages) > self.MAX_MESSAGES:
            raise PlannerError("Planner session exceeds bounded limit")
        serialized = json.dumps(self.messages, ensure_ascii=False)
        if len(serialized.encode("utf-8")) > MAX_PLANNING_CONTEXT_BYTES:
            raise PlannerError("Planner session exceeds bounded limit")

    def transcript(self) -> list[dict]:
        return copy.deepcopy(self.messages)

    def add_control_message(self, *, speaker: str, mode: str,
                            attempt: int | None, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self._check_bounds()
        self._notify(speaker, mode, attempt, text)

    async def call(self, *, mode: str, raw_task: str, context: dict,
                   attempt: int = 1) -> dict:
        if raw_task != self.raw_task:
            raise PlannerError("Planner session raw_task mismatch")
        if mode not in {"INITIAL", "READINESS", "REPLAN"}:
            raise PlannerError("Unknown Planner mode")
        user_text = ""
        if attempt == 1:
            if mode == "INITIAL" and not self._initial_added:
                payload = {"mode": mode, "raw_task": self.raw_task, "context": context}
                speaker = "TASK"
                self._initial_added = True
            else:
                payload = {"source": "SERVER", "mode": mode, "context": context}
                speaker = "SERVER"
            user_text = json.dumps(payload, ensure_ascii=False)
            self.messages.append({"role": "user", "content": user_text})
            self._check_bounds()
            self._notify(speaker, mode, attempt,
                         self.raw_task if speaker == "TASK" else user_text)

        model = get_model_spec(self.planner_model_id)
        if model.provider != "gigachat":
            raise PlannerError("Unsupported Planner provider")
        body = {
            "model": model.provider_model_id,
            "messages": copy.deepcopy(self.messages),
            "temperature": 0.0,
            "max_tokens": 8192,
            "stream": False,
            "function_call": "none",
        }
        self._diagnostic("request", {
            "mode": mode, "planner_model_id": self.planner_model_id,
            "provider_model_id": body["model"], "temperature": body["temperature"],
            "max_tokens": body["max_tokens"], "function_call": body["function_call"],
        })
        self._diagnostic("context", {
            "mode": mode, "system": body["messages"][0]["content"],
            "user": user_text or body["messages"][-1]["content"],
        })
        try:
            token = await get_access_token()
            async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    CHAT_URL, headers={"Authorization": f"Bearer {token}"}, json=body,
                )
                response.raise_for_status()
            data = response.json()
            usage = extract_usage(data)
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content")
            raw_text = content if isinstance(content, str) else json.dumps(message, ensure_ascii=False)
            self.messages.append({"role": "assistant", "content": raw_text})
            self.turn_count += 1
            self._check_bounds()
            self._notify("PLANNER", mode, attempt, raw_text)
            self._diagnostic("response", {
                "mode": mode, "finish_reason": choice.get("finish_reason"),
                "content": content, "function_call": message.get("function_call"),
                "usage": usage,
            })
            if choice.get("finish_reason") not in {"stop", "eos"} or message.get("function_call"):
                raise PlannerError("Planner returned an unexpected finish/tool call")
            if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_PLANNER_RESPONSE_BYTES:
                raise PlannerError("Invalid Planner response size")
            value = strict_json(content)
            return validate_readiness(value) if mode == "READINESS" else validate_plan(value)
        except PlannerError as exc:
            self._diagnostic("error", {"mode": mode, "error_type": type(exc).__name__,
                                       "error_message": str(exc)})
            raise
        except Exception as exc:
            message = f"Planner call failed: {type(exc).__name__}"
            self._diagnostic("error", {"mode": mode, "error_type": "PlannerError",
                                       "error_message": message})
            raise PlannerError(message) from exc


async def run_planner(*, mode: str, raw_task: str, context: dict,
                      planner_model_id: str = DEFAULT_PLANNER_MODEL_ID,
                      diagnostic_callback=None, session: PlannerSession | None = None,
                      attempt: int = 1) -> dict:
    if session is not None:
        return await session.call(
            mode=mode, raw_task=raw_task, context=context, attempt=attempt,
        )
    def diagnostic(kind: str, payload: dict) -> None:
        if diagnostic_callback is None:
            return
        try:
            diagnostic_callback(kind, payload)
        except Exception:
            pass

    try:
        body = build_planner_body(mode, raw_task, context, planner_model_id)
        diagnostic("request", {
            "mode": mode,
            "planner_model_id": planner_model_id,
            "provider_model_id": body["model"],
            "temperature": body["temperature"],
            "max_tokens": body["max_tokens"],
            "function_call": body["function_call"],
        })
        diagnostic("context", {
            "mode": mode,
            "system": body["messages"][0]["content"],
            "user": body["messages"][1]["content"],
        })
        token = await get_access_token()
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_SECONDS) as client:
            response = await client.post(CHAT_URL, headers={"Authorization": f"Bearer {token}"}, json=body)
            response.raise_for_status()
        data = response.json()
        usage = extract_usage(data)
        choice = data["choices"][0]
        message = choice["message"]
        diagnostic("response", {
            "mode": mode,
            "finish_reason": choice.get("finish_reason"),
            "content": message.get("content"),
            "function_call": message.get("function_call"),
            "usage": usage,
        })
        if choice.get("finish_reason") not in {"stop", "eos"} or message.get("function_call"):
            raise PlannerError("Planner returned an unexpected finish/tool call")
        content = message["content"]
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_PLANNER_RESPONSE_BYTES:
            raise PlannerError("Invalid Planner response size")
        value = strict_json(content)
        return validate_readiness(value) if mode == "READINESS" else validate_plan(value)
    except PlannerError as exc:
        diagnostic("error", {
            "mode": mode,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        })
        raise
    except Exception as exc:
        # Do not copy HTTP bodies, headers or sensitive prompts into runtime trace.
        message = f"Planner call failed: {type(exc).__name__}"
        diagnostic("error", {
            "mode": mode,
            "error_type": "PlannerError",
            "error_message": message,
        })
        raise PlannerError(message) from exc
