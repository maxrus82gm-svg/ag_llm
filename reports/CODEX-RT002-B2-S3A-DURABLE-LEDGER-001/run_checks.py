"""Guard before imports; synthetic pytest and same-interpreter workers only."""
import os
from pathlib import Path
import runpy
import sys
import tempfile
import json

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
guard = ROOT / "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/guard"
control = "--prove-guard" in sys.argv
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT), ORDINARY_GUARD_NETWORK="none",
                  ORDINARY_GUARD_LOG=str(PACKAGE / ("evidence/guard_controls.jsonl" if control else "evidence/guard_tests.jsonl")),
                  PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
os.environ["PYTHONPATH"] = str(guard) + os.pathsep + str(ROOT)
runpy.run_path(str(guard / "sitecustomize.py"))
sys.path.insert(0, str(ROOT))
if control:
    import socket
    checks = []
    for name, probe in [("socket", lambda: socket.socket().connect(("192.0.2.1", 443))),
                        ("dns", lambda: socket.getaddrinfo("offline.invalid", 443)),
                        ("credentials", lambda: os.environ["GIGACHAT_ACCESS_TOKEN"])]:
        try:
            probe()
        except PermissionError:
            checks.append(name)
    assert checks == ["socket", "dns", "credentials"]
    print(json.dumps({"blocked_before_io": checks, "actual_provider_calls": 0}))
elif len(sys.argv) > 1 and sys.argv[1] == "--worker":
    from test_rt002_s3a_ledger import worker
    print(json.dumps(worker(*sys.argv[2:])))
else:
    import pytest
    if len(sys.argv) > 2 and sys.argv[1] == "--mutant":
        from dataclasses import replace
        import ultra_budget_policy as policy
        import ultra_budget_ledger as ledger
        mutant = sys.argv[2]
        del sys.argv[1:3]
        if mutant == "ignore_policy_deny":
            original = policy.evaluate_request
            def unchecked(*args):
                decision = original(*args)
                return replace(decision, verdict=policy.ALLOW, reasons=()) if decision.estimate and decision.estimate.tokens is not None else decision
            policy.evaluate_request = unchecked
        elif mutant == "free_unknown":
            original = policy.AttemptRecord.liability_tokens.fget
            policy.AttemptRecord.liability_tokens = property(lambda self: 0 if self.state == policy.UNKNOWN_TERMINAL else original(self))
        elif mutant == "ignore_checksum":
            ledger._hash = lambda value: "0" * 64
        else:
            raise ValueError("Unknown offline negative control")
    with tempfile.TemporaryDirectory(prefix="codex_s3a_suite_") as directory:
        raise SystemExit(pytest.main(["-p", "no:cacheprovider", "--basetemp", str(Path(directory) / "cases"), *sys.argv[1:]]))
