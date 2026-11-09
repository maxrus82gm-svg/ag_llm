"""Focused activation checks, including the real permanent Windows TEST CMD."""
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time
import unittest
from uuid import uuid4

from web_alarm import launcher

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "reports/CODEX-WUA-CHAT-ORDINARY-TEST-ACTIVATION-001"


class ActivationTests(unittest.TestCase):
    def test_active_profile_uses_bridge_and_old_stage5_is_available(self):
        config = ROOT / "web_alarm/launch_test_config.json"
        launch = launcher.load_launch(config)
        self.assertEqual((launch.name, launch.standard, launch.script),
                         ("ordinary-core-offline", False, "web_alarm/ordinary_test_fixture.py"))
        raw = json.loads(config.read_text(encoding="utf-8"))
        raw["active"] = "stage5-offline"
        with tempfile.TemporaryDirectory(prefix="activation_config_") as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            old = launcher.load_launch(path)
        self.assertEqual(old.script, "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/review_fixture.py")
        self.assertEqual(old.args, ("--web",))

    def test_missing_test_config_cannot_fall_back_to_standard(self):
        import io
        with tempfile.TemporaryDirectory(prefix="activation_missing_") as temp:
            output = io.StringIO()
            code = launcher.main(["--config", str(Path(temp) / "missing.json"), "--require-test"], out=output)
        self.assertEqual(code, 2)
        self.assertIn("ЗАПУСК ОСТАНОВЛЕН", output.getvalue())

    @unittest.skipUnless(os.name == "nt", "physical CMD check requires Windows")
    def test_permanent_cmd_chat_flow_and_cleanup(self):
        protected = ["Start_WebAlarm_Standard.cmd", "Start_WebAlarm_Test.cmd", "web_alarm/launcher.py"]
        before = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in protected}
        env = {k: os.environ[k] for k in os.environ if not k.upper().startswith("GIGACHAT_")}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        # An environment marker alone must never skip installing the guard.
        env["ORDINARY_GUARD_LOG"] = "caller-marker-is-not-proof-of-a-guard"
        command = [env.get("COMSPEC", "cmd.exe"), "/d", "/c", str(ROOT / "Start_WebAlarm_Test.cmd")]
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        lines, output = queue.Queue(), []

        def read():
            for raw in iter(process.stdout.readline, b""):
                text = raw.decode("utf-8", errors="replace")
                output.append(text)
                lines.put(text)
        reader = threading.Thread(target=read, daemon=True); reader.start()
        ready = None
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    line = lines.get(timeout=.2)
                except queue.Empty:
                    self.assertIsNone(process.poll(), "".join(output))
                    continue
                if line.startswith("ORDINARY_TEST_READY "):
                    ready = json.loads(line.split(" ", 1)[1]); break
            self.assertIsNotNone(ready, "".join(output))
            root = Path(ready["root"]).resolve()
            self.assertEqual(root.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue(root.name.startswith("ordinary_core_TEST_"))
            self.assertTrue(ready["browser_requested"])
            self.assertFalse(ready["real_available"])
            origin = ready["url"].rstrip("/")
            port = int(origin.rsplit(":", 1)[1])

            def http(method, path, body=None, headers=None):
                conn = HTTPConnection("127.0.0.1", port, timeout=8)
                try:
                    conn.request(method, path, None if body is None else json.dumps(body).encode("utf-8"),
                                 {"Content-Type": "application/json", **(headers or {})})
                    response = conn.getresponse(); data = response.read()
                    return response.status, json.loads(data) if "application/json" in response.getheader("Content-Type", "") else data.decode("utf-8")
                finally:
                    conn.close()

            _, capability = http("GET", "/ui/ultra-chat/capability")
            self.assertTrue(capability["turn_test"]["core_bridge"])
            self.assertFalse(capability["turn_test"]["real_available"])
            self.assertTrue(capability["turn_test"]["models"])
            readcap = capability["ultra_chat"]
            readheaders = {readcap["header"]: readcap["token"]}
            _, capability = http("GET", "/ui/ultra-chat/write-capability")
            writecap = capability["ultra_chat_write"]
            write = {writecap["header"]: writecap["token"], "Origin": origin}
            code, workspace = http("POST", "/ultra/chat/workspaces", {"title": "Activation fixture"}, write)
            self.assertEqual(code, 201)
            ws = workspace["wa_workspace_id"]
            base = f"/ultra/chat/workspaces/{ws}/chats"
            chats = ["chat_" + uuid4().hex for _ in range(2)]
            for index, chat in enumerate(chats):
                body = {"chat_id": chat, **({"initialize_workspace": True} if index == 0 else {})}
                self.assertEqual(http("POST", base, body, write)[0], 201)
            turns = []
            for chat, text in [(chats[0], "first-A"), (chats[1], "private-B"),
                               (chats[0], "second-A"), (chats[0], "third-A")]:
                path = f"{base}/{chat}/turns"
                body = {"idempotency_key": uuid4().hex, "model_ref": "gigachat_2_pro", "text": text}
                code, turn = http("POST", path, body, write)
                self.assertEqual((code, turn["state"]), (200, "SUCCEEDED"))
                self.assertEqual(http("POST", path, body, write), (200, turn))
                self.assertEqual(http("GET", path + "/latest", headers=readheaders)[1]["turn"], turn)
                turns.append(turn)
            import run_store
            summary = run_store.load_run_summary(root / "projects" / ws, turns[-1]["run_id"], chats[0])
            context = summary["turn"]["prepared"]["context"]
            self.assertEqual([m["content"] for m in context if m["role"] == "user"], ["first-A", "second-A"])
            self.assertNotIn("private-B", repr(context))
            path = f"{base}/{chats[0]}/messages"
            _, history = http("GET", path, headers=readheaders)
            self.assertEqual(len(history["messages"]), 6)
            self.assertEqual(http("GET", path, headers=readheaders)[1], history)
            self.assertIn('data-stage5-offline="true"', http("GET", "/")[1])
            bad = {"idempotency_key": uuid4().hex, "text": "no real call", "model_ref": "gigachat_2_pro", "config_ref": "REAL"}
            self.assertEqual(http("POST", f"{base}/{chats[0]}/turns", bad, write)[0], 400)
            self.assertEqual(http("GET", path, headers=readheaders)[1], history)
            self.assertEqual(ready["core_bridge"], True)
        finally:
            if process.poll() is None:
                process.stdin.write(b"\n"); process.stdin.flush(); process.stdin.close()
            code = process.wait(timeout=20)
            reader.join(5)
            process.stdout.close()
            (PACKAGE / "evidence/cmd.stdout.txt").write_text("".join(output), encoding="utf-8")
        self.assertEqual(code, 0, "".join(output))
        self.assertIn("ORDINARY_TEST_CLEANED", "".join(output))
        self.assertFalse(Path(ready["root"]).exists())
        self.assertEqual(before, {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in protected})
        (PACKAGE / "evidence/cmd_result.json").write_text(json.dumps({
            "command": command, "exit_code": code, "core_bridge": True,
            "browser_requested": ready["browser_requested"], "browser_opened": ready["browser_opened"],
            "two_chats": True, "complete_context": True, "replay_no_duplicates": True,
            "http_reopen": True, "real_denied": True, "temp_removed": True,
            "protected_launch_files_unchanged": True, "visual_browser_F5": "NOT RUN"}, indent=2), encoding="utf-8")
