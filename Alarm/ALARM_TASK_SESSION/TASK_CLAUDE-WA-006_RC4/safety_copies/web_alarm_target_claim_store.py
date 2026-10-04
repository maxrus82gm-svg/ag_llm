"""Persistent canonical-target claims for the RC-3 conflict gate.

One JSON file per physical target (``target_claims/<target_hash>.json``) holds
the single ACTIVE claim, if any, plus the history of ended claims. The file is
replaced atomically, so ownership is always one consistent document.

Conflict identity is the physical target: the RC-1 canonical (resolved) path,
OS-case-normalized with POSIX separators. Two workspace-relative spellings,
nested workspace roots or junction aliases of one file therefore share one
identity. Lock and record names use its SHA-256, never the raw path.

There is no lease, TTL or heartbeat (RT-001 V17): a claim ends only through an
explicit owner release or an owner rebase, never because time passed or a
process/Chat disappeared.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .models import SCHEMA_VERSION, new_id

CLAIM_STORE_VERSION = 1

ACTIVE = "ACTIVE"
RELEASED = "RELEASED"
SUPERSEDED = "SUPERSEDED"
_STATUSES = (ACTIVE, RELEASED, SUPERSEDED)
AUTHORIZED = "AUTHORIZED"
DENIED = "DENIED"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_FIELDS = frozenset(
    {
        "claim_id",
        "generation",
        "task_id",
        "microtask_id",
        "operation_id",
        "workspace_id",
        "target",
        "target_key",
        "operation_revision",
        "operation_request_fingerprint",
        "contract_version",
        "cas_basis",
        "status",
        "created_at",
        "provenance",
        "ended_at",
        "end_reason",
        "ended_by",
        "superseded_by",
        "authorizations",
    }
)
_AUTHORIZATION_FIELDS = frozenset(
    {
        "authorization_id",
        "result",
        "result_code",
        "operation_revision",
        "observed",
        "at",
    }
)
_FILE_FIELDS = frozenset(
    {
        "claim_store_version",
        "schema_version",
        "target_hash",
        "physical_key",
        "next_generation",
        "active",
        "history",
    }
)


class TargetClaimStoreError(RuntimeError):
    """Raised when claim state is invalid or cannot be persisted."""


def physical_target_key(path: Path) -> str:
    """Conflict identity of an already canonical (resolved) physical path."""
    key = os.path.normcase(str(path))
    if os.sep != "/":
        key = key.replace(os.sep, "/")
    return key


def target_hash(physical_key: str) -> str:
    return hashlib.sha256(physical_key.encode("utf-8")).hexdigest()


def claim_identity(target_digest: str, generation: int, task_id: str, operation_id: str, revision: int) -> str:
    raw = json.dumps(
        [target_digest, generation, task_id, operation_id, revision],
        separators=(",", ":"),
    ).encode("utf-8")
    return "claim_" + hashlib.sha256(raw).hexdigest()[:32]


def authorization_identity(claim_id: str, revision: int, observed: dict[str, Any], code: str) -> str:
    raw = json.dumps(
        [claim_id, revision, observed, code], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "auth_" + hashlib.sha256(raw).hexdigest()[:32]


def _fail(message: str) -> None:
    raise TargetClaimStoreError(message)


def _check_state(name: str, value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"exists", "size", "sha256"}:
        _fail(f"{name} must be an authority state")
    if not isinstance(value["exists"], bool):
        _fail(f"{name}.exists must be boolean")
    if value["exists"]:
        if isinstance(value["size"], bool) or not isinstance(value["size"], int) or value["size"] < 0:
            _fail(f"{name}.size is invalid")
        if not isinstance(value["sha256"], str) or not _SHA256_RE.match(value["sha256"]):
            _fail(f"{name}.sha256 is invalid")
    elif value["size"] is not None or value["sha256"] is not None:
        _fail(f"absent {name} must not carry size/sha256")


def validate_claim(claim: Any) -> None:
    if not isinstance(claim, dict) or set(claim) != _CLAIM_FIELDS:
        _fail("claim has unexpected fields")
    for name in (
        "claim_id",
        "task_id",
        "microtask_id",
        "operation_id",
        "workspace_id",
        "target",
        "target_key",
        "operation_request_fingerprint",
        "created_at",
    ):
        if not isinstance(claim[name], str) or not claim[name].strip():
            _fail(f"claim.{name} must be a non-empty string")
    for name in ("generation", "operation_revision"):
        value = claim[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            _fail(f"claim.{name} must be a positive integer")
    if claim["contract_version"] != 2:
        _fail("only contract v2 operations can hold a target claim")
    _check_state("claim.cas_basis", claim["cas_basis"])
    if claim["status"] not in _STATUSES:
        _fail("claim.status is invalid")
    ended = claim["status"] != ACTIVE
    for name in ("ended_at", "end_reason"):
        if ended != (isinstance(claim[name], str) and bool(claim[name].strip())):
            _fail(f"claim.{name} must be set exactly when the claim has ended")
    if (claim["status"] == SUPERSEDED) != isinstance(claim["superseded_by"], str):
        _fail("claim.superseded_by must be set exactly for SUPERSEDED claims")
    for name in ("provenance",) + (("ended_by",) if claim["ended_by"] is not None else ()):
        value = claim[name]
        if not isinstance(value, dict) or set(value) != {"agent", "channel", "authority"} or value[
            "authority"
        ] != "claimed":
            _fail(f"claim.{name} must be claimed agent/channel provenance")
    if not isinstance(claim["authorizations"], list):
        _fail("claim.authorizations must be a list")
    seen: set[str] = set()
    for item in claim["authorizations"]:
        if not isinstance(item, dict) or set(item) != _AUTHORIZATION_FIELDS:
            _fail("authorization has unexpected fields")
        if item["result"] not in (AUTHORIZED, DENIED) or item["authorization_id"] in seen:
            _fail("authorization result/identity is invalid")
        seen.add(item["authorization_id"])
        if item["observed"] is not None:
            _check_state("authorization.observed", item["observed"])


def empty_target_file(physical_key: str) -> dict[str, Any]:
    return {
        "claim_store_version": CLAIM_STORE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "target_hash": target_hash(physical_key),
        "physical_key": physical_key,
        "next_generation": 1,
        "active": None,
        "history": [],
    }


def validate_target_file(data: Any, physical_key: str) -> None:
    if not isinstance(data, dict) or set(data) != _FILE_FIELDS:
        _fail("target claim file has unexpected fields")
    if data["claim_store_version"] != CLAIM_STORE_VERSION or data["schema_version"] != SCHEMA_VERSION:
        _fail("unsupported target claim file version")
    if data["physical_key"] != physical_key or data["target_hash"] != target_hash(physical_key):
        _fail("target claim file identity mismatch")
    generation = data["next_generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        _fail("next_generation is invalid")
    if not isinstance(data["history"], list):
        _fail("history must be a list")
    claims = list(data["history"]) + ([data["active"]] if data["active"] is not None else [])
    for claim in claims:
        validate_claim(claim)
        if claim["generation"] >= generation:
            _fail("claim generation is not below next_generation")
    if data["active"] is not None and data["active"]["status"] != ACTIVE:
        _fail("active slot holds an ended claim")
    if any(item["status"] == ACTIVE for item in data["history"]):
        _fail("history holds an ACTIVE claim")
    if len({claim["claim_id"] for claim in claims}) != len(claims):
        _fail("duplicate claim_id")


class TargetClaimStore:
    """Atomic per-target claim documents under machine-local WEB-02 storage.

    Callers must hold the target lock (``lock_path``) around read-modify-write.
    """

    def __init__(self, storage_root: Path) -> None:
        self.root = Path(storage_root) / "target_claims"
        self.locks = Path(storage_root) / "locks" / "targets"

    def path(self, physical_key: str) -> Path:
        return self.root / f"{target_hash(physical_key)}.json"

    def lock_path(self, physical_key: str) -> Path:
        return self.locks / f"{target_hash(physical_key)}.lock"

    def load(self, physical_key: str) -> dict[str, Any]:
        path = self.path(physical_key)
        if not path.exists():
            return empty_target_file(physical_key)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TargetClaimStoreError(f"cannot read target claim file: {path}") from exc
        validate_target_file(data, physical_key)
        return data

    def write(self, data: dict[str, Any]) -> None:
        validate_target_file(data, data["physical_key"])
        path = self.path(data["physical_key"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
        raw = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise TargetClaimStoreError(f"cannot persist target claim file: {path}") from exc
