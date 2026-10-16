"""Probe: are unlocked O_APPEND writes from several processes atomic on this Windows/Python?

Reproduces the exact write patterns of the two JSONL writers without importing web_alarm:
  text  -- transport_event_store (pinned): open("a", utf-8, newline="\n"), write, flush, fsync
  binary -- event_checkpoint_store: open("a+b"), tail check, write, flush, fsync
K worker processes start on a file barrier and each append M records (~300 bytes). The oracle is raw:
exactly K*M LF-terminated lines, each a valid JSON object with a unique (worker, n) pair.
Disposable TEMP only. Usage: probe_append_atomicity.py <mode:text|binary> <workers> <records> <out.json>
"""
import json
import multiprocessing as mp
import os
import sys
import tempfile
import time
from pathlib import Path


def worker(path, mode, wid, records, go):
    while not os.path.exists(go):
        time.sleep(0.001)
    pad = "x" * 240
    for n in range(records):
        line = json.dumps({"w": wid, "n": n, "pad": pad}, separators=(",", ":")) + "\n"
        if mode == "text":
            with open(path, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        else:
            with open(path, "a+b") as handle:
                handle.seek(0, os.SEEK_END)
                if handle.tell():
                    handle.seek(-1, os.SEEK_END)
                    handle.read(1)
                handle.write(line.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())


def main():
    mode, workers, records, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
    base = Path(tempfile.mkdtemp(prefix="aud01t-append-"))
    path, go = str(base / "log.jsonl"), str(base / "go")
    procs = [mp.Process(target=worker, args=(path, mode, w, records, go)) for w in range(workers)]
    for p in procs:
        p.start()
    time.sleep(0.5)
    Path(go).write_text("go")
    for p in procs:
        p.join(120)
    data = Path(path).read_bytes()
    lines = data.split(b"\n")
    tail = lines.pop()
    valid, invalid, seen = 0, 0, set()
    for chunk in lines:
        try:
            obj = json.loads(chunk.decode("utf-8"))
            seen.add((obj["w"], obj["n"]))
            valid += 1
        except Exception:
            invalid += 1
    result = {"mode": mode, "workers": workers, "records_each": records, "expected": workers * records,
              "lf_lines": len(lines), "valid_json_lines": valid, "invalid_lines": invalid,
              "unique_records": len(seen), "unterminated_tail_bytes": len(tail), "file_bytes": len(data),
              "exit_codes": [p.exitcode for p in procs], "python": sys.version, "platform": sys.platform}
    result["atomic"] = (valid == len(seen) == workers * records and invalid == 0 and not tail)
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
