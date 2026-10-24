"""Which temp root does the guarded child of test_web_alarm_runner_guard really use, and where does a write land?

Builds the same fixture as the test (base/inner, base/outside, base/guard/sitecustomize.py = the real GUARD from
wa4a_acceptance.py of the given code root) and starts a child exactly like the test's child() does, in two env
variants:
  old   - the env the published test built: PYTHON* removed, TMP/TEMP = inner, everything else inherited (TMPDIR too)
  fixed - the same, plus TMPDIR = inner
In the child: tempfile.gettempdir(), the guard's own _audit_temp, then one write to base/outside/probe.txt. Reported:
the roots relative to base / the parent temp, the outcome, and whether the file physically exists afterwards.
Run it with and without TMPDIR in the parent environment. Usage: probe_child_root.py <code-root> <out.json>
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

code_root, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
sys.path.insert(0, str(code_root))
import wa4a_acceptance  # noqa: E402  (the GUARD text of the code under test)

CHILD = r'''
import json, os, sys, tempfile
import sitecustomize
target = sys.argv[1]
try:
    with open(target, "wb") as handle:
        handle.write(b"x")
    outcome = "allowed"
except PermissionError as exc:
    outcome = "blocked" if str(exc).startswith("WA4-A isolation") else "oserror"
print("RESULT " + json.dumps({"gettempdir": tempfile.gettempdir(), "audit_temp": str(sitecustomize._audit_temp),
                              "outcome": outcome}))
'''


def where(path: str, base: Path, parent_temp: Path) -> str:
    p = os.path.normcase(os.path.abspath(path))
    for name, root in (("<BASE>/inner", base / "inner"), ("<BASE>", base), ("<PARENT-TEMP>", parent_temp)):
        r = os.path.normcase(str(root))
        if p == r:
            return name
        if p.startswith(r + os.sep):
            return name + "/" + p[len(r) + 1:].replace(os.sep, "/")
    return "<OTHER>"


parent_temp = Path(tempfile.gettempdir()).resolve()
result = {"parent_env": {k: ("set" if os.environ.get(k) else "unset") for k in ("TMPDIR", "TEMP", "TMP")},
          "parent_gettempdir": "<PARENT-TEMP>", "variants": {}}
for variant in ("old", "fixed"):
    base = Path(tempfile.mkdtemp(prefix="wa_guard_probe_")).resolve()
    try:
        inner, outside, guard = base / "inner", base / "outside", base / "guard"
        for folder in (inner, outside, guard):
            folder.mkdir()
        (guard / "sitecustomize.py").write_text(wa4a_acceptance.GUARD, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
        env.update(PYTHONPATH=str(guard), PYTHONDONTWRITEBYTECODE="1", TMP=str(inner), TEMP=str(inner),
                   WA4A_GUARD_LOG=str(inner / "guard.jsonl"))
        if variant == "fixed":
            env["TMPDIR"] = str(inner)
        target = outside / "probe.txt"
        proc = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", CHILD, str(target)], env=env,
                              capture_output=True, timeout=60)
        [line] = [x for x in proc.stdout.decode("utf-8").splitlines() if x.startswith("RESULT ")]
        child = json.loads(line[len("RESULT "):])
        log = inner / "guard.jsonl"
        result["variants"][variant] = {
            "child_TMPDIR": "inner" if env.get("TMPDIR") == str(inner) else ("inherited" if env.get("TMPDIR") else "unset"),
            "child_gettempdir": where(child["gettempdir"], base, parent_temp),
            "guard_root": where(child["audit_temp"], base, parent_temp),
            "write_to": where(str(target), base, parent_temp), "outcome": child["outcome"],
            "file_exists_after": target.exists(),
            "guard_violation_lines": len(log.read_text(encoding="utf-8").splitlines()) if log.exists() else 0,
            "child_exit": proc.returncode}
    finally:
        shutil.rmtree(base, ignore_errors=True)
out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(result, indent=1, sort_keys=True))
