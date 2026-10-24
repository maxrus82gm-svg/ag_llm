"""Publication-safe copies of Web Alarm diagnostic evidence (offline, operator-run, never imported by runtime).

Why (CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001): per-TASK helpers replaced three literal spellings of the local
TEMP/home/repo roots. Paths that reached evidence through a Python repr inside JSON (doubled or quadrupled
backslashes), lower-cased physical keys, extended-length prefixes, or message tails truncated inside a profile
name were published unchanged, and files outside ``runs/`` were never checked at all.

Design:
* detection is structural - any drive, UNC, extended-length or POSIX home path, any mix and number of
  separators, any case - so it does not depend on who runs it, on which drive or from which folder;
* only the identifying prefix of a path is replaced (``<TEMP>``, ``<HOME>``, ``<REPO>``, ``<UNC>``, ``<ABS>``);
  the remainder keeps its exact separators and escaping, so nested JSON stays valid and diagnostics stay legible;
* JSON is edited string token by string token: numbers, literals, whitespace, key order and duplicate keys
  keep their original bytes; protected identifiers (test ids, statuses) must not change or the file is refused;
* the output is a pure function of (input bytes, policy) - no clock, no machine data - so anybody can rerun
  ``stage`` on the published originals and compare SHA-256;
* the machine's own identity (user, computer, profile folder) is used only by the final publication gate as an
  independent backstop; anything left over, any secret-like value or any unsupported file refuses publication.

Integrity and completeness (CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001, F-ES-01 / F-ES-02):
* ``--manifest``: every listed file must match its declared SHA-256 and size, and every present file must be
  listed; a broken, duplicate-key, self-listing or incomplete manifest, unsafe or case-colliding ids, links in the
  package refuse the run before anything is written. The candidate's manifest.json is re-hashed to describe the
  sanitized bytes (the original stays in ``originals/``). Without ``--manifest`` a manifest.json is an ordinary file.
* ``verify`` recomputes everything from the preserved originals - schema, ids, totals, verdict, safety, manifest
  results, the exact sets of originals and sanitized copies - and never trusts the mapping's own claims. Proving
  that nothing was removed needs an anchor outside the bundle: ``--package`` (the source as it is now) or
  ``--mapping-sha256`` (the mapping hash printed by ``stage`` and recorded elsewhere). Without one: NOT_PROVEN,
  publication REFUSED. A manifest inside the package is a claim, not a cryptographic anchor. ``--package`` must be
  independent of the bundle (not the bundle, not inside it, not containing it, not reaching it through a link or a
  hard-linked file) - otherwise ``package-not-independent`` and REFUSED (F-ES-03).

Commands (``python -m web_alarm.evidence_sanitizer``)::

  scan   PACKAGE [--manifest] [--json FILE]               read-only inventory; never prints matched values
  stage  PACKAGE --out DIR [--manifest]                   preserve originals, write sanitized copies and mapping.json
  verify DIR [--package PACKAGE] [--mapping-sha256 HEX]   re-prove the bundle; see above

``--out`` must be outside the package and either outside the repository or under its git-ignored ``logs/``.
Exit codes: 0 = safe, 2 = findings remain / integrity not proven / publication refused, 3 = usage or environment
error. Python >= 3.12 (possessive quantifiers; junction detection).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

POLICY_VERSION = 1
REPO_ROOT = Path(__file__).resolve().parents[1]
LINE_SEPARATORS = "".join(chr(code) for code in (0x85, 0x2028, 0x2029))

TEMP, HOME, REPO, UNC, ABS, FRAGMENT, POSIX_HOME, SECRET = (
    "TEMP", "HOME", "REPO", "UNC", "ABS", "FRAGMENT", "POSIX_HOME", "SECRET")
ILLUSTRATIVE, SYSTEM, DRIVE_ROOT = "ILLUSTRATIVE", "SYSTEM", "DRIVE_ROOT"
REPLACED_KINDS = frozenset({TEMP, HOME, REPO, UNC, ABS, FRAGMENT, POSIX_HOME, SECRET})
KEPT_KINDS = frozenset({ILLUSTRATIVE, SYSTEM, DRIVE_ROOT})
PROTECTED_KEYS = frozenset({"test", "test_id", "selector", "status", "outcome", "exit", "label", "task"})
SYSTEM_ROOTS = frozenset({"windows", "program files", "program files (x86)", "programdata"})
PUBLIC_PROFILES = frozenset({"public", "default", "default user", "all users"})
PROFILE_ROOTS = frozenset({"users", "documents and settings"})
GENERIC_HOSTS = frozenset({"workgroup", "localhost"})
GENERIC_WORDS = GENERIC_HOSTS | {"users", "public", "default", "desktop", "laptop", "workstation", "win", "home"}
ELLIPSES = frozenset({"\u2026", "..."})
EXIT_SAFE, EXIT_REFUSED, EXIT_USAGE = 0, 2, 3

# A path component: ordinary name characters, or a JSON/Python ``\uXXXX`` escape of a nested level (so an escaped
# non-ASCII profile name stays one component). Single spaces are allowed inside ("Program Files", "Zq Synth"),
# but never in front of another drive path. A separator is any run of / or \, except a backslash that starts a
# ``\uXXXX`` escape.
# Possessive quantifiers (Python >= 3.11) keep matching linear on long backslash runs: separators and name
# characters are disjoint, so nothing ever needs to be given back.
_NAME_CHAR = r"[^\s\\/\"'<>|*?:;`\x00-\x1f]"
_ESC = r"\\++u[0-9a-fA-F]{4}"
_UNIT = rf"(?:{_NAME_CHAR}|{_ESC})"
_FIRST_UNIT = rf"(?:{_NAME_CHAR}|(?<!\\){_ESC})"  # a fragment never starts inside a backslash run
_COMP = rf"{_UNIT}++(?:[ ]++(?![A-Za-z]:[\\/]){_UNIT}++)*+"
_SEP = r"(?:/|\\(?!u[0-9a-fA-F]{4}))++"
_TAIL = rf"(?:{_SEP}{_COMP})*+(?:{_SEP})?+"
_TAIL1 = rf"(?:{_SEP}{_COMP})++(?:{_SEP})?+"
_XPREFIX = r"(?<!\\)\\{2,}+[?.][\\/]++"
_PATH = re.compile(
    rf"(?P<ext>{_XPREFIX})?(?<!\w)(?P<drive>[A-Za-z]:)(?=[\\/])(?P<drive_tail>{_TAIL})"
    rf"|(?P<xunc>{_XPREFIX}UNC)(?P<xunc_tail>{_TAIL1})"
    rf"|(?<![\w\\/:<>])(?P<lead>\\{{2,}}+)(?P<host>[A-Za-z0-9][\w.$-]*+)(?P<unc_tail>{_TAIL1})"
    rf"|(?<![\w.~\\/<>-])(?P<posix>/(?:home|Users)/)(?P<posix_name>[^\s/\\\"'<>|:;`]++)"
    rf"|(?<![\w<>])(?P<profile>(?i:users|documents and settings))(?P<profile_tail>{_TAIL1})"
    rf"|(?<![\w<>])(?P<frag_name>{_FIRST_UNIT}{_UNIT}*+)(?P<frag_sep>{_SEP})"
    rf"(?P<frag_tail>(?i:appdata{_SEP}(?:local|roaming|locallow)\b){_TAIL})"
)
_RUN = re.compile(r"[\\/]+")
_HEX4 = re.compile(r"u[0-9a-fA-F]{4}")
_ESCAPED_U = re.compile(r"\\+u([0-9a-fA-F]{4})")
_ESCAPE_START = re.compile(r"[nrtbf\"'](?:\s|$)")
_SECRETS = (
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("api-key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
)
_SECRET_ASSIGN = re.compile(
    r"(?i)\b(?P<key>password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret"
    r"|authorization)\b(?P<op>['\"]?\s*[:=]\s*)(?P<quote>['\"]?)"
    r"(?P<value>(?=[^\s'\",;]*\d)(?=[^\s'\",;]*[A-Za-z])[^\s'\",;]{8,})")
_JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)


class EvidenceError(Exception):
    """A refusal or usage error whose message never contains matched values."""


@dataclass(frozen=True)
class Policy:
    repo_anchors: tuple[str, ...] = (REPO_ROOT.name,)
    protected_keys: frozenset[str] = PROTECTED_KEYS

    def as_dict(self) -> dict:
        return {"version": POLICY_VERSION, "repo_anchors": sorted(a.lower() for a in self.repo_anchors),
                "protected_keys": sorted(self.protected_keys)}


def _logical(component: str) -> str:
    """Component as a human would read it: nested ``\\uXXXX`` escapes decoded, stray separators removed."""
    return _ESCAPED_U.sub(lambda m: chr(int(m.group(1), 16)), component).strip("\\/").lower()


def _separator_width(tail: str) -> int:
    """Backslashes per separator at this escape level, read from the first run (1 raw, 2 repr/JSON, 4, ...)."""
    m = _RUN.match(tail)
    if m is None or "/" in m.group(0):
        return 1
    width = len(m.group(0))
    if width >= 3 and _HEX4.match(tail, m.end()):  # separator + escape of the first name: 2+1, 4+2, ...
        return 2 * width // 3
    return width


def _components(tail: str, offset: int) -> list[tuple[str, int, int]]:
    """(logical name, start, end) of every component of ``tail``; positions are absolute in the scanned string.

    At escape level k a separator is 2**k backslashes and a nested ``\\uXXXX`` escape takes half of that, so in
    a run followed by ``uXXXX`` the last width//2 backslashes belong to the name, the rest is the separator."""
    escape = _separator_width(tail) // 2
    cuts = []
    for m in _RUN.finditer(tail):
        start, end = m.start(), m.end()
        if escape and m.group(0).endswith("\\") and _HEX4.match(tail, end):
            end -= min(escape, len(m.group(0)))
        if end > start:
            cuts.append((start, end))
    comps, pos = [], 0
    for start, end in cuts + [(len(tail), len(tail))]:
        if start > pos:
            comps.append((_logical(tail[pos:start]), offset + pos, offset + start))
        pos = end
    return comps


