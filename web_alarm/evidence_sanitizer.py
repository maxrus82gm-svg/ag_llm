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

Commands (``python -m web_alarm.evidence_sanitizer``)::

  scan   PACKAGE [--manifest] [--json FILE]   read-only inventory; never prints matched values
  stage  PACKAGE --out DIR [--manifest]       preserve originals, write sanitized copies and mapping.json
  verify DIR [--package PACKAGE]              recheck hashes, rescan, reproduce sanitized bytes from originals

``--out`` must be outside the package and either outside the repository or under its git-ignored ``logs/``.
Exit codes: 0 = safe, 2 = findings remain / publication refused, 3 = usage or environment error.
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
        if reason not in self.reasons:
            self.reasons.append(reason)


def _json_values(text: str) -> list[str]:
    return [json.loads(m.group(0)) for m in _JSON_STRING.finditer(text)]


def process_bytes(rel: str, data: bytes, policy: Policy = Policy(), identity: re.Pattern | None = None) -> FileResult:
    """Sanitize one file's bytes; never raises for bad content (the result is BLOCKED instead)."""
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
        except ValueError:
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
        except ValueError:
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

def _inside(child: Path, parent: Path) -> bool:
    child_s, parent_s = os.path.normcase(str(child)), os.path.normcase(str(parent))
    try:
        return os.path.commonpath([child_s, parent_s]) == parent_s
    except ValueError:  # different drives
        return False


