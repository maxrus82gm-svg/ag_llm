"""Rebuild the before->final source diff from the byte copies inside evidence.zip and compare with the
published source-changes.diff and with the local repository bytes (read-only)."""
import difflib
import hashlib
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
PKG = REPO / "reports" / "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
OUT = Path(sys.argv[1])
versions = json.loads((PKG / "versions.json").read_bytes())
sha = lambda d: hashlib.sha256(d).hexdigest()
changes = {c["path"]: c for c in versions["changes"]}
diff_text = []
with zipfile.ZipFile(PKG / "evidence.zip") as zf:
    names = zf.namelist()
    for n in names:
        if not n.startswith("sources/"):
            continue
        data = zf.read(n)
        if n == "sources/control-inputs.json":
            kind, rel, local = "final", "control-inputs.json", (PKG / "control-inputs.json").read_bytes()
        else:
            kind, rel = n.split("/", 2)[1], n.split("/", 2)[2]
        if rel == "quality_controls.py":
            local = (PKG / rel).read_bytes()
        elif rel == "control-inputs.json":
            pass
        else:
            local = (REPO / rel).read_bytes() if (REPO / rel).exists() else None
        c = changes.get(rel, {})
        pin = c.get("before_sha256") if kind == "before" else c.get("after_sha256")
        print(f"{n:<55} zip={sha(data)[:12]} pin={str(pin)[:12]} pin_ok={pin is None or sha(data) == pin} "
              f"local_eq={'n/a(before)' if kind == 'before' else local == data}")
    for rel in ("web_alarm/task_store.py", "web_alarm/event_checkpoint_store.py", "web_alarm/operation_store.py"):
        before = zf.read("sources/before/" + rel).decode("utf-8").splitlines(keepends=True)
        after = zf.read("sources/final/" + rel).decode("utf-8").splitlines(keepends=True)
        diff_text.extend(difflib.unified_diff(before, after, "a/" + rel, "b/" + rel, n=4))
OUT.write_text("".join(diff_text), encoding="utf-8", newline="\n")
pub = (PKG / "source-changes.diff").read_bytes().decode("utf-8")
plus = lambda t: sorted(l[1:].rstrip() for l in t.splitlines() if l.startswith("+") and not l.startswith("+++"))
minus = lambda t: sorted(l[1:].rstrip() for l in t.splitlines() if l.startswith("-") and not l.startswith("---"))
mine = "".join(diff_text)
print("my diff +/-:", len(plus(mine)), len(minus(mine)), " published +/-:", len(plus(pub)), len(minus(pub)))
print("added lines equal:", plus(mine) == plus(pub), " removed lines equal:", minus(mine) == minus(pub))
