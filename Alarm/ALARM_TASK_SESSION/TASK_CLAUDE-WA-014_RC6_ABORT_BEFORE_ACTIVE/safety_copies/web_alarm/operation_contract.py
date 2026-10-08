"""Durable Operation Contract v2 and legacy v1 compatibility (RC-1).

The contract has its own version and does not touch the global
``SCHEMA_VERSION`` used by all storage schemas:

- contract v1 (legacy WA-3.2 records) is read as-is, never rewritten into v2
  shape, and is never sufficient for a future RETRY re-arm;
- contract v2 is self-contained: canonical target identity, server-observed
  pre-state, declared or payload-derived expected post-state, immutable payload
  reference, claimed provenance, policy decisions, a versioned request
  fingerprint, record revision and a server-observed DONE receipt.

Stored records are validated fail-closed: an unknown contract version, an
unexpected field or an inconsistent contract is an error, never a guess.
Expected post-state declared by a caller before mutation is a pre-commitment;
the server can derive it from the payload only in WA4-E.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .file_state import (
    AUTHORITY_FIELDS,
    FileState,
    authority_of,
    eol_only_drift,
    observe_bytes,
    same_authority,
)
from .models import MicrotaskStatus, OperationRecord, OperationStatus, record_to_dict
from .storage_policy import MAX_PAYLOAD_BYTES, PAYLOAD_RETENTION
from .target_identity import CanonicalTarget, TargetIdentityError, target_key

LEGACY_CONTRACT_VERSION = 1
OPERATION_CONTRACT_VERSION = 2
SUPPORTED_CONTRACT_VERSIONS = (LEGACY_CONTRACT_VERSION, OPERATION_CONTRACT_VERSION)
LEGACY_FINGERPRINT_VERSION = 1
FINGERPRINT_VERSION = 2

V2_RECORD_FIELDS = ("contract_version", "revision", "contract", "receipt", "recovery_settlement")
_SETTLEMENT_FIELDS = frozenset({"action", "resolution_id", "basis_operation_revision", "settled_at"})
_SETTLEMENT_OPTIONAL = frozenset({"microtask_status"})
_MICROTASK_STATUSES = frozenset(status.value for status in MicrotaskStatus)
PRE_STATE_SOURCE = "server_observed_at_intent"
RECEIPT_SOURCE = "server_observed_at_done"
POST_STATE_SOURCES = ("payload", "declared", "mutation_kind")
PROVENANCE_AUTHORITY = "claimed"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EOL_VALUES = ("lf", "crlf", "mixed", "none")
_STATE_FIELDS = AUTHORITY_FIELDS + ("eol", "bom", "normalized_sha256")
_CONTRACT_FIELDS = frozenset(
    {
        "workspace_id",
        "target_key",
        "mutation_kind",
        "pre_state",
        "declared_pre_state",
        "expected_post_state",
        "payload_ref",
        "provenance",
        "policy",
        "fingerprint_version",
        "complete",
        "issues",
    }
)
_RECEIPT_FIELDS = frozenset(
    _STATE_FIELDS
    + ("source", "observed_at", "revision", "matches_expected_post", "eol_only_drift")
)


class OperationContractError(ValueError):
    """Contract input or stored contract is invalid or inconsistent."""


class OperationScopeError(OperationContractError):
    """Target or payload is outside the allowed storage/secret scope."""


class MutationKind(str, Enum):
    CREATE = "CREATE"
    WRITE = "WRITE"
    DELETE = "DELETE"


_ACTION_KINDS = {
    "create": MutationKind.CREATE,
    "create_file": MutationKind.CREATE,
    "write": MutationKind.WRITE,
    "write_file": MutationKind.WRITE,
    "edit": MutationKind.WRITE,
    "rewrite": MutationKind.WRITE,
    "replace": MutationKind.WRITE,
    "delete": MutationKind.DELETE,
    "delete_file": MutationKind.DELETE,
    "remove": MutationKind.DELETE,
}


def mutation_kind_for(action: str) -> MutationKind | None:
    return _ACTION_KINDS.get(action.strip().lower())


def _canonical_json_sha256(material: Mapping[str, Any]) -> str:
    try:
        raw = json.dumps(
            material,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise OperationContractError("operation request is not JSON-serializable") from exc
    return hashlib.sha256(raw).hexdigest()


def fingerprint_v1(
    *,
    task_id: str,
    microtask_id: str,
    action: str,
    target: str,
    expected_precondition_sha256: str | None,
    request_payload: Any,
) -> str:
    """Unchanged WA-3.2 algorithm; legacy records are compared with it only."""
    return _canonical_json_sha256(
        {
            "task_id": task_id,
            "microtask_id": microtask_id,
            "action": action,
            "target": target,
            "expected_precondition_sha256": expected_precondition_sha256,
            "request": request_payload,
        }
    )


def fingerprint_v2(
    *,
    task_id: str,
    microtask_id: str,
    action: str,
    target_key: str,
    expected_precondition_sha256: str | None,
    declared_pre_state: Mapping[str, Any] | None,
    expected_post_state: Mapping[str, Any] | None,
    payload: Mapping[str, Any] | None,
    secret_override: bool,
    request_payload: Any,
) -> str:
    """Identity of one logical operation request.

    Built only from what the caller declares: never from server observations,
    provenance or timestamps, so a replay from a new process/Chat with the same
    request yields the same fingerprint, and any spelling of the same target
    yields the same ``target_key``.
    """
    return _canonical_json_sha256(
        {
            "fingerprint_version": FINGERPRINT_VERSION,
            "task_id": task_id,
            "microtask_id": microtask_id,
            "action": action,
            "target_key": target_key,
            "expected_precondition_sha256": expected_precondition_sha256,
            "declared_pre_state": authority_of(declared_pre_state),
            "expected_post_state": authority_of(expected_post_state),
            "payload": (
                {"sha256": payload["sha256"], "size": payload["size"]}
                if payload is not None
                else None
            ),
            "secret_override": secret_override,
            "request": request_payload,
        }
    )


def _check_sha(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise OperationContractError(f"{name} must be lowercase hex SHA-256")
    return value


def _check_size(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OperationContractError(f"{name} must be a non-negative integer")
    return value


def parse_declared_state(name: str, value: Any) -> dict[str, Any] | None:
    """Validate a caller-declared physical state: authority fields only."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise OperationContractError(f"{name} must be an object")
    unknown = set(value) - set(AUTHORITY_FIELDS)
    if unknown:
        raise OperationContractError(f"{name} has unknown fields: {sorted(unknown)}")
    exists = value.get("exists")
    if not isinstance(exists, bool):
        raise OperationContractError(f"{name}.exists must be boolean")
    if not exists:
        if value.get("size") is not None or value.get("sha256") is not None:
            raise OperationContractError(f"absent {name} cannot have size or sha256")
        return {"exists": False, "size": None, "sha256": None}
    sha = value.get("sha256")
    if isinstance(sha, str):
        sha = sha.strip().lower()
    return {
        "exists": True,
        "size": _check_size(f"{name}.size", value.get("size")),
        "sha256": _check_sha(f"{name}.sha256", sha),
    }