def _classify_profile(comps, policy: Policy, start: int):
    """comps[0] is a profile root (users / documents and settings), comps[1] the profile name."""
    if len(comps) < 2:
        return None
    name = comps[1][0]
    if name in ELLIPSES:
        return ILLUSTRATIVE, None
    if name in PUBLIC_PROFILES:
        return SYSTEM, None
    names = [c[0] for c in comps]
    if names[2:5] == ["appdata", "local", "temp"]:
        return TEMP, (start, comps[4][2])
    anchors = {a.lower() for a in policy.repo_anchors}
    hits = [i for i, n in enumerate(names) if i >= 2 and n in anchors]
    if hits:
        return REPO, (start, comps[hits[-1]][2])
    return HOME, (start, comps[1][2])


def _classify_drive(comps, policy: Policy, start: int, drive_end: int):
    if not comps:
        return DRIVE_ROOT, None
    names = [c[0] for c in comps]
    anchors = {a.lower() for a in policy.repo_anchors}
    hits = [i for i, n in enumerate(names) if n in anchors]
    # a profile anywhere in front of the repository folder identifies the user, even behind C:\Windows\..\
    profile = next((i for i, n in enumerate(names[:-1]) if n in PROFILE_ROOTS), None)
    if profile is not None and (not hits or profile < hits[-1]):
        found = _classify_profile(comps[profile:], policy, start)
        if found and found[0] != SYSTEM:
            return found
    if hits:
        return REPO, (start, comps[hits[-1]][2])
    if names[0] in ELLIPSES:
        return ILLUSTRATIVE, None
    if names[0] in SYSTEM_ROOTS or (names[0] in PROFILE_ROOTS and len(names) > 1 and names[1] in PUBLIC_PROFILES):
        return SYSTEM, None
    # Unknown absolute path: only the drive and the parent folders are hidden. With a single component there is
    # nothing to hide, and in escaped text "as f:\\n    with ..." is a traceback line, not a path - leave both.
    if len(comps) < 2 or _ESCAPE_START.match(names[0]):
        return None
    return ABS, (start, comps[-2][2])


def _classify(m: re.Match, policy: Policy):
    """(kind, span, placeholder) for one regex match, or None when the candidate is not a path after all."""
    if m.group("drive"):
        comps = _components(m.group("drive_tail"), m.start("drive_tail"))
        found = _classify_drive(comps, policy, m.start("drive"), m.end("drive"))
        return (found[0], found[1], None) if found else None
    if m.group("xunc"):
        comps = _components(m.group("xunc_tail"), m.start("xunc_tail"))
        return (UNC, (comps[0][1], comps[1][2]), None) if len(comps) >= 2 else None
    if m.group("lead"):
        first_sep = re.match(r"[\\/]+", m.group("unc_tail")).group(0)
        # a UNC root is two separators of its own escape level: \\h\s, \\\\h\\s, ... (\\n\\n is not one)
        if not (first_sep.startswith("/") or len(m.group("lead")) == 2 * len(first_sep)):
            return None
        comps = _components(m.group("unc_tail"), m.start("unc_tail"))
        return UNC, (m.start("lead"), comps[0][2]), None
    if m.group("posix"):
        return POSIX_HOME, (m.start("posix"), m.end("posix_name")), "<HOME>"
    if m.group("profile"):
        comps = [("users", m.start("profile"), m.end("profile"))]
        comps += _components(m.group("profile_tail"), m.start("profile_tail"))
        found = _classify_profile(comps, policy, m.start("profile"))
        return (found[0], found[1], None) if found else None
    name = _logical(m.group("frag_name"))
    if name in ELLIPSES or name in PROFILE_ROOTS:
        return None
    comps = _components(m.group("frag_tail"), m.start("frag_tail"))
    if [c[0] for c in comps[:3]] == ["appdata", "local", "temp"]:
        return FRAGMENT, (m.start("frag_name"), comps[2][2]), "<TEMP>"
    return FRAGMENT, (m.start("frag_name"), m.end("frag_name")), "<HOME>"