def package_files(package: Path, use_manifest: bool) -> tuple[list[str], dict]:
    """Relative ids to process (sorted) and the package manifest's own entries (if requested)."""
    if not package.is_dir():
        raise EvidenceError("package directory not found")
    entries = {}
    if use_manifest:
        manifest_path = package / "manifest.json"
        if not manifest_path.is_file():
            raise EvidenceError("manifest.json not found in package")
        listed = json.loads(manifest_path.read_bytes()).get("files")
        entries = dict(listed) if isinstance(listed, dict) else {name: {} for name in listed or []}
        ids = sorted(set(entries) | {"manifest.json"})
    else:
        ids = sorted(p.relative_to(package).as_posix() for p in package.rglob("*")
                     if p.is_file() and "__pycache__" not in p.relative_to(package).parts)
    for rel in ids:
        rel_path = PurePosixPath(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts or not _inside((package / rel).resolve(), package.resolve()):
            raise EvidenceError("manifest entry escapes the package")
    return ids, entries


UNSUPPORTED_REASONS = frozenset({"invalid-json", "invalid-jsonl", "structure", "key-collision", "value-changed",
                                 "protected-field-changed", "binary-with-findings"})


def scan(package: Path, use_manifest: bool = False, policy: Policy = Policy(), identity=None) -> dict:
    """Read-only inventory of a package: categories and counts per file id, never values."""
    ids, _entries = package_files(package, use_manifest)
    files, classes = [], Counter()
    for rel in ids:
        path = package / rel
        if not path.is_file():
            files.append({"id": rel, "class": "MISSING"})
            classes["MISSING"] += 1
            continue
        r = process_bytes(rel, path.read_bytes(), policy, identity)
        replaced = sum(r.counts[k] for k in REPLACED_KINDS)
        if r.original_identity_hits or r.counts[SECRET]:
            cls = "CONFIRMED"
        elif replaced:
            cls = "SUSPECT"
        elif any(r.counts[k] for k in KEPT_KINDS):
            cls = "BENIGN_ONLY"
        else:
            cls = "CLEAN"
        if UNSUPPORTED_REASONS.intersection(r.reasons):
            cls = "UNSUPPORTED" if cls == "CLEAN" else cls + "+UNSUPPORTED"
        classes[cls] += 1
        files.append({"id": rel, "kind": r.kind, "bytes": r.source_bytes, "sha256": r.source_sha256, "class": cls,
                      "findings": dict(sorted(r.counts.items())), "identity_hits": r.original_identity_hits,
                      "json_tokens_affected": r.json_tokens_changed,
                      "after_sanitizing": "PASS" if r.safety == "PASS" else "BLOCKED:" + ",".join(r.reasons)})
    return {"tool": "web_alarm.evidence_sanitizer", "policy": policy.as_dict(), "package": package.name,
            "files_scanned": len(ids), "classes": dict(sorted(classes.items())),
            "findings_total": _summary_counts_from(files), "files": files}


def _summary_counts_from(files) -> dict:
    total = Counter()
    for f in files:
        total.update(f.get("findings", {}))
    return dict(sorted(total.items()))


def _check_out_dir(out: Path, package: Path) -> Path:
    out_r, pkg_r, repo = out.resolve(), package.resolve(), REPO_ROOT.resolve()
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


def _mapping_row(r: FileResult, manifest_entry: dict | None, original_sha: str | None, out_sha: str | None) -> dict:
    row = {"id": r.id, "kind": r.kind, "source_sha256": r.source_sha256, "source_bytes": r.source_bytes,
           "preserved_original": "originals/" + r.id, "preserved_sha256": original_sha,
           "sanitized_id": ("sanitized/" + r.id) if out_sha else None, "sanitized_sha256": out_sha,
           "sanitized_bytes": len(r.output) if r.output is not None else None,
           "changed": out_sha is not None and out_sha != r.source_sha256,
           "replacements": {k: v for k, v in sorted(r.counts.items()) if k in REPLACED_KINDS},
           "kept": {k: v for k, v in sorted(r.counts.items()) if k in KEPT_KINDS},
           "json_tokens": r.json_tokens, "json_tokens_changed": r.json_tokens_changed,
           "structure": r.structure, "safety": r.safety, "reasons": r.reasons}
    if manifest_entry is not None:
        expected = manifest_entry.get("sha256")
        row["manifest_sha256_match"] = None if expected is None else expected == r.source_sha256
    return row


def _tool_sha() -> str:
    """SHA-256 of this module with LF line ends, so LF and CRLF checkouts report the same tool revision."""
    return _sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n"))


def stage(package: Path, out: Path, use_manifest: bool = False, policy: Policy = Policy(), identity=None) -> dict:
    """Preserve originals and write sanitized copies + mapping.json into a new private directory."""
    ids, entries = package_files(package, use_manifest)
    out_r = _check_out_dir(out, package)
    out_r.mkdir(parents=True, exist_ok=True)
    rows = []
    for rel in ids:
        source = package / rel
        data = source.read_bytes()
        r = process_bytes(rel, data, policy, identity)
        original_sha = _write_new(out_r / "originals" / rel, data)
        out_sha = _write_new(out_r / "sanitized" / rel, r.output) if r.output is not None else None
        if _sha(source.read_bytes()) != r.source_sha256:
            r.refuse("source-changed-during-staging")
        rows.append(_mapping_row(r, entries.get(rel) if use_manifest else None, original_sha, out_sha))
    blocked = [row["id"] for row in rows if row["safety"] != "PASS"]
    mapping = {
        "tool": "web_alarm.evidence_sanitizer", "tool_sha256_lf": _tool_sha(), "policy": policy.as_dict(),
        "package": package.name, "selection": "manifest" if use_manifest else "all-files",
        "files_total": len(rows), "files_changed": sum(1 for r in rows if r["changed"]),
        "files_blocked": len(blocked), "replacements_total": _sum_rows(rows, "replacements"),
        "kept_total": _sum_rows(rows, "kept"),
        "identity_gate": "ENFORCED" if identity is not None else "NOT ENFORCED",
        "verdict": "SAFE PUBLICATION CANDIDATE (needs USER GO)" if not blocked else "REFUSED", "files": rows,
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


def verify(out: Path, package: Path | None = None, identity=None) -> dict:
    """Recheck a staged set: hashes, completeness, gate, and reproduction from the preserved originals."""
    mapping_path = out / "mapping.json"
    if not mapping_path.is_file():
        raise EvidenceError("mapping.json not found")
    mapping = json.loads(mapping_path.read_bytes())
    policy_dict = mapping.get("policy", {})
    if policy_dict.get("version") != POLICY_VERSION:
        raise EvidenceError("mapping policy version is not supported by this tool")
    policy = Policy(tuple(policy_dict.get("repo_anchors", ())), frozenset(policy_dict.get("protected_keys", ())))
    problems = Counter()
    listed = set()
    for row in mapping["files"]:
        rel = row["id"]
        listed.add(rel)
        original = out / "originals" / rel
        if not original.is_file() or _sha(original.read_bytes()) != row["source_sha256"]:
            problems["original-missing-or-changed"] += 1
            continue
        data = original.read_bytes()
        if package is not None:
            current = package / rel
            if not current.is_file() or _sha(current.read_bytes()) != row["source_sha256"]:
                problems["package-differs-from-preserved-original"] += 1
        again = process_bytes(rel, data, policy, identity)
        expected = row.get("sanitized_sha256")
        sanitized = out / "sanitized" / rel
        if expected is None:
            if sanitized.exists():
                problems["blocked-file-has-sanitized-copy"] += 1
            if again.safety == "PASS":
                problems["blocked-file-now-passes"] += 1
            continue
        if not sanitized.is_file() or _sha(sanitized.read_bytes()) != expected:
            problems["sanitized-missing-or-changed"] += 1
        if again.output is None or _sha(again.output) != expected:
            problems["not-reproducible"] += 1
        if again.safety != "PASS":
            problems["gate-fails-now"] += 1
    extra = [p for p in (out / "sanitized").rglob("*") if p.is_file()
             and p.relative_to(out / "sanitized").as_posix() not in listed] if (out / "sanitized").is_dir() else []
    if extra:
        problems["unlisted-sanitized-files"] += len(extra)
    blocked = sum(1 for row in mapping["files"] if row["safety"] != "PASS")
    return {"files_checked": len(mapping["files"]), "files_blocked_in_mapping": blocked,
            "problems": dict(sorted(problems.items())),
            "verdict": "CONSISTENT" if not problems else "INCONSISTENT",
            "publication": "SAFE CANDIDATE" if not problems and not blocked else "REFUSED"}


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
    p_verify.add_argument("--package")
    args = parser.parse_args(argv)

    tokens = list(args.identity_token) + ([] if args.no_local_identity else local_identity_tokens())
    identity = identity_pattern(tokens)
    policy = Policy(tuple(args.repo_anchor)) if args.repo_anchor else Policy()
    try:
        if args.command == "scan":
            report = scan(Path(args.package), args.manifest, policy, identity)
            if args.json_out:
                target = Path(args.json_out)
                if _inside(target.resolve(), Path(args.package).resolve()):
                    raise EvidenceError("inventory file must not be written into the scanned package")
                with open(target, "xb") as handle:
                    handle.write((json.dumps(report, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
            _print({k: v for k, v in report.items() if k != "files"})
            leaks = sum(v for k, v in report["classes"].items() if k.startswith(("CONFIRMED", "SUSPECT", "UNSUP")))
            return EXIT_REFUSED if leaks else EXIT_SAFE
        if args.command == "stage":
            mapping = stage(Path(args.package), Path(args.out), args.manifest, policy, identity)
            _print({k: v for k, v in mapping.items() if k != "files"} |
                   {"blocked": [{"id": r["id"], "reasons": r["reasons"]} for r in mapping["files"]
                                if r["safety"] != "PASS"]})
            return EXIT_SAFE if mapping["files_blocked"] == 0 else EXIT_REFUSED
        report = verify(Path(args.out), Path(args.package) if args.package else None, identity)
        _print(report)
        return EXIT_SAFE if report["publication"] == "SAFE CANDIDATE" else EXIT_REFUSED
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
