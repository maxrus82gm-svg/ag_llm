"""Reuse the existing strict guard with this TASK's output/worker paths only."""
import os
from pathlib import Path
import runpy
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
guard = ROOT / "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/guard"
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT), ORDINARY_GUARD_NETWORK="none",
                  ORDINARY_GUARD_LOG=str(PACKAGE / "evidence/s3a.guard.jsonl"),
                  PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
os.environ["PYTHONPATH"] = str(guard) + os.pathsep + str(ROOT)
runpy.run_path(str(guard / "sitecustomize.py"))
sys.path.insert(0, str(ROOT))
import test_rt002_s3a_ledger as suite

suite.DRIVER = Path(__file__).resolve()  # same tests; worker capture stays in this TASK
if len(sys.argv) > 1 and sys.argv[1] == "--worker":
    import json
    print(json.dumps(suite.worker(*sys.argv[2:])))
else:
    import pytest
    with tempfile.TemporaryDirectory(prefix="codex_s1_s3a_regression_") as directory:
        raise SystemExit(pytest.main(["-p", "no:cacheprovider", "--basetemp", str(Path(directory) / "cases"),
            "test_rt002_s3a_ledger.py", "-q", "--junitxml=" + str(PACKAGE / "evidence/s3a.xml")]))
