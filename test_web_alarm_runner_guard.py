"""F-T1: the WA4-A runner isolation guard (``wa4a_acceptance.GUARD``) on Windows path spellings and real races.

Every case runs the real GUARD source as the sitecustomize of a fresh child Python whose TMPDIR/TEMP/TMP is a private
``inner`` folder (checked: the child reports the root its guard really uses), so "outside" is a sibling folder that is
still inside the real disposable TEMP: even a broken guard cannot write anywhere else. Oracles are independent of the guard's decision code: the child's per-operation outcome
(``WA4-A isolation`` PermissionError or not), the number of lines in the guard's own violation log, and the files that
really exist afterwards.

Root cause reproduced by these tests (see the task report): ``Path.resolve()`` (ntpath.realpath) adds ``\\\\?\\`` while
it resolves a path that does not exist yet and strips it again only if a second lookup fails with the same Windows
error; when another process creates the missing parent in between (error 3 then 2), the prefix stays and the TEMP
comparison fails. A folder removed while it is resolved resolves into ``<drive>:\\$Extend\\$Deleted``.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import wa4a_acceptance

CHILD = r'''
import ctypes, json, ntpath, os, sys, threading, time
cfg = json.loads(open(sys.argv[1], encoding="utf-8").read())
real = ntpath._getfinalpathname
create_dir = ctypes.windll.kernel32.CreateDirectoryW  # not audited: plays the other process, not the guarded one


def injected(kind, at):
    state = {"failed": 0, "deleted": 0}

    def wrapper(path):
        try:
            value = real(path)
        except OSError:
            state["failed"] += 1
            if state["failed"] == 1 and kind == "parent_created_between_lookups":
                if not create_dir(at, None):
                    raise RuntimeError("injection could not create the folder")
            raise
        if kind in ("deleted_once", "deleted_always") and os.path.normcase(path) == os.path.normcase(at):
            state["deleted"] += 1
            if kind == "deleted_always" or state["deleted"] == 1:
                # synthetic answer of the shape Windows gives for a folder removed while it is open
                return "\\\\?\\" + value[4:6] + "\\$Extend\\$Deleted\\0123456789ABCDEF01234567"
        return value
    return wrapper


def run(op):
    kind = op["op"]
    if op.get("cwd"):
        os.chdir(op["cwd"])
    if op.get("inject"):
        ntpath._getfinalpathname = injected(op["inject"], op["at"])
    try:
        if kind == "write":
            with open(op["path"], "wb") as handle:
                handle.write(b"x")
        elif kind == "read":
            with open(op["path"], "rb") as handle:
                handle.read()
        elif kind == "mkdir":
            os.mkdir(op["path"])
        elif kind == "replace":
            os.replace(op["path"], op["path2"])
        return {"outcome": "allowed"}
    except PermissionError as exc:
        return {"outcome": "blocked" if str(exc).startswith("WA4-A isolation") else "oserror:PermissionError"}
    except OSError as exc:
        return {"outcome": "oserror:" + type(exc).__name__}
    finally:
        ntpath._getfinalpathname = real


def race(op):
    folder, stop = op["dir"], threading.Event()
    target = os.path.join(folder, "d", "f.txt")

    def churn():
        while not stop.is_set():
            if create_dir(os.path.join(folder, "d"), None):
                ctypes.windll.kernel32.RemoveDirectoryW(os.path.join(folder, "d"))
    worker = threading.Thread(target=churn, daemon=True)
    worker.start()
    # "r+b" is a write for the guard, but the file never exists, so nothing stays behind to stop the churn
    counts = {"passed_guard": 0, "blocked": 0, "iterations": 0}
    deadline = time.monotonic() + op["seconds"]
    while counts["iterations"] < op["iterations"] and time.monotonic() < deadline:
        counts["iterations"] += 1
        try:
            with open(target, "r+b"):
                pass
            counts["passed_guard"] += 1
        except PermissionError as exc:
            counts["blocked" if str(exc).startswith("WA4-A isolation") else "passed_guard"] += 1
        except OSError:
            counts["passed_guard"] += 1
    stop.set()
    worker.join(10)
    return counts


import sitecustomize, tempfile  # the guard this child really runs under, and the root it really allows
out = {"_root": {"guard": str(sitecustomize._audit_temp), "gettempdir": tempfile.gettempdir()}}
for op in cfg["ops"]:
    out[op["name"]] = race(op) if op["op"] == "race" else run(op)
sys.stdout.write("RESULT " + json.dumps(out) + "\n")  # stdout: the child may write nowhere outside its own temp
'''


@unittest.skipUnless(os.name == "nt", "F-T1 is a Windows path-resolution race")
class RunnerGuardTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_guard_")).resolve()
        self.addCleanup(self._cleanup, self.base)
        self.inner, self.outside = self.base / "inner", self.base / "outside"
        self.inner.mkdir()
        self.outside.mkdir()
        self.guard_dir = self.base / "guard"
        self.guard_dir.mkdir()
        (self.guard_dir / "sitecustomize.py").write_text(wa4a_acceptance.GUARD, encoding="utf-8")
        self.log = self.inner / "guard.jsonl"
        self.facts = [{"task": "CLAUDE-WA4-R-FT1-ARCHIVE-RETRY-001", "test": self.id()}]
        self.calls = 0

    @staticmethod
    def _cleanup(base: Path):
        for path in base.rglob("*"):
            if path.is_junction():
                os.rmdir(path)
        shutil.rmtree(base, ignore_errors=True)

    def child(self, ops: list[dict], parent_env: dict[str, str] | None = None) -> tuple[dict, int]:
        """Run ops in a guarded child whose allowed root must be exactly ``inner``.

        tempfile (and so the guard) takes the first of TMPDIR, TEMP, TMP: all three are set, and the child reports
        the root its guard really uses. CI sets TMPDIR (FT1-CI-REPAIR: an inherited TMPDIR made the child guard
        protect the runner's TEMP instead of ``inner``, so every "outside" fixture counted as inside).
        """
        self.calls += 1
        cfg = self.base / f"cfg_{self.calls}.json"
        cfg.write_text(json.dumps({"ops": ops}), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
        env.update(parent_env or {})
        env.update(PYTHONPATH=str(self.guard_dir), PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(self.inner),
                   TMP=str(self.inner), TEMP=str(self.inner), WA4A_GUARD_LOG=str(self.log))
        proc = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", CHILD, str(cfg)], env=env,
                              capture_output=True, timeout=120)
        if proc.returncode != 0:
            self.facts.append({"child_exit": proc.returncode, "child_stderr_tail": proc.stderr.decode(errors="replace")[-600:]})
        self.assertEqual(proc.returncode, 0, "the guarded child did not finish")
        violations = len([line for line in self.log.read_text(encoding="utf-8").splitlines() if line.strip()]) \
            if self.log.exists() else 0
        [line] = [x for x in proc.stdout.decode("utf-8").splitlines() if x.startswith("RESULT ")]
        results = json.loads(line[len("RESULT "):])
        root = results.pop("_root")
        inner = os.path.normcase(str(self.inner))
        self.facts.append({"child_root_is_inner": {k: os.path.normcase(v) == inner for k, v in root.items()}})
        self.assertEqual(os.path.normcase(root["guard"]), inner, "the child's guard does not protect its own temp")
        self.assertEqual(os.path.normcase(root["gettempdir"]), inner, "the child's tempfile root is not its own temp")
        return results, violations

    def shapes(self) -> dict[str, int]:
        """Masked form of every guard violation reason: the fixture folder and NTFS ids never leave the test."""
        found: dict[str, int] = {}
        if not self.log.exists():
            return found
        base = str(self.base).lower()
        for line in self.log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            reason = json.loads(line)["reason"]
            low = reason.lower()
            at = low.find(base)
            shape = (reason[:at] + "<BASE>" + reason[at + len(base):]) if at >= 0 else reason
            shape = re.sub(r"(?i)\$deleted\\[0-9a-f]+", r"$Deleted\\<ID>", shape.replace("\\\\?\\", "<PREFIX>"))
            if "<BASE>" not in shape and "$Deleted" not in shape:
                shape = "<OTHER-FORM>"
            found[shape] = found.get(shape, 0) + 1
        return found

    def check(self, ops: list[dict], expected: dict[str, str], parent_env: dict[str, str] | None = None):
        results, violations = self.child(ops, parent_env)
        self.facts.append({"outcomes": {name: r["outcome"] for name, r in results.items()},
                           "guard_violation_lines": violations})
        for name, outcome in expected.items():
            with self.subTest(name):
                self.assertEqual(results[name]["outcome"], outcome)
        self.assertEqual(violations, list(expected.values()).count("blocked"),
                         "the guard log does not match the refused operations")
        return results

    def test_equivalent_spellings_inside_temp_are_allowed(self):
        inner = str(self.inner)
        (self.inner / "a").mkdir()
        ops = [{"name": "plain", "op": "write", "path": inner + "\\plain.txt"},
               {"name": "case", "op": "write", "path": inner.upper() + "\\CASE.txt"},
               {"name": "forward_slashes", "op": "write", "path": inner.replace("\\", "/") + "/slash.txt"},
               {"name": "dot_and_dotdot", "op": "write", "path": inner + "\\a\\..\\.\\a\\dot.txt"},
               {"name": "relative", "op": "write", "path": "rel.txt", "cwd": inner},
               {"name": "trailing_dot", "op": "write", "path": inner + "\\trail.txt."},
               {"name": "mkdir", "op": "mkdir", "path": inner + "\\made"},
               {"name": "replace_inside", "op": "replace", "path": inner + "\\plain.txt",
                "path2": inner + "\\a\\moved.txt"}]
        self.check(ops, {op["name"]: "allowed" for op in ops})
        self.assertEqual(sorted(p.name for p in self.inner.rglob("*.txt")),
                         ["CASE.txt", "dot.txt", "moved.txt", "rel.txt", "slash.txt", "trail.txt"])

    def test_short_8dot3_spelling_of_temp_is_allowed(self):
        import ctypes
        buffer = ctypes.create_unicode_buffer(1024)
        length = ctypes.windll.kernel32.GetShortPathNameW(str(self.inner), buffer, 1024)
        short = buffer.value if length else ""
        if not short or os.path.normcase(short) == os.path.normcase(str(self.inner)):
            self.skipTest("this volume has no 8.3 short names for the temp folder: NOT RUN")
        self.check([{"name": "short", "op": "write", "path": short + "\\short.txt"}], {"short": "allowed"})
        self.assertTrue((self.inner / "short.txt").exists())

    def test_every_escape_from_temp_is_still_refused_and_writes_nothing(self):
        import _winapi
        inner, outside = str(self.inner), str(self.outside)
        (self.inner / "src.txt").write_bytes(b"s")
        (self.outside / "gone").mkdir()
        (self.inner / "kept").mkdir()  # resolves into $Deleted on every lookup: e.g. a junction into NTFS metadata
        _winapi.CreateJunction(outside, str(self.inner / "jx"))
        ops = [{"name": "sibling", "op": "write", "path": outside + "\\f1.txt"},
               {"name": "dotdot", "op": "write", "path": inner + "\\..\\outside\\f2.txt"},
               {"name": "dotdot_slashes_case", "op": "write", "path": (inner + "/../OUTSIDE/f3.txt").replace("\\", "/")},
               {"name": "extended_outside", "op": "write", "path": "\\\\?\\" + outside + "\\f4.txt"},
               {"name": "extended_inside_stays_strict", "op": "write", "path": "\\\\?\\" + inner + "\\f5.txt"},
               {"name": "junction", "op": "write", "path": inner + "\\jx\\f6.txt"},
               {"name": "replace_out", "op": "replace", "path": inner + "\\src.txt", "path2": outside + "\\f7.txt"},
               {"name": "mkdir_out", "op": "mkdir", "path": outside + "\\made"},
               {"name": "race_injection_outside", "op": "write", "path": outside + "\\new\\f8.txt",
                "inject": "parent_created_between_lookups", "at": outside + "\\new"},
               {"name": "deleted_once_outside", "op": "write", "path": outside + "\\gone\\f9.txt",
                "inject": "deleted_once", "at": outside + "\\gone"},
               {"name": "always_deleted_inside_stays_strict", "op": "write", "path": inner + "\\kept\\f10.txt",
                "inject": "deleted_always", "at": inner + "\\kept"},
               {"name": "git_metadata_read", "op": "read", "path": inner + "\\.git\\config"}]
        self.check(ops, {op["name"]: "blocked" for op in ops})
        self.assertEqual(sorted(p.name for p in self.outside.rglob("*")), ["gone", "new"],
                         "a refused operation left a file outside temp")
        self.assertEqual(sorted(p.name for p in self.inner.rglob("f*.txt")), [])
        self.assertTrue((self.inner / "src.txt").exists())

    def test_child_guard_protects_its_own_temp_even_when_the_parent_sets_tmpdir(self):
        # the CI shape (TMPDIR = TEMP = TMP = runner temp) reproduced here, whatever this host's environment is
        outer = str(self.base)
        results = self.check([{"name": "sibling", "op": "write", "path": str(self.outside) + "\\f1.txt"},
                              {"name": "inside", "op": "write", "path": str(self.inner) + "\\f2.txt"}],
                             {"sibling": "blocked", "inside": "allowed"},
                             parent_env={"TMPDIR": outer, "TEMP": outer, "TMP": outer})
        self.assertEqual(sorted(p.name for p in self.outside.iterdir()), [], "a refused write left a file outside")
        self.assertTrue((self.inner / "f2.txt").exists())
        self.assertEqual(set(results), {"sibling", "inside"})

    def test_folder_created_by_another_process_between_lookups_is_not_a_violation(self):
        inner = str(self.inner)
        ops = [{"name": "write_below_new_folder", "op": "write", "path": inner + "\\new\\f.txt",
                "inject": "parent_created_between_lookups", "at": inner + "\\new"},
               {"name": "mkdir_below_new_folder", "op": "mkdir", "path": inner + "\\new2\\sub",
                "inject": "parent_created_between_lookups", "at": inner + "\\new2"}]
        self.check(ops, {"write_below_new_folder": "allowed", "mkdir_below_new_folder": "allowed"})
        self.assertTrue((self.inner / "new" / "f.txt").exists())
        self.assertTrue((self.inner / "new2" / "sub").is_dir())

    def test_folder_resolving_into_deleted_once_is_not_a_violation_inside_temp(self):
        (self.inner / "gone").mkdir()
        ops = [{"name": "write_below_deleted_once", "op": "write", "path": str(self.inner) + "\\gone\\f.txt",
                "inject": "deleted_once", "at": str(self.inner) + "\\gone"}]
        self.check(ops, {"write_below_deleted_once": "allowed"})
        self.assertTrue((self.inner / "gone" / "f.txt").exists())

    def test_real_mkdir_rmdir_race_never_produces_a_false_violation(self):
        (self.inner / "race").mkdir()
        results, violations = self.child([{"name": "race", "op": "race", "dir": str(self.inner / "race"),
                                           "iterations": 3000, "seconds": 20.0}])
        counts = results["race"]
        self.facts.append({"race": counts, "guard_violation_lines": violations, "shapes": self.shapes()})
        self.assertEqual(counts["passed_guard"] + counts["blocked"], counts["iterations"])
        self.assertGreater(counts["iterations"], 500, "the race loop barely ran: the test proves nothing")
        self.assertEqual((counts["blocked"], violations), (0, 0), "false isolation violation inside temp")
        self.assertEqual(sorted(p.name for p in self.outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
