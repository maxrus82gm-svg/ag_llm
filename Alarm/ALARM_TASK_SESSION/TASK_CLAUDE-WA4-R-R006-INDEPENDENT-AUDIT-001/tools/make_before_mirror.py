"""Build a disposable TEMP mirror of the runtime BEFORE R-006 (attribution only, never production).
Copies web_alarm/ and wa4a_acceptance.py from the repo, then overwrites the three R-006-changed modules with the
'sources/before' bytes preserved in evidence.zip, and verifies them against versions.json before-pins."""
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
PKG = REPO / "reports" / "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
mirror = Path(tempfile.mkdtemp(prefix="claude-wa4r006-before-mirror-"))
shutil.copytree(REPO / "web_alarm", mirror / "web_alarm", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copy2(REPO / "wa4a_acceptance.py", mirror / "wa4a_acceptance.py")
versions = json.loads((PKG / "versions.json").read_bytes())
before = {c["path"]: c["before_sha256"] for c in versions["changes"] if "before_sha256" in c}
with zipfile.ZipFile(PKG / "evidence.zip") as zf:
    for rel, pin in before.items():
        data = zf.read("sources/before/" + rel)
        assert hashlib.sha256(data).hexdigest() == pin, rel
        (mirror / rel).write_bytes(data)
        print("before", rel, pin[:12])
print("MIRROR", mirror)