def decode_payload_spec(value: Any) -> bytes | None:
    """Decode an API payload ``{"encoding": "utf-8"|"base64", "data": str}``."""
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"encoding", "data"}:
        raise OperationContractError("payload must be an object with encoding and data")
    data = value["data"]
    if not isinstance(data, str):
        raise OperationContractError("payload.data must be a string")
    encoding = value["encoding"]
    if encoding == "utf-8":
        return data.encode("utf-8")
    if encoding == "base64":
        try:
            return base64.b64decode(data.encode("ascii"), validate=True)
        except (binascii.Error, UnicodeEncodeError) as exc:
            raise OperationContractError("payload.data is not valid base64") from exc
    raise OperationContractError("payload.encoding must be utf-8 or base64")


def _absent_state() -> dict[str, Any]:
    return FileState(exists=False).to_dict()


@dataclass(slots=True)
class ContractRequest:
    """Validated caller request for a new v2 operation, before observation."""

    action: str
    mutation_kind: MutationKind | None
    target: CanonicalTarget
    expected_precondition_sha256: str | None
    declared_pre_state: dict[str, Any] | None
    expected_post_state: dict[str, Any] | None
    payload: bytes | None
    payload_identity: dict[str, Any] | None
    secret_pattern: str | None
    secret_override: bool
    agent: str | None
    channel: str | None
    explicit_contract: bool
    fingerprint: str


