"""Negative controls (source mutants) for CLAUDE-WA4-R-AUD01T02B-REPAIR-001.

Production files are never touched. For each mutant a disposable TEMP mirror receives a copy of
web_alarm/*.py and the repair test module; exactly ONE snippet of ONE repaired file is replaced
(the snippet must occur exactly once), and ONE named test runs there in a fresh Python process
(children of concurrency tests import the mirror, so cross-process mutants are real). A mutant is
CAUGHT when that test does not pass AND its output contains the expected assertion text. The same
selectors first run on an unmutated mirror and must pass (control).
Usage: quality_mutants_aud01t02b.py <repo-root> <python> <out.json>
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO, PYTHON, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
MODULE = "test_web_alarm_aud01t02b_repair"
T, S, E = "web_alarm/transport_event_store.py", "web_alarm/state_machine.py", "web_alarm/event_checkpoint_store.py"
TF, TD = f"{MODULE}.TransportFramingTests", f"{MODULE}.TransportDurabilityTests"
MH, MC, HC = f"{MODULE}.MicrotaskHistoryTests", f"{MODULE}.MicrotaskCommitTests", f"{MODULE}.HistoryConcurrencyTests"

MUTANTS = [
    ("T1 reader splits on str.splitlines (pre-repair framing)", T,
     '        for index, chunk in enumerate(data.split(b"\\n")[:-1], start=1):\n'
     '            try:\n'
     '                line = chunk.removesuffix(b"\\r").decode("utf-8")\n',
     '        for index, chunk in enumerate(data.decode("utf-8").splitlines(), start=1):\n'
     '            try:\n'
     '                line = chunk\n',
     f"{TF}.test_pre_repair_raw_separator_and_crlf_records_stay_readable_and_appendable",
     ["invalid transport event JSON"]),
    ("T2 reader accepts an unterminated tail", T,
     '        if data and not data.endswith(b"\\n"):\n            raise TransportEventStoreError(\n'
     '                f"unterminated transport event log: {self.events_path}"\n            )\n\n        records',
     '        records',
     f"{TF}.test_unterminated_tail_is_refused_never_spliced",
     ["TransportEventStoreError not raised"]),
    ("T3 writer leaves U+0085/U+2028/U+2029 raw", T,
     "(line.translate(_ESCAPED_LINE_BOUNDARIES) + \"\\n\")",
     "(line + \"\\n\")",
     f"{TF}.test_http_separator_text_keeps_transport_evidence_readable_and_appendable",
     ["raw line separator written into the transport log"]),
    ("T4 append without the store lock", T,
     "            lock.acquire()\n        except (StoreLockTimeout, OSError) as exc:\n"
     "            raise TransportEventStoreError",
     "            pass\n        except (StoreLockTimeout, OSError) as exc:\n"
     "            raise TransportEventStoreError",
     f"{TD}.test_concurrent_processes_lose_no_transport_event",
     ["racing appends tore or spliced transport records", "lost or overwrote transport evidence",
      "an event was written twice"]),
    ("T5 failed append is not rolled back", T,
     "                        handle.truncate(size)\n                        os.fsync(handle.fileno())\n",
     "                        pass\n",
     f"{TD}.test_failed_durable_append_is_rolled_back_and_reported",
     ["a failed durable append left its bytes in the log"]),
    ("E1 TASK history append without the events lock", E,
     "            lock.acquire()\n        except (StoreLockTimeout, OSError) as exc:\n"
     "            raise EventCheckpointStoreError",
     "            pass\n        except (StoreLockTimeout, OSError) as exc:\n"
     "            raise EventCheckpointStoreError",
     f"{HC}.test_concurrent_reports_from_processes_lose_no_event",
     ["racing appends tore or spliced TASK history records", "lost or overwrote TASK history events"]),
    ("S1 no history check at transition entry", S,
     "        self._require_readable_history(task_id, microtask_id, requested.value)\n\n        if expected_status",
     "\n        if expected_status",
     f"{MH}.test_invalid_line_history_refuses_steps_and_rejections_without_writes",
     # first failing assertion is the HTTP code: the rejection path ran and wrote REJECTED
     ["a refused lifecycle step persisted state", "'transition_rejected'] != [409, 'state_machine_error']"]),
    ("S2 plain/ACTIVE commit without the in-lock history check", S,
     "            self._require_readable_history(task_id, microtask_id, requested.value)\n            try:\n",
     "            try:\n",
     f"{MH}.test_history_turning_unreadable_before_the_commit_lock_is_refused",
     # first failing assertion is the HTTP code: the step committed and then could not record its event
     ["status persisted over a history known to be torn", "IS persisted, but its history event was not recorded"]),
    ("S3 activation commit without the locked activation rules (activate=False)", S,
     "expected=current, status=requested, activate=activate",
     "expected=current, status=requested, activate=False",
     "test_web_alarm_recovery_coordinator_repair3.CrashConsistencyTests"
     ".test_f4_activation_rechecks_earlier_microtasks_under_the_lock",
     ["TransitionRejected not raised"]),
    ("S9 plain commit accepts any current status (no compare-and-set)", S,
     "expected=current, status=requested, activate=activate",
     "expected=list(MicrotaskStatus), status=requested, activate=activate",
     f"{MC}.test_plain_step_decided_on_a_stale_status_is_rejected_under_the_lock",
     ["transition_rejected", "a stale step overwrote a newer status"]),
    ("S4 VERIFIED commit without the in-lock history check", S,
     "                self._require_readable_history(task_id, microtask_id, MicrotaskStatus.VERIFIED.value)\n",
     "",
     f"{MH}.test_history_turning_unreadable_before_the_commit_lock_is_refused",
     ["DONE->VERIFIED"]),
    ("S5 VERIFIED event appended after the locks are released (pre-repair order)", S,
     "                    return self._stale_reason(current, MicrotaskStatus.VERIFIED, exc), None, None\n"
     "                return None, updated, self._record_transition(task_id, microtask_id, operation_id, payload)\n",
     "                    return self._stale_reason(current, MicrotaskStatus.VERIFIED, exc), None, None\n"
     "        return None, updated, self._record_transition(task_id, microtask_id, operation_id, payload)\n",
     f"{MC}.test_closeout_cannot_interleave_between_status_and_its_event",
     ["closeout completed the TASK between a status and its event"]),
    ("S6 history failure after commit raised as a refusal", S,
     '            return f"{type(exc).__name__}: {exc}"\n        return None\n',
     "            raise\n        return None\n",
     f"{MC}.test_history_failure_after_commit_is_reported_as_committed",
     ["a committed step was reported as refused"]),
    ("S7 unencodable text not checked before the commit", S,
     '                    value.encode("utf-8")\n',
     "                    pass\n",
     f"{MH}.test_unencodable_text_is_refused_before_any_write",
     # first failing assertion is the HTTP code: the step committed, its event failed to encode
     ["a refused lifecycle step persisted state", "'history_error': \"UnicodeEncodeError"]),
    ("S8 prepare without the history check", S,
     '        self._require_readable_history(task_id, microtask_id, "prepare")\n',
     "",
     f"{MH}.test_prepare_on_unreadable_history_writes_no_restore_point",
     ["a refused lifecycle step persisted state", "state_machine_error"]),
]


def mirror() -> Path:
    root = Path(tempfile.mkdtemp(prefix="aud01t02b-mutant-"))
    (root / "web_alarm").mkdir()
    for path in (REPO / "web_alarm").glob("*.py"):
        shutil.copyfile(path, root / "web_alarm" / path.name)
    for path in REPO.glob("test_web_alarm_*.py"):  # the module under test and the fixtures it imports
        shutil.copyfile(path, root / path.name)
    return root


def run(root: Path, selector: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "GIT_"))}
    iso = root / "_iso"
    for name in ("localappdata", "appdata", "pycache"):
        (iso / name).mkdir(parents=True, exist_ok=True)
    env.update(LOCALAPPDATA=str(iso / "localappdata"), APPDATA=str(iso / "appdata"),
               PYTHONPYCACHEPREFIX=str(iso / "pycache"), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    started = time.time()
    proc = subprocess.run([PYTHON, "-B", "-X", "utf8", "-m", "unittest", "-v", selector], cwd=root, env=env,
                          capture_output=True, timeout=600)
    output = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    return {"returncode": proc.returncode, "seconds": round(time.time() - started, 2), "output": output}


if len(sys.argv) > 4 and sys.argv[4] == "--dry":  # only check that every snippet occurs exactly once
    for name, rel, old, new, selector, expected in MUTANTS:
        print((REPO / rel).read_text(encoding="utf-8").count(old), "|", name)
    sys.exit(0)

results = {"repo": str(REPO), "python": PYTHON, "module_sha256": hashlib.sha256((REPO / f"{MODULE}.py").read_bytes()).hexdigest(),
           "source_sha256": {f: hashlib.sha256((REPO / f).read_bytes()).hexdigest() for f in (T, S, E)},
           "controls": [], "mutants": []}
control_root = mirror()
for selector in sorted({m[4] for m in MUTANTS}):
    outcome = run(control_root, selector)
    results["controls"].append({"selector": selector, "passed": outcome["returncode"] == 0,
                                "seconds": outcome["seconds"], "tail": outcome["output"][-300:]})
shutil.rmtree(control_root, ignore_errors=True)
for name, rel, old, new, selector, expected in MUTANTS:
    root = mirror()
    text = (root / rel).read_text(encoding="utf-8")
    occurrences = text.count(old)
    entry = {"mutant": name, "file": rel, "selector": selector, "snippet_occurrences": occurrences}
    if occurrences != 1:
        entry["verdict"] = "INVALID_MUTANT"
    else:
        (root / rel).write_bytes(text.replace(old, new).encode("utf-8"))
        outcome = run(root, selector)
        hit = [e for e in expected if e in outcome["output"]]
        entry.update(returncode=outcome["returncode"], seconds=outcome["seconds"], expected_found=hit,
                     verdict="CAUGHT" if outcome["returncode"] != 0 and hit else "NOT_CAUGHT",
                     tail=outcome["output"][-600:])
    results["mutants"].append(entry)
    shutil.rmtree(root, ignore_errors=True)
results["controls_all_pass"] = all(c["passed"] for c in results["controls"])
results["mutants_caught"] = sum(1 for m in results["mutants"] if m["verdict"] == "CAUGHT")
results["mutants_total"] = len(MUTANTS)
results["verdict"] = "PASS" if results["controls_all_pass"] and results["mutants_caught"] == len(MUTANTS) else "FAIL"
OUT.write_text(json.dumps(results, ensure_ascii=True, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: results[k] for k in ("controls_all_pass", "mutants_caught", "mutants_total", "verdict")}))
for m in results["mutants"]:
    print(m["verdict"], "|", m["mutant"], "|", m.get("returncode"), "|", m.get("expected_found"))
