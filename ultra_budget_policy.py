"""RT-002/B2 S2 — Ultra budget policy and conservative estimation.

Pure policy contract: no I/O, no clock, no network, no runtime hooks. Nothing in the production
runtime imports this module yet; S2 does not enforce anything. Ownership of the next steps (B2):
  S3a  durable reserve/terminal ledger (persists the liability semantics defined here),
  S3b  mandatory pre-HTTP guard on every physical LLM send (calls evaluate_request with the
       exact wire bytes produced by serialize_request_body),
  S3c  reserve before tool mutation, S4 full-read cap wiring, S5 UI / saved snapshots.

Units are explicit and never mixed:
  *_bytes             exact UTF-8 bytes of the final serialized HTTP body (measured, not estimated)
  *_tokens_est        conservative model/role-specific estimate (NOT a guaranteed tokenizer bound)
  *_liability_tokens  budget liability: estimate + output reserve while in flight or UNKNOWN,
                      provider-reported processed tokens once known (never money)
  *_attempts          physical provider attempts (retries, replans, repairs, diagnostics included)
Provider-reported usage, cached/precached tokens and money are separate quantities; no tariff
is applied anywhere in this module.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping

POLICY_SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------------------------
# Routes (S1 inventory: 7 physical LLM POST sites + OAuth, which is not an LLM bill)

SCOPE_RUN = "RUN"
SCOPE_COMPRESSOR = "COMPRESSOR_JOB"
SCOPE_MCP = "MCP_SESSION"
SCOPE_NONE = "NOT_BUDGETED"

CLASS_WORK = "WORK"
CLASS_MANDATORY_VERIFICATION = "MANDATORY_VERIFICATION"
CLASS_OPTIONAL_DIAGNOSTIC = "OPTIONAL_DIAGNOSTIC"
CLASS_AUTH = "AUTH"


@dataclass(frozen=True)
class RouteSpec:
    route_id: str
    role: str            # accounting role; also the token-profile key
    scope: str
    budget_class: str
    reachability: str    # ACTIVE / LEGACY_REACHABLE / UNREACHABLE_PROVEN (S1)


# The policy knows routes, not call sites: binding each physical send site to its constant route_id
# (and refusing a caller-chosen one) is S3b. The S1<->route mapping is pinned by the S2 test.
ROUTES: Mapping[str, RouteSpec] = {
    spec.route_id: spec for spec in (
        RouteSpec("executor", "executor", SCOPE_RUN, CLASS_WORK, "ACTIVE"),
        RouteSpec("audit_diagnostic", "executor", SCOPE_RUN, CLASS_OPTIONAL_DIAGNOSTIC, "ACTIVE"),
        RouteSpec("planner_session", "planner", SCOPE_RUN, CLASS_WORK, "ACTIVE"),
        RouteSpec("planner_direct", "planner", SCOPE_RUN, CLASS_WORK, "UNREACHABLE_PROVEN"),
        RouteSpec("verifier_final", "dredd", SCOPE_RUN, CLASS_MANDATORY_VERIFICATION, "ACTIVE"),
        RouteSpec("verifier_permission", "dredd", SCOPE_RUN, CLASS_WORK, "ACTIVE"),
        RouteSpec("planner_review", "dredd", SCOPE_RUN, CLASS_WORK, "ACTIVE"),
        RouteSpec("compressor", "compressor", SCOPE_COMPRESSOR, CLASS_WORK, "ACTIVE"),
        RouteSpec("mcp_chat", "mcp", SCOPE_MCP, CLASS_WORK, "LEGACY_REACHABLE"),
        RouteSpec("oauth", "auth", SCOPE_NONE, CLASS_AUTH, "ACTIVE"),
    )
}
PROFILE_KEYS = frozenset(spec.role for spec in ROUTES.values() if spec.scope != SCOPE_NONE)

# ---------------------------------------------------------------------------------------------
# Exact measurement of the request that will be sent


def serialize_request_body(body: Mapping[str, Any]) -> bytes:
    """Exactly the bytes httpx 0.28.x sends for `json=body` (S1: wire != sorted snapshot).

    S3b must send these bytes (content=...) so that measurement, hash and wire are one object.
    """
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class RequestMeasure:
    route_id: str
    provider_model_id: str
    wire_bytes: int                 # exact
    wire_sha256: str                # exact, of the bytes that will be sent
    output_reserve_tokens: int      # body max_tokens (exact request parameter)


def measure_request(route_id: str, body: Mapping[str, Any]) -> RequestMeasure:
    if not isinstance(body, Mapping):
        raise PolicyInputError("body must be a JSON object")
    try:
        data = serialize_request_body(body)
    except (TypeError, ValueError) as exc:   # NaN/inf, non-JSON values, lone surrogates (UnicodeEncodeError)
        raise PolicyInputError(f"body cannot be serialized as the sent JSON ({type(exc).__name__})") from exc
    max_tokens = body.get("max_tokens")
    if not _is_int(max_tokens) or not 1 <= max_tokens <= MAX_SANE_TOKENS:
        raise PolicyInputError("max_tokens must be a positive integer to reserve output tokens")
    if _text_problem(body.get("model")):
        raise PolicyInputError("model must be a non-empty provider model id")
    return RequestMeasure(route_id, body["model"], len(data), hashlib.sha256(data).hexdigest(), max_tokens)


# ---------------------------------------------------------------------------------------------
# Errors and reasons


class PolicyInputError(ValueError):
    """Malformed input to a pure policy function (programming/integration error)."""


class PolicyValidationError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


@dataclass(frozen=True)
class Reason:
    code: str
    text: str


def _reason(code: str, text: str) -> Reason:
    return Reason(code, text)


# ---------------------------------------------------------------------------------------------
# Policy snapshot: schema, validation, revision

MAX_SANE_BYTES = 1 << 30            # 1 GiB: structural ceiling, not a default
MAX_SANE_TOKENS = 10 ** 10
MAX_SANE_ATTEMPTS = 10 ** 6
MAX_SANE_BYTES_PER_TOKEN = 64.0
MISSING_PROFILE_MODES = ("DENY", "HARD_BOUND")
OUTPUT_RESERVE_MODES = ("MAX_TOKENS",)
SCOPE_MODES = ("DENY", "BUDGET")
ROLES_WITH_ATTEMPT_CAPS = ("planner", "executor", "dredd")


@dataclass(frozen=True)
class TokenProfile:
    provider_model_id: str
    profile_key: str               # route role
    bytes_per_token: float         # conservative divisor: estimate = ceil(wire_bytes / bytes_per_token)
    samples: int
    source_sha256: str             # calibration dataset provenance


@dataclass(frozen=True)
class RunLimits:
    max_request_bytes: int
    max_request_input_tokens_est: int
    max_verification_request_bytes: int          # Final Audit packets differ from work requests
    max_verification_request_input_tokens_est: int
    max_run_liability_tokens: int
    max_run_attempts: int
    max_attempts_per_role: Mapping[str, int | None]
    verification_reserve_tokens: int
    verification_reserve_attempts: int


@dataclass(frozen=True)
class ScopeLimits:
    mode: str
    max_request_bytes: int | None = None
    max_request_input_tokens_est: int | None = None
    max_scope_liability_tokens: int | None = None
    max_scope_attempts: int | None = None


@dataclass(frozen=True)
class PolicySnapshot:
    schema_version: int
    revision_label: str
    run: RunLimits
    profiles: tuple[TokenProfile, ...]
    missing_profile: str
    output_reserve: str
    compressor: ScopeLimits
    mcp: ScopeLimits
    max_full_read_bytes: int
    revision_sha256: str


MAX_TEXT_CHARS = 200


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _show(value) -> str:
    """Bounded, always-encodable rendering of untrusted input for error texts."""
    try:
        text = repr(value)                     # escapes lone surrogates; may refuse a gigantic int
    except Exception:                          # noqa: BLE001 - any repr failure must not escape validation
        text = f"<{type(value).__name__}>"
    return text if len(text) <= 60 else text[:57] + "..."


def _text_problem(value, *, max_chars: int = MAX_TEXT_CHARS) -> str | None:
    """Identifier/label text: non-empty str, bounded, UTF-8 encodable (json.loads yields lone surrogates)."""
    if not isinstance(value, str) or not value.strip():
        return f"ожидается непустая строка, получено {_show(value)}"
    if len(value) > max_chars:
        return f"строка длиннее {max_chars} символов"
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return f"строка не кодируется в UTF-8 (одиночный суррогат): {_show(value)}"
    return None


def _is_sha256_hex(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _check_keys(obj, path: str, required: set, optional: set, problems: list[str]) -> bool:
    if not isinstance(obj, Mapping):
        problems.append(f"{path}: ожидается объект, получено {_show(obj)}")
        return False
    keys = set(obj)
    for missing in sorted(required - keys):
        problems.append(f"{path}.{missing}: обязательное поле отсутствует")
    for unknown in sorted(keys - required - optional, key=_show):   # keys of mixed types are not orderable
        name = unknown if isinstance(unknown, str) and not _text_problem(unknown) else _show(unknown)
        problems.append(f"{path}.{name}: неизвестное поле (опечатка или неподдерживаемая единица)")
    return True


def _int_field(obj, key: str, path: str, problems: list[str], *, minimum: int, maximum: int,
               allow_none: bool = False):
    value = obj.get(key)
    if value is None and allow_none and key in obj:
        return None
    if not _is_int(value):
        problems.append(f"{path}.{key}: ожидается целое число в единицах поля, получено {_show(value)}")
        return None
    if value < minimum or value > maximum:
        problems.append(f"{path}.{key}: значение {_show(value)} вне допустимого диапазона [{minimum}, {maximum}]")
        return None
    return value


def validate_policy(raw: Mapping[str, Any]) -> PolicySnapshot:
    """Strict validation; every problem is reported in human-readable form. No implicit defaults."""
    problems: list[str] = []
    top_required = {"schema_version", "revision_label", "run", "estimation", "output_reserve",
                    "compressor", "mcp", "read"}
    if not _check_keys(raw, "policy", top_required, set(), problems):
        raise PolicyValidationError(problems)
    if raw.get("schema_version") != POLICY_SCHEMA_VERSION or not _is_int(raw.get("schema_version")):
        problems.append(f"policy.schema_version: поддерживается только {POLICY_SCHEMA_VERSION}")
    label = raw.get("revision_label")
    label_problem = _text_problem(label)
    if label_problem:
        problems.append(f"policy.revision_label: непустая строка до {MAX_TEXT_CHARS} символов ({label_problem})")

    run_raw = raw.get("run")
    run_keys = {"max_request_bytes", "max_request_input_tokens_est", "max_verification_request_bytes",
                "max_verification_request_input_tokens_est", "max_run_liability_tokens",
                "max_run_attempts", "max_attempts_per_role", "verification_reserve_tokens",
                "verification_reserve_attempts"}
    run = None
    if _check_keys(run_raw, "policy.run", run_keys, set(), problems):
        values = {
            "max_request_bytes": _int_field(run_raw, "max_request_bytes", "policy.run", problems,
                                            minimum=1, maximum=MAX_SANE_BYTES),
            "max_request_input_tokens_est": _int_field(run_raw, "max_request_input_tokens_est", "policy.run",
                                                       problems, minimum=1, maximum=MAX_SANE_TOKENS),
            "max_verification_request_bytes": _int_field(run_raw, "max_verification_request_bytes", "policy.run",
                                                         problems, minimum=1, maximum=MAX_SANE_BYTES),
            "max_verification_request_input_tokens_est": _int_field(
                run_raw, "max_verification_request_input_tokens_est", "policy.run", problems,
                minimum=1, maximum=MAX_SANE_TOKENS),
            "max_run_liability_tokens": _int_field(run_raw, "max_run_liability_tokens", "policy.run", problems,
                                                   minimum=1, maximum=MAX_SANE_TOKENS),
            "max_run_attempts": _int_field(run_raw, "max_run_attempts", "policy.run", problems,
                                           minimum=1, maximum=MAX_SANE_ATTEMPTS),
            "verification_reserve_tokens": _int_field(run_raw, "verification_reserve_tokens", "policy.run",
                                                      problems, minimum=0, maximum=MAX_SANE_TOKENS),
            "verification_reserve_attempts": _int_field(run_raw, "verification_reserve_attempts", "policy.run",
                                                        problems, minimum=0, maximum=MAX_SANE_ATTEMPTS),
        }
        per_role_raw = run_raw.get("max_attempts_per_role")
        per_role = {}
        if _check_keys(per_role_raw, "policy.run.max_attempts_per_role", set(ROLES_WITH_ATTEMPT_CAPS), set(),
                       problems):
            for role in ROLES_WITH_ATTEMPT_CAPS:
                per_role[role] = _int_field(per_role_raw, role, "policy.run.max_attempts_per_role", problems,
                                            minimum=1, maximum=MAX_SANE_ATTEMPTS, allow_none=True)
        if None not in (values["max_run_liability_tokens"], values["verification_reserve_tokens"]) \
                and values["verification_reserve_tokens"] >= values["max_run_liability_tokens"]:
            problems.append("policy.run.verification_reserve_tokens: резерв должен быть меньше лимита RUN, "
                            "иначе на основную работу не остаётся бюджета")
        if None not in (values["max_run_attempts"], values["verification_reserve_attempts"]) \
                and values["verification_reserve_attempts"] >= values["max_run_attempts"]:
            problems.append("policy.run.verification_reserve_attempts: резерв попыток должен быть меньше лимита")
        for key in ("max_request_input_tokens_est", "max_verification_request_input_tokens_est"):
            if None not in (values[key], values["max_run_liability_tokens"]) \
                    and values[key] > values["max_run_liability_tokens"]:
                problems.append(f"policy.run.{key}: не может превышать лимит RUN")
        if not any(v is None for v in values.values()) and len(per_role) == len(ROLES_WITH_ATTEMPT_CAPS):
            run = RunLimits(max_attempts_per_role=dict(per_role), **values)

    est_raw = raw.get("estimation")
    profiles: list[TokenProfile] = []
    missing_profile = None
    if _check_keys(est_raw, "policy.estimation", {"profiles", "missing_profile"}, set(), problems):
        missing_profile = est_raw.get("missing_profile")
        if missing_profile not in MISSING_PROFILE_MODES:
            problems.append(f"policy.estimation.missing_profile: одно из {MISSING_PROFILE_MODES}")
        seen = set()
        items = est_raw.get("profiles")
        if not isinstance(items, list):
            problems.append("policy.estimation.profiles: ожидается список")
            items = []
        for index, item in enumerate(items):
            path = f"policy.estimation.profiles[{index}]"
            if not _check_keys(item, path, {"provider_model_id", "profile_key", "bytes_per_token", "samples",
                                            "source_sha256"}, set(), problems):
                continue
            model, key = item.get("provider_model_id"), item.get("profile_key")
            bpt = item.get("bytes_per_token")
            ok = True
            model_problem = _text_problem(model)
            if model_problem:
                problems.append(f"{path}.provider_model_id: непустая строка ({model_problem})")
                ok = False
            if not isinstance(key, str) or key not in PROFILE_KEYS:   # type first: a list/dict is unhashable
                problems.append(f"{path}.profile_key: неизвестная роль {_show(key)}")
                ok = False
            # range before any float conversion: math.isfinite(10**400) raises OverflowError; NaN/inf fail the range
            if isinstance(bpt, bool) or not isinstance(bpt, (int, float)) or not 0 < bpt <= MAX_SANE_BYTES_PER_TOKEN:
                problems.append(f"{path}.bytes_per_token: конечное число в (0, {MAX_SANE_BYTES_PER_TOKEN}]")
                ok = False
            samples = _int_field(item, "samples", path, problems, minimum=1, maximum=10 ** 9)
            sha = item.get("source_sha256")
            if not _is_sha256_hex(sha):
                problems.append(f"{path}.source_sha256: 64 hex символа")
                ok = False
            if ok and (model, key) in seen:
                problems.append(f"{path}: повторный профиль для ({model}, {key})")
                ok = False
            if ok and samples is not None:
                seen.add((model, key))
                profiles.append(TokenProfile(model, key, float(bpt), samples, sha))

    output_reserve = raw.get("output_reserve")
    if output_reserve not in OUTPUT_RESERVE_MODES:
        problems.append(f"policy.output_reserve: одно из {OUTPUT_RESERVE_MODES}")

    def scope(name: str):
        scope_raw = raw.get(name)
        keys = {"mode", "max_request_bytes", "max_request_input_tokens_est", "max_scope_liability_tokens",
                "max_scope_attempts"}
        if not isinstance(scope_raw, Mapping):
            problems.append(f"policy.{name}: ожидается объект")
            return None
        mode = scope_raw.get("mode")
        if mode not in SCOPE_MODES:
            problems.append(f"policy.{name}.mode: одно из {SCOPE_MODES}")
            return None
        if mode == "DENY":
            _check_keys(scope_raw, f"policy.{name}", {"mode"}, set(), problems)
            return ScopeLimits("DENY")
        if not _check_keys(scope_raw, f"policy.{name}", keys, set(), problems):
            return None
        limits = ScopeLimits(
            "BUDGET",
            _int_field(scope_raw, "max_request_bytes", f"policy.{name}", problems, minimum=1, maximum=MAX_SANE_BYTES),
            _int_field(scope_raw, "max_request_input_tokens_est", f"policy.{name}", problems, minimum=1,
                       maximum=MAX_SANE_TOKENS),
            _int_field(scope_raw, "max_scope_liability_tokens", f"policy.{name}", problems, minimum=1,
                       maximum=MAX_SANE_TOKENS),
            _int_field(scope_raw, "max_scope_attempts", f"policy.{name}", problems, minimum=1,
                       maximum=MAX_SANE_ATTEMPTS),
        )
        return None if None in (limits.max_request_bytes, limits.max_request_input_tokens_est,
                                limits.max_scope_liability_tokens, limits.max_scope_attempts) else limits

    compressor, mcp = scope("compressor"), scope("mcp")
    read_raw = raw.get("read")
    max_read = None
    if _check_keys(read_raw, "policy.read", {"max_full_read_bytes"}, set(), problems):
        max_read = _int_field(read_raw, "max_full_read_bytes", "policy.read", problems, minimum=1,
                              maximum=MAX_SANE_BYTES)
    if problems or run is None or compressor is None or mcp is None or max_read is None:
        raise PolicyValidationError(problems or ["policy: некорректная структура"])
    normalized = json.loads(json.dumps(raw, ensure_ascii=False, sort_keys=True))
    revision = hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":")).encode("utf-8")).hexdigest()
    return PolicySnapshot(POLICY_SCHEMA_VERSION, label, run, tuple(profiles), missing_profile, output_reserve,
                          compressor, mcp, max_read, revision)


# ---------------------------------------------------------------------------------------------
# Conservative estimation and calibration

EST_CALIBRATED = "CONSERVATIVE_CALIBRATED"
EST_HARD_BOUND = "HARD_BOUND_ASSUMPTION"
EST_NEEDS_CALIBRATION = "NEEDS_CALIBRATION"


@dataclass(frozen=True)
class TokenEstimate:
    tokens: int | None
    status: str
    profile: TokenProfile | None
    note: str


def estimate_input_tokens(snapshot: PolicySnapshot, provider_model_id: str, profile_key: str, wire_bytes: int,
                          *, breached: Iterable[tuple[str, str]] = ()) -> TokenEstimate:
    """Upper-side estimate of provider input tokens (prompt + precached) for one request.

    CONSERVATIVE_CALIBRATED: ceil(bytes / bytes_per_token) with a profile calibrated on observed
    (bytes, provider tokens) pairs; empirical, not a proof.
    HARD_BOUND_ASSUMPTION: tokens <= bytes, valid only under the assumption that every token
    (including chat-template tokens) covers >= 1 byte of the JSON body; never optimistic, very loose.
    NEEDS_CALIBRATION: no usable profile and the policy forbids the hard bound.
    A profile whose estimate was exceeded by a provider-known value in this RUN is not used again.
    """
    if not isinstance(provider_model_id, str) or not isinstance(profile_key, str):
        raise PolicyInputError("provider_model_id and profile_key must be strings")
    if not _is_int(wire_bytes) or not 0 <= wire_bytes <= MAX_SANE_BYTES:   # a float division must not overflow
        raise PolicyInputError(f"wire_bytes must be an integer in [0, {MAX_SANE_BYTES}]")
    try:
        breached = set(breached)
    except TypeError as exc:
        raise PolicyInputError("breached must hold (provider_model_id, profile_key) pairs") from exc
    profile = next((p for p in snapshot.profiles
                    if p.provider_model_id == provider_model_id and p.profile_key == profile_key), None)
    if profile is not None and (provider_model_id, profile_key) not in breached:
        return TokenEstimate(math.ceil(wire_bytes / profile.bytes_per_token), EST_CALIBRATED, profile,
                             f"калиброванный профиль {provider_model_id}/{profile_key}, "
                             f"{profile.bytes_per_token:.3f} байт/токен, n={profile.samples}")
    why = "оценка ранее превышена фактом" if profile is not None else "нет профиля"
    if snapshot.missing_profile == "HARD_BOUND":
        return TokenEstimate(wire_bytes, EST_HARD_BOUND, None,
                             f"{why}: верхняя граница-допущение токены <= байты ({wire_bytes})")
    return TokenEstimate(None, EST_NEEDS_CALIBRATION, None,
                         f"{why} для {provider_model_id}/{profile_key}; политика требует калибровку")


@dataclass(frozen=True)
class CalibrationRow:
    provider_model_id: str
    profile_key: str
    wire_bytes: int
    prompt_tokens: int
    precached_prompt_tokens: int | None
    completion_tokens: int


def processed_input_tokens(row: CalibrationRow) -> int:
    return row.prompt_tokens + (row.precached_prompt_tokens or 0)


def _calibration_row_problem(row) -> str | None:
    if not isinstance(row, CalibrationRow):
        return f"ожидается CalibrationRow, получено {_show(row)}"
    if _text_problem(row.provider_model_id):
        return f"provider_model_id {_show(row.provider_model_id)}"
    if not isinstance(row.profile_key, str) or row.profile_key not in PROFILE_KEYS:
        return f"profile_key {_show(row.profile_key)}"
    if not _is_int(row.wire_bytes) or not 0 <= row.wire_bytes <= MAX_SANE_BYTES:
        return f"wire_bytes {_show(row.wire_bytes)}"
    for name in ("prompt_tokens", "completion_tokens", "precached_prompt_tokens"):
        value = getattr(row, name)
        if value is None and name == "precached_prompt_tokens":
            continue
        if not _is_int(value) or not 0 <= value <= MAX_SANE_TOKENS:
            return f"{name} {_show(value)}"
    return None


def calibrate_profiles(rows: Iterable[CalibrationRow], *, margin: float, source_sha256: str,
                       min_samples: int) -> tuple[list[dict], list[dict]]:
    """Profiles from the observed lower envelope of bytes/token, divided by (1 + margin).

    Returns (profiles accepted for a snapshot, per-group report). Groups with fewer than
    min_samples observations are reported as NEEDS_CALIBRATION and produce no profile.
    """
    if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not 0 <= margin <= 10:
        raise PolicyInputError("margin must be a number in [0, 10]")
    if not _is_int(min_samples) or min_samples < 1:
        raise PolicyInputError("min_samples must be a positive integer")
    if not _is_sha256_hex(source_sha256):
        raise PolicyInputError("source_sha256 must be 64 lowercase hex characters")
    rows = list(rows)
    for index, row in enumerate(rows):
        problem = _calibration_row_problem(row)
        if problem:
            raise PolicyInputError(f"calibration row {index}: {problem}")
    groups: dict[tuple[str, str], list[CalibrationRow]] = {}
    for row in rows:
        if processed_input_tokens(row) > 0:
            groups.setdefault((row.provider_model_id, row.profile_key), []).append(row)
    profiles, report = [], []
    for (model, key), items in sorted(groups.items()):
        ratios = sorted(r.wire_bytes / processed_input_tokens(r) for r in items)
        floor = ratios[0]
        bpt = math.floor(floor / (1 + margin) * 10000) / 10000   # a divisor is only ever rounded DOWN
        usable = len(items) >= min_samples and bpt > 0
        entry = {"provider_model_id": model, "profile_key": key, "samples": len(items),
                 "observed_min_bytes_per_token": round(floor, 4),
                 "observed_median_bytes_per_token": round(ratios[len(ratios) // 2], 4),
                 "observed_max_bytes_per_token": round(ratios[-1], 4),
                 "bytes_per_token": bpt,
                 "status": "CALIBRATED" if usable else EST_NEEDS_CALIBRATION}
        report.append(entry)
        if usable:
            profiles.append({"provider_model_id": model, "profile_key": key, "bytes_per_token": bpt,
                             "samples": len(items), "source_sha256": source_sha256})
    return profiles, report


# ---------------------------------------------------------------------------------------------
# Liability semantics of one physical attempt (pure; durable persistence is S3a)

RESERVED = "RESERVED"
SENT = "SENT"
NOT_SENT = "NOT_SENT"
KNOWN_TERMINAL = "KNOWN_TERMINAL"
UNKNOWN_TERMINAL = "UNKNOWN_TERMINAL"
RECONCILED = "RECONCILED"
ANOMALY = "ANOMALY"
OPEN_STATES = (RESERVED, SENT)
TERMINAL_OUTCOMES = ("completed", "provider_error", "timeout", "transport_error", "parse_error", "cancelled")


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    precached_prompt_tokens: int | None   # None = provider did not report it (UNKNOWN, not zero)


def validate_usage(raw: Any) -> tuple[str, Usage | None, str]:
    """('KNOWN', usage, '') | ('MISSING', None, why) | ('INVALID', None, why).

    Integers only (bool is not an integer here), non-negative; a reported total must equal
    prompt + completion. A missing precached field stays None and is never read as zero.
    """
    if raw is None:
        return "MISSING", None, "usage отсутствует"
    if not isinstance(raw, Mapping):
        return "INVALID", None, "usage не является объектом"
    if "prompt_tokens" not in raw and "completion_tokens" not in raw:
        return "MISSING", None, "usage без счётчиков"
    values = {}
    for key in ("prompt_tokens", "completion_tokens"):
        value = raw.get(key)
        if not _is_int(value) or value < 0:
            return "INVALID", None, f"{key}={_show(value)} не является неотрицательным целым"
        values[key] = value
    precached = raw.get("precached_prompt_tokens") if "precached_prompt_tokens" in raw else None
    if "precached_prompt_tokens" in raw and (not _is_int(precached) or precached < 0):
        return "INVALID", None, f"precached_prompt_tokens={_show(precached)} некорректен"
    total = raw.get("total_tokens")
    if "total_tokens" in raw and (not _is_int(total) or total != values["prompt_tokens"] + values["completion_tokens"]):
        return "INVALID", None, f"total_tokens={_show(total)} не равен prompt + completion"
    return "KNOWN", Usage(values["prompt_tokens"], values["completion_tokens"], precached), ""


# A provider answer was received (2xx or an HTTP error status) vs. no answer was observed.
RESPONSE_OUTCOMES = ("completed", "parse_error", "provider_error")
NO_RESPONSE_OUTCOMES = ("timeout", "transport_error", "cancelled")


@dataclass(frozen=True)
class AttemptRecord:
    attempt_id: str
    route_id: str
    provider_model_id: str
    scope_id: str
    reserved_input_tokens_est: int
    reserved_output_tokens: int
    state: str = RESERVED
    usage: Usage | None = None
    terminal_outcomes: tuple[str, ...] = ()                          # every terminal received, in order
    anomalies: tuple[str, ...] = ()
    terminal_events: tuple[tuple[str, Usage | None], ...] = ()       # distinct accepted (outcome, usage) facts

    @property
    def reserved_liability_tokens(self) -> int:
        return self.reserved_input_tokens_est + self.reserved_output_tokens

    def _input_of(self, usage: Usage) -> int:
        if usage.precached_prompt_tokens is None:
            # cached part not reported: the estimate stays the upper side of the input
            return max(usage.prompt_tokens, self.reserved_input_tokens_est)
        return usage.prompt_tokens + usage.precached_prompt_tokens

    @property
    def known_input_tokens(self) -> int | None:
        return None if self.usage is None else self._input_of(self.usage)

    @property
    def liability_tokens(self) -> int:
        if self.state == NOT_SENT:
            return 0
        if self.state in (KNOWN_TERMINAL, RECONCILED):
            return self.known_input_tokens + self.usage.completion_tokens
        if self.state == ANOMALY:   # contradictory claims: the largest of the reservation and every claim
            claims = [u for u in (self.usage, *(u for _o, u in self.terminal_events)) if u is not None]
            return max([self.reserved_liability_tokens] + [self._input_of(u) + u.completion_tokens for u in claims])
        return self.reserved_liability_tokens  # RESERVED, SENT, UNKNOWN_TERMINAL

    @property
    def estimate_breached(self) -> bool:
        """Provider-known input exceeded the estimate (prompt alone suffices when precached is unreported)."""
        if self.state not in (KNOWN_TERMINAL, RECONCILED) or self.usage is None:
            return False
        if self.usage.prompt_tokens > self.reserved_input_tokens_est:
            return True
        return (self.usage.precached_prompt_tokens is not None
                and self.usage.prompt_tokens + self.usage.precached_prompt_tokens > self.reserved_input_tokens_est)


def reserve_attempt(attempt_id: str, measure: RequestMeasure, estimate: TokenEstimate, scope_id: str) -> AttemptRecord:
    if estimate.tokens is None:
        raise PolicyInputError("cannot reserve without a token estimate")
    return AttemptRecord(attempt_id, measure.route_id, measure.provider_model_id, scope_id,
                         estimate.tokens, measure.output_reserve_tokens)


def mark_sent(record: AttemptRecord) -> AttemptRecord:
    if record.state != RESERVED:
        return replace(record, state=ANOMALY, anomalies=record.anomalies + (f"SENT from {record.state}",))
    return replace(record, state=SENT)


def mark_not_sent(record: AttemptRecord) -> AttemptRecord:
    """Only a PROVEN not-sent (S3b) releases a reservation; never after SENT."""
    if record.state != RESERVED:
        return replace(record, state=ANOMALY, anomalies=record.anomalies + (f"NOT_SENT from {record.state}",))
    return replace(record, state=NOT_SENT)


def _refines(previous_outcome: str, outcome: str) -> bool:
    """The only way an UNKNOWN attempt may change its terminal outcome: the same outcome (now with usage),
    or a late provider answer after a no-response outcome (B2 §4: late known corrects the same attempt)."""
    return outcome == previous_outcome or (previous_outcome in NO_RESPONSE_OUTCOMES and outcome in RESPONSE_OUTCOMES)


def apply_terminal(record: AttemptRecord, outcome: str, raw_usage: Any) -> AttemptRecord:
    """Settle one terminal event. One physical attempt has one terminal truth:
    - a replay of an already accepted (outcome, usage) event is idempotent (at-least-once delivery);
    - an UNKNOWN attempt may be refined (see _refines): with usage it becomes RECONCILED;
    - anything else contradicts what is already settled -> ANOMALY, whose liability is the largest of the
      reservation and every claim (never lowered by contradictory data); ANOMALY is absorbing.
    """
    if not isinstance(outcome, str) or outcome not in TERMINAL_OUTCOMES:
        return replace(record, state=ANOMALY, anomalies=record.anomalies + (f"unknown outcome {_show(outcome)}",),
                       terminal_outcomes=record.terminal_outcomes
                       + (outcome if isinstance(outcome, str) else _show(outcome),))
    status, usage, why = validate_usage(raw_usage)
    outcomes = record.terminal_outcomes + (outcome,)
    if status == "INVALID":
        return replace(record, state=ANOMALY, terminal_outcomes=outcomes, anomalies=record.anomalies + (why,))
    event = (outcome, usage)                                   # usage is None when the provider gave none
    events = record.terminal_events + (event,)
    if record.state in (RESERVED, NOT_SENT):
        return replace(record, state=ANOMALY, terminal_outcomes=outcomes, terminal_events=events,
                       anomalies=record.anomalies + (f"terminal before SENT ({record.state})",),
                       usage=usage if usage is not None else record.usage)
    if record.state == SENT:
        return replace(record, state=KNOWN_TERMINAL if usage is not None else UNKNOWN_TERMINAL, usage=usage,
                       terminal_outcomes=outcomes, terminal_events=events)
    if event in record.terminal_events:                        # the same fact delivered again
        return replace(record, terminal_outcomes=outcomes)
    if record.state == ANOMALY:
        return replace(record, terminal_outcomes=outcomes, terminal_events=events)
    previous = record.terminal_events[-1][0] if record.terminal_events else None
    if record.state == UNKNOWN_TERMINAL and previous is not None and _refines(previous, outcome):
        return replace(record, state=RECONCILED if usage is not None else UNKNOWN_TERMINAL, usage=usage,
                       terminal_outcomes=outcomes, terminal_events=events)
    usage_note = "с usage" if usage is not None else "без usage"
    return replace(record, state=ANOMALY, terminal_outcomes=outcomes, terminal_events=events,
                   anomalies=record.anomalies + (f"противоречивый terminal {outcome} ({usage_note}) после "
                                                 f"{previous} в состоянии {record.state}",))


def orphan_terminal_record(attempt_id: str, scope_id: str, outcome: str, raw_usage: Any) -> AttemptRecord:
    """A terminal without a known reservation is a ledger anomaly: it blocks new sends in its scope."""
    status, usage, _why = validate_usage(raw_usage)
    usage = usage if status == "KNOWN" else None
    return AttemptRecord(attempt_id, "<orphan>", "<unknown>", scope_id, 0, 0, state=ANOMALY, usage=usage,
                         terminal_outcomes=(_show(outcome) if not isinstance(outcome, str) else outcome,),
                         anomalies=("terminal without reservation",),
                         terminal_events=((outcome, usage),) if isinstance(outcome, str) else ())


# ---------------------------------------------------------------------------------------------
# Budget view and decision

ALLOW = "ALLOW"
DENY = "DENY"
NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class BudgetView:
    limit_liability_tokens: int | None
    known_liability_tokens: int
    in_flight_liability_tokens: int
    unknown_liability_tokens: int
    anomaly_liability_tokens: int
    protected_reserve_tokens: int
    attempts_used: int
    attempts_by_role: Mapping[str, int]
    anomalies: tuple[str, ...]
    breached_profiles: frozenset

    @property
    def committed_liability_tokens(self) -> int:
        return (self.known_liability_tokens + self.in_flight_liability_tokens + self.unknown_liability_tokens
                + self.anomaly_liability_tokens)


@dataclass(frozen=True)
class RunContext:
    scope_id: str
    final_audit_enabled: bool   # separate user control; the budget never switches it off


@dataclass(frozen=True)
class Decision:
    verdict: str
    reasons: tuple[Reason, ...]
    route_id: str
    estimate: TokenEstimate | None = None
    reservation_liability_tokens: int | None = None
    view: BudgetView | None = None
    consequence: str | None = None


def _usage_problem(usage) -> str | None:
    if not isinstance(usage, Usage):
        return f"usage {_show(usage)}"
    for name in ("prompt_tokens", "completion_tokens", "precached_prompt_tokens"):
        value = getattr(usage, name)
        if not (value is None and name == "precached_prompt_tokens") and (not _is_int(value) or value < 0):
            return f"usage.{name} {_show(value)}"
    return None


def _record_problem(record: AttemptRecord) -> str | None:
    """Structural check of a record (S3a will rehydrate them from storage); None when it is well-formed."""
    for name in ("attempt_id", "route_id", "provider_model_id", "state"):
        if not isinstance(getattr(record, name), str):
            return f"{name} {_show(getattr(record, name))}"
    for name in ("reserved_input_tokens_est", "reserved_output_tokens"):
        value = getattr(record, name)
        if not _is_int(value) or value < 0:
            return f"{name} {_show(value)}"
    if record.usage is not None and _usage_problem(record.usage):
        return _usage_problem(record.usage)
    if record.state in (KNOWN_TERMINAL, RECONCILED) and record.usage is None:
        return f"{record.state} без usage"
    for name in ("terminal_outcomes", "anomalies"):
        value = getattr(record, name)
        if not isinstance(value, tuple) or not all(isinstance(item, str) for item in value):
            return f"{name} {_show(value)}"
    events = record.terminal_events
    if not isinstance(events, tuple) or not all(
            isinstance(e, tuple) and len(e) == 2 and isinstance(e[0], str)
            and (e[1] is None or not _usage_problem(e[1])) for e in events):
        return f"terminal_events {_show(events)}"
    return None


def budget_view(snapshot: PolicySnapshot, attempts: Iterable[AttemptRecord], scope_id: str,
                *, final_audit_enabled: bool) -> BudgetView:
    known = in_flight = unknown = anomaly = used = 0
    by_role: dict[str, int] = {}
    anomalies: list[str] = []
    breached = set()
    for record in attempts:
        if not isinstance(record, AttemptRecord):   # its scope is unknowable: it blocks every scope
            anomalies.append(f"не запись попытки: {_show(record)}")
            continue
        if record.scope_id != scope_id:
            continue
        problem = _record_problem(record)
        if problem:   # never trust a malformed record's numbers; keep what can be read, then block
            anomalies.append(f"{_show(record.attempt_id)}: повреждённая запись ({problem})")
            if _is_int(record.reserved_input_tokens_est) and _is_int(record.reserved_output_tokens):
                anomaly += max(record.reserved_input_tokens_est, 0) + max(record.reserved_output_tokens, 0)
            continue
        spec = ROUTES.get(record.route_id)
        if spec is None:
            anomalies.append(f"{record.attempt_id}: неизвестный маршрут {_show(record.route_id)}")
            anomaly += record.liability_tokens
            continue
        if record.state != NOT_SENT:
            used += 1
            if spec.budget_class != CLASS_MANDATORY_VERIFICATION:   # role caps bound work, not Final Audit
                by_role[spec.role] = by_role.get(spec.role, 0) + 1
        liability = record.liability_tokens
        if record.state in (KNOWN_TERMINAL, RECONCILED):
            known += liability
        elif record.state in OPEN_STATES:
            in_flight += liability
        elif record.state == UNKNOWN_TERMINAL:
            unknown += liability
        elif record.state == ANOMALY:
            anomaly += liability
            anomalies.extend(f"{record.attempt_id}: {a}" for a in record.anomalies or ("ANOMALY без пояснения",))
        elif record.state == NOT_SENT:
            pass   # proven not sent (S3b): the reservation is released, liability 0
        else:   # e.g. a corrupt state rehydrated by a future ledger: keep the reservation and block
            anomaly += liability
            anomalies.append(f"{record.attempt_id}: неизвестное состояние {_show(record.state)}")
        if record.estimate_breached:
            breached.add((record.provider_model_id, spec.role))
    reserve = snapshot.run.verification_reserve_tokens if final_audit_enabled else 0
    return BudgetView(None, known, in_flight, unknown, anomaly, reserve, used, by_role, tuple(anomalies),
                      frozenset(breached))


def _measure_problem(measure: RequestMeasure) -> str | None:
    """A hand-built measure must not lower liability (e.g. a negative output reserve) or dodge the estimate."""
    if not _is_int(measure.wire_bytes) or not 0 <= measure.wire_bytes <= MAX_SANE_BYTES:
        return f"wire_bytes={_show(measure.wire_bytes)}"
    if not _is_int(measure.output_reserve_tokens) or not 1 <= measure.output_reserve_tokens <= MAX_SANE_TOKENS:
        return f"output_reserve_tokens={_show(measure.output_reserve_tokens)}"
    if _text_problem(measure.provider_model_id):
        return f"provider_model_id: {_text_problem(measure.provider_model_id)}"
    if not _is_sha256_hex(measure.wire_sha256):
        return "wire_sha256 не является SHA-256"
    return None


def evaluate_request(snapshot: PolicySnapshot, attempts: Iterable[AttemptRecord], measure: RequestMeasure,
                     context: RunContext) -> Decision:
    """Pure pre-send decision for ONE physical attempt. S3b must call it with the exact wire measure."""
    attempts = list(attempts)
    spec = ROUTES.get(measure.route_id) if isinstance(measure.route_id, str) else None   # a list is unhashable
    if spec is None:
        return Decision(DENY, (_reason("UNKNOWN_ROUTE", f"маршрут {_show(measure.route_id)} не инвентаризирован"),),
                        measure.route_id)
    if spec.scope == SCOPE_NONE:
        return Decision(NOT_APPLICABLE, (_reason("NOT_LLM_TRAFFIC", "OAuth не расходует токены модели"),),
                        measure.route_id)
    problem = _measure_problem(measure)
    if problem:
        return Decision(DENY, (_reason("INVALID_MEASURE", f"измерение запроса некорректно: {problem}"),),
                        measure.route_id)
    reasons: list[Reason] = []
    if spec.scope == SCOPE_RUN:
        verification = spec.budget_class == CLASS_MANDATORY_VERIFICATION
        max_request_bytes = (snapshot.run.max_verification_request_bytes if verification
                             else snapshot.run.max_request_bytes)
        max_request_tokens = (snapshot.run.max_verification_request_input_tokens_est if verification
                              else snapshot.run.max_request_input_tokens_est)
        limit_tokens = snapshot.run.max_run_liability_tokens
        limit_attempts = snapshot.run.max_run_attempts
    else:
        scope_limits = snapshot.compressor if spec.scope == SCOPE_COMPRESSOR else snapshot.mcp
        if scope_limits.mode == "DENY":
            return Decision(DENY, (_reason("ROUTE_DISABLED_BY_POLICY",
                                           f"маршрут {spec.route_id} запрещён политикой ({spec.scope})"),),
                            measure.route_id)
        max_request_bytes = scope_limits.max_request_bytes
        max_request_tokens = scope_limits.max_request_input_tokens_est
        limit_tokens = scope_limits.max_scope_liability_tokens
        limit_attempts = scope_limits.max_scope_attempts
    final_audit = context.final_audit_enabled and spec.scope == SCOPE_RUN
    view = budget_view(snapshot, attempts, context.scope_id, final_audit_enabled=final_audit)
    view = replace(view, limit_liability_tokens=limit_tokens)
    if view.anomalies:
        return Decision(DENY, (_reason("LEDGER_ANOMALY", "учёт попыток противоречив: новые отправки запрещены "
                                       "до восстановления (" + "; ".join(view.anomalies[:3]) + ")"),),
                        measure.route_id, view=view, consequence="NO_NEW_SENDS")
    if measure.wire_bytes > max_request_bytes:
        reasons.append(_reason("REQUEST_BYTES_EXCEEDED",
                               f"запрос {measure.wire_bytes} байт больше лимита {max_request_bytes} байт"))
    estimate = estimate_input_tokens(snapshot, measure.provider_model_id, spec.role, measure.wire_bytes,
                                     breached=view.breached_profiles)
    if estimate.tokens is None:
        return Decision(DENY, tuple(reasons) + (_reason(EST_NEEDS_CALIBRATION, estimate.note),),
                        measure.route_id, estimate=estimate, view=view)
    if estimate.tokens > max_request_tokens:
        reasons.append(_reason("REQUEST_TOKENS_EXCEEDED",
                               f"оценка входа {estimate.tokens} токенов больше лимита {max_request_tokens}"))
    liability = estimate.tokens + measure.output_reserve_tokens
    mandatory = spec.budget_class == CLASS_MANDATORY_VERIFICATION
    protected_tokens = 0 if mandatory or not final_audit else view.protected_reserve_tokens
    protected_attempts = 0 if mandatory or not final_audit else snapshot.run.verification_reserve_attempts
    if view.committed_liability_tokens + liability + protected_tokens > limit_tokens:
        detail = (f"после запроса обязательства {view.committed_liability_tokens + liability} "
                  f"(+ резерв проверки {protected_tokens}) больше лимита {limit_tokens}")
        reasons.append(_reason("RUN_LIABILITY_EXCEEDED" if not protected_tokens or
                               view.committed_liability_tokens + liability > limit_tokens
                               else "VERIFICATION_RESERVE_PROTECTED", detail))
    if view.attempts_used + 1 + protected_attempts > limit_attempts:
        code = ("RUN_ATTEMPTS_EXCEEDED" if not protected_attempts or view.attempts_used + 1 > limit_attempts
                else "VERIFICATION_RESERVE_PROTECTED")
        reasons.append(_reason(code, f"попытка {view.attempts_used + 1} (+ резерв проверки {protected_attempts}) "
                                     f"больше лимита {limit_attempts}"))
    if spec.scope == SCOPE_RUN and not mandatory:   # a role cap never silently disables Final Audit
        role_cap = snapshot.run.max_attempts_per_role.get(spec.role)
        if role_cap is not None and view.attempts_by_role.get(spec.role, 0) + 1 > role_cap:
            reasons.append(_reason("ROLE_ATTEMPTS_EXCEEDED", f"роль {spec.role}: лимит попыток {role_cap}"))
    if reasons:
        consequence = "NO_SUCCESS_WITHOUT_AUDIT" if mandatory else None
        return Decision(DENY, tuple(reasons), measure.route_id, estimate=estimate,
                        reservation_liability_tokens=liability, view=view, consequence=consequence)
    return Decision(ALLOW, (_reason("WITHIN_POLICY", "запрос укладывается в политику"),), measure.route_id,
                    estimate=estimate, reservation_liability_tokens=liability, view=view)


def preflight_run(snapshot: PolicySnapshot, context: RunContext) -> tuple[Reason, ...]:
    """Human-readable warnings for a RUN start / UI preview (S5). Never changes the policy."""
    warnings = []
    if context.final_audit_enabled and snapshot.run.verification_reserve_tokens == 0:
        warnings.append(_reason("RESERVE_ZERO_WITH_FINAL_AUDIT",
                                "Final Audit включён, но резерв проверки 0: основная работа может израсходовать "
                                "весь лимит, и RUN завершится без SUCCESS"))
    if context.final_audit_enabled and snapshot.run.verification_reserve_attempts == 0:
        warnings.append(_reason("RESERVE_ATTEMPTS_ZERO_WITH_FINAL_AUDIT",
                                "Final Audit включён, но резерв попыток проверки 0"))
    reserve, largest = snapshot.run.verification_reserve_tokens, snapshot.run.max_verification_request_input_tokens_est
    if context.final_audit_enabled and 0 < reserve < largest:
        warnings.append(_reason("RESERVE_BELOW_ONE_MAX_VERIFICATION",
                                f"резерв проверки {reserve} токенов меньше одного максимального запроса Final Audit "
                                f"({largest}); если основная работа исчерпает лимит, крупный Final Audit будет "
                                "запрещён и RUN завершится без SUCCESS"))
    if snapshot.missing_profile == "HARD_BOUND":
        warnings.append(_reason("HARD_BOUND_FALLBACK",
                                "для моделей без калибровки используется грубая граница токены <= байты"))
    if snapshot.mcp.mode == "DENY":
        warnings.append(_reason("MCP_DISABLED", "прямой MCP-чат запрещён политикой"))
    if snapshot.compressor.mode == "DENY":
        warnings.append(_reason("COMPRESSOR_DISABLED", "компрессор сообщений запрещён политикой"))
    return tuple(warnings)


def evaluate_full_read(snapshot: PolicySnapshot, file_bytes: int) -> Decision:
    """S4 contract (not wired): a whole-file READ larger than the cap is refused, never silently cut."""
    if not _is_int(file_bytes) or file_bytes < 0:
        raise PolicyInputError("file_bytes must be a non-negative integer")
    if file_bytes > snapshot.max_full_read_bytes:
        return Decision(DENY, (_reason("FULL_READ_EXCEEDS_CAP",
                                       f"файл {file_bytes} байт больше лимита полного чтения "
                                       f"{snapshot.max_full_read_bytes}; используйте поиск или чтение диапазона"),),
                        "read_file")
    return Decision(ALLOW, (_reason("WITHIN_POLICY", "полное чтение в пределах лимита"),), "read_file")
