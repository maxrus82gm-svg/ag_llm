"""Use the existing OFFLINE guard before importing test/product code."""
import os
from pathlib import Path
import runpy
import sys
import unittest

root = Path(__file__).resolve().parents[2]
os.environ.update(ORDINARY_GUARD_ROOT=str(root), ORDINARY_GUARD_NETWORK="loopback",
                  ORDINARY_GUARD_LOG=str(Path(__file__).resolve().parent / "evidence/guard.jsonl"))
runpy.run_path(str(root / "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/guard/sitecustomize.py"))
sys.path.insert(0, str(root))
if "--web-only" in sys.argv:
    sys.argv.remove("--web-only")
    names = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    def cases(suite):
        for case in suite:
            if isinstance(case, unittest.TestSuite):
                yield from cases(case)
            else:
                yield case
    loaded = list(cases(unittest.defaultTestLoader.loadTestsFromNames(names)))
    omitted = [case.id() for case in loaded if ".test_tk" in case.id()]
    print("WEB_ONLY: separate Tk cases not run in this process: " + repr(omitted), flush=True)
    selected = unittest.TestSuite(case for case in loaded if case.id() not in omitted)
    result = unittest.TextTestRunner(verbosity=2).run(selected)
    raise SystemExit(0 if result.wasSuccessful() else 1)
else:
    unittest.main(module=None)
