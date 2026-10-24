"""Record the source revision the runner would hash, and optionally copy it into a disposable TEMP mirror.

The hashed set is exactly what wa4a_acceptance.py puts into results.json["source_sha256"]: web_alarm/*.py, the root
test_web_alarm*.py files and wa4a_acceptance.py. A mirror is a plain copy of that set (plus the package data the tests
read) under TEMP, so later RED runs can execute the pre-change bytes while the working tree changes.
Usage: snapshot.py <out.json> [--mirror <name>]
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def files():
    found = sorted((REPO / "web_alarm").glob("*.py")) + sorted(REPO.glob("test_web_alarm*.py"))
    return found + [REPO / "wa4a_acceptance.py"]


out = Path(sys.argv[1])
hashes = {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files()}
record = {"files": len(hashes), "sha256": hashes}
if "--mirror" in sys.argv:
    name = sys.argv[sys.argv.index("--mirror") + 1]
    mirror = Path(tempfile.gettempdir()).resolve() / name
    if mirror.exists():
        raise SystemExit("mirror already exists: refusing to overwrite")
    shutil.copytree(REPO / "web_alarm", mirror / "web_alarm", ignore=shutil.ignore_patterns("__pycache__"))
    for path in files()[len(list((REPO / "web_alarm").glob("*.py"))):]:
        shutil.copy2(path, mirror / path.name)
    copied = {p.relative_to(mirror).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(mirror.rglob("*.py")) if "web_alarm" in p.parts or p.parent == mirror}
    assert all(copied.get(k) == v for k, v in hashes.items()), "mirror does not match the working tree"
    record["mirror"] = f"<TEMP>/{name}"
out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"files": len(hashes), "mirror": record.get("mirror"),
                  "wa4a_acceptance.py": hashes["wa4a_acceptance.py"][:16],
                  "web_alarm/transport_event_recovery.py": hashes["web_alarm/transport_event_recovery.py"][:16]}))
