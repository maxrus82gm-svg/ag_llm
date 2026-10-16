"""Probe: can a lock-free reader observe a partially written record while ONE writer appends?

One writer process appends LF-terminated JSON records (open "a+b", write, flush, fsync -- the
event_checkpoint_store pattern; no write-write race because there is one writer). Several reader
processes read the whole file in a loop and classify every read: clean (ends with LF, every line
parses) or torn (no final LF / unparsable line). Disposable TEMP only.
Usage: probe_read_during_append.py <records> <readers> <out.json>
"""
import json
import multiprocessing as mp
import os
import sys
import tempfile
import time
from pathlib import Path


def writer(path, records, go, done):
    while not os.path.exists(go):
        time.sleep(0.001)
    pad = "y" * 280
    for n in range(records):
        line = (json.dumps({"n": n, "pad": pad}, separators=(",", ":")) + "\n").encode()
        with open(path, "a+b") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
    Path(done).write_text("done")


def reader(path, go, done, out):
    while not os.path.exists(go):
        time.sleep(0.001)
    clean = torn = 0
    examples = []
    while not os.path.exists(done):
        try:
            data = Path(path).read_bytes()
        except OSError:
            continue
        ok = data == b"" or data.endswith(b"\n")
        if ok:
            try:
                for chunk in data.split(b"\n")[:-1]:
                    json.loads(chunk)
            except ValueError:
                ok = False
        if ok:
            clean += 1
        else:
            torn += 1
            if len(examples) < 3:
                examples.append(data[-60:].hex())
    Path(out).write_text(json.dumps({"clean": clean, "torn": torn, "examples": examples}))


def main():
    records, readers, out = int(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
    base = Path(tempfile.mkdtemp(prefix="aud01t-readappend-"))
    path, go, done = str(base / "log.jsonl"), str(base / "go"), str(base / "done")
    Path(path).write_bytes(b"")
    procs = [mp.Process(target=writer, args=(path, records, go, done))]
    outs = [str(base / f"r{i}.json") for i in range(readers)]
    procs += [mp.Process(target=reader, args=(path, go, done, o)) for o in outs]
    for p in procs:
        p.start()
    time.sleep(0.5)
    Path(go).write_text("go")
    for p in procs:
        p.join(180)
    per_reader = [json.loads(Path(o).read_text()) for o in outs]
    result = {"records": records, "readers": readers, "per_reader": per_reader,
              "total_clean_reads": sum(r["clean"] for r in per_reader),
              "total_torn_reads": sum(r["torn"] for r in per_reader),
              "python": sys.version, "platform": sys.platform}
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_reader"}, indent=1))


if __name__ == "__main__":
    main()
