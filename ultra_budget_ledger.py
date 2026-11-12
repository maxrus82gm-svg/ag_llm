"""RT-002/B2 S3a OFFLINE durable reservations. No transport or production hooks.

Authoritative events live in the existing Run Store workspace index. All reads,
decisions and commits use its shared Ultra workspace writer lock. Summaries are
not budget authority. The immutable enrollment marker prevents silent re-creation
when the index/ledger is missing. Only an explicitly fresh audit store can enroll;
adopting historical accounting needs a separately approved migration.

A receipt is NOT permission to perform HTTP. S3b must bind the final bytes and
consume a fresh mark_sent transition exactly once. Replayed receipts never imply
a new physical attempt. Proof of NOT_SENT is supplied by that future trusted guard.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import uuid

import context_storage as core
import run_store as store
import ultra_budget_policy as policy

SCHEMA_VERSION = 1
INDEX_KEY = "budget_ledger"
MARKER_NAME = "budget.enrollment.json"
MAX_EVENTS = 4096  # bounded format capacity, not a spending limit; no compaction/reset


class LedgerDenied(ValueError):
    """No new send is authorized, including after an ambiguous storage failure."""


@dataclass(frozen=True)
class Receipt:
    record: policy.AttemptRecord
    replayed: bool
    revision: int


@dataclass(frozen=True)
class Recovered:
    workspace_id: str
    ledger_id: str
    revision: int
    event_count: int
    attempts: tuple[policy.AttemptRecord, ...]


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _copy(value):
    return json.loads(_json(value))


def _hash(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _engine_id():
    # Replaying reserves with a changed estimator/route table could lower old liability.
    # An upgrade needs an approved migration; CRLF alone is not a policy-engine change.
    return hashlib.sha256(Path(policy.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _text(value):
    if policy._text_problem(value):
        raise LedgerDenied("INVALID_IDENTITY")
    return value


def _keys(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise LedgerDenied("INVALID_LEDGER_SHAPE")


def _replay(events):
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise LedgerDenied("INVALID_OR_FULL_LEDGER")
    records, envelopes, scopes, seen = {}, {}, {}, set()
    for event in events:
        _keys(event, {"op", "provider_attempt_id", "data"})
        attempt = _text(event["provider_attempt_id"])
        fingerprint = _hash(event)
        if fingerprint in seen:
            raise LedgerDenied("DUPLICATE_STORED_EVENT")
        seen.add(fingerprint)
        data, op = event["data"], event["op"]
        if op == "reserve":
            _keys(data, {"policy", "route_id", "wire_utf8", "context", "binding"})
            if attempt in records:
                raise LedgerDenied("ATTEMPT_ID_CONFLICT")
            snapshot = policy.validate_policy(data["policy"])
            _keys(data["context"], {"scope_id", "final_audit_enabled"})
            context = policy.RunContext(**data["context"])
            _keys(data["binding"], {"run_id", "chat_id", "turn_id", "logical_call_id"})
            for key, value in data["binding"].items():
                if value is not None or key == "logical_call_id":
                    _text(value)
            if type(data["wire_utf8"]) is not str:
                raise LedgerDenied("INVALID_WIRE")
            wire = data["wire_utf8"].encode("utf-8")
            body = json.loads(wire)
            measure = policy.measure_request(data["route_id"], body)
            if policy.serialize_request_body(body) != wire:
                raise LedgerDenied("WIRE_NOT_S2_SERIALIZATION")
            decision = policy.evaluate_request(snapshot, records.values(), measure, context)
            if decision.verdict != policy.ALLOW:
                raise LedgerDenied("POLICY_DENY:" + ",".join(r.code for r in decision.reasons))
            spec = policy.ROUTES[measure.route_id]
            if spec.scope == policy.SCOPE_RUN and data["binding"]["run_id"] != context.scope_id:
                raise LedgerDenied("RUN_SCOPE_BINDING_CONFLICT")
            if spec.scope == policy.SCOPE_ORDINARY and (context.scope_id != attempt
                    or data["binding"]["turn_id"] is None or data["binding"]["run_id"] is None):
                raise LedgerDenied("ORDINARY_SCOPE_BINDING_CONFLICT")
            pin = (spec.scope, snapshot.revision_sha256, context.final_audit_enabled)
            if context.scope_id in scopes and scopes[context.scope_id] != pin:
                raise LedgerDenied("IMMUTABLE_SCOPE_POLICY_CONFLICT")
            scopes[context.scope_id] = pin
            records[attempt] = policy.reserve_attempt(attempt, measure, decision.estimate, context.scope_id)
            envelopes[attempt] = data
        else:
            if attempt not in records:
                raise LedgerDenied("UNKNOWN_ATTEMPT")
            record = records[attempt]
            if op == "mark_sent":
                if data != {}:
                    raise LedgerDenied("INVALID_SENT_EVENT")
                records[attempt] = policy.mark_sent(record)
            elif op == "mark_not_sent":
                _keys(data, {"kind", "reference"})
                if data["kind"] != "PROVEN_PRE_SEND_NOT_SENT":
                    raise LedgerDenied("NOT_SENT_PROOF_REQUIRED")
                _text(data["reference"])
                records[attempt] = policy.mark_not_sent(record)
            elif op == "terminal":
                _keys(data, {"outcome", "usage"})
                records[attempt] = policy.apply_terminal(record, data["outcome"], data["usage"])
            else:
                raise LedgerDenied("UNKNOWN_EVENT")
    return records, envelopes


class BudgetLedger:
    """Workspace-wide S3a owner, shared by future Tk/Web adapters. No implicit init."""

    def __init__(self, workspace_root, workspace_id):
        try:
            self.root = Path(workspace_root).absolute()
        except (TypeError, ValueError, OSError) as error:
            raise LedgerDenied("INVALID_WORKSPACE_PATH") from error
        self.workspace_id = _text(workspace_id)

    def _identity(self):
        # Check lexical parents BEFORE resolve; an alias must not bypass reparse refusal.
        for path in (*reversed(self.root.parents), self.root):
            if core._is_link_or_reparse(path.lstat()):
                raise LedgerDenied("UNSAFE_WORKSPACE_PATH")
        identity = core.read_workspace_identity_bounded(self.root)
        if identity.get("status") != "ok" or identity.get("workspace_id") != self.workspace_id:
            raise LedgerDenied("WORKSPACE_IDENTITY_UNAVAILABLE")

    def _marker(self):
        return store._checked_path(self.root / ".ultra" / "audit" / MARKER_NAME)

    @contextmanager
    def _locked(self, *, enrollment=False):
        try:
            self._identity()
            if not enrollment and not os.path.lexists(self._marker()):
                raise LedgerDenied("LEDGER_NOT_ENROLLED")
            with store._index_lock(self.root):
                self._identity()
                yield
        except LedgerDenied:
            raise
        except Exception as error:
            # Failure never means an empty/affordable budget. No paths or request data leak.
            raise LedgerDenied("STORAGE_OR_INPUT_DENY:" + type(error).__name__) from error

    def _load(self):
        marker = store._read_json(self._marker())
        _keys(marker, {"schema_version", "workspace_id", "ledger_id", "policy_engine_sha256"})
        _text(marker["ledger_id"])
        if (type(marker["schema_version"]) is not int or marker["schema_version"] != SCHEMA_VERSION
                or marker["workspace_id"] != self.workspace_id or marker["policy_engine_sha256"] != _engine_id()):
            raise LedgerDenied("INVALID_ENROLLMENT")
        index = store.load_workspace_run_index(self.root)
        value = index.get(INDEX_KEY)
        _keys(value, {"schema_version", "workspace_id", "ledger_id", "policy_engine_sha256", "events", "events_sha256"})
        if (type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION
                or value["workspace_id"] != self.workspace_id or value["ledger_id"] != marker["ledger_id"]
                or value["policy_engine_sha256"] != marker["policy_engine_sha256"]
                or type(value["ledger_id"]) is not str or not value["ledger_id"]
                or value["events_sha256"] != _hash(value["events"])):
            raise LedgerDenied("LEDGER_INTEGRITY_DENY")
        records, envelopes = _replay(value["events"])
        return index, value, records, envelopes

    def initialize(self):
        """Explicit fresh enrollment. Existing audit facts need approved adoption, never zero."""
        with self._locked(enrollment=True):
            if os.path.lexists(self._marker()):
                index, value, records, _ = self._load()
            else:
                audit = store._checked_path(self.root / ".ultra/audit", directory=True)
                if any(audit.iterdir()):
                    raise LedgerDenied("EXISTING_AUDIT_REQUIRES_MIGRATION")
                index = store.load_workspace_run_index(self.root)
                marker = {"schema_version": SCHEMA_VERSION, "workspace_id": self.workspace_id, "ledger_id": uuid.uuid4().hex,
                          "policy_engine_sha256": _engine_id()}
                # Marker-first crash may block enrollment, never silently bootstrap zero again.
                store._atomic_json(self._marker(), marker)
                value = {**marker, "events": [], "events_sha256": _hash([])}
                index[INDEX_KEY] = value
                store._save_index(self.root, index)
                index, value, records, _ = self._load()
            return Recovered(self.workspace_id, value["ledger_id"], index["revision"], len(value["events"]), tuple(records.values()))

    def recover(self):
        """Verify existing committed facts; no execution/release/automatic reset or repair."""
        with self._locked():
            index, value, records, _ = self._load()
            return Recovered(self.workspace_id, value["ledger_id"], index["revision"], len(value["events"]), tuple(records.values()))

    def _event(self, op, attempt, data):
        with self._locked():
            attempt = _text(attempt)
            event = _copy({"op": op, "provider_attempt_id": attempt, "data": data})
            index, value, records, envelopes = self._load()
            if op == "reserve" and attempt in envelopes:
                if event["data"] != envelopes[attempt]:
                    raise LedgerDenied("ATTEMPT_ID_CONFLICT")
                return Receipt(records[attempt], True, index["revision"])
            if event in value["events"]:
                return Receipt(records[attempt], True, index["revision"])
            candidate = {**value, "events": [*value["events"], event]}
            _replay(candidate["events"])
            candidate["events_sha256"] = _hash(candidate["events"])
            index[INDEX_KEY] = candidate
            store._save_index(self.root, index)
            loaded, saved, records, _ = self._load()
            if saved != candidate:
                raise LedgerDenied("COMMIT_READBACK_MISMATCH")
            return Receipt(records[attempt], False, loaded["revision"])

    def reserve(self, provider_attempt_id, raw_policy, route_id, final_wire_body, context, binding):
        try:
            if type(final_wire_body) is not bytes or type(context) is not policy.RunContext:
                raise LedgerDenied("INVALID_REQUEST_INPUT")
            envelope = {"policy": raw_policy, "route_id": route_id, "wire_utf8": final_wire_body.decode("utf-8"),
                        "context": asdict(context), "binding": binding}
            return self._event("reserve", provider_attempt_id, envelope)
        except LedgerDenied:
            raise
        except Exception as error:
            raise LedgerDenied("INPUT_DENY:" + type(error).__name__) from error

    def reservation(self, provider_attempt_id):
        """Readback the exact committed envelope and state; never grants a send."""
        with self._locked():
            index, _, records, envelopes = self._load()
            attempt = _text(provider_attempt_id)
            if attempt not in envelopes:
                raise LedgerDenied("UNKNOWN_ATTEMPT")
            return Receipt(records[attempt], True, index["revision"]), _copy(envelopes[attempt])

    def mark_sent(self, provider_attempt_id):
        return self._event("mark_sent", provider_attempt_id, {})

    def mark_not_sent(self, provider_attempt_id, proof=None):
        return self._event("mark_not_sent", provider_attempt_id, proof)

    def terminal(self, provider_attempt_id, outcome, usage):
        return self._event("terminal", provider_attempt_id, {"outcome": outcome, "usage": usage})
