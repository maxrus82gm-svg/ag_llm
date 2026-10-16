"""Disposable TEMP mirror for a FAIL-first run of the FINAL test module against PRE-REPAIR sources.

Copies web_alarm/*.py, every root test_web_alarm_*.py and wa4a_acceptance.py from the repository, then
overwrites the three repaired modules with the exact pre-repair bytes from ../baseline/web_alarm/
(SHA-checked). The repository is only read. Prints the mirror path. Usage: make_baseline_mirror.py
"""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
before = json.loads((HERE / "baseline-gate.json").read_bytes())["source_sha256_all"]
root = Path(tempfile.mkdtemp(prefix="aud01t02b-baseline-mirror-"))
(root / "web_alarm").mkdir()
for path in (REPO / "web_alarm").glob("*.py"):
    shutil.copyfile(path, root / "web_alarm" / path.name)
for path in REPO.glob("test_web_alarm_*.py"):
    shutil.copyfile(path, root / path.name)
shutil.copyfile(REPO / "wa4a_acceptance.py", root / "wa4a_acceptance.py")
for name in ("transport_event_store.py", "state_machine.py", "event_checkpoint_store.py"):
    data = (HERE / "baseline" / "web_alarm" / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == before[f"web_alarm/{name}"], name
    (root / "web_alarm" / name).write_bytes(data)
print(root)
