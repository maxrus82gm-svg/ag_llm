"""Local-only shared plan editor. Cooperative coordination, not an OS authorization boundary."""
import argparse
import contextlib
import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile
import time

PLAN = "34.1_Общий план развития WUA и Colibri.md"
ARCHIVE = "34.1.1_Выполненные этапы общего плана.md"
ACTORS = ("WUA", "COLIBRI")
FIELDS = ("stage", "priority", "status", "task", "dependency", "criterion", "evidence", "next")
STATES = {"PLANNED", "IN_PROGRESS", "SUBMITTED", "VERIFIED", "ACCEPTED", "BLOCKED", "OPEN", "NOT_RUN"}
PREFIX = "WUA-COLIBRI-BRIDGE-001/"

def sha(data):
    return hashlib.sha256(data).hexdigest()

@contextlib.contextmanager
def locked(root, timeout=15):
    import msvcrt
    lockpath = root / ".git" / "wua-colibri-plan.lock"
    if not lockpath.parent.is_dir():
        raise ValueError("Expected the single canonical local Git checkout")
    with open(lockpath, "a+b") as f:
        if f.tell() == 0:
            f.write(b"0")
            f.flush()
        end = time.monotonic() + timeout
        while True:
            f.seek(0)
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= end:
                    raise RuntimeError("PLAN_BUSY: retry read; do not break the lock")
                time.sleep(.1)
        try:
            yield
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

def atomic(path, data):
    fd, name = tempfile.mkstemp(prefix=".plan-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
        if path.read_bytes() != data:
            raise RuntimeError("readback mismatch")
    finally:
        if os.path.exists(name):
            os.unlink(name)

def sections(text, actor):
    start, end = "<!-- " + actor + ":BEGIN -->", "<!-- " + actor + ":END -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("invalid section markers")
    a = text.index(start) + len(start)
    b = text.index(end)
    if b <= a:
        raise ValueError("invalid section ordering")
    return a, b

def locate(text, actor, stage):
    a, b = sections(text, actor)
    hits = list(re.finditer(r"(?m)^\| "+re.escape(PREFIX+stage)+r" \|[^\r\n]*", text[a:b]))
    if len(hits) != 1:
        raise ValueError("stage not unique in actor section")
    h = hits[0]
    cells = [x.strip() for x in h.group().strip("|").split("|")]
    if len(cells) != len(FIELDS):
        raise ValueError("invalid row")
    return a+h.start(), a+h.end(), cells

def update(data, actor, stage, changes):
    text = data.decode("utf-8")
    a,b,cells = locate(text, actor, stage)
    for key, value in changes.items():
        if key not in ("status", "task", "evidence", "next"):
            raise ValueError("field immutable; shared plan change requires both coordinators")
        if not value or any(c in value for c in "|\r\n<>") or len(value)>1500:
            raise ValueError("invalid cell")
        if key == "status" and value not in STATES:
            raise ValueError("invalid status")
        cells[FIELDS.index(key)] = value
    if cells[2] in ("SUBMITTED", "VERIFIED", "ACCEPTED") and cells[6] in ("—", "-", "TBD"):
        raise ValueError("evidence required")
    return (text[:a]+"| "+" | ".join(cells)+" |"+text[b:]).encode("utf-8")

def archive_stage(plan, archive, stage):
    txt = plan.decode("utf-8")
    hist = archive.decode("utf-8")
    rows = []
    for actor in ACTORS:
        a,b,cells = locate(txt,actor,stage)
        if cells[2] != "ACCEPTED" or cells[6] in ("—","-","TBD"):
            raise ValueError("both sides must be ACCEPTED with evidence")
        rows.append((actor,a,b,txt[a:b]))
    marker = "<!-- ARCHIVED:"+PREFIX+stage+" -->"
    entry = "\n"+marker+"\n## "+PREFIX+stage+"\n\n"+"\n\n".join(actor+"\n\n"+line for actor,_,_,line in rows)+"\n"
    if marker in hist:
        if entry not in hist:
            raise ValueError("archive conflict; preserve both and investigate")
    else:
        hist += entry
    for _,a,b,_ in sorted(rows,key=lambda x:x[1],reverse=True):
        txt = txt[:a]+txt[b:].lstrip("\r\n")
    return txt.encode("utf-8"),hist.encode("utf-8")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("read","update","archive"))
    p.add_argument("--actor",choices=ACTORS)
    p.add_argument("--stage")
    p.add_argument("--expect",help="SHA256 from last locked read")
    for field in ("status","task","evidence","next"):
        p.add_argument("--"+field)
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    docs=root/"Документация"
    plan=docs/PLAN
    archive=docs/ARCHIVE
    with locked(root):
        data=plan.read_bytes()
        if args.command=="read":
            print("PLAN_SHA256="+sha(data))
            print(data.decode("utf-8"))
            return
        if not args.expect or args.expect!=sha(data):
            raise ValueError("STALE_PLAN: read again, reconcile, retry")
        if not args.actor or not args.stage:
            raise ValueError("actor and stage required")
        if args.command=="update":
            changes={k:getattr(args,k) for k in ("status","task","evidence","next") if getattr(args,k) is not None}
            if not changes:
                raise ValueError("no changes")
            new=update(data,args.actor,args.stage,changes)
            # Prove foreign section byte-for-byte unchanged.
            other=ACTORS[1-ACTORS.index(args.actor)]
            oldtext,newtext=data.decode("utf-8"),new.decode("utf-8")
            a,b=sections(oldtext,other)
            c,e=sections(newtext,other)
            if oldtext[a:b]!=newtext[c:e]:
                raise RuntimeError("foreign section changed")
            atomic(plan,new)
        else:
            if args.actor!="WUA":
                raise ValueError("WUA archives jointly accepted stages")
            new,hist=archive_stage(data,archive.read_bytes(),args.stage)
            atomic(archive,hist)  # verify archive before removal, recoverable if second replace fails
            atomic(plan,new)
        print("PLAN_SHA256="+sha(plan.read_bytes()))

if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except (OSError,ValueError,RuntimeError) as exc:
        sys.exit(str(exc))