def find_paths(text: str, policy: Policy = Policy()) -> list[tuple[str, int, int, str | None]]:
    """Every path-like span as (kind, start, end, placeholder); placeholder None = kept unchanged.

    (start, end) is the identifying prefix to replace for REPLACED kinds, the whole match for kept kinds.
    A rejected candidate does not swallow its text: the search resumes one character later."""
    found, pos = [], 0
    while True:
        m = _PATH.search(text, pos)
        if m is None:
            return found
        verdict = _classify(m, policy)
        if verdict is None:
            pos = m.start() + 1
            continue
        kind, span, placeholder = verdict
        if kind in KEPT_KINDS:
            found.append((kind, m.start(), m.end(), None))
        else:
            found.append((kind, span[0], span[1], placeholder or f"<{kind}>"))
        pos = max(m.end(), m.start() + 1)


def _redact_secrets(text: str, counts: Counter) -> str:
    for _name, pattern in _SECRETS:
        text, n = pattern.subn("<SECRET>", text)
        if n:
            counts[SECRET] += n

    def assign(m):
        counts[SECRET] += 1
        return m.group("key") + m.group("op") + m.group("quote") + "<SECRET>"

    return _SECRET_ASSIGN.sub(assign, text)


def sanitize_text(text: str, policy: Policy = Policy()) -> tuple[str, Counter]:
    """Replace identifying path prefixes and secret-like values; returns (text, Counter of kinds)."""
    counts = Counter()
    pieces, pos = [], 0
    for kind, start, end, placeholder in find_paths(text, policy):
        counts[kind] += 1
        if placeholder is None:
            continue
        pieces.append(text[pos:start])
        pieces.append(placeholder)
        pos = end
    pieces.append(text[pos:])
    return _redact_secrets("".join(pieces), counts), counts


def _encode_like(value: str, token: str) -> str:
    ascii_only = token.isascii()
    out = json.dumps(value, ensure_ascii=ascii_only)
    for ch in LINE_SEPARATORS:  # keep U+0085/2028/2029 escaped: raw ones split lines in many readers
        out = out.replace(ch, "\\u%04x" % ord(ch))
    return out


def sanitize_json_text(text: str, policy: Policy = Policy()) -> tuple[str, Counter, int, int]:
    """Token-wise sanitizer for (already validated) JSON / JSONL text: returns (text, counts, tokens, changed)."""
    counts, pieces, pos, tokens, changed = Counter(), [], 0, 0, 0
    for m in _JSON_STRING.finditer(text):
        tokens += 1
        value = json.loads(m.group(0))
        new_value, found = sanitize_text(value, policy)
        counts.update(found)
        if new_value != value:
            changed += 1
            pieces.append(text[pos:m.start()])
            pieces.append(_encode_like(new_value, m.group(0)))
            pos = m.end()
    pieces.append(text[pos:])
    return "".join(pieces), counts, tokens, changed


class _Obj(list):
    """JSON object kept as an ordered list of pairs (duplicate keys are evidence too)."""


def _load_pairs(text: str):
    return json.loads(text, object_pairs_hook=_Obj)


def _compare(old, new, policy: Policy, issues: Counter) -> None:
    if isinstance(old, _Obj):
        if not isinstance(new, _Obj) or len(old) != len(new):
            issues["structure"] += 1
            return
        if len({k for k, _ in old}) != len({k for k, _ in new}):
            issues["key-collision"] += 1
        for (old_key, old_value), (new_key, new_value) in zip(old, new):
            if sanitize_text(old_key, policy)[0] != new_key:
                issues["structure"] += 1
            if old_key in policy.protected_keys and isinstance(old_value, str) and old_value != new_value:
                issues["protected-field-changed"] += 1
            _compare(old_value, new_value, policy, issues)
    elif isinstance(old, list):
        if not isinstance(new, list) or isinstance(new, _Obj) or len(old) != len(new):
            issues["structure"] += 1
            return
        for a, b in zip(old, new):
            _compare(a, b, policy, issues)
    elif isinstance(old, str):
        if not isinstance(new, str) or sanitize_text(old, policy)[0] != new:
            issues["structure"] += 1
    elif isinstance(old, float) and math.isnan(old):
        if not (isinstance(new, float) and math.isnan(new)):
            issues["value-changed"] += 1
    elif type(old) is not type(new) or old != new:
        issues["value-changed"] += 1


def identity_pattern(tokens) -> re.Pattern | None:
    words = sorted({t.lower() for t in tokens if t and len(t) >= 3}, key=len, reverse=True)
    if not words:
        return None
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(w) for w in words) + r")(?![A-Za-z0-9])", re.I)


def local_identity_tokens(extra=()) -> list[str]:
    """User / computer / profile-folder names of this machine, whole values and their words (>= 3 chars)."""
    raw = [os.environ.get(k) for k in ("USERNAME", "USER", "LOGNAME", "COMPUTERNAME", "HOSTNAME", "USERDOMAIN")]
    raw += [Path.home().name, *extra]
    tokens = set()
    for value in filter(None, raw):
        value = value.strip()
        if len(value) >= 3 and value.lower() not in GENERIC_HOSTS:
            tokens.add(value)
        for word in re.split(r"[\s._-]+", value):  # DESKTOP-AB12CD -> AB12CD (the generic word is skipped)
            if len(word) >= 3 and word.lower() not in GENERIC_WORDS:
                tokens.add(word)
    return sorted(tokens, key=str.lower)


def _unescape(text: str) -> str:
    return _ESCAPED_U.sub(lambda m: chr(int(m.group(1), 16)), text)


def _views(text: str, json_values) -> list[str]:
    """Text as published plus every decoded JSON string, each also with nested \\uXXXX escapes decoded."""
    views = [text, *json_values]
    return views + [_unescape(v) for v in views if "u" in v]


def _identity_hits(text: str, json_values, identity: re.Pattern | None) -> int:
    """Occurrences of local names: the largest count over the published, decoded and unescaped views."""
    if identity is None:
        return 0
    groups = ([text], json_values, [_unescape(text)], [_unescape(v) for v in json_values])
    return max(sum(len(identity.findall(v)) for v in group) for group in groups)


def _gate(views, policy: Policy, identity: re.Pattern | None) -> Counter:
    left = Counter()
    for view in views:
        for kind, *_rest, placeholder in find_paths(view, policy):
            if placeholder is not None:
                left["residual-path"] += 1
        left["residual-secret"] += sanitize_text(view, policy)[1][SECRET]
        if identity is not None:
            left["residual-identity"] += len(identity.findall(view))
    return +left


def safe_message(text: str, identity: re.Pattern | None = None) -> str:
    text = sanitize_text(str(text))[0]
    return identity.sub("<ID>", text) if identity is not None else text


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class FileResult:
    id: str
    kind: str
    source_sha256: str
    source_bytes: int
    output: bytes | None = None
    counts: Counter = field(default_factory=Counter)
    original_identity_hits: int = 0
    json_tokens: int = 0
    json_tokens_changed: int = 0
    structure: str = "NOT_APPLICABLE"
    safety: str = "PASS"
    reasons: list[str] = field(default_factory=list)

    def refuse(self, reason: str) -> None:
        self.safety = "BLOCKED"
        self.output = None  # a refused file never gets a publishable copy, whatever refused it and when
        if reason not in self.reasons:
            self.reasons.append(reason)