def prepare_request(
    *,
    task_id: str,
    microtask_id: str,
    action: str,
    target: CanonicalTarget,
    expected_precondition_sha256: str | None,
    request_payload: Any,
    expected_pre_state: Any = None,
    expected_post_state: Any = None,
    payload: bytes | None = None,
    secret_pattern: str | None = None,
    allow_secret_target: bool = False,
    agent: str | None = None,
    channel: str | None = None,
    max_payload_bytes: int = MAX_PAYLOAD_BYTES,
) -> ContractRequest:
    """Validate request-only consistency. Observation-dependent checks come later."""
    if not isinstance(allow_secret_target, bool):
        raise OperationContractError("allow_secret_target must be boolean")
    if secret_pattern is not None and not allow_secret_target:
        raise OperationScopeError(
            f"target matches secret deny-list pattern {secret_pattern!r}; "
            "an explicit allow_secret_target is required"
        )
    for name, value in (("agent", agent), ("channel", channel)):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise OperationContractError(f"{name} must be a non-empty string when provided")
    kind = mutation_kind_for(action)
    declared_pre = parse_declared_state("expected_pre_state", expected_pre_state)
    declared_post = parse_declared_state("expected_post_state", expected_post_state)
    # Old-style requests (no payload, no declared states) keep WA-3.2 semantics:
    # they are recorded as v2 but stay incomplete instead of gaining derived facts.
    explicit = payload is not None or declared_pre is not None or declared_post is not None

    payload_state: FileState | None = None
    payload_identity: dict[str, Any] | None = None
    if payload is not None:
        if not isinstance(payload, (bytes, bytearray)):
            raise OperationContractError("payload must be bytes")
        payload = bytes(payload)
        if len(payload) > max_payload_bytes:
            raise OperationScopeError(
                f"payload exceeds size limit: {len(payload)} > {max_payload_bytes} bytes"
            )
        if kind is MutationKind.DELETE:
            raise OperationContractError("DELETE operation cannot carry a payload")
        payload_state = observe_bytes(payload)
        payload_identity = {"sha256": payload_state.sha256, "size": payload_state.size}

    post: dict[str, Any] | None = None
    if payload_state is not None and kind in {MutationKind.CREATE, MutationKind.WRITE}:
        if declared_post is not None and not same_authority(declared_post, payload_state):
            raise OperationContractError(
                "declared expected_post_state contradicts payload bytes"
            )
        post = dict(payload_state.to_dict(), source="payload")
    elif declared_post is not None:
        post = dict(declared_post, eol=None, bom=None, normalized_sha256=None, source="declared")
    elif kind is MutationKind.DELETE and explicit:
        post = dict(_absent_state(), source="mutation_kind")
    if post is not None and kind is MutationKind.DELETE and post["exists"]:
        raise OperationContractError("DELETE expected_post_state must be absent")
    if post is not None and kind in {MutationKind.CREATE, MutationKind.WRITE} and not post["exists"]:
        raise OperationContractError(f"{kind.value} expected_post_state must exist")

    fingerprint = fingerprint_v2(
        task_id=task_id,
        microtask_id=microtask_id,
        action=action,
        target_key=target.key,
        expected_precondition_sha256=expected_precondition_sha256,
        declared_pre_state=declared_pre,
        expected_post_state=post,
        payload=payload_identity,
        secret_override=allow_secret_target,
        request_payload=request_payload,
    )
    return ContractRequest(
        action=action,
        mutation_kind=kind,
        target=target,
        expected_precondition_sha256=expected_precondition_sha256,
        declared_pre_state=declared_pre,
        expected_post_state=post,
        payload=payload,
        payload_identity=payload_identity,
        secret_pattern=secret_pattern,
        secret_override=allow_secret_target,
        agent=agent.strip() if agent else None,
        channel=channel.strip() if channel else None,
        explicit_contract=explicit,
        fingerprint=fingerprint,
    )


