"""WEB26 independent OFFLINE RT-002 S3a/Run Store CI.
Only synthetic TEMP fixtures. No project source, live workspace, or provider writes.
The reviewer owns this runner; it never invokes task-local evidence writers.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(os.environ.get("WEB26_EVIDENCE_DIR", Path(tempfile.gettempdir()) / "web26_s3a_ci"))
EVIDENCE.mkdir(parents=True, exist_ok=True)
MODE = sys.argv[1] if len(sys.argv) > 1 else ""
VALID = {"guard-proof", "s3a", "runstore", "mutant-policy-deny",
         "mutant-unknown-liability", "mutant-checksum", "--worker"}
if MODE not in VALID:
    raise SystemExit("Expected one explicit CI mode")
if MODE == "--worker" and "ORDINARY_GUARD_LOG" not in os.environ:
    raise SystemExit("Worker must inherit an already configured early guard")

TASK_TMP = EVIDENCE / (MODE.replace("-", "_") + "_" + str(os.getpid()))
TASK_TMP.mkdir(parents=True, exist_ok=True)
for key in ("TEMP", "TMP", "LOCALAPPDATA", "APPDATA"):
    target = TASK_TMP / key.lower()
    target.mkdir(exist_ok=True)
    os.environ[key] = str(target)
tempfile.tempdir = str(TASK_TMP / "temp")
for key in ("GIGACHAT_CREDENTIALS", "GIGACHAT_SCOPE", "GIGACHAT_ACCESS_TOKEN",
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
    try:
        del os.environ[key]   # erase inherited secrets WITHOUT reading their values
    except KeyError:
        pass

GUARD = ROOT / "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/guard"
guard_log = Path(os.environ["ORDINARY_GUARD_LOG"]) if MODE == "--worker" else TASK_TMP / "guard.jsonl"
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT), ORDINARY_GUARD_NETWORK="none",
                  ORDINARY_GUARD_LOG=str(guard_log),
                  PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1",
                  PYTHONPATH=str(GUARD) + os.pathsep + str(ROOT))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
runpy.run_path(str(GUARD / "sitecustomize.py"))  # installed BEFORE any runtime imports

import test_rt002_s3a_ledger as suite
suite.DRIVER = Path(__file__).resolve()  # child uses THIS reviewer entrypoint

if MODE == "--worker":
    print(json.dumps(suite.worker(*sys.argv[2:])))
    raise SystemExit(0)

if MODE == "guard-proof":
    probes = [
        ("physical_socket", lambda: socket.socket().connect(("192.0.2.1", 443))),
        ("dns", lambda: socket.getaddrinfo("offline.invalid", 443)),
        ("credential", lambda: os.environ["GIGACHAT_ACCESS_TOKEN"]),
        ("git_metadata", lambda: (ROOT / ".git/config").open("rb")),
        ("non_python_process", lambda: subprocess.Popen(["cmd.exe", "/c", "echo never"])),
        ("live_workspace_write", lambda: (ROOT / ".ultra" / "never.txt").open("wb")),
    ]
    blocked, unexpected = [], []
    for label, probe in probes:
        try:
            probe()
        except PermissionError:
            blocked.append(label)
        except Exception as error:
            unexpected.append([label, type(error).__name__])
        else:
            unexpected.append([label, "NOT_BLOCKED"])
    events = [json.loads(x) for x in guard_log.read_text(encoding="utf-8").splitlines()] if guard_log.exists() else []
    success = len(blocked) == len(probes) and not unexpected and len(events) == len(probes)
    result = {"mode": MODE, "status": "PASS" if success else "FAIL", "blocked": blocked,
              "unexpected": unexpected, "guard_events": events}
    (TASK_TMP / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    raise SystemExit(0 if success else 2)

PINNED = {
    "test_rt002_s3a_ledger.py": "4cd18201030b1c3e3cbdcd640cbfdc306c8697c7b54482fb1dddebb4db243c0b",
    "ultra_budget_ledger.py": "3d64c3024bfc42957c3c0612b33c228ce0beea3e9b790fc97a5b1bbfe2aaf220",
}
SOURCES = [*PINNED, "ultra_budget_policy.py", "context_storage.py",
           "run_store.py", "test_run_store_v2.py"]
def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}

before = hashes()
if any(before[name] != pin for name, pin in PINNED.items()):
    raise SystemExit("SOURCE_DRIFT: independent baseline hashes do not match approved ledger/test")
if MODE == "mutant-policy-deny":
    import ultra_budget_policy as policy
    original = policy.evaluate_request
    def unchecked(*args):
        decision = original(*args)
        return replace(decision, verdict=policy.ALLOW, reasons=()) if decision.estimate and decision.estimate.tokens is not None else decision
    policy.evaluate_request = unchecked
elif MODE == "mutant-unknown-liability":
    import ultra_budget_policy as policy
    original = policy.AttemptRecord.liability_tokens.fget
    policy.AttemptRecord.liability_tokens = property(
        lambda self: 0 if self.state == policy.UNKNOWN_TERMINAL else original(self))
elif MODE == "mutant-checksum":
    import ultra_budget_ledger as ledger
    ledger._hash = lambda _: "0" * 64

import pytest
xml = TASK_TMP / "pytest.xml"
target = "test_run_store_v2.py" if MODE == "runstore" else "test_rt002_s3a_ledger.py"
pytest_exit = int(pytest.main(["-p", "no:cacheprovider", "--basetemp", str(TASK_TMP / "cases"),
                               "-q", target, "--junitxml=" + str(xml)]))
node = ET.parse(xml).getroot()
suite_xml = node.find("testsuite") if node.tag == "testsuites" else node
counts = {field: int(suite_xml.get(field, "0")) for field in ("tests", "failures", "errors", "skipped")}
after = hashes()
guard_events = [json.loads(x) for x in guard_log.read_text(encoding="utf-8").splitlines()] if guard_log.exists() else []
mutant = MODE.startswith("mutant-")
expected_total = 51 if MODE == "runstore" else 35
if mutant:
    accepted = (pytest_exit == 1 and counts["tests"] == 35 and counts["failures"] > 0
                and counts["errors"] == counts["skipped"] == 0)
else:
    accepted = (pytest_exit == 0 and counts["tests"] == expected_total
                and counts["failures"] == counts["errors"] == counts["skipped"] == 0)
accepted = accepted and before == after and not guard_events
result = {"mode": MODE, "status": "PASS" if accepted else "FAIL",
          "pytest_exit": pytest_exit, "counts": counts, "mutant_expected_RED": mutant,
          "source_sha256": after, "sources_unchanged": before == after,
          "guard_denials": len(guard_events), "synthetic_only": True}
(TASK_TMP / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if accepted else 3)
