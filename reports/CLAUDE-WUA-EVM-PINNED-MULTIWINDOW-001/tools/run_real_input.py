"""Run the real-input check of the pinned windows in its three phases on one synthetic storage:
1. main      - a fresh demo (tools/demo_evm_pins.py) and real_input_check.js main (regression + windows);
2. restored  - the demo process stopped and started again over the same storage: the windows must come back;
3. corrupt   - the demo stopped, only the layout part of ultra/evm_view.json damaged (the board kept), started again.
The storage is a new TEMP folder, removed at the end. Records: <out>/real_input_<phase>.json and <out>/real_input_run.json.
Usage: run_real_input.py <browser.exe> <out dir>
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(base: Path, port: int) -> subprocess.Popen:
    proc = subprocess.Popen([sys.executable, "-B", str(TOOLS / "demo_evm_pins.py"), "--port", str(port), "--base", str(base)],
                            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    line = proc.stdout.readline()
    if "on http://127.0.0.1:" not in line:
        proc.kill()
        raise SystemExit("the demo did not start: " + line)
    return proc


def stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def phase(browser: str, port: int, out: Path, name: str) -> dict:
    done = subprocess.run(["node", str(TOOLS / "real_input_check.js"), browser, f"http://127.0.0.1:{port}/#evm", str(out), name],
                          cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    record = out / f"real_input_{name}.json"
    facts = json.loads(record.read_text(encoding="utf-8")) if record.exists() else {}
    print(name, done.returncode, done.stdout.strip().splitlines()[-1] if done.stdout.strip() else done.stderr[-300:], flush=True)
    return {"exit": done.returncode, "checks": facts.get("checks"), "failed": facts.get("failed"),
            "failed_checks": [f"{s['step'][:3]}: {c['check']}" for s in facts.get("steps", []) for c in s["checks"] if not c["ok"]],
            "step_errors": [f"{s['step'][:3]}: {s['error']}" for s in facts.get("steps", []) if s.get("error")]}


def main():
    browser, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="claude-evmpins-run-"))
    view = base / "web_alarm_storage" / "ultra" / "evm_view.json"
    run = {"task": "CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", "purpose": "real browser input in three phases on one synthetic storage", "phases": {}}
    try:
        port = free_port()
        demo = start(base, port)
        try:
            run["phases"]["main"] = phase(browser, port, out, "main")
        finally:
            stop(demo)
        time.sleep(0.5)
        demo = start(base, free_port())
        port = int(demo.args[demo.args.index("--port") + 1])
        try:
            run["phases"]["restored"] = phase(browser, port, out, "restored")
        finally:
            stop(demo)
        stored = json.loads(view.read_text(encoding="utf-8"))
        board = {k: stored[k] for k in ("revision", "sections")}
        stored["layout"] = {"revision": stored["layout"]["revision"], "windows": [{"connection_id": "api:gigachat:gigachat_2", "x": "oops", "y": 1}]}
        view.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")
        run["damaged"] = "layout.windows[0].x is a string; revision and sections kept as they were"
        demo = start(base, free_port())
        port = int(demo.args[demo.args.index("--port") + 1])
        try:
            run["phases"]["corrupt"] = phase(browser, port, out, "corrupt")
        finally:
            stop(demo)
        after = json.loads(view.read_text(encoding="utf-8"))
        run["after_corrupt_phase"] = {"board_kept": {k: after[k] for k in ("revision", "sections")} == board,
                                      "layout_windows": len(after["layout"]["windows"]),
                                      "damaged_copies_kept": len([p for p in view.parent.iterdir() if p.name.startswith("evm_view.json.corrupt-")])}
    finally:
        shutil.rmtree(base, ignore_errors=True)
    run["checks"] = sum(p.get("checks") or 0 for p in run["phases"].values())
    run["failed"] = sum(p.get("failed") or 0 for p in run["phases"].values())
    (out / "real_input_run.json").write_text(json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"checks": run["checks"], "failed": run["failed"], **run.get("after_corrupt_phase", {})}, ensure_ascii=False))


if __name__ == "__main__":
    main()