def finalize_contract(
    request: ContractRequest,
    *,
    workspace_id: str,
    observed_pre: FileState,
    observed_at: str,
    payload_ref: Mapping[str, Any] | None,
    max_payload_bytes: int = MAX_PAYLOAD_BYTES,
) -> dict[str, Any]:
    """Bind the request to the server-observed pre-state and build contract v2."""
    kind = request.mutation_kind
    if request.explicit_contract:
        if kind is MutationKind.CREATE and observed_pre.exists:
            raise OperationContractError("CREATE target already exists")
        if kind is MutationKind.DELETE and not observed_pre.exists:
            raise OperationContractError("DELETE target does not exist")
        if request.declared_pre_state is not None and not same_authority(
            request.declared_pre_state, observed_pre
        ):
            raise OperationContractError(
                "declared expected_pre_state does not match current target bytes"
            )

    issues: list[str] = []
    if request.expected_precondition_sha256 is not None and (
        not observed_pre.exists
        or observed_pre.sha256 != request.expected_precondition_sha256
    ):
        issues.append("declared_precondition_sha256_mismatch")
    if kind is None:
        issues.append("unknown_mutation_kind")
    if request.expected_post_state is None:
        issues.append("expected_post_state_missing")
    if kind in {MutationKind.CREATE, MutationKind.WRITE} and payload_ref is None:
        issues.append("payload_missing")

    return {
        "workspace_id": workspace_id,
        "target_key": request.target.key,
        "mutation_kind": kind.value if kind is not None else None,
        "pre_state": dict(
            observed_pre.to_dict(), source=PRE_STATE_SOURCE, observed_at=observed_at
        ),
        "declared_pre_state": request.declared_pre_state,
        "expected_post_state": request.expected_post_state,
        "payload_ref": dict(payload_ref) if payload_ref is not None else None,
        "provenance": {
            "agent": request.agent,
            "channel": request.channel,
            "authority": PROVENANCE_AUTHORITY,
        },
        "policy": {
            "secret_pattern": request.secret_pattern,
            "secret_override": request.secret_override,
            "max_payload_bytes": max_payload_bytes,
            "retention": PAYLOAD_RETENTION,
        },
        "fingerprint_version": FINGERPRINT_VERSION,
        "complete": not issues,
        "issues": issues,
    }


def make_receipt(
    observed: FileState,
    expected_post: Mapping[str, Any] | None,
    *,
    observed_at: str,
    revision: int,
) -> dict[str, Any]:
    matches = None if expected_post is None else same_authority(expected_post, observed)
    return dict(
        observed.to_dict(),
        source=RECEIPT_SOURCE,
        observed_at=observed_at,
        revision=revision,
        matches_expected_post=matches,
        eol_only_drift=eol_only_drift(expected_post, observed),
    )


# --- stored record validation -------------------------------------------------


def _check_state(name: str, value: Any, *, extra: frozenset[str] = frozenset()) -> None:
    if not isinstance(value, Mapping):
        raise OperationContractError(f"{name} must be an object")
    expected_keys = set(_STATE_FIELDS) | set(extra)
    if set(value) != expected_keys:
        raise OperationContractError(f"{name} has unexpected fields")
    exists = value["exists"]
    if not isinstance(exists, bool):
        raise OperationContractError(f"{name}.exists must be boolean")
    if not exists:
        if any(value[field] is not None for field in _STATE_FIELDS if field != "exists"):
            raise OperationContractError(f"absent {name} must not carry file metadata")
        return
    _check_size(f"{name}.size", value["size"])
    _check_sha(f"{name}.sha256", value["sha256"])
    if value["eol"] is not None and value["eol"] not in _EOL_VALUES:
        raise OperationContractError(f"{name}.eol is invalid")
    if value["bom"] is not None and not isinstance(value["bom"], bool):
        raise OperationContractError(f"{name}.bom must be boolean")
    if value["normalized_sha256"] is not None:
        _check_sha(f"{name}.normalized_sha256", value["normalized_sha256"])


