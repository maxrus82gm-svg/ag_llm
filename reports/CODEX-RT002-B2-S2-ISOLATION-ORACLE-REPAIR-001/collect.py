"""Parent capture only; guarded worker owns test execution. No production imports here."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
mode = sys.argv[1]
argv = [str(ROOT / ".venv/Scripts/python.exe"), "-B", "-X", "utf8", str(PACKAGE / "run_guarded.py"), mode]
run = subprocess.run(argv, cwd=ROOT, capture_output=True)
(PACKAGE / "evidence" / (mode + ".stdout.txt")).write_bytes(run.stdout)
(PACKAGE / "evidence" / (mode + ".stderr.txt")).write_bytes(run.stderr)
meta = {"argv": argv, "exit_code": run.returncode, "s2_source_sha256": hashlib.sha256((ROOT / "test_rt002_s2_budget_policy.py").read_bytes()).hexdigest()}
(PACKAGE / "evidence" / (mode + ".execution.json")).write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
try:
    result = json.JSONDecoder().raw_decode(run.stdout.decode("utf-8"))[0]
    if mode in {"s1", "s2"} and "sandbox" in result:
        sandbox = Path(result["sandbox"])
        for name, target in [("result.json", mode + ".result.json"), ("unittest.log", mode + ".unittest.txt")]:
            (PACKAGE / "evidence" / target).write_bytes((sandbox / name).read_bytes())
    if mode not in {"s1", "s2"}:
        (PACKAGE / "evidence" / (mode + ".result.json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": mode, "exit": run.returncode, "counts": result.get("counts"), "gate": result.get("gate"),
                      "isolation_violations": result.get("isolation_violations"), "controls": result.get("expected_blocked_before_io")}, ensure_ascii=False))
except (ValueError, KeyError):
    print(run.stdout.decode("utf-8")); print(run.stderr.decode("utf-8"))
raise SystemExit(run.returncode)
