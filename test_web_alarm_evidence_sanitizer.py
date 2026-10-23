"""Publication-safe evidence: structural path detection, JSON-preserving sanitizing and a refusing gate.

Oracles do not reuse the sanitizer: hand-written expected strings, raw searches for synthetic identity tokens
(any case, raw, \\uXXXX-escaped, UTF-16) and recomputed SHA-256. The literal-replacement algorithm of the earlier
per-TASK helpers is reproduced first to show the original leak (RED), then the new tool on the same input.
All names and paths are synthetic; files live in TEMP only.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from web_alarm import evidence_sanitizer as es

ROOT = Path(__file__).resolve().parent
USER = "zqsynthuser"
HOST = "ZQSYNTH-PC9"
CYR = "\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0439"  # Cyrillic profile name
TEMP_ROOT = "C:\\Users\\" + USER + "\\AppData\\Local\\Temp"
HOME_ROOT = "C:\\Users\\" + USER
REPO_ABS = "Q:\\Work\\ag_llm"
POLICY = es.Policy(("ag_llm",))
IDENTITY = es.identity_pattern([USER, HOST, CYR])
ELLIPSIS = chr(0x2026)
LS_ESCAPE = "\\" + "u2028"  # the JSON escape of U+2028 as six characters


def legacy_sanitize(text: str, temp: str = TEMP_ROOT, repo: str = REPO_ABS, home: str = HOME_ROOT) -> str:
    """Algorithm of the earlier helpers (TASK_CLAUDE-WA4-R-*/tools/collect_evidence.py, sanitize_paths.py):
    three literal, case-sensitive spellings of each root."""
    for raw, token in ((temp, "<TEMP>"), (repo, "<REPO>"), (home, "<USER>")):
        for form in (raw, raw.replace("\\", "\\\\"), raw.replace("\\", "/")):
            text = text.replace(form, token)
    return text


def leaks(data, *tokens) -> list:
    """Independent oracle: synthetic tokens still present in any case, raw or \\uXXXX-escaped (any level)."""
    if isinstance(data, bytes):
        views = [data.decode("utf-8", "replace"), data.decode("utf-16-le", "replace"),
                 data[1:].decode("utf-16-le", "replace")]
    else:
        views = [data]
    views = [v.lower() for v in views]
    found = []
    for token in tokens or (USER, HOST, CYR):
        low = token.lower()
        escaped = json.dumps(low)[1:-1]
        if any(low in v or escaped in v for v in views):
            found.append(token)
    return found


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def results_doc() -> str:
    """A synthetic runner results.json with formatting that must survive byte-for-byte."""
    error = ("Traceback (most recent call last):\n  File \"" + REPO_ABS + "\\web_alarm\\x.py\", line 7\n"
             "PermissionError: [WinError 5] Access is denied: " + repr(TEMP_ROOT + "\\wa_tr_1\\state\\lock"))
    isolation = "write outside disposable temp: " + "\\\\?\\" + TEMP_ROOT + "\\wa_tr_1\\state"
    return ('{\n "tests_run": 3, "elapsed": 1.50, "big": 12345678901234567890, "ratio": 1e3, "nan": NaN,\n'
            ' "tests": [\n'
            '  {"test": "test_a.T.test_one", "status": "PASS", "error": null},\n'
            '  {"test": "test_a.T.test_two", "status": "FAIL", "error": ' + json.dumps(error) + '},\n'
            '  {"test": "test_a.T.test_three", "status": "SKIP", "error": "symlink privilege"}\n'
            ' ],\n'
            ' "isolation_violations": [' + json.dumps(isolation) + '],\n'
            ' "dup": 1, "dup": 2,\n'
            ' "sep": "a' + LS_ESCAPE + 'b \\u0416"\n}\n')


class TempCase(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_evsan_"))
        self.addCleanup(shutil.rmtree, self.base, True)

    def make_package(self, files: dict, manifest: bool = True) -> Path:
        pkg = self.base / ("pkg_" + uuid.uuid4().hex[:6])
        for rel, data in files.items():
            path = pkg / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
        if manifest:
            listed = {rel: {"bytes": (pkg / rel).stat().st_size, "sha256": sha((pkg / rel).read_bytes())}
                      for rel in files}
            (pkg / "manifest.json").write_text(json.dumps({"files": listed}, indent=1), encoding="utf-8")
        return pkg

    def base_forms(self) -> list[str]:
        raw = str(self.base.resolve())
        return [raw, raw.replace("\\", "/"), raw.replace("\\", "\\\\"), raw.lower()]

    def assert_no_base_path(self, text: str):
        for form in self.base_forms():
            self.assertNotIn(form.lower(), text.lower())


def standard_package_files() -> dict:
    return {
        "report.md": "Guard compares `\\\\?\\C:\\" + ELLIPSIS + "\\Temp\\" + ELLIPSIS + "` with TEMP.\n"
                     "Runner: " + REPO_ABS + "\\wa4a_acceptance.py\n",
        "runs/a/results.json": results_doc(),
        "runs/a/summary.json": json.dumps({"exit": 1, "base": TEMP_ROOT + "\\claude-x-1",
                                           "non_pass": [["test_a.T.test_two", "FAIL",
                                                         (TEMP_ROOT + "\\mirror\\x")[9:]]]}, indent=1),
        "tools/run.py": 'REPO = r"' + REPO_ABS + '"\nprint("ok")\n',
        "sample/data.bin": b"\x00\x01\x02binary\xff\xfe" * 8,
        "nested/deep/notes.txt": "attempt dir " + TEMP_ROOT.lower().replace("\\", "/") + "/wa_x\r\nend\r\n",
    }


class LegacyGapTests(unittest.TestCase):
    """RED first: shapes that reached published evidence although the literal replacement had run."""

    def shapes(self) -> dict:
        lock = TEMP_ROOT + "\\wa_tailrec_x\\state\\locks\\transport"
        return {
            "repr-inside-json": json.dumps("[WinError 5] Access is denied: " + repr(lock)),
            "lowercase-physical-key": json.dumps(
                {"physical_key": (TEMP_ROOT + "\\wa4r002_x\\project\\data.txt").lower().replace("\\", "/")}),
            "extended-prefix-repr": json.dumps("outside disposable temp: " + repr("\\\\?\\" + lock)),
            "truncated-tail": json.dumps((TEMP_ROOT + "\\claude-mirror-M5\\x")[9:]),
            "frames-json-in-json": json.dumps(json.dumps(
                {"frames": ['  File "' + REPO_ABS + '\\web_alarm\\task_store.py", line 1, in f']})),
        }

    def test_legacy_replacement_leaks_every_shape(self):
        for name, shape in self.shapes().items():
            with self.subTest(shape=name):
                legacy = legacy_sanitize(shape)
                self.assertTrue(leaks(legacy) or "Work" in legacy, "legacy unexpectedly clean")

    def test_new_sanitizer_closes_every_shape_and_keeps_json_valid(self):
        for name, shape in self.shapes().items():
            with self.subTest(shape=name):
                new, counts, _tokens, changed = es.sanitize_json_text(shape, POLICY)
                self.assertEqual(leaks(new), [])
                self.assertNotIn("Work", new)
                self.assertEqual(changed, 1)
                json.loads(new)

    def test_truncated_inside_profile_name(self):
        for cut in range(9, 9 + len(USER) - 2):  # the message tail may start anywhere inside the name
            with self.subTest(cut=cut):
                text = (TEMP_ROOT + "\\claude-mirror\\x")[cut:]
                self.assertEqual(es.sanitize_text(text, POLICY)[0], "<TEMP>\\claude-mirror\\x")


class PathFormTests(unittest.TestCase):
    REPLACED = [
        (TEMP_ROOT + "\\wa_x\\state", "<TEMP>\\wa_x\\state"),
        ("c:/users/" + USER + "/appdata/local/temp/wa/p.txt", "<TEMP>/wa/p.txt"),
        ("C:/Users\\" + USER + "/AppData\\Local/Temp\\wa", "<TEMP>\\wa"),
        ("\\\\?\\" + TEMP_ROOT + "\\wa\\locks", "\\\\?\\<TEMP>\\wa\\locks"),
        ("C:\\Users\\ZQSYNT~1\\AppData\\Local\\Temp\\wa", "<TEMP>\\wa"),
        ("C:\\Users\\Zq Synth\\AppData\\Local\\Temp\\wa", "<TEMP>\\wa"),
        ("C:\\Users\\" + CYR + "\\Documents\\a.txt", "<HOME>\\Documents\\a.txt"),
        (HOME_ROOT, "<HOME>"),
        (HOME_ROOT + "\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\json\\decoder.py",
         "<HOME>\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\json\\decoder.py"),
        (REPO_ABS + "\\web_alarm\\task_store.py", "<REPO>\\web_alarm\\task_store.py"),
        ("D:\\a\\ag_llm\\ag_llm\\test_x.py", "<REPO>\\test_x.py"),
        ("C:\\Users\\" + USER + "\\src\\ag_llm\\web_alarm\\x.py", "<REPO>\\web_alarm\\x.py"),
        ("E:\\Clients\\Ivanov\\report.txt", "<ABS>\\report.txt"),
        ("\\\\fileserver\\share$\\people\\x.txt", "<UNC>\\people\\x.txt"),
        ("\\\\?\\UNC\\fileserver\\share\\x.txt", "\\\\?\\UNC\\<UNC>\\x.txt"),
        ("/home/" + USER + "/wa/x and /Users/" + USER + "/y", "<HOME>/wa/x and <HOME>/y"),
        ("file:///C:/Users/" + USER + "/x.html", "file:///<HOME>/x.html"),
        (USER + "\\AppData\\Local\\Temp\\claude-mirror\\x", "<TEMP>\\claude-mirror\\x"),
        ("thuser\\AppData\\Roaming\\x", "<HOME>\\AppData\\Roaming\\x"),
        ("sers\\" + USER + "\\AppData\\Local\\Temp\\x", "sers\\<TEMP>\\x"),
        ("C:\\Windows\\..\\Users\\" + USER + "\\x", "<HOME>\\x"),
        ("path " + TEMP_ROOT + "\\a and C:\\Users\\other\\b", "path <TEMP>\\a and <HOME>\\b"),
        ("'" + TEMP_ROOT + "\\a', '" + TEMP_ROOT + "\\b'", "'<TEMP>\\a', '<TEMP>\\b'"),
        # a rejected UNC candidate (separator level does not match) must not swallow the profile behind it
        ("\\\\h\\\\\\\\Users\\\\" + USER + "\\\\x", "\\\\h\\\\\\\\<HOME>\\\\x"),
    ]
    KEPT = [
        "C:\\Program Files\\Python312\\Lib\\unittest\\case.py",
        "C:\\Windows\\Temp\\x.log",
        "C:\\Users\\Public\\Documents\\x",
        "\\\\?\\C:\\" + ELLIPSIS + "\\Temp\\" + ELLIPSIS,
        "C:\\Users\\...\\AppData",
        "C:\\",
        "D:\\data",
        "https://example.com/a/b?x=1",
        "ratio 1:2, Gate A: done, 12:30",
        "with self.open(mode='rb') as f:\\n    data = f.read()",
        "lambda x:\\n\\treturn x",
        "LOCALAPPDATA/APPDATA and pycache in TEMP",
        "\\\\n\\\\nTraceback follows",
        "<TEMP>\\wa\\x and <HOME>\\y and <REPO>\\z and <UNC>\\s",
    ]

    # subTest labels are indexes: a test id is a protected identifier, and a synthetic path inside it would make
    # the failure evidence itself unpublishable (the sanitizer refuses to rewrite test ids)
    def test_identifying_prefix_replaced_exactly(self):
        for case, (text, expected) in enumerate(self.REPLACED):
            with self.subTest(case=case):
                self.assertEqual(es.sanitize_text(text, POLICY)[0], expected)

    def test_benign_and_illustrative_text_untouched(self):
        for case, text in enumerate(self.KEPT):
            with self.subTest(case=case):
                self.assertEqual(es.sanitize_text(text, POLICY)[0], text)

    def test_idempotent(self):
        for text, _expected in self.REPLACED:
            once = es.sanitize_text(text, POLICY)[0]
            self.assertEqual(es.sanitize_text(once, POLICY)[0], once)
            self.assertEqual([k for k, *_r, p in es.find_paths(once, POLICY) if p], [])


class EscapingLevelTests(unittest.TestCase):
    """A path nested 0..3 times in JSON (and in repr) loses only its prefix and keeps its escaping."""

    def levels(self, name: str, ensure_ascii: bool) -> list[str]:
        out = ["C:\\Users\\" + name + "\\AppData\\Local\\Temp\\w"]
        for _ in range(3):
            out.append(json.dumps(out[-1], ensure_ascii=ensure_ascii)[1:-1])
        return out

    def test_levels_ascii_and_cyrillic(self):
        for index, name in enumerate((USER, CYR, "Zq Synth")):
            for ensure_ascii in (True, False):
                for depth, text in enumerate(self.levels(name, ensure_ascii)):
                    with self.subTest(name=index, ascii=ensure_ascii, depth=depth):
                        out = es.sanitize_text(text, POLICY)[0]
                        self.assertEqual(leaks(out, name), [])
                        for _ in range(depth):
                            out = json.loads('"' + out + '"')
                        self.assertEqual(out, "<TEMP>\\w")

    def test_repr_layers(self):
        text = repr("C:\\Users\\" + CYR + "\\AppData\\Local\\Temp\\w")
        for depth in range(3):
            with self.subTest(depth=depth):
                out = es.sanitize_text(text, POLICY)[0]
                self.assertEqual(leaks(out, CYR), [])
                text = json.dumps(text)[1:-1]


class JsonDocumentTests(unittest.TestCase):
    def test_results_document_keeps_structure_counters_and_formatting(self):
        doc = results_doc()
        r = es.process_bytes("runs/a/results.json", doc.encode("utf-8"), POLICY, IDENTITY)
        self.assertEqual((r.safety, r.structure, r.reasons), ("PASS", "PASS", []))
        out = r.output.decode("utf-8")
        self.assertEqual(leaks(out), [])
        self.assertNotIn("Work", out)
        old, new = json.loads(doc), json.loads(out)
        self.assertEqual(new["tests_run"], 3)
        self.assertEqual([t["status"] for t in new["tests"]], ["PASS", "FAIL", "SKIP"])
        self.assertEqual([t["test"] for t in new["tests"]], [t["test"] for t in old["tests"]])
        self.assertEqual(len(new["isolation_violations"]), 1)
        self.assertEqual(new["big"], 12345678901234567890)
        self.assertTrue(math.isnan(new["nan"]))
        for kept in ('"elapsed": 1.50', '"ratio": 1e3', '"nan": NaN', '"dup": 1, "dup": 2',
                     '"a' + LS_ESCAPE + 'b \\u0416"', '{"test": "test_a.T.test_one", "status": "PASS", "error": null}'):
            self.assertIn(kept, out)
        self.assertNotIn(chr(0x2028), out)
        self.assertIn("\\\\\\\\?\\\\<TEMP>\\\\wa_tr_1", out)  # extended prefix kept for the F-T1 diagnosis
        self.assertEqual(r.json_tokens_changed, 2)
        self.assertEqual((r.counts["TEMP"], r.counts["REPO"]), (2, 1))
        changed = [(a, b) for a, b in zip(doc.splitlines(), out.splitlines()) if a != b]
        self.assertEqual(len(changed), 2)

    def test_key_collision_refused(self):
        doc = json.dumps({HOME_ROOT + "\\a": 1, "C:\\Users\\other\\a": 2})
        r = es.process_bytes("x.json", doc.encode(), POLICY, IDENTITY)
        self.assertEqual(r.safety, "BLOCKED")
        self.assertIn("key-collision", r.reasons)
        self.assertIsNone(r.output)

    def test_protected_identifier_change_refused(self):
        doc = json.dumps({"tests": [{"test": "test_x [" + HOME_ROOT + "\\x]", "status": "PASS"}]})
        r = es.process_bytes("results.json", doc.encode(), POLICY, IDENTITY)
        self.assertIn("protected-field-changed", r.reasons)
        self.assertIsNone(r.output)

    def test_bom_and_crlf_preserved(self):
        data = b"\xef\xbb\xbf" + ('{\r\n "p": ' + json.dumps(TEMP_ROOT + "\\x") + '\r\n}\r\n').encode()
        r = es.process_bytes("x.json", data, POLICY, IDENTITY)
        self.assertEqual(r.safety, "PASS")
        self.assertTrue(r.output.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(r.output.count(b"\r\n"), 3)
        self.assertEqual(json.loads(r.output[3:]), {"p": "<TEMP>\\x"})

    def test_invalid_and_truncated_json_refused_without_output(self):
        for case, data in enumerate((b'{"a": "' + TEMP_ROOT.encode() + b'"', b"", b"{]")):
            with self.subTest(case=case):
                r = es.process_bytes("bad.json", data, POLICY, IDENTITY)
                self.assertEqual((r.safety, r.structure, r.output), ("BLOCKED", "FAIL", None))
                self.assertIn("invalid-json", r.reasons)

    def test_jsonl(self):
        good = (json.dumps({"p": TEMP_ROOT + "\\a"}) + "\n" + json.dumps({"n": 1}) + "\n").encode()
        r = es.process_bytes("events.jsonl", good, POLICY, IDENTITY)
        self.assertEqual(r.safety, "PASS")
        self.assertEqual([json.loads(x) for x in r.output.decode().splitlines()], [{"p": "<TEMP>\\a"}, {"n": 1}])
        bad = good + b'{"torn": "' + TEMP_ROOT.encode() + b'\n'
        r = es.process_bytes("events.jsonl", bad, POLICY, IDENTITY)
        self.assertIn("invalid-jsonl", r.reasons)
        self.assertIsNone(r.output)


class GateTests(unittest.TestCase):
    """The final gate refuses publication when anything identifying is left, never silently passes it."""

    def test_identity_outside_a_path_refused(self):
        r = es.process_bytes("notes.md", ("operator " + USER + " approved").encode(), POLICY, IDENTITY)
        self.assertEqual(r.safety, "BLOCKED")
        self.assertIn("residual-identity", r.reasons)
        self.assertIsNone(r.output)

    def test_escaped_cyrillic_identity_caught_at_any_level(self):
        for level, doc in enumerate((json.dumps({"who": CYR}), json.dumps({"inner": json.dumps({"who": CYR})}))):
            with self.subTest(level=level):
                self.assertNotIn(CYR, doc)
                r = es.process_bytes("x.json", doc.encode(), POLICY, IDENTITY)
                self.assertIn("residual-identity", r.reasons)

    def test_secret_redacted_and_refused(self):
        token = "ghp_" + "Zq9" * 12
        text = "push with " + token + " then password=s3cretValue9"
        out, counts = es.sanitize_text(text, POLICY)
        # assertFalse with a fixed message: a failure must not print the (synthetic) secret into the evidence
        self.assertFalse(token in out, "synthetic token survived")
        self.assertFalse("s3cretValue9" in out, "synthetic password survived")
        self.assertEqual(counts["SECRET"], 2)
        r = es.process_bytes("log.txt", text.encode(), POLICY, IDENTITY)
        self.assertIn("secret-redacted-review-required", r.reasons)
        self.assertIsNone(r.output)

    def test_symbolic_secret_keys_are_not_secrets(self):
        text = 'payload={"secret": MARKER, "line": 1}'
        self.assertEqual(es.sanitize_text(text, POLICY), (text, es.Counter()))

    def test_binary_with_utf16_path_refused_both_alignments(self):
        path16 = ("C:\\Users\\" + USER + "\\x").encode("utf-16-le")
        for data in (b"\x00\x01" + path16, b"\x00" + path16):
            with self.subTest(odd=len(data) % 2):
                r = es.process_bytes("blob.bin", data, POLICY, IDENTITY)
                self.assertEqual((r.kind, r.safety), ("binary", "BLOCKED"))
                self.assertIn("binary-with-findings", r.reasons)

    def test_clean_binary_copied_identically(self):
        data = b"\x00\x01\x02binary\xff\xfe" * 8
        r = es.process_bytes("blob.bin", data, POLICY, IDENTITY)
        self.assertEqual((r.kind, r.safety, r.output), ("binary", "PASS", data))

    def test_illustrative_markdown_passes_unchanged(self):
        data = ("guard sees `\\\\?\\C:\\" + ELLIPSIS + "\\Temp\\" + ELLIPSIS + "`").encode()
        r = es.process_bytes("report.md", data, POLICY, IDENTITY)
        self.assertEqual((r.safety, r.output), ("PASS", data))

    def test_local_identity_tokens(self):
        env = {"USERNAME": "Zq.Synth", "COMPUTERNAME": "DESKTOP-AB12CD", "USERDOMAIN": "WORKGROUP"}
        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch("pathlib.Path.home", return_value=Path("C:/Users/zqprofile")):
            tokens = {t.lower() for t in es.local_identity_tokens()}
        self.assertTrue({"zq.synth", "synth", "desktop-ab12cd", "ab12cd", "zqprofile"} <= tokens)
        self.assertFalse({"desktop", "workgroup", "zq"} & tokens)


class DeterminismTests(TempCase):
    def test_output_does_not_depend_on_local_identity(self):
        doc = results_doc().encode()
        outputs = {es.process_bytes("r.json", doc, POLICY, ident).output
                   for ident in (None, IDENTITY, es.identity_pattern(["someoneelse", "OTHER-HOST"]))}
        self.assertEqual(len(outputs), 1)

    def test_two_stagings_are_byte_identical(self):
        pkg = self.make_package(standard_package_files())
        first = es.stage(pkg, self.base / "s1", True, POLICY, IDENTITY)
        second = es.stage(pkg, self.base / "s2", True, POLICY, IDENTITY)
        self.assertEqual((self.base / "s1" / "mapping.json").read_bytes(), (self.base / "s2" / "mapping.json").read_bytes())
        self.assertEqual(first, second)
        for row in first["files"]:
            if row["sanitized_id"]:
                self.assertEqual((self.base / "s1" / row["sanitized_id"]).read_bytes(),
                                 (self.base / "s2" / row["sanitized_id"]).read_bytes())


class StageVerifyTests(TempCase):
    def snapshot(self, pkg: Path) -> dict:
        return {p.relative_to(pkg).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in sorted(pkg.rglob("*")) if p.is_file()}

    def test_stage_preserves_originals_and_maps_every_file(self):
        files = standard_package_files()
        pkg = self.make_package(files)
        before = self.snapshot(pkg)
        out = self.base / "staging"
        mapping = es.stage(pkg, out, True, POLICY, IDENTITY)
        self.assertEqual(self.snapshot(pkg), before)  # source package untouched (bytes and mtime)
        self.assertEqual(mapping["verdict"], "SAFE PUBLICATION CANDIDATE (needs USER GO)")
        self.assertEqual(mapping["files_total"], len(files) + 1)
        self.assertEqual(sorted(r["id"] for r in mapping["files"]), sorted([*files, "manifest.json"]))
        for row in mapping["files"]:
            source = (pkg / row["id"]).read_bytes()
            self.assertEqual(row["source_sha256"], sha(source))
            self.assertEqual((out / "originals" / row["id"]).read_bytes(), source)
            sanitized = (out / row["sanitized_id"]).read_bytes()
            self.assertEqual(row["sanitized_sha256"], sha(sanitized))
            self.assertEqual(leaks(sanitized), [])
            self.assertNotIn(b"Work", sanitized)
            if row["id"] != "manifest.json":
                self.assertIs(row["manifest_sha256_match"], True)
        changed = {r["id"] for r in mapping["files"] if r["changed"]}
        # manifest.json changes too: the candidate's manifest is re-hashed to describe the sanitized bytes
        self.assertEqual(changed, {"report.md", "runs/a/results.json", "runs/a/summary.json", "tools/run.py",
                                   "nested/deep/notes.txt", "manifest.json"})
        text = (out / "mapping.json").read_text(encoding="utf-8")
        self.assert_no_base_path(text)
        self.assertEqual(leaks(text), [])
        report = es.verify(out, pkg, IDENTITY)
        self.assertEqual((report["verdict"], report["publication"], report["problems"]),
                         ("CONSISTENT", "SAFE CANDIDATE", {}))

    def test_verify_detects_tampering_and_drift(self):
        pkg = self.make_package(standard_package_files())
        cases = {
            "sanitized-missing-or-changed": lambda out: (out / "sanitized/runs/a/summary.json").write_text("{}"),
            "original-missing-or-changed": lambda out: (out / "originals/tools/run.py").unlink(),
            "unlisted-sanitized-files": lambda out: (out / "sanitized/extra.txt").write_text("x"),
            "package-differs-from-preserved-original": lambda out: (pkg / "report.md").write_text("changed"),
        }
        for problem, tamper in cases.items():
            with self.subTest(problem=problem):
                out = self.base / ("t_" + problem)
                es.stage(pkg, out, True, POLICY, IDENTITY)
                tamper(out)
                report = es.verify(out, pkg, IDENTITY)
                self.assertEqual(report["verdict"], "INCONSISTENT")
                self.assertIn(problem, report["problems"])

    def test_manifest_mismatch_reported(self):
        pkg = self.make_package({"a.txt": "alpha"})
        manifest = json.loads((pkg / "manifest.json").read_text())
        manifest["files"]["a.txt"]["sha256"] = "0" * 64
        (pkg / "manifest.json").write_text(json.dumps(manifest))
        mapping = es.stage(pkg, self.base / "out", True, POLICY, IDENTITY)
        row = next(r for r in mapping["files"] if r["id"] == "a.txt")
        self.assertIs(row["manifest_sha256_match"], False)

    def test_manifest_entry_escaping_package_refused(self):
        pkg = self.make_package({"a.txt": "alpha"})
        (pkg / "manifest.json").write_text(json.dumps({"files": {"../outside.txt": {}}}))
        with self.assertRaises(es.EvidenceError):
            es.stage(pkg, self.base / "out", True, POLICY, IDENTITY)
        self.assertFalse((self.base / "out").exists())

    def test_blocked_file_has_no_sanitized_copy_and_refuses(self):
        pkg = self.make_package({"ok.txt": TEMP_ROOT + "\\a", "bad.md": "signed by " + USER})
        out = self.base / "out"
        mapping = es.stage(pkg, out, True, POLICY, IDENTITY)
        self.assertEqual(mapping["verdict"], "REFUSED")
        bad = next(r for r in mapping["files"] if r["id"] == "bad.md")
        self.assertEqual((bad["safety"], bad["sanitized_id"]), ("BLOCKED", None))
        self.assertFalse((out / "sanitized" / "bad.md").exists())
        self.assertEqual((out / "originals" / "bad.md").read_bytes(), (pkg / "bad.md").read_bytes())
        self.assertEqual(es.verify(out, pkg, IDENTITY)["publication"], "REFUSED")

    def test_output_location_guards_create_nothing(self):
        pkg = self.make_package({"a.txt": "alpha"})
        busy = self.base / "busy"
        busy.mkdir()
        (busy / "keep.txt").write_text("x")
        inside_repo = es.REPO_ROOT / ("zz-evidence-guard-" + uuid.uuid4().hex)
        for out in (pkg / "staging", pkg, self.base, inside_repo, busy):
            with self.subTest(out=out.name):
                with self.assertRaises(es.EvidenceError):
                    es.stage(pkg, out, True, POLICY, IDENTITY)
        self.assertFalse((pkg / "staging").exists())
        self.assertFalse(inside_repo.exists())
        self.assertEqual(sorted(p.name for p in busy.iterdir()), ["keep.txt"])
        logs_target = es.REPO_ROOT / "logs" / ("zz-evidence-guard-" + uuid.uuid4().hex)
        self.assertEqual(es._check_out_dir(logs_target, pkg), logs_target.resolve())  # accepted, not created
        self.assertFalse(logs_target.exists())
        with self.assertRaises(es.EvidenceError):
            es._check_out_dir(es.REPO_ROOT / "logs", pkg)

    def test_source_changed_during_staging_refused(self):
        pkg = self.make_package({"a.txt": TEMP_ROOT + "\\a", "b.txt": "beta"})
        original = es.process_bytes

        def racing(rel, data, *args, **kwargs):
            if rel == "a.txt":
                (pkg / "a.txt").write_text("changed underneath")
            return original(rel, data, *args, **kwargs)

        with mock.patch.object(es, "process_bytes", racing):
            mapping = es.stage(pkg, self.base / "out", True, POLICY, IDENTITY)
        row = next(r for r in mapping["files"] if r["id"] == "a.txt")
        self.assertIn("source-changed-during-staging", row["reasons"])
        self.assertEqual(mapping["verdict"], "REFUSED")


class CliTests(TempCase):
    def run_main(self, *argv) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = es.main(["--no-local-identity", "--identity-token", USER, "--identity-token", CYR,
                            "--repo-anchor", "ag_llm", *map(str, argv)])
        return code, buffer.getvalue()

    def test_scan_stage_verify_exit_codes_and_quiet_output(self):
        pkg = self.make_package(standard_package_files())
        code, out = self.run_main("scan", pkg, "--manifest")
        self.assertEqual(code, es.EXIT_REFUSED)  # leaks are present in the source package
        # results/summary/notes carry the synthetic user; report.md and tools/run.py only the repository path
        self.assertEqual(json.loads(out)["classes"], {"CLEAN": 2, "CONFIRMED": 3, "SUSPECT": 2})
        for text in (out,):
            self.assert_no_base_path(text)
            self.assertEqual(leaks(text), [])
        code, out = self.run_main("stage", pkg, "--out", self.base / "staging", "--manifest")
        self.assertEqual(code, es.EXIT_SAFE, out)
        self.assert_no_base_path(out)
        code, out = self.run_main("verify", self.base / "staging", "--package", pkg)
        self.assertEqual(code, es.EXIT_SAFE, out)
        code, out = self.run_main("scan", self.base / "staging" / "sanitized", "--manifest")
        self.assertEqual(code, es.EXIT_SAFE, out)  # the candidate's manifest describes the sanitized bytes

    def test_inventory_file_never_written_into_the_package(self):
        pkg = self.make_package({"a.txt": "alpha"})
        code, out = self.run_main("scan", pkg, "--json", pkg / "inventory.json")
        self.assertEqual(code, es.EXIT_USAGE)
        self.assertFalse((pkg / "inventory.json").exists())
        self.assert_no_base_path(out)
        target = self.base / "inventory.json"
        code, _out = self.run_main("scan", pkg, "--json", target)
        self.assertEqual(code, es.EXIT_SAFE)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["files_scanned"], 2)

    def test_errors_do_not_echo_paths(self):
        code, out = self.run_main("scan", self.base / ("missing_" + USER))
        self.assertEqual(code, es.EXIT_USAGE)
        self.assertIn("package directory not found", out)
        self.assert_no_base_path(out)
        self.assertEqual(leaks(out), [])
        code, out = self.run_main("verify", self.base)
        self.assertEqual(code, es.EXIT_USAGE)
        self.assert_no_base_path(out)

    def test_unexpected_errors_are_reported_without_paths(self):
        broken = self.base / ("broken_" + USER)
        broken.mkdir()
        (broken / "mapping.json").write_text(json.dumps({"policy": {"version": es.POLICY_VERSION}}))
        code, out = self.run_main("verify", broken)  # a schema-broken mapping is a refusal, not a crash
        self.assertEqual(code, es.EXIT_REFUSED)
        self.assert_no_base_path(out)
        pkg = self.make_package({"a.txt": "alpha"})
        boom = RuntimeError("helper failed at " + TEMP_ROOT + "\\x for " + USER)
        with mock.patch.object(es, "process_bytes", side_effect=boom):
            code, out = self.run_main("scan", pkg)  # an unexpected exception: no traceback, no path, no name
        self.assertEqual(code, es.EXIT_USAGE)
        self.assertIn("RuntimeError", out)
        self.assert_no_base_path(out)
        self.assertEqual(leaks(out), [])
        pkg = self.make_package({"a.txt": "alpha"})
        existing = self.base / "already.json"
        existing.write_text("keep")
        code, out = self.run_main("scan", pkg, "--json", existing)
        self.assertEqual(code, es.EXIT_USAGE)
        self.assertEqual(existing.read_text(), "keep")
        self.assert_no_base_path(out)

    def test_tool_revision_is_line_ending_independent(self):
        source = Path(es.__file__).read_bytes()
        self.assertEqual(es._tool_sha(), sha(source.replace(b"\r\n", b"\n")))
        pkg = self.make_package({"a.txt": "alpha"})
        mapping = es.stage(pkg, self.base / "out", True, POLICY, IDENTITY)
        self.assertEqual(mapping["tool_sha256_lf"], es._tool_sha())

    def test_module_entry_point(self):
        pkg = self.make_package({"a.txt": "alpha"})
        proc = subprocess.run([sys.executable, "-B", "-m", "web_alarm.evidence_sanitizer", "--no-local-identity",
                               "scan", str(pkg)], cwd=ROOT, capture_output=True, timeout=120)
        self.assertEqual(proc.returncode, es.EXIT_SAFE, proc.stderr[-400:])
        self.assertEqual(json.loads(proc.stdout)["classes"], {"CLEAN": 2})


class RobustnessTests(unittest.TestCase):
    def test_pathological_backslash_runs_are_bounded(self):
        texts = ["C:" + "\\" * 20000 + "x", "\\\\" * 10000 + "u", ("\\\\h" + "\\" * 50) * 400,
                 "users" + "\\" * 20000, "a\\" * 20000 + "AppData\\Local"]
        started = time.monotonic()
        for text in texts:
            es.sanitize_text(text, POLICY)
        self.assertLess(time.monotonic() - started, 20.0)


# ------------------------------------------------------------------------------------------------------------------
# CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001: F-ES-01 (manifest integrity) and F-ES-02 (bundle completeness).
# Oracles: hashlib, literal verdict strings / exit codes, and plain file / json edits of the bundle - never the
# sanitizer's own helpers. The first test of each class is the independent verifier's reproduction (RED before).

SAFE_VERDICT = "SAFE PUBLICATION CANDIDATE (needs USER GO)"


def run_cli(*argv) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = es.main(["--no-local-identity", "--identity-token", USER, "--repo-anchor", "ag_llm", *map(str, argv)])
    return code, buffer.getvalue()


def load_mapping(out: Path) -> dict:
    return json.loads((out / "mapping.json").read_text(encoding="utf-8"))


def save_mapping(out: Path, mapping: dict) -> None:
    (out / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def row_of(mapping: dict, rel: str) -> dict:
    return next(r for r in mapping["files"] if r["id"] == rel)


class ManifestIntegrityTests(TempCase):
    """F-ES-01: a manifest that does not describe the actual bytes refuses publication in stage, scan and verify."""

    def two_files(self) -> Path:
        return self.make_package({"a.txt": TEMP_ROOT + "\\a", "b.json": json.dumps({"p": TEMP_ROOT + "\\b"})})

    def edit_manifest(self, pkg: Path, mutate) -> None:
        manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
        mutate(manifest["files"])
        (pkg / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    def test_wrong_sha256_refuses_stage_and_verify(self):
        pkg = self.two_files()
        self.edit_manifest(pkg, lambda files: files["a.txt"].update(sha256="0" * 64))
        out = self.base / "out"
        mapping = es.stage(pkg, out, True, POLICY, IDENTITY)
        self.assertEqual(mapping["verdict"], "REFUSED")
        row = row_of(mapping, "a.txt")
        self.assertEqual((row["safety"], row["sanitized_id"]), ("BLOCKED", None))
        self.assertFalse((out / "sanitized" / "a.txt").exists())
        self.assertEqual(es.verify(out, pkg, IDENTITY)["publication"], "REFUSED")
        self.assertEqual(es.verify(out, None, IDENTITY)["publication"], "REFUSED")

    def test_wrong_sha256_cli_exit_codes(self):
        pkg = self.two_files()
        self.edit_manifest(pkg, lambda files: files["b.json"].update(sha256="f" * 64))
        self.assertEqual(run_cli("scan", pkg, "--manifest")[0], es.EXIT_REFUSED)
        code, out = run_cli("stage", pkg, "--out", self.base / "out", "--manifest")
        self.assertEqual(code, es.EXIT_REFUSED, out)
        self.assertEqual(run_cli("verify", self.base / "out", "--package", pkg)[0], es.EXIT_REFUSED)

    def test_wrong_size_refuses(self):
        pkg = self.two_files()
        self.edit_manifest(pkg, lambda files: files["a.txt"].update(bytes=files["a.txt"]["bytes"] + 1))
        mapping = es.stage(pkg, self.base / "out", True, POLICY, IDENTITY)
        self.assertEqual(mapping["verdict"], "REFUSED")
        self.assertIn("manifest-bytes-mismatch", row_of(mapping, "a.txt")["reasons"])

    def test_missing_or_mistyped_integrity_fields_refuse(self):
        def drop(key):
            return lambda files: files["a.txt"].pop(key)

        def put(key, value):
            return lambda files: files["a.txt"].update({key: value})

        variants = [drop("sha256"), drop("bytes"), put("sha256", 12), put("sha256", "0" * 63),
                    put("sha256", "z" * 64), put("bytes", "5"), put("bytes", True), put("bytes", -1),
                    put("bytes", 1.5), lambda files: files.update({"a.txt": "not an object"})]
        for case, mutate in enumerate(variants):
            with self.subTest(case=case):
                pkg = self.two_files()
                self.edit_manifest(pkg, mutate)
                out = self.base / ("out_%d" % case)
                mapping = es.stage(pkg, out, True, POLICY, IDENTITY)
                self.assertEqual(mapping["verdict"], "REFUSED")
                self.assertIn("manifest-entry-invalid", row_of(mapping, "a.txt")["reasons"])
                self.assertEqual(es.verify(out, pkg, IDENTITY)["publication"], "REFUSED")

    def test_unusable_manifest_refuses_before_writing(self):
        def as_list(pkg):
            (pkg / "manifest.json").write_text(json.dumps({"files": ["a.txt", "b.json"]}))

        def broken(pkg):
            (pkg / "manifest.json").write_text('{"files": {"a.txt": ')

        def duplicate_key(pkg):
            text = (pkg / "manifest.json").read_text(encoding="utf-8")
            entry = json.dumps({"bytes": 1, "sha256": "0" * 64})
            (pkg / "manifest.json").write_text(text.replace('"files": {', '"files": {"a.txt": ' + entry + ",", 1))

        def missing_file(pkg):
            (pkg / "b.json").unlink()

        def no_manifest(pkg):
            (pkg / "manifest.json").unlink()

        for case, damage in enumerate((as_list, broken, duplicate_key, missing_file, no_manifest)):
            with self.subTest(case=case):
                pkg = self.two_files()
                damage(pkg)
                out = self.base / ("refused_%d" % case)
                with self.assertRaises(es.IntegrityRefusal):
                    es.stage(pkg, out, True, POLICY, IDENTITY)
                self.assertFalse(out.exists())
                self.assertEqual(run_cli("stage", pkg, "--out", out, "--manifest")[0], es.EXIT_REFUSED)
                self.assertFalse(out.exists())

    def test_unsafe_manifest_ids_refuse(self):
        for case, rel in enumerate(("../outside.txt", "a.txt:stream", "C:/x.txt", "sub\\a.txt", "./a.txt",
                                    "sub//a.txt", "", "/abs.txt", "A.TXT")):
            with self.subTest(case=case):
                pkg = self.two_files()
                self.edit_manifest(pkg, lambda files: files.update({rel: {"bytes": 1, "sha256": "0" * 64}}))
                out = self.base / ("unsafe_%d" % case)
                with self.assertRaises(es.IntegrityRefusal):
                    es.stage(pkg, out, True, POLICY, IDENTITY)
                self.assertFalse(out.exists())

    def test_file_missing_from_manifest_is_refused(self):
        pkg = self.two_files()
        (pkg / "extra.txt").write_text("not listed")
        mapping = es.stage(pkg, self.base / "out", True, POLICY, IDENTITY)
        self.assertEqual(mapping["verdict"], "REFUSED")
        row = row_of(mapping, "extra.txt")
        self.assertEqual((row["safety"], row["sanitized_id"]), ("BLOCKED", None))
        self.assertIn("not-listed-in-manifest", row["reasons"])
        self.assertEqual(run_cli("scan", pkg, "--manifest")[0], es.EXIT_REFUSED)

    def test_manifest_changed_during_staging_refused(self):
        pkg = self.two_files()
        original = es.process_bytes

        def racing(rel, data, *args, **kwargs):
            if rel == "a.txt":
                self.edit_manifest(pkg, lambda files: files["b.json"].update(bytes=999))
            return original(rel, data, *args, **kwargs)

        with mock.patch.object(es, "process_bytes", racing):
            mapping = es.stage(pkg, self.base / "out", True, POLICY, IDENTITY)
        self.assertEqual(mapping["verdict"], "REFUSED")
        self.assertIn("source-changed-during-staging", row_of(mapping, "manifest.json")["reasons"])

    def test_mapping_cannot_be_edited_into_a_safe_candidate(self):
        pkg = self.two_files()
        self.edit_manifest(pkg, lambda files: files["a.txt"].update(sha256="0" * 64))
        out = self.base / "out"
        es.stage(pkg, out, True, POLICY, IDENTITY)
        forged = b"<TEMP>\\a"
        (out / "sanitized" / "a.txt").write_bytes(forged)
        mapping = load_mapping(out)
        row = row_of(mapping, "a.txt")
        row.update(safety="PASS", reasons=[], sanitized_id="sanitized/a.txt", sanitized_sha256=sha(forged),
                   sanitized_bytes=len(forged), changed=True, manifest_sha256_match=True)
        row.pop("manifest_check", None)
        mapping.update(files_blocked=0, verdict=SAFE_VERDICT)
        save_mapping(out, mapping)
        for package in (pkg, None):
            with self.subTest(with_package=package is not None):
                report = es.verify(out, package, IDENTITY)
                self.assertEqual((report["verdict"], report["publication"]), ("INCONSISTENT", "REFUSED"))

    def test_fully_consistent_forgery_still_fails_the_manifest_reproof(self):
        # Stage a correct package, then make the package manifest lie about a.txt and forge the bundle so that every
        # derived field agrees with the lie (preserved manifest, its row, a.txt's manifest fields). Only verify's own
        # re-check of the manifest against the preserved bytes can tell - the candidate manifest is identical.
        pkg = self.two_files()
        out = self.base / "out"
        self.assertEqual(es.stage(pkg, out, True, POLICY, IDENTITY)["verdict"], SAFE_VERDICT)
        self.edit_manifest(pkg, lambda files: files["a.txt"].update(sha256="0" * 64))
        lying = (pkg / "manifest.json").read_bytes()
        (out / "originals" / "manifest.json").write_bytes(lying)
        mapping = load_mapping(out)
        row_of(mapping, "manifest.json").update(source_sha256=sha(lying), source_bytes=len(lying),
                                                 preserved_sha256=sha(lying))
        row_of(mapping, "a.txt").update(manifest_check="MISMATCH", manifest_sha256_match=False)
        save_mapping(out, mapping)
        anchor = sha((out / "mapping.json").read_bytes())
        for package, mapping_anchor in ((pkg, None), (None, anchor)):
            with self.subTest(with_package=package is not None):
                report = es.verify(out, package, IDENTITY, mapping_anchor)
                self.assertEqual((report["verdict"], report["publication"]), ("INCONSISTENT", "REFUSED"))
                self.assertIn("map-claims-pass-but-recomputation-refuses", report["problems"])

    def test_candidate_manifest_describes_sanitized_bytes(self):
        pkg = self.make_package(standard_package_files())
        out = self.base / "out"
        mapping = es.stage(pkg, out, True, POLICY, IDENTITY)
        self.assertEqual(mapping["verdict"], SAFE_VERDICT)
        self.assertEqual((out / "originals" / "manifest.json").read_bytes(), (pkg / "manifest.json").read_bytes())
        candidate = json.loads((out / "sanitized" / "manifest.json").read_text(encoding="utf-8"))
        for rel in standard_package_files():
            data = (out / "sanitized" / rel).read_bytes()
            self.assertEqual(candidate["files"][rel], {"bytes": len(data), "sha256": sha(data)})
        self.assertEqual(run_cli("scan", out / "sanitized", "--manifest")[0], es.EXIT_SAFE)


class BundleCompletenessTests(TempCase):
    """F-ES-02: verify proves source -> manifest/selection -> originals -> mapping -> sanitized as a whole set."""

    def staged(self, files=None, use_manifest=True) -> tuple[Path, Path]:
        pkg = self.make_package(files or {"a.txt": TEMP_ROOT + "\\a", "b.txt": "beta"}, manifest=use_manifest)
        out = self.base / ("out_" + uuid.uuid4().hex[:6])
        self.assertEqual(es.stage(pkg, out, use_manifest, POLICY, IDENTITY)["verdict"], SAFE_VERDICT)
        return pkg, out

    def test_deleted_row_and_sanitized_copy_is_refused(self):
        pkg, out = self.staged()
        mapping = load_mapping(out)
        mapping["files"] = [r for r in mapping["files"] if r["id"] != "b.txt"]
        save_mapping(out, mapping)
        (out / "sanitized" / "b.txt").unlink()
        for package in (pkg, None):
            with self.subTest(with_package=package is not None):
                report = es.verify(out, package, IDENTITY)
                self.assertEqual(report["publication"], "REFUSED")
                self.assertNotEqual(report["problems"], {})
        self.assertEqual(run_cli("verify", out, "--package", pkg)[0], es.EXIT_REFUSED)
        self.assertEqual(run_cli("verify", out)[0], es.EXIT_REFUSED)

    def test_fully_removed_file_is_caught_against_source_and_unproven_without(self):
        for use_manifest in (True, False):
            with self.subTest(manifest=use_manifest):
                pkg, out = self.staged(use_manifest=use_manifest)
                mapping = load_mapping(out)
                mapping["files"] = [r for r in mapping["files"] if r["id"] != "b.txt"]
                mapping["files_total"] -= 1
                save_mapping(out, mapping)
                (out / "sanitized" / "b.txt").unlink()
                (out / "originals" / "b.txt").unlink()
                with_source = es.verify(out, pkg, IDENTITY)
                self.assertEqual(with_source["publication"], "REFUSED")
                self.assertIn("package-inventory-differs", with_source["problems"])
                alone = es.verify(out, None, IDENTITY)
                self.assertEqual((alone["publication"], alone["completeness"]), ("REFUSED", "NOT_PROVEN"))

    def test_external_mapping_anchor_proves_completeness(self):
        pkg, out = self.staged()
        anchor = sha((out / "mapping.json").read_bytes())
        self.assertEqual(es.verify(out, None, IDENTITY)["publication"], "REFUSED")  # nothing trusted to compare
        report = es.verify(out, None, IDENTITY, anchor)
        self.assertEqual((report["publication"], report["completeness"]),
                         ("SAFE CANDIDATE", "PROVEN_BY_EXTERNAL_MAPPING_SHA256"))
        self.assertEqual(run_cli("verify", out, "--mapping-sha256", anchor)[0], es.EXIT_SAFE)
        mapping = load_mapping(out)
        mapping["package"] = "renamed"
        save_mapping(out, mapping)
        tampered = es.verify(out, None, IDENTITY, anchor)
        self.assertEqual(tampered["publication"], "REFUSED")
        self.assertIn("mapping-anchor-mismatch", tampered["problems"])

    def test_metadata_tampering_is_detected(self):
        def total(m):
            m["files_total"] += 1

        def blocked(m):
            m["files_blocked"] = 1

        def changed_total(m):
            m["files_changed"] = 0

        def verdict(m):
            m["verdict"] = "REFUSED"

        def selection(m):
            m["selection"] = "all-files"

        def bad_selection(m):
            m["selection"] = "everything"

        def weaker_policy(m):
            m["policy"]["protected_keys"] = []

        def anchor_users(m):
            m["policy"]["repo_anchors"] = ["users"]

        def duplicate_row(m):
            m["files"].append(dict(m["files"][0]))

        def case_duplicate(m):
            m["files"].append(dict(m["files"][0], id=m["files"][0]["id"].upper()))

        def traversal(m):
            m["files"][0]["id"] = "../outside.txt"

        def unknown_safety(m):
            m["files"][0]["safety"] = "MAYBE"

        def flag_flip(m):
            row_of(m, "b.txt")["changed"] = True

        def sha_type(m):
            m["files"][0]["source_sha256"] = 7

        def files_not_list(m):
            m["files"] = {}

        for case, mutate in enumerate((total, blocked, changed_total, verdict, selection, bad_selection,
                                       weaker_policy, anchor_users, duplicate_row, case_duplicate, traversal,
                                       unknown_safety, flag_flip, sha_type, files_not_list)):
            with self.subTest(case=case):
                pkg, out = self.staged()
                mapping = load_mapping(out)
                mutate(mapping)
                save_mapping(out, mapping)
                report = es.verify(out, pkg, IDENTITY)
                self.assertEqual((report["verdict"], report["publication"]), ("INCONSISTENT", "REFUSED"))

    def test_traversal_id_never_reads_outside_the_bundle(self):
        pkg, out = self.staged()
        outside = self.base / "outside.txt"
        outside.write_text("alpha")
        mapping = load_mapping(out)
        # originals/../../outside.txt is exactly the file planted next to the bundle, with a matching hash
        mapping["files"][0].update(id="../../outside.txt", source_sha256=sha(b"alpha"), source_bytes=5)
        save_mapping(out, mapping)
        self.assertEqual((out / "originals" / "../../outside.txt").resolve(), outside.resolve())
        with mock.patch.object(es, "process_bytes", wraps=es.process_bytes) as spy:
            report = es.verify(out, pkg, IDENTITY)
        self.assertEqual(report["publication"], "REFUSED")
        self.assertNotIn("../../outside.txt", [c.args[0] for c in spy.call_args_list])

    def test_leftovers_and_partial_bundles(self):
        pkg, out = self.staged()
        (out / "mapping.json.tmp").write_text("{}")
        self.assertIn("unexpected-bundle-entries", es.verify(out, pkg, IDENTITY)["problems"])
        (out / "mapping.json.tmp").unlink()
        (out / "mapping.json").unlink()
        with self.assertRaises(es.EvidenceError):
            es.verify(out, pkg, IDENTITY)

    @unittest.skipUnless(sys.platform == "win32", "junctions are a Windows feature")
    def test_junction_inside_bundle_is_refused(self):
        import _winapi
        pkg, out = self.staged()
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "c.txt").write_text("gamma")
        _winapi.CreateJunction(str(elsewhere), str(out / "sanitized" / "linked"))
        report = es.verify(out, pkg, IDENTITY)
        self.assertEqual(report["publication"], "REFUSED")
        self.assertIn("link-in-bundle", report["problems"])

    def test_all_files_selection_compares_the_whole_source_inventory(self):
        for damage in ("added", "removed"):
            with self.subTest(damage=damage):
                pkg, out = self.staged(use_manifest=False)
                if damage == "added":
                    (pkg / "late.txt").write_text("late")
                else:
                    (pkg / "b.txt").unlink()
                report = es.verify(out, pkg, IDENTITY)
                self.assertEqual(report["publication"], "REFUSED")
                self.assertIn("package-inventory-differs", report["problems"])

    def test_valid_bundles_pass_in_both_selection_modes(self):
        for case, (files, use_manifest) in enumerate(((None, True), (None, False),
                                                      (standard_package_files(), True),
                                                      (standard_package_files(), False))):
            with self.subTest(case=case):
                pkg, out = self.staged(files, use_manifest)
                report = es.verify(out, pkg, IDENTITY)
                self.assertEqual((report["verdict"], report["publication"], report["problems"],
                                  report["completeness"]),
                                 ("CONSISTENT", "SAFE CANDIDATE", {}, "PROVEN_AGAINST_PACKAGE"))
                self.assertEqual(run_cli("verify", out, "--package", pkg)[0], es.EXIT_SAFE)
                self.assertEqual(run_cli("verify", out)[0], es.EXIT_REFUSED)  # completeness not provable alone

    def test_deeply_nested_json_is_refused_without_crashing(self):
        deep = "[" * 5000 + "]" * 5000  # beyond the JSON decoder's recursion limit
        r = es.process_bytes("deep.json", deep.encode(), POLICY, IDENTITY)
        self.assertEqual((r.safety, r.output), ("BLOCKED", None))
        pkg = self.make_package({"a.txt": "alpha"})
        (pkg / "manifest.json").write_text('{"files": ' + deep + "}")
        with self.assertRaises(es.IntegrityRefusal):
            es.stage(pkg, self.base / "deep_out", True, POLICY, IDENTITY)
        pkg, out = self.staged()
        (out / "mapping.json").write_text(deep)
        report = es.verify(out, pkg, IDENTITY)
        self.assertEqual(report["publication"], "REFUSED")
        self.assertIn("mapping-invalid", report["problems"])

    def test_local_name_in_a_file_name_is_refused(self):
        name = "runs/notes-" + USER + ".txt"
        pkg = self.make_package({"a.txt": "alpha", name: "clean content"})
        mapping = es.stage(pkg, self.base / "out", True, POLICY, IDENTITY)
        self.assertEqual(mapping["verdict"], "REFUSED")
        row = row_of(mapping, name)
        self.assertEqual((row["safety"], row["sanitized_id"]), ("BLOCKED", None))
        self.assertIn("identity-in-file-name", row["reasons"])
        self.assertFalse((self.base / "out" / "sanitized" / name).exists())
        # the manifest lists that name in its own content, so it is refused too (by the content gate)
        self.assertIn("residual-identity", row_of(mapping, "manifest.json")["reasons"])
        code, out = run_cli("scan", pkg, "--manifest")
        self.assertEqual(code, es.EXIT_REFUSED)
        self.assertEqual(json.loads(out)["classes"].get("CONFIRMED"), 2)

    def test_unsafe_repo_anchor_is_refused_in_stage_and_cli(self):
        pkg = self.make_package({"a.txt": HOME_ROOT + "\\x"})
        for case, anchor in enumerate(("users", "AppData", "Temp", "", "a/b", "C:", "Program Files")):
            with self.subTest(case=case):
                out = self.base / ("anchor_%d" % case)
                with self.assertRaises(es.EvidenceError):
                    es.stage(pkg, out, True, es.Policy((anchor,)), IDENTITY)
                self.assertFalse(out.exists())
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = es.main(["--no-local-identity", "--repo-anchor", "users", "scan", str(pkg)])
        self.assertEqual(code, es.EXIT_USAGE)

    # REVISE F-ES-03: the --package anchor must be independent of the bundle it is supposed to prove complete.
    def assert_not_independent(self, out, package):
        report = es.verify(out, package, IDENTITY)
        self.assertEqual(report["publication"], "REFUSED")
        self.assertNotEqual(report["completeness"], "PROVEN_AGAINST_PACKAGE")
        self.assertIn("package-not-independent", report["problems"])

    def test_bundle_internal_folder_is_not_an_independent_package(self):
        for use_manifest in (True, False):
            with self.subTest(manifest=use_manifest):
                _pkg, out = self.staged(use_manifest=use_manifest)
                self.assert_not_independent(out, out / "originals")  # the verifier's reproduction
                self.assert_not_independent(out, out / "sanitized" / ".." / "originals")  # non-canonical spelling
                self.assert_not_independent(out, out)
                self.assertEqual(run_cli("verify", out, "--package", out / "originals")[0], es.EXIT_REFUSED)

    @unittest.skipUnless(sys.platform == "win32", "case-insensitive paths are a Windows property")
    def test_case_variant_spelling_is_the_same_folder(self):
        _pkg, out = self.staged()
        self.assert_not_independent(out, Path(str(out / "originals").upper()))

    @unittest.skipUnless(sys.platform == "win32", "extended-length paths are a Windows spelling")
    def test_extended_length_spelling_is_the_same_folder(self):
        _pkg, out = self.staged()
        extended = Path("\\\\?\\" + str((out / "originals").resolve()))
        self.assertTrue(extended.is_dir())
        self.assert_not_independent(out, extended)
        # the bundle root itself: no file ids in common, so only the path comparison can tell
        self.assert_not_independent(out, Path("\\\\?\\" + str(out.resolve())))

    def test_bundle_inside_the_package_is_not_independent(self):
        pkg, out = self.staged()
        nested = pkg.parent / "outer"
        shutil.copytree(out, nested / "bundle")
        for rel in ("a.txt", "b.txt", "manifest.json"):
            shutil.copy2(pkg / rel, nested / rel)
        self.assert_not_independent(nested / "bundle", nested)

    @unittest.skipUnless(sys.platform == "win32", "junctions are a Windows feature")
    def test_junction_to_the_bundle_is_not_independent(self):
        import _winapi
        _pkg, out = self.staged()
        alias = self.base / "looks_external"
        _winapi.CreateJunction(str(out / "originals"), str(alias))
        self.assert_not_independent(out, alias)

    def test_hard_linked_copy_of_the_originals_is_not_independent(self):
        _pkg, out = self.staged()
        clone = self.base / "hardlinked"
        for path in sorted((out / "originals").rglob("*")):
            if path.is_file():
                target = clone / path.relative_to(out / "originals")
                target.parent.mkdir(parents=True, exist_ok=True)
                os.link(path, target)
        self.assert_not_independent(out, clone)

    def test_independent_package_and_mapping_anchor_still_prove_completeness(self):
        pkg, out = self.staged()
        copy = self.base / "independent_copy"
        shutil.copytree(pkg, copy)  # a real copy elsewhere is a legitimate source
        for package in (pkg, copy):
            with self.subTest(package=package.name[:4]):
                report = es.verify(out, package, IDENTITY)
                self.assertEqual((report["publication"], report["completeness"]),
                                 ("SAFE CANDIDATE", "PROVEN_AGAINST_PACKAGE"))
        anchor = sha((out / "mapping.json").read_bytes())
        self.assertEqual(es.verify(out, None, IDENTITY, anchor)["publication"], "SAFE CANDIDATE")
        refused = es.verify(out, out / "originals", IDENTITY, anchor)  # a valid anchor does not excuse a self-package
        self.assertEqual(refused["publication"], "REFUSED")
        self.assertIn("package-not-independent", refused["problems"])

    def test_mapping_without_optional_new_fields_still_verifies(self):
        pkg, out = self.staged()
        mapping = load_mapping(out)
        for row in mapping["files"]:
            row.pop("manifest_check", None)
        save_mapping(out, mapping)
        self.assertEqual(es.verify(out, pkg, IDENTITY)["publication"], "SAFE CANDIDATE")


if __name__ == "__main__":
    unittest.main()
