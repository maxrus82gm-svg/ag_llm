"""F-T1 mechanism probe: when does Path.resolve() on Windows keep the extended-length prefix for a TEMP path?

No guard, no repository writes; every file lives in a fresh TEMP directory that is removed at the end. Output paths
are reported relative to that directory only.

1. sequenced: the real nt._getfinalpathname is called; between the first failing call and the next one the probe
   really creates the missing parent directory (or the file), i.e. the state change another process makes in a race.
   Nothing returned by the OS is faked.
2. race: one thread creates/removes the parent directory in a loop while the main thread resolves a file below it;
   bounded by iterations and wall time.
Usage: probe_realpath.py <out.json>
"""
import json
import ntpath
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

PREFIX = "\\\\?\\"
base = Path(tempfile.mkdtemp(prefix="claude-ft1-probe-")).resolve()
real = ntpath._getfinalpathname
result = {"python": sys.version.split()[0], "platform": sys.platform}


def rel(text):
    raw = str(text)
    for form in (PREFIX + str(base), str(base)):
        if raw.lower().startswith(form.lower()):
            return ("<PREFIX>" if raw.startswith(PREFIX) else "") + "<BASE>" + raw[len(form):]
    return "<OTHER>"


def sequenced(name, target, make):
    calls = []

    def wrapper(path):
        try:
            value = real(path)
            calls.append("ok")
            return value
        except OSError as exc:
            calls.append(exc.winerror)
            if len(calls) == 1 and make is not None:
                make()  # the concurrent creation, done for real between two OS calls
            raise
    ntpath._getfinalpathname = wrapper
    try:
        resolved = Path(target).resolve()
    finally:
        ntpath._getfinalpathname = real
    result.setdefault("sequenced", {})[name] = {"winerrors_seen": calls, "resolved": rel(resolved),
                                                "kept_extended_prefix": str(resolved).startswith(PREFIX),
                                                "is_relative_to_temp_root": resolved.is_relative_to(base)}


case = base / "a"
case.mkdir()
sequenced("control_parent_missing_nothing_changes", case / "sub" / "f.txt", None)
sequenced("parent_created_between_calls", case / "sub2" / "f.txt", lambda: (case / "sub2").mkdir())
sequenced("nested_parent_created_between_calls", case / "x" / "y" / "f.txt", lambda: (case / "x").mkdir())
(case / "sub3").mkdir()
sequenced("file_created_between_calls", case / "sub3" / "f.txt", lambda: (case / "sub3" / "f.txt").write_bytes(b""))
sequenced("control_existing_file", case / "sub3" / "f.txt", None)

race_dir = base / "race"
race_dir.mkdir()
stop = threading.Event()


def churn():
    while not stop.is_set():
        try:
            os.mkdir(race_dir / "d")
            os.rmdir(race_dir / "d")
        except OSError:
            pass


worker = threading.Thread(target=churn, daemon=True)
worker.start()
counts = {"iterations": 0, "kept_extended_prefix": 0, "not_relative_to_temp_root": 0}
shapes = {}
deadline = time.monotonic() + 20.0
while counts["iterations"] < 20000 and time.monotonic() < deadline:
    resolved = Path(race_dir / "d" / "f.txt").resolve()
    counts["iterations"] += 1
    if str(resolved).startswith(PREFIX):
        counts["kept_extended_prefix"] += 1
    if not resolved.is_relative_to(base):
        counts["not_relative_to_temp_root"] += 1
        shape = str(resolved).replace(PREFIX, "<PREFIX>")
        lower = shape.lower()
        at = lower.find(str(base).lower())
        while at >= 0:
            shape = shape[:at] + "<BASE>" + shape[at + len(str(base)):]
            lower = shape.lower()
            at = lower.find(str(base).lower())
        if "<BASE>" not in shape:
            shape = "<NO-BASE-FORM:" + str(len(shape)) + " chars>"
        shapes[shape] = shapes.get(shape, 0) + 1
counts["not_relative_shapes"] = shapes
stop.set()
worker.join(5)
result["race_unpatched"] = counts
shutil.rmtree(base)
Path(sys.argv[1]).write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(result, indent=1, sort_keys=True))
