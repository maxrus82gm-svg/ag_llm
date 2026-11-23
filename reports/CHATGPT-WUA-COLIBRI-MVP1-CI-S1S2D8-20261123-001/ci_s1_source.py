"""#666 hosted CI S1 SOURCE-ONLY review with nonzero, fail-closed test census.

Full S1 historic pinned RAW gate is run separately on authorised HOME and
cannot be declared PASSED by a hosted runner without those original bytes.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode=True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import test_rt002_s1_routes as s1

def main():
    base=Path(tempfile.mkdtemp(prefix="wua666-s1-static-"))
    for k in ("TEMP","TMP","APPDATA","LOCALAPPDATA"):
        p=base/k.lower()
        p.mkdir()
        os.environ[k]=str(p)
    for k in ("GIGACHAT_CREDENTIALS","HTTP_PROXY","HTTPS_PROXY","ALL_PROXY"):
        os.environ.pop(k,None)
    tempfile.tempdir=str(base/"temp")
    (base/"temp").mkdir(exist_ok=True)
    s1._SANDBOX=base
    s1._ISOLATED=True
    violations=s1._install_guards(base)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(s1.StaticRouteInventoryTests)
    count=suite.countTestCases()
    if count < 8:
        raise RuntimeError("S1 source-only census unexpectedly too small")
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    valid=(result.testsRun==count and count>0 and not result.failures
           and not result.errors and not result.skipped and not violations)
    print(f"S1_STATIC_SOURCE_ONLY_RESULT tests={count} ok={valid} violations={len(violations)}")
    return 0 if valid else 1

if __name__=="__main__":
    raise SystemExit(main())
