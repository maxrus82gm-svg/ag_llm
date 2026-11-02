"""Run pytest-style test files of this task in isolation and record a path-free result.

test_run_store_v2.py is pytest-style (tmp_path/monkeypatch), so the unittest-only guarded runner wa4a_acceptance.py
cannot collect it. Isolation here: a fresh TEMP folder per run holds pytest's --basetemp, LOCALAPPDATA, APPDATA,
USERPROFILE/HOME and PYTHONPYCACHEPREFIX; python -B and PYTHONDONTWRITEBYTECODE=1 (no .pyc in the repository);
-p no:cacheprovider (the repository .pytest_cache is not touched); the working folder is the repository (imports).
The repository-root entries are listed before and after: nothing may be created or changed there by the run.
Results come from pytest's JUnit XML. Usage: run_pytest.py <purpose> <out.json> <selector> [<selector> ...]
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(os.environ.get("P9_CODE_ROOT") or Path(__file__).resolve().parents[3])


def root_state() -> dict:
    """Name, kind and mtime of every repository-root entry plus the content hash of root files (no recursion)."""
    state = {}
    for entry in os.scandir(REPO):
        st = os.lstat(entry.path)
        if entry.is_file(follow_symlinks=False):
            state[entry.name] = ("file", st.st_mtime_ns, hashlib.sha256(Path(entry.path).read_bytes()).hexdigest())
        else:
            state[entry.name] = ("dir", st.st_mtime_ns)
    return state


def main():
    purpose, target, selectors = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
    base = Path(tempfile.mkdtemp(prefix="p9-pytest-")).resolve()
    for name in ("localappdata", "appdata", "home", "basetemp", "pycache"):
        (base / name).mkdir()
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "GIT_", "PYTEST"))}
    env.update(LOCALAPPDATA=str(base / "localappdata"), APPDATA=str(base / "appdata"), USERPROFILE=str(base / "home"),
               HOME=str(base / "home"), PYTHONDONTWRITEBYTECODE="1", PYTHONPYCACHEPREFIX=str(base / "pycache"),
               PYTHONIOENCODING="utf-8")
    junit = base / "junit.xml"
    before = root_state()
    started = time.time()
    done = subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q", "-rs",
                           f"--basetemp={base / 'basetemp'}", f"--junitxml={junit}", *selectors],
                          cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    wall = round(time.time() - started, 1)
    after = root_state()
    changed_root = sorted(k for k in set(before) | set(after)
                          if before.get(k) != after.get(k) and not (before.get(k, ("",))[0] == "dir" == after.get(k, ("",))[0]
                                                                     and k in {"__pycache__"}))
    tests = []
    if junit.is_file():
        for case in ET.parse(junit).getroot().iter("testcase"):
            status = "PASS"
            detail = ""
            for tag, label in (("failure", "FAIL"), ("error", "ERROR"), ("skipped", "SKIP")):
                node = case.find(tag)
                if node is not None:
                    status = label
                    detail = (node.get("message") or "").splitlines()[0][:200] if node.get("message") else ""
                    break
            row = {"test": f"{case.get('classname')}.{case.get('name')}", "status": status}
            if detail:
                row["detail"] = detail.replace(str(base), "<tmp>").replace(str(REPO), "<repo>")
            tests.append(row)
    counts = {s: sum(1 for t in tests if t["status"] == s) for s in ("PASS", "FAIL", "ERROR", "SKIP")}
    record = {"task": "CLAUDE-WUA-CHAT-RUNSTORE-P9-001", "purpose": purpose, "runner": "pytest via .venv (isolated, see tool docstring)",
              "selectors": selectors, "exit": done.returncode, "wall_seconds": wall, "tests_run": len(tests),
              "passed": counts["PASS"], "failures": counts["FAIL"], "errors": counts["ERROR"], "skips": counts["SKIP"],
              "repository_root_changed": changed_root, "tests": tests}
    assert len(tests) == sum(counts.values())
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    shutil.rmtree(base, ignore_errors=True)
    print(json.dumps({k: record[k] for k in ("exit", "tests_run", "passed", "failures", "errors", "skips", "repository_root_changed")}))
    if done.returncode not in (0, 1):
        print(done.stdout[-1500:].replace(str(REPO), "<repo>"))


if __name__ == "__main__":
    main()
