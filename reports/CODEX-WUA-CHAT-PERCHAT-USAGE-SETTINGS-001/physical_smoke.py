"""Focused P0/P1 smoke through the unchanged permanent TEST CMD."""
from pathlib import Path
from types import SimpleNamespace
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import test_web_alarm_ultra_chat_s5 as helpers

PACKAGE = Path(__file__).resolve().parent
env = {k: os.environ[k] for k in os.environ if not k.upper().startswith("GIGACHAT_")}
env["PYTHONDONTWRITEBYTECODE"] = "1"
cmd = [env.get("COMSPEC", "cmd.exe"), "/d", "/c", str(ROOT / "Start_WebAlarm_Test.cmd")]
process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdin=subprocess.PIPE,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
lines, transcript = queue.Queue(), []
def reader():
    for data in iter(process.stdout.readline, b""):
        line = data.decode("utf-8", errors="replace"); transcript.append(line); lines.put(line)
worker = threading.Thread(target=reader, daemon=True); worker.start()
ready = None
try:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try: line = lines.get(timeout=.2)
        except queue.Empty:
            assert process.poll() is None, "".join(transcript)
            continue
        if line.startswith("ORDINARY_TEST_READY "):
            ready = json.loads(line.split(" ", 1)[1]); break
    assert ready is not None, "".join(transcript)
    temp_root = Path(ready["root"]).resolve()
    assert temp_root.parent == Path(tempfile.gettempdir()).resolve()
    assert temp_root.name.startswith("ordinary_core_TEST_")
    server = SimpleNamespace(server_address=("127.0.0.1", int(ready["url"].rstrip("/").rsplit(":", 1)[1])))
    helper = helpers.HttpAndTkTests("test_http_cancel_reopen_usage_and_standard_gate")
    http = lambda *args, **kwargs: helper.http(server, *args, **kwargs)
    cap, read, write = helper.tokens(server)
    assert cap["chat_preferences"] and cap["core_bridge"] and not cap["real_available"]
    code, ws = http("POST", "/ultra/chat/workspaces", {"title": "Usage/settings synthetic smoke"}, write)
    assert code == 201
    chats = ["chat_" + uuid4().hex for _ in range(2)]
    base = f'/ultra/chat/workspaces/{ws["wa_workspace_id"]}/chats'
    for i, chat in enumerate(chats):
        assert http("POST", base, {"chat_id": chat, **({"initialize_workspace": True} if i == 0 else {})}, write)[0] == 201
    a, b = (f"{base}/{c}" for c in chats)
    settings = {"compression_threshold_tokens": 123456, "answer_tokens": 20000}
    assert http("POST", a + "/settings", settings, write)[0] == 200
    for model in ("gigachat_2_pro", "gigachat_ultra"):
        body = {"text": "synthetic smoke", "model_ref": model, "idempotency_key": uuid4().hex}
        code, turn = http("POST", a + "/turns", body, write)
        assert (code, turn["state"]) == (200, "SUCCEEDED")
        assert http("POST", a + "/turns", body, write) == (200, turn)
    for _ in range(2):
        saved = http("GET", a + "/settings", headers=read)[1]
        assert saved["settings"] == settings and saved["applied_to_provider"] is False
    assert http("GET", b + "/settings", headers=read)[1]["settings"] == {"compression_threshold_tokens": 250000, "answer_tokens": 10000}
    summary = http("GET", a + "/messages", headers=read)[1]["usage_summary"]
    assert summary["synthetic"] and summary["attempts"] == 2 and summary["missing"]["total_tokens"] == 2
    assert http("GET", b + "/messages", headers=read)[1]["usage_summary"]["attempts"] == 0
    assert http("POST", a + "/turns", {**body, "config_ref": "REAL"}, write)[0] == 400
    page = http("GET", "/")[1]
    assert 'id="chatUsage"' in page and 'id="chatPreferences"' in page
finally:
    if process.poll() is None:
        process.stdin.write(b"\n"); process.stdin.flush(); process.stdin.close()
    code = process.wait(timeout=20); worker.join(5); process.stdout.close()
    (PACKAGE / "evidence/physical.stdout.txt").write_text("".join(transcript), encoding="utf-8")
assert code == 0 and "ORDINARY_TEST_CLEANED" in "".join(transcript)
assert not temp_root.exists()
result = {"command": cmd, "exit_code": code, "browser_opened": ready["browser_opened"],
          "P0_unknown_and_chat_isolation": "PASS", "P1_saved_preferences_and_model_switch": "PASS",
          "repeat_no_duplicate": "PASS", "real_refusal": "PASS", "temp_cleanup": "PASS", "visual_F5": "NOT RUN"}
(PACKAGE / "evidence/physical.result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