def _json_values(text: str) -> list[str]:
    return [json.loads(m.group(0)) for m in _JSON_STRING.finditer(text)]


def process_bytes(rel: str, data: bytes, policy: Policy = Policy(), identity: re.Pattern | None = None) -> FileResult:
    """Sanitize one file's bytes; never raises for bad content (the result is BLOCKED instead).

    The file id is published as well (candidate tree, mapping, manifest), so a local name in it refuses the file."""
    result = _process_content(rel, data, policy, identity)
    if identity is not None and identity.search(rel):
        result.refuse("identity-in-file-name")
    return result


def _process_content(rel: str, data: bytes, policy: Policy, identity: re.Pattern | None) -> FileResult:
    result = FileResult(rel, "text", _sha(data), len(data))
    bom = data[:3] == b"\xef\xbb\xbf"
    try:
        text = data[3 if bom else 0:].decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is None or "\x00" in text:
        result.kind = "binary"
        views = [data.decode("utf-8", "replace"), data.decode("latin-1")]
        for shift in (0, 1):  # UTF-16 text may start at an even or an odd offset
            chunk = data[shift:]
            views.append(chunk[:len(chunk) // 2 * 2].decode("utf-16-le", "replace"))
        found = Counter()
        for view in views:
            found |= sanitize_text(view, policy)[1]
            result.original_identity_hits = max(result.original_identity_hits, _identity_hits(view, [], identity))
        result.counts = found
        if any(found[k] for k in REPLACED_KINDS) or result.original_identity_hits:
            result.refuse("binary-with-findings")
        else:
            result.output = data
        return result

    suffix = PurePosixPath(rel).suffix.lower()
    if suffix in (".json", ".jsonl"):
        result.kind = suffix[1:]
        records = [line for line in text.split("\n") if line.strip()] if suffix == ".jsonl" else [text]
        try:
            old_records = [_load_pairs(r) for r in records]
        except (ValueError, RecursionError):
            result.structure = "FAIL"
            result.refuse("invalid-" + result.kind)
            return result
        result.original_identity_hits = _identity_hits(text, _json_values(text), identity)
        new_text, result.counts, result.json_tokens, result.json_tokens_changed = sanitize_json_text(text, policy)
        new_records = [line for line in new_text.split("\n") if line.strip()] if suffix == ".jsonl" else [new_text]
        issues = Counter()
        try:
            if len(new_records) != len(old_records):
                issues["structure"] += 1
            for old, new in zip(old_records, new_records):
                _compare(old, _load_pairs(new), policy, issues)
        except (ValueError, RecursionError):
            issues["structure"] += 1
        result.structure = "FAIL" if issues else "PASS"
        for issue in sorted(issues):
            result.refuse(issue)
        gate_views = _views(new_text, _json_values(new_text) if not issues else [])
    else:
        result.original_identity_hits = _identity_hits(text, [], identity)
        new_text, result.counts = sanitize_text(text, policy)
        gate_views = _views(new_text, [])
    for reason in sorted(_gate(gate_views, policy, identity)):
        result.refuse(reason)
    if result.counts[SECRET]:
        result.refuse("secret-redacted-review-required")
    if result.safety == "PASS":
        result.output = (b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8")
    return result


# ----------------------------------------------------------------------------------------------- package level
#
# Integrity (F-ES-01) and completeness (F-ES-02), CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001:
# * a manifest is a claim, not an anchor: in manifest mode every listed file must match its declared SHA-256 and
#   size, the manifest must be strict JSON (no duplicate keys) with safe, unique ids, every listed file must exist
#   and every present file must be listed - otherwise the file (or, before anything is written, the run) is refused;
# * verify trusts nothing the bundle says about itself: schema, ids, totals, verdict, safety, manifest results and
#   the exact sets of originals and sanitized copies are recomputed; completeness against coordinated deletion
#   needs a trusted anchor outside the bundle - the source package (--package) or the mapping's SHA-256 recorded
#   out of band (--mapping-sha256). Without one, completeness is NOT_PROVEN and publication is REFUSED.

class IntegrityRefusal(EvidenceError):
    """The input cannot be shown to be what it claims (manifest / inventory): nothing is written, CLI exit 2."""


VERDICT_SAFE = "SAFE PUBLICATION CANDIDATE (needs USER GO)"
SELECTIONS = ("manifest", "all-files")
KINDS = frozenset({"text", "json", "jsonl", "binary"})
TRANSIENT_REASONS = frozenset({"source-changed-during-staging"})
ANCHOR_FORBIDDEN = PROFILE_ROOTS | SYSTEM_ROOTS | PUBLIC_PROFILES | ELLIPSES | {
    "appdata", "local", "locallow", "roaming", "temp", "tmp"}
BUNDLE_ENTRIES = frozenset({"mapping.json", "originals", "sanitized"})
UNSUPPORTED_REASONS = frozenset({"invalid-json", "invalid-jsonl", "structure", "key-collision", "value-changed",
                                 "protected-field-changed", "binary-with-findings"})
_HEX64 = re.compile(r"[0-9a-fA-F]{64}")
_ID_FORBIDDEN = re.compile(r'[\\:*?"<>|\x00-\x1f]')


def _inside(child: Path, parent: Path) -> bool:
    child_s, parent_s = os.path.normcase(str(child)), os.path.normcase(str(parent))
    try:
        return os.path.commonpath([child_s, parent_s]) == parent_s
    except ValueError:  # different drives
        return False


def _is_hex(value) -> bool:
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def _is_count(value) -> bool:
    return type(value) is int and value >= 0


def _strict_json(data):
    """json.loads that refuses duplicate object keys (the last value would silently win)."""
    def pairs(items):
        keys = [key for key, _ in items]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate key")
        return dict(items)

    text = data.decode("utf-8-sig") if isinstance(data, bytes) else data
    return json.loads(text, object_pairs_hook=pairs)


def _id_problem(rel) -> str | None:
    """A file id is a relative POSIX path that names one ordinary file the same way on every platform."""
    if not isinstance(rel, str) or not rel or rel.startswith("/") or _ID_FORBIDDEN.search(rel):
        return "unsafe-id"  # backslash, drive or stream colon, wildcard, control character
    for part in rel.split("/"):
        if part in ("", ".", "..") or part != part.rstrip(" ."):
            return "unsafe-id"  # empty / dot segments; Windows silently drops trailing dots and spaces
    return None


def _check_ids(ids) -> None:
    seen = set()
    for rel in ids:
        if _id_problem(rel):
            raise IntegrityRefusal("unsafe file id in the package or its manifest")
        if rel.casefold() in seen:
            raise IntegrityRefusal("two file ids name the same file on a case-insensitive file system")
        seen.add(rel.casefold())


def _is_link(entry) -> bool:
    is_junction = getattr(entry, "is_junction", None)  # os.DirEntry and Path, Python >= 3.12
    return entry.is_symlink() or bool(is_junction and is_junction())


def _walk(root: Path, skip_cache: bool) -> tuple[list[str], int]:
    """Relative ids of the ordinary files under root and the number of links / special entries (never followed)."""
    files, links, stack = [], 0, [(root, "")]
    while stack:
        directory, prefix = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                rel = prefix + entry.name
                if _is_link(entry):
                    links += 1
                elif entry.is_dir(follow_symlinks=False):
                    if not (skip_cache and entry.name == "__pycache__"):
                        stack.append((Path(entry.path), rel + "/"))
                elif entry.is_file(follow_symlinks=False):
                    files.append(rel)
                else:
                    links += 1
    return sorted(files), links


@dataclass
class Selection:
    ids: list[str]
    entries: dict  # manifest "files" object (manifest mode)
    manifest_bytes: bytes | None  # read once; the same bytes are checked, processed and preserved
    unlisted: set[str]


def package_files(package: Path, use_manifest: bool) -> Selection:
    """The exact set of files to process; refuses (IntegrityRefusal) anything that cannot be accounted for."""
    package = Path(package)
    if not package.is_dir():
        raise EvidenceError("package directory not found")
    present, links = _walk(package, skip_cache=True)
    if links:
        raise IntegrityRefusal("the package contains links, junctions or special files")
    _check_ids(present)
    if not use_manifest:
        return Selection(present, {}, None, set())
    if "manifest.json" not in present:
        raise IntegrityRefusal("manifest.json not found in the package")
    manifest_bytes = (package / "manifest.json").read_bytes()
    try:
        doc = _strict_json(manifest_bytes)
    except (ValueError, RecursionError):
        raise IntegrityRefusal("manifest.json is not valid JSON or repeats a key") from None
    files = doc.get("files") if isinstance(doc, dict) else None
    if not isinstance(files, dict):
        raise IntegrityRefusal("manifest.json has no files object with integrity entries")
    _check_ids(files)
    if "manifest.json" in files:
        raise IntegrityRefusal("manifest.json lists itself; its own hash cannot be checked")
    if any(rel not in present for rel in files):
        raise IntegrityRefusal("a file listed in manifest.json is missing from the package")
    unlisted = set(present) - set(files) - {"manifest.json"}
    return Selection(sorted(set(files) | {"manifest.json"} | unlisted), files, manifest_bytes, unlisted)


def _manifest_check(entry, data: bytes) -> tuple[str, list[str], bool | None]:
    """(status, reasons, sha256 match) of one manifest entry against the actual bytes."""
    if not isinstance(entry, dict):
        return "INVALID_ENTRY", ["manifest-entry-invalid"], None
    digest, size = entry.get("sha256"), entry.get("bytes")
    match = digest.lower() == _sha(data) if _is_hex(digest) else None
    if match is None or not _is_count(size):
        return "INVALID_ENTRY", ["manifest-entry-invalid"], match
    reasons = ([] if match else ["manifest-sha256-mismatch"]) + ([] if size == len(data) else ["manifest-bytes-mismatch"])
    return ("MISMATCH" if reasons else "MATCH"), reasons, match


def _escape_line_separators(text: str) -> str:
    for ch in LINE_SEPARATORS:
        text = text.replace(ch, "\\u%04x" % ord(ch))
    return text


def _rehash_manifest(manifest: bytes, outputs: dict) -> tuple[bytes, int] | None:
    """The candidate's manifest: sha256/bytes of every listed file set to its sanitized copy (None if unusable)."""
    try:
        doc = _strict_json(manifest)
    except (ValueError, RecursionError):
        return None
    files = doc.get("files") if isinstance(doc, dict) else None
    if not isinstance(files, dict):
        return None
    changed = 0
    for rel in sorted(outputs):
        data, entry = outputs[rel], files.get(rel)
        if data is None or not isinstance(entry, dict):
            continue
        fresh = {"sha256": _sha(data), "bytes": len(data)}
        if entry.get("sha256") != fresh["sha256"] or entry.get("bytes") != fresh["bytes"]:
            entry.update(fresh)
            changed += 1
    if not changed:
        return manifest, 0
    eol = "\r\n" if b"\r\n" in manifest else "\n"
    text = _escape_line_separators(json.dumps(doc, ensure_ascii=False, indent=1)) + "\n"
    bom = b"\xef\xbb\xbf" if manifest.startswith(b"\xef\xbb\xbf") else b""
    return bom + text.replace("\n", eol).encode("utf-8"), changed


def _candidate_manifest(manifest_result: FileResult, outputs: dict, policy: Policy, identity) -> tuple[bytes | None, int]:
    """Re-hash the sanitized manifest for the candidate and pass it through the gate again (same in stage/verify)."""
    if manifest_result.output is None:
        return None, 0
    rehashed = _rehash_manifest(manifest_result.output, outputs)
    if rehashed is None:
        manifest_result.refuse("manifest-rehash-failed")
        return None, 0
    candidate, count = rehashed
    if count:
        again = process_bytes("manifest.json", candidate, policy, identity)
        if again.safety != "PASS" or again.output != candidate:
            manifest_result.refuse("manifest-rehash-failed")
            return None, 0
    return candidate, count


def _policy_problems(policy: Policy) -> list[str]:
    found = []
    if not policy.repo_anchors:
        found.append("no-repo-anchor")
    for anchor in policy.repo_anchors:
        low = anchor.lower() if isinstance(anchor, str) else ""
        if not low or low != low.strip() or _ID_FORBIDDEN.search(low) or "/" in low or low in (".", "..") \
                or low in ANCHOR_FORBIDDEN:
            found.append("unsafe-repo-anchor")  # e.g. "users" would turn C:\Users\<name> into <REPO>\<name>
    if not PROTECTED_KEYS <= set(policy.protected_keys):
        found.append("protected-keys-weakened")
    return found


def scan(package: Path, use_manifest: bool = False, policy: Policy = Policy(), identity=None) -> dict:
    """Read-only inventory of a package: categories and counts per file id, never values."""
    package = Path(package)
    selection = package_files(package, use_manifest)
    files, classes = [], Counter()
    for rel in selection.ids:
        data = selection.manifest_bytes if rel == "manifest.json" and use_manifest else (package / rel).read_bytes()
        r = process_bytes(rel, data, policy, identity)
        status = None
        if use_manifest and rel != "manifest.json":
            status = "NOT_LISTED" if rel in selection.unlisted else _manifest_check(selection.entries[rel], data)[0]
        replaced = sum(r.counts[k] for k in REPLACED_KINDS)
        if r.original_identity_hits or r.counts[SECRET] or "identity-in-file-name" in r.reasons:
            cls = "CONFIRMED"
        elif replaced:
            cls = "SUSPECT"
        elif any(r.counts[k] for k in KEPT_KINDS):
            cls = "BENIGN_ONLY"
        else:
            cls = "CLEAN"
        if UNSUPPORTED_REASONS.intersection(r.reasons):
            cls = "UNSUPPORTED" if cls == "CLEAN" else cls + "+UNSUPPORTED"
        if status not in (None, "MATCH"):
            cls = "INTEGRITY" if cls == "CLEAN" else cls + "+INTEGRITY"
        classes[cls] += 1
        files.append({"id": rel, "kind": r.kind, "bytes": r.source_bytes, "sha256": r.source_sha256, "class": cls,
                      "findings": dict(sorted(r.counts.items())), "identity_hits": r.original_identity_hits,
                      "json_tokens_affected": r.json_tokens_changed, "manifest_check": status,
                      "after_sanitizing": "PASS" if r.safety == "PASS" else "BLOCKED:" + ",".join(r.reasons)})
    return {"tool": "web_alarm.evidence_sanitizer", "policy": policy.as_dict(), "package": package.name,
            "selection": "manifest" if use_manifest else "all-files", "files_scanned": len(selection.ids),
            "classes": dict(sorted(classes.items())), "findings_total": _summary_counts_from(files), "files": files}


def _summary_counts_from(files) -> dict:
    total = Counter()
    for f in files:
        total.update(f.get("findings", {}))
    return dict(sorted(total.items()))


def _check_out_dir(out: Path, package: Path) -> Path:
    out_r, pkg_r, repo = Path(out).resolve(), Path(package).resolve(), REPO_ROOT.resolve()
    if _inside(out_r, pkg_r) or _inside(pkg_r, out_r):
        raise EvidenceError("output directory overlaps the source package")
    if _inside(out_r, repo) and not (_inside(out_r, repo / "logs") and out_r != (repo / "logs")):
        raise EvidenceError("output directory is inside the repository but outside the git-ignored logs/")
    if out_r.exists() and (not out_r.is_dir() or any(out_r.iterdir())):
        raise EvidenceError("output directory exists and is not empty")
    return out_r


def _write_new(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    back = path.read_bytes()
    if back != data:
        raise EvidenceError("read-back mismatch while writing the staging area")
    return _sha(back)


def _mapping_row(r: FileResult, original_sha: str, out_sha: str | None, check: tuple | None,
                 rehashed: int | None) -> dict:
    row = {"id": r.id, "kind": r.kind, "source_sha256": r.source_sha256, "source_bytes": r.source_bytes,
           "preserved_original": "originals/" + r.id, "preserved_sha256": original_sha,
           "sanitized_id": ("sanitized/" + r.id) if out_sha else None, "sanitized_sha256": out_sha,
           "sanitized_bytes": len(r.output) if r.output is not None else None,
           "changed": out_sha is not None and out_sha != r.source_sha256,
           "replacements": {k: v for k, v in sorted(r.counts.items()) if k in REPLACED_KINDS},
           "kept": {k: v for k, v in sorted(r.counts.items()) if k in KEPT_KINDS},
           "json_tokens": r.json_tokens, "json_tokens_changed": r.json_tokens_changed,
           "structure": r.structure, "safety": r.safety, "reasons": r.reasons}
    if check is not None:
        row["manifest_check"], row["manifest_sha256_match"] = check
    if rehashed is not None:
        row["manifest_rehashed_entries"] = rehashed
    return row


def _tool_sha() -> str:
    """SHA-256 of this module with LF line ends, so LF and CRLF checkouts report the same tool revision."""
    return _sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n"))


def stage(package: Path, out: Path, use_manifest: bool = False, policy: Policy = Policy(), identity=None) -> dict:
    """Preserve originals and write sanitized copies + mapping.json into a new private directory.

    Order: account for every file (refuse before writing), read each file once, process, check the manifest,
    re-hash the candidate manifest, re-read the sources (refuse what changed meanwhile), then write."""
    if _policy_problems(policy):
        raise EvidenceError("unsafe sanitizing policy: " + ", ".join(sorted(set(_policy_problems(policy)))))
    package = Path(package)
    selection = package_files(package, use_manifest)
    out_r = _check_out_dir(out, package)
    work = {}
    for rel in selection.ids:
        data = selection.manifest_bytes if rel == "manifest.json" and use_manifest else (package / rel).read_bytes()
        r = process_bytes(rel, data, policy, identity)
        check = None
        if use_manifest and rel != "manifest.json":
            if rel in selection.unlisted:
                check = ("NOT_LISTED", None)
                r.refuse("not-listed-in-manifest")
            else:
                status, reasons, match = _manifest_check(selection.entries[rel], data)
                check = (status, match)
                for reason in reasons:
                    r.refuse(reason)
        work[rel] = (data, r, check)
    rehashed = None
    if use_manifest:
        manifest_result = work["manifest.json"][1]
        outputs = {rel: work[rel][1].output for rel in selection.entries}
        candidate, rehashed = _candidate_manifest(manifest_result, outputs, policy, identity)
        if candidate is not None:
            manifest_result.output = candidate
    for rel, (data, r, _check) in work.items():
        current = package / rel
        if not current.is_file() or _sha(current.read_bytes()) != r.source_sha256:
            r.refuse("source-changed-during-staging")
    out_r.mkdir(parents=True, exist_ok=True)
    rows = []
    for rel in selection.ids:
        data, r, check = work[rel]
        original_sha = _write_new(out_r / "originals" / rel, data)
        out_sha = _write_new(out_r / "sanitized" / rel, r.output) if r.output is not None else None
        rows.append(_mapping_row(r, original_sha, out_sha, check, rehashed if rel == "manifest.json" else None))
    blocked = [row["id"] for row in rows if row["safety"] != "PASS"]
    mapping = {
        "tool": "web_alarm.evidence_sanitizer", "tool_sha256_lf": _tool_sha(), "policy": policy.as_dict(),
        "package": package.name, "selection": "manifest" if use_manifest else "all-files",
        "files_total": len(rows), "files_changed": sum(1 for r in rows if r["changed"]),
        "files_blocked": len(blocked), "replacements_total": _sum_rows(rows, "replacements"),
        "kept_total": _sum_rows(rows, "kept"),
        "identity_gate": "ENFORCED" if identity is not None else "NOT ENFORCED",
        "verdict": VERDICT_SAFE if not blocked else "REFUSED", "files": rows,
    }
    tmp = out_r / "mapping.json.tmp"
    tmp.write_bytes((json.dumps(mapping, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    os.replace(tmp, out_r / "mapping.json")
    return mapping


def _sum_rows(rows, key) -> dict:
    total = Counter()
    for row in rows:
        total.update(row[key])
    return dict(sorted(total.items()))


def _mapping_policy(raw, problems: Counter) -> Policy:
    """The mapping's policy, accepted only if it is a complete, current and not weakened policy."""
    if not isinstance(raw, dict) or raw.get("version") != POLICY_VERSION:
        problems["policy-invalid"] += 1
        return Policy()
    anchors, keys = raw.get("repo_anchors"), raw.get("protected_keys")
    if not (isinstance(anchors, list) and all(isinstance(a, str) for a in anchors)
            and isinstance(keys, list) and all(isinstance(k, str) for k in keys)):
        problems["policy-invalid"] += 1
        return Policy()
    policy = Policy(tuple(anchors), frozenset(keys))
    if _policy_problems(policy):
        problems["policy-invalid"] += 1
        return Policy(tuple(a for a in anchors if not _policy_problems(Policy((a,)))) or ("ag_llm",))
    return policy


def _row_problem(row) -> str | None:
    if not isinstance(row, dict):
        return "mapping-row-invalid"
    rel = row.get("id")
    if _id_problem(rel):
        return "unsafe-id"
    valid = (row.get("kind") in KINDS and _is_hex(row.get("source_sha256")) and _is_count(row.get("source_bytes"))
             and row.get("preserved_original") == "originals/" + rel
             and row.get("preserved_sha256") == row.get("source_sha256")
             and row.get("safety") in ("PASS", "BLOCKED") and isinstance(row.get("changed"), bool)
             and isinstance(row.get("reasons"), list) and all(isinstance(x, str) for x in row["reasons"]))
    if not valid:
        return "mapping-row-invalid"
    if row["safety"] == "PASS":
        if row.get("sanitized_id") != "sanitized/" + rel or not _is_hex(row.get("sanitized_sha256")) \
                or not _is_count(row.get("sanitized_bytes")) or row["reasons"]:
            return "mapping-row-invalid"
    elif row.get("sanitized_id") is not None or row.get("sanitized_sha256") is not None or not row["reasons"]:
        return "mapping-row-invalid"
    return None


def _bundle_files(out: Path, name: str, problems: Counter) -> set[str]:
    root = out / name
    if _is_link(root):
        problems["link-in-bundle"] += 1
        return set()
    if not root.is_dir():
        return set()
    files, links = _walk(root, skip_cache=False)
    if links:
        problems["link-in-bundle"] += links
    return set(files)


def _verify_manifest(rows, ids, results, policy, identity, problems) -> bytes | None:
    """Re-prove manifest integrity from the preserved manifest and originals; return the expected candidate."""
    manifest = results.get("manifest.json")
    if manifest is None:
        problems["manifest-missing"] += 1
        return None
    try:
        doc = _strict_json(manifest[0])
        files = doc.get("files") if isinstance(doc, dict) else None
        if not isinstance(files, dict) or "manifest.json" in files or any(_id_problem(k) for k in files):
            raise ValueError("unusable manifest")
    except (ValueError, RecursionError):
        problems["manifest-invalid"] += 1
        manifest[1].refuse("manifest-invalid")
        return None
    listed = set(files)
    flagged = {r["id"] for r in rows if "not-listed-in-manifest" in r["reasons"]}
    if flagged & listed or ids != listed | {"manifest.json"} | flagged:
        problems["mapping-set-differs-from-manifest"] += 1
    for rel in listed & set(results):
        status, reasons, match = _manifest_check(files[rel], results[rel][0])
        results[rel][2] = (status, match)
        for reason in reasons:
            results[rel][1].refuse(reason)
    for rel in (flagged - listed) & set(results):
        results[rel][2] = ("NOT_LISTED", None)
        results[rel][1].refuse("not-listed-in-manifest")
    outputs = {rel: results[rel][1].output for rel in listed & set(results)}
    return _candidate_manifest(manifest[1], outputs, policy, identity)[0]


def _canonical(path: Path) -> str:
    """One comparable spelling of an existing path: absolute, symlinks/junctions/8.3 names resolved, the Windows
    extended-length prefix removed, case-folded where the platform is case-insensitive."""
    real = os.path.realpath(path, strict=True)
    if real.startswith("\\\\?\\UNC\\"):
        real = "\\\\" + real[8:]
    elif real.startswith("\\\\?\\"):
        real = real[4:]
    return os.path.normcase(real)


def _overlap(a: Path, b: Path) -> bool:
    """True when one existing directory is the other one or lies inside it."""
    first, second = _canonical(a), _canonical(b)
    try:
        return os.path.commonpath([first, second]) in (first, second)
    except ValueError:  # different drives
        return False


def _verify_report(problems: Counter, checked: int, claimed_blocked: int, blocked: int, completeness: str) -> dict:
    clean = not problems
    return {"files_checked": checked, "files_blocked_in_mapping": claimed_blocked, "files_blocked_recomputed": blocked,
            "problems": dict(sorted(problems.items())), "verdict": "CONSISTENT" if clean else "INCONSISTENT",
            "completeness": completeness,
            "publication": "SAFE CANDIDATE" if clean and not blocked and completeness != "NOT_PROVEN" else "REFUSED"}


def verify(out: Path, package: Path | None = None, identity=None, mapping_anchor: str | None = None) -> dict:
    """Re-prove a staged set from scratch; nothing the bundle says about itself is taken on trust."""
    out = Path(out)
    mapping_path = out / "mapping.json"
    if not mapping_path.is_file():
        raise EvidenceError("mapping.json not found")
    if package is not None and not Path(package).is_dir():
        raise EvidenceError("package directory not found")
    raw = mapping_path.read_bytes()
    problems = Counter()
    anchored = False
    if mapping_anchor is not None:
        anchored = _sha(raw) == str(mapping_anchor).lower()
        if not anchored:
            problems["mapping-anchor-mismatch"] += 1
    # F-ES-03: a package that is (inside) the bundle, contains it, or reaches it through a link proves nothing
    independent = package is None or not _overlap(out, Path(package))
    if not independent:
        problems["package-not-independent"] += 1
    completeness = ("PROVEN_AGAINST_PACKAGE" if package is not None and independent
                    else "PROVEN_BY_EXTERNAL_MAPPING_SHA256" if anchored else "NOT_PROVEN")
    try:
        mapping = _strict_json(raw)
    except (ValueError, RecursionError):
        mapping = None
    if not isinstance(mapping, dict) or not isinstance(mapping.get("files"), list):
        problems["mapping-invalid"] += 1
        return _verify_report(problems, 0, 0, 0, completeness)
    policy = _mapping_policy(mapping.get("policy"), problems)
    selection = mapping.get("selection")
    if selection not in SELECTIONS:
        problems["mapping-invalid"] += 1
    rows, seen = [], set()
    for row in mapping["files"]:
        issue = _row_problem(row)
        if issue is None and row["id"].casefold() in seen:
            issue = "duplicate-ids"
        if issue:
            problems[issue] += 1
            continue
        seen.add(row["id"].casefold())
        rows.append(row)
    by_id = {row["id"]: row for row in rows}
    ids = set(by_id)
    claimed_blocked = sum(1 for row in mapping["files"] if not isinstance(row, dict) or row.get("safety") != "PASS")

    unexpected = [p.name for p in out.iterdir() if p.name not in BUNDLE_ENTRIES]
    if unexpected:
        problems["unexpected-bundle-entries"] += len(unexpected)
    originals = _bundle_files(out, "originals", problems)
    sanitized = _bundle_files(out, "sanitized", problems)
    if ids - originals:
        problems["original-missing-or-changed"] += len(ids - originals)
    if originals - ids:
        problems["unlisted-originals"] += len(originals - ids)
    claimed_pass = {rel for rel, row in by_id.items() if row["safety"] == "PASS"}
    if sanitized - claimed_pass:
        problems["unlisted-sanitized-files"] += len(sanitized - claimed_pass)
    if claimed_pass - sanitized:
        problems["sanitized-missing-or-changed"] += len(claimed_pass - sanitized)

    results = {}
    for rel in sorted(ids & originals):
        row, data = by_id[rel], (out / "originals" / rel).read_bytes()
        if _sha(data) != row["source_sha256"] or len(data) != row["source_bytes"]:
            problems["original-missing-or-changed"] += 1
            continue
        results[rel] = [data, process_bytes(rel, data, policy, identity), None]
    candidate = _verify_manifest(rows, ids, results, policy, identity, problems) if selection == "manifest" else None

    blocked = changed = 0
    for rel in sorted(ids):
        row = by_id[rel]
        if rel not in results:
            blocked += 1
            continue
        data, r, check = results[rel]
        expected = candidate if rel == "manifest.json" and selection == "manifest" else r.output
        recomputed = "PASS" if r.safety == "PASS" and expected is not None else "BLOCKED"
        if recomputed != row["safety"]:
            if row["safety"] == "PASS":
                problems["map-claims-pass-but-recomputation-refuses"] += 1
            elif not TRANSIENT_REASONS.intersection(row["reasons"]):
                problems["blocked-file-now-passes"] += 1
        final_pass = recomputed == "PASS" and row["safety"] == "PASS"
        if final_pass:
            if _sha(expected) != row["sanitized_sha256"] or len(expected) != row["sanitized_bytes"]:
                problems["not-reproducible"] += 1
            if rel in sanitized and _sha((out / "sanitized" / rel).read_bytes()) != row["sanitized_sha256"]:
                problems["sanitized-missing-or-changed"] += 1
        else:
            blocked += 1
        is_changed = final_pass and _sha(expected) != row["source_sha256"]
        changed += is_changed
        claimed_check = (row.get("manifest_check"), row.get("manifest_sha256_match"))
        if row["changed"] != is_changed or ("manifest_check" in row and claimed_check != (check or (None, None))) \
                or ("manifest_check" not in row and "manifest_sha256_match" in row
                    and row["manifest_sha256_match"] != (check or (None, None))[1]):
            problems["mapping-field-mismatch"] += 1
    total = len(mapping["files"])
    expected_verdict = VERDICT_SAFE if blocked == 0 and len(rows) == total else "REFUSED"
    if (mapping.get("files_total"), mapping.get("files_blocked"), mapping.get("files_changed"),
            mapping.get("verdict")) != (total, blocked, changed, expected_verdict):
        problems["mapping-totals-mismatch"] += 1

    if package is not None and independent:
        package = Path(package)
        try:
            source = package_files(package, selection == "manifest")
        except IntegrityRefusal:
            problems["package-inventory-differs"] += 1
        else:
            if set(source.ids) != ids or len(rows) != total:
                problems["package-inventory-differs"] += 1
            for rel in sorted(set(source.ids) & ids):
                if rel in originals and os.path.samefile(package / rel, out / "originals" / rel):
                    independent = False  # a hard link to the bundle's own preserved copy, not a source
                data = source.manifest_bytes if rel == "manifest.json" and source.manifest_bytes is not None \
                    else (package / rel).read_bytes()
                if _sha(data) != by_id[rel]["source_sha256"]:
                    problems["package-differs-from-preserved-original"] += 1
        if not independent:
            problems["package-not-independent"] += 1
            completeness = "PROVEN_BY_EXTERNAL_MAPPING_SHA256" if anchored else "NOT_PROVEN"
    return _verify_report(problems, len(rows), claimed_blocked, blocked, completeness)


# ---------------------------------------------------------------------------------------------------------- CLI

def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=True, indent=1))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m web_alarm.evidence_sanitizer",
                                     description="Publication-safe Web Alarm evidence (offline).")
    parser.add_argument("--repo-anchor", action="append", help="repository folder name(s) mapped to <REPO>")
    parser.add_argument("--identity-token", action="append", default=[],
                        help="extra local name that must never be published (whole word, >= 3 chars)")
    parser.add_argument("--no-local-identity", action="store_true",
                        help="do not add this machine's user/computer names to the publication gate")
    sub = parser.add_subparsers(dest="command", required=True)
    p_scan = sub.add_parser("scan")
    p_scan.add_argument("package")
    p_scan.add_argument("--manifest", action="store_true")
    p_scan.add_argument("--json", dest="json_out")
    p_stage = sub.add_parser("stage")
    p_stage.add_argument("package")
    p_stage.add_argument("--out", required=True)
    p_stage.add_argument("--manifest", action="store_true")
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("out")
    p_verify.add_argument("--package", help="source package: proves completeness against its inventory")
    p_verify.add_argument("--mapping-sha256", help="SHA-256 of mapping.json recorded outside the bundle at stage time")
    args = parser.parse_args(argv)

    tokens = list(args.identity_token) + ([] if args.no_local_identity else local_identity_tokens())
    identity = identity_pattern(tokens)
    policy = Policy(tuple(args.repo_anchor)) if args.repo_anchor else Policy()
    try:
        if _policy_problems(policy):
            raise EvidenceError("unsafe --repo-anchor")
        if args.command == "scan":
            report = scan(Path(args.package), args.manifest, policy, identity)
            if args.json_out:
                target = Path(args.json_out)
                if _inside(target.resolve(), Path(args.package).resolve()):
                    raise EvidenceError("inventory file must not be written into the scanned package")
                with open(target, "xb") as handle:
                    handle.write((json.dumps(report, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
            _print({k: v for k, v in report.items() if k != "files"})
            refused = sum(v for k, v in report["classes"].items()
                          if {"CONFIRMED", "SUSPECT", "UNSUPPORTED", "INTEGRITY"} & set(k.split("+")))
            return EXIT_REFUSED if refused else EXIT_SAFE
        if args.command == "stage":
            mapping = stage(Path(args.package), Path(args.out), args.manifest, policy, identity)
            written = Path(args.out) / "mapping.json"
            _print({k: v for k, v in mapping.items() if k != "files"} |
                   {"mapping_sha256": _sha(written.read_bytes()),
                    "blocked": [{"id": r["id"], "reasons": r["reasons"]} for r in mapping["files"]
                                if r["safety"] != "PASS"]})
            return EXIT_SAFE if mapping["files_blocked"] == 0 else EXIT_REFUSED
        if args.mapping_sha256 is not None and not _is_hex(args.mapping_sha256):
            raise EvidenceError("--mapping-sha256 must be 64 hexadecimal characters")
        report = verify(Path(args.out), Path(args.package) if args.package else None, identity, args.mapping_sha256)
        _print(report)
        return EXIT_SAFE if report["publication"] == "SAFE CANDIDATE" else EXIT_REFUSED
    except IntegrityRefusal as exc:
        _print({"error": safe_message(exc, identity), "publication": "REFUSED"})
        return EXIT_REFUSED
    except EvidenceError as exc:
        _print({"error": safe_message(exc, identity)})
        return EXIT_USAGE
    except OSError as exc:  # strerror only: the filename attribute may hold a private path
        _print({"error": type(exc).__name__ + ": " + safe_message(exc.strerror or "", identity)})
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001 - a default traceback would print absolute paths
        _print({"error": type(exc).__name__ + ": " + safe_message(exc, identity)})
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
