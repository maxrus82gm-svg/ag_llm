"""Server restart keeps the board: two real processes of tools/demo_evm_dnd.py over one TEMP storage.

1. start the demo (new storage), read /ultra/model-cards over HTTP;
2. save a new API order and favourites with an MCP and a local reference, exactly as the page does
   (POST /ultra/model-cards/view, same-origin Origin header);
3. stop the process, start a new one over the same storage, read again and compare;
4. remove the TEMP storage. Synthetic data only: no real storage, keys, network beyond loopback.
Usage: restart_check.py <out.json>
"""
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(base: Path, port: int) -> subprocess.Popen:
    proc = subprocess.Popen([sys.executable, "-B", str(TOOLS / "demo_evm_dnd.py"), "--port", str(port), "--base", str(base)],
                            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    line = proc.stdout.readline()
    if "on http://127.0.0.1:" not in line:
        proc.kill()
        raise SystemExit("the demo did not start: " + line)
    return proc


def call(port: int, method: str, path: str, body=None):
    origin = f"http://127.0.0.1:{port}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(origin + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **({"Origin": origin} if method != "GET" else {})})
    with urllib.request.urlopen(req, timeout=10) as answer:
        return json.loads(answer.read().decode("utf-8"))


def stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def main():
    base = Path(tempfile.mkdtemp(prefix="claude-evmdnd-restart-"))
    record = {"task": "CLAUDE-WUA-EVM-INTERACTION-DND-001", "purpose": "the board survives a server restart (two demo processes, one storage)"}
    try:
        port = free_port()
        first = start(base, port)
        try:
            view = call(port, "GET", "/ultra/model-cards")["view"]
            api = list(reversed(view["sections"]["api"]))
            view = call(port, "POST", "/ultra/model-cards/view", {"base_revision": view["revision"], "section": "api", "order": api})["view"]
            favs = ["local:demo:qwen-14b"] + view["sections"]["favorites"] + ["mcp:demo:files-tool"]
            saved = call(port, "POST", "/ultra/model-cards/view", {"base_revision": view["revision"], "section": "favorites", "order": favs})["view"]
        finally:
            stop(first)
        time.sleep(0.5)
        port2 = free_port()
        second = start(base, port2)
        try:
            again = call(port2, "GET", "/ultra/model-cards")["view"]
        finally:
            stop(second)
        tail = lambda ids: [x.split(":", 1)[0] + ":" + x.rsplit(":", 1)[-1] for x in ids]
        record.update({
            "saved_before_restart": {"revision": saved["revision"], "api": tail(saved["sections"]["api"]), "favorites": tail(saved["sections"]["favorites"])},
            "read_after_restart": {"revision": again["revision"], "api": tail(again["sections"]["api"]), "favorites": tail(again["sections"]["favorites"])},
            "same": again["sections"] == saved["sections"] and again["revision"] == saved["revision"],
            "processes": 2, "ports_differ": port != port2,
        })
    finally:
        shutil.rmtree(base, ignore_errors=True)
    record["verdict"] = "PASS" if record.get("same") else "FAIL"
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": record["verdict"], "revision": record.get("read_after_restart", {}).get("revision")}))
    sys.exit(0 if record["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