def _check_text(name: str, value: Any, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or not value.strip():
        raise OperationContractError(f"{name} must be a non-empty string")


def validate_record(record: OperationRecord) -> None:
    """Fail-closed structural validation of a loaded operation record."""
    version = record.contract_version
    if isinstance(version, bool) or version not in SUPPORTED_CONTRACT_VERSIONS:
        raise OperationContractError(f"unsupported operation contract version: {version!r}")
    if version == LEGACY_CONTRACT_VERSION:
        if any(
            getattr(record, field) is not None
            for field in ("revision", "contract", "receipt", "recovery_settlement")
        ):
            raise OperationContractError("legacy record carries contract v2 fields")
        return

    revision = record.revision
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise OperationContractError("revision must be a positive integer")
    _check_sha("request_fingerprint", record.request_fingerprint)
    contract = record.contract
    if not isinstance(contract, Mapping) or set(contract) != _CONTRACT_FIELDS:
        raise OperationContractError("contract must have exactly the v2 fields")
    _check_text("contract.workspace_id", contract["workspace_id"])
    try:
        expected_key = target_key(record.target)
    except TargetIdentityError as exc:
        raise OperationContractError("operation target is invalid") from exc
    if contract["target_key"] != expected_key:
        raise OperationContractError("contract.target_key does not match target")
    kind = contract["mutation_kind"]
    if kind is not None and kind not in {item.value for item in MutationKind}:
        raise OperationContractError("contract.mutation_kind is invalid")
    _check_state(
        "contract.pre_state",
        contract["pre_state"],
        extra=frozenset({"source", "observed_at"}),
    )
    if contract["pre_state"]["source"] != PRE_STATE_SOURCE:
        raise OperationContractError("contract.pre_state.source is invalid")
    _check_text("contract.pre_state.observed_at", contract["pre_state"]["observed_at"])
    if contract["declared_pre_state"] is not None:
        if parse_declared_state("declared_pre_state", contract["declared_pre_state"]) != dict(
            contract["declared_pre_state"]
        ):
            raise OperationContractError("contract.declared_pre_state is not canonical")
    post = contract["expected_post_state"]
    if post is not None:
        _check_state("contract.expected_post_state", post, extra=frozenset({"source"}))
        if post["source"] not in POST_STATE_SOURCES:
            raise OperationContractError("contract.expected_post_state.source is invalid")
    payload_ref = contract["payload_ref"]
    if payload_ref is not None:
        if not isinstance(payload_ref, Mapping) or set(payload_ref) != {
            "sha256",
            "size",
            "store",
            "retention",
        }:
            raise OperationContractError("contract.payload_ref has unexpected fields")
        _check_sha("contract.payload_ref.sha256", payload_ref["sha256"])
        _check_size("contract.payload_ref.size", payload_ref["size"])
        if post is not None and post["source"] == "payload" and not same_authority(
            post, {"exists": True, "size": payload_ref["size"], "sha256": payload_ref["sha256"]}
        ):
            raise OperationContractError("payload-derived post-state does not match payload_ref")
    provenance = contract["provenance"]
    if not isinstance(provenance, Mapping) or set(provenance) != {
        "agent",
        "channel",
        "authority",
    }:
        raise OperationContractError("contract.provenance has unexpected fields")
    _check_text("contract.provenance.agent", provenance["agent"], optional=True)
    _check_text("contract.provenance.channel", provenance["channel"], optional=True)
    if provenance["authority"] != PROVENANCE_AUTHORITY:
        raise OperationContractError("contract.provenance.authority must be 'claimed'")
    policy = contract["policy"]
    if not isinstance(policy, Mapping) or set(policy) != {
        "secret_pattern",
        "secret_override",
        "max_payload_bytes",
        "retention",
    }:
        raise OperationContractError("contract.policy has unexpected fields")
    if not isinstance(policy["secret_override"], bool):
        raise OperationContractError("contract.policy.secret_override must be boolean")
    if policy["secret_pattern"] is not None and not policy["secret_override"]:
        raise OperationContractError("secret-scoped contract lacks explicit override")
    if contract["fingerprint_version"] != FINGERPRINT_VERSION:
        raise OperationContractError("unsupported contract fingerprint_version")
    issues = contract["issues"]
    if not isinstance(issues, list) or not all(isinstance(item, str) for item in issues):
        raise OperationContractError("contract.issues must be a list of strings")
    if contract["complete"] is not (not issues):
        raise OperationContractError("contract.complete contradicts contract.issues")

    receipt = record.receipt
    if receipt is not None:
        if not isinstance(receipt, Mapping) or set(receipt) != _RECEIPT_FIELDS:
            raise OperationContractError("receipt has unexpected fields")
        _check_state(
            "receipt",
            {field: receipt[field] for field in _STATE_FIELDS},
        )
        if receipt["source"] != RECEIPT_SOURCE:
            raise OperationContractError("receipt.source is invalid")
        _check_text("receipt.observed_at", receipt["observed_at"])
        _check_size("receipt.revision", receipt["revision"])
        if receipt["matches_expected_post"] not in (True, False, None):
            raise OperationContractError("receipt.matches_expected_post is invalid")
        if not isinstance(receipt["eol_only_drift"], bool):
            raise OperationContractError("receipt.eol_only_drift must be boolean")
        if record.status not in {
            OperationStatus.DONE,
            OperationStatus.VERIFIED,
            OperationStatus.FAILED,
        }:
            raise OperationContractError("receipt exists before DONE")
    elif record.status in {OperationStatus.DONE, OperationStatus.VERIFIED}:
        raise OperationContractError("DONE/VERIFIED v2 operation has no receipt")

    settlement = record.recovery_settlement
    if settlement is not None:
        if not isinstance(settlement, Mapping) or set(settlement) - _SETTLEMENT_OPTIONAL != _SETTLEMENT_FIELDS:
            raise OperationContractError("recovery_settlement has unexpected fields")
        # RC-6 Repair #4B: the microtask status observed when the settlement was
        # written (absent in settlements recorded before Repair #4B)
        if "microtask_status" in settlement and settlement["microtask_status"] not in _MICROTASK_STATUSES:
            raise OperationContractError("recovery_settlement.microtask_status is invalid")
        if settlement["action"] not in {"ADOPT", "ABORT", "ROLLBACK"}:
            raise OperationContractError("recovery_settlement.action is invalid")
        _check_text("recovery_settlement.resolution_id", settlement["resolution_id"])
        _check_size("recovery_settlement.basis_operation_revision", settlement["basis_operation_revision"])
        _check_text("recovery_settlement.settled_at", settlement["settled_at"])
        if settlement["action"] == "ADOPT":
            if record.status is not OperationStatus.VERIFIED or record.receipt is None:
                raise OperationContractError("ADOPT settlement requires VERIFIED operation with receipt")


def record_for_storage(record: OperationRecord) -> dict[str, Any]:
    """Serialize without changing the on-disk shape of legacy v1 records."""
    data = record_to_dict(record)
    if record.contract_version == LEGACY_CONTRACT_VERSION:
        for field in V2_RECORD_FIELDS:
            data.pop(field, None)
    return data


def assess(record: OperationRecord) -> dict[str, Any]:
    """Contract sufficiency facts for RC-2; this is not a resolver decision."""
    if record.contract_version == LEGACY_CONTRACT_VERSION:
        return {
            "contract_version": LEGACY_CONTRACT_VERSION,
            "legacy": True,
            "complete": False,
            "rearm_contract_sufficient": False,
            "issues": ["legacy_contract_v1"],
        }
    contract = record.contract or {}
    complete = bool(contract.get("complete"))
    return {
        "contract_version": record.contract_version,
        "legacy": False,
        "complete": complete,
        "rearm_contract_sufficient": complete,
        "issues": list(contract.get("issues", [])),
    }
