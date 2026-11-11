"""Four existing tests, strict OFFLINE; no new product or test implementation."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PKG = Path(__file__).resolve().parent
TESTS = [
    "test_web_alarm_ordinary_core_bridge.CoreBridgeTests.test_real_transport_object_is_never_dispatched",
    "test_web_alarm_ordinary_core_bridge.CoreBridgeTests.test_bad_ids_model_and_config_cannot_read_or_send",
    "test_web_alarm_perchat_usage_settings.PerChatTests.test_preflight_rejection_is_not_an_unknown_paid_attempt",
    "test_web_alarm_ordinary_core_bridge.CoreBridgeTests.test_transport_failure_does_not_replay_or_enter_next_context",
]

if __name__ == "__main__" and "--guarded" in sys.argv:
    import runpy
    runpy.run_path(str(ROOT / "reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py"))
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromNames(TESTS)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(guard_installed=True, tests_run=result.testsRun,
                          failures=len(result.failures), errors=len(result.errors),
                          skipped=len(result.skipped))))
    sys.exit(not result.wasSuccessful())

if __name__ == "__main__":
    evidence = PKG / "evidence"
    assert not (evidence / "tests.result.json").exists(), "Preserve previous evidence"
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("GIGACHAT_") and k.upper() not in ("PYTHONPATH", "PYTHONSTARTUP")}
    env.update(PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
               ORDINARY_GUARD_NETWORK="deny", ORDINARY_GUARD_ROOT=str(ROOT),
               ORDINARY_GUARD_LOG=str(evidence / "tests.guard.jsonl"))
    command = [str(ROOT / ".venv/Scripts/python.exe"), "-B", "-X", "utf8", str(Path(__file__).resolve()), "--guarded"]
    started = time.monotonic()
    run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=60)
    (evidence / "tests.stdout.txt").write_bytes(run.stdout)
    (evidence / "tests.stderr.txt").write_bytes(run.stderr)
    facts = json.loads(run.stdout.decode("utf-8").strip().splitlines()[-1]) if run.returncode == 0 else {}
    log = evidence / "tests.guard.jsonl"
    facts.update(command=command, selected_tests=TESTS, exit_code=run.returncode,
                 elapsed_seconds=time.monotonic() - started, python=sys.version,
                 network_mode="deny (stdlib asyncio self-pipe only)",
                 guard_violations=len(log.read_text(encoding="utf-8").splitlines()) if log.exists() else 0)
    (evidence / "tests.result.json").write_text(json.dumps(facts, indent=2), encoding="utf-8")
    print(run.stderr.decode("utf-8", errors="replace"))
    print(json.dumps(facts, indent=2))
    sys.exit(run.returncode or bool(facts.get("guard_violations")))
