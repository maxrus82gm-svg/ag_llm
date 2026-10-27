"""The one permanent Start_WebAlarm.bat and its launcher (CLAUDE-WUA-CHAT-LAUNCHER-001).

Standard launch = the main application with the usual persistent storage, green banner, page unchanged. Any other
launch = a named test profile with a red warning, a pause before the browser, a marked page and its own TEMP storage
and port. Run under the guarded runner: LOCALAPPDATA points into TEMP there, so the "standard storage" of these
tests is a disposable folder. Loopback only; no browser is opened (the opener is replaced).
"""
from __future__ import annotations

import _thread
import io
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from web_alarm import launcher
from web_alarm import server as wa_server
from web_alarm.workspace_registry import default_storage_root


def leftover_storages() -> set:
    return set(Path(tempfile.gettempdir()).glob("wa-test-launch-*"))

REPO = Path(launcher.__file__).resolve().parents[1]
BAT = REPO / "Start_WebAlarm.bat"
SHIPPED = json.loads(launcher.CONFIG_PATH.read_text(encoding="utf-8"))


def config(base: Path, active: str, **profile_changes) -> Path:
    data = json.loads(json.dumps(SHIPPED))
    data["active"] = active
    for name, changes in profile_changes.items():
        data["test_profiles"].setdefault(name, {}).update(changes)
    path = base / "launch_config.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_launch_")).resolve()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.base, ignore_errors=True))
        self.assertTrue(str(default_storage_root()).startswith(tempfile.gettempdir()[:3]))

    def run_launch(self, launch, **kwargs):
        """Whichever way a launch ends (self-test, refusal, stop), it leaves no disposable test storage behind."""
        before = leftover_storages()
        out = io.StringIO()
        code = launcher.run_web_alarm(launch, out=out, colors=False, **kwargs)
        self.assertEqual(leftover_storages() - before, set(), "the disposable test storage must be removed when the launch ends")
        return code, out.getvalue()


class ConfigTests(Base):
    def test_l1_the_shipped_configuration_is_the_standard_launch(self):
        launch = launcher.load_launch()
        self.assertEqual((launch.name, launch.standard, launch.storage, launch.port), ("standard", True, "default", 8765),
                         "a test profile is left active in web_alarm/launch_config.json - return it to \"standard\"")
        self.assertNotIn("standard", SHIPPED["test_profiles"])

    def test_l2_missing_file_is_standard_and_every_shipped_profile_is_valid_and_non_standard(self):
        self.assertTrue(launcher.load_launch(self.base / "absent.json").standard)
        for name in SHIPPED["test_profiles"]:
            with self.subTest(profile=name):
                launch = launcher.load_launch(config(self.base, name))
                self.assertEqual((launch.name, launch.standard), (name, False))
                self.assertNotEqual(launch.port, launcher.STANDARD_PORT)

    def test_l3_unsafe_or_broken_configurations_are_refused(self):
        cases = {
            "unknown active": lambda: config(self.base, "nope"),
            "profile named standard": lambda: config(self.base, "standard", standard={"title": "x", "kind": "web_alarm", "storage": "temp", "port": 9000}),
            "standard storage": lambda: config(self.base, "isolated-empty", **{"isolated-empty": {"storage": "default"}}),
            "standard port": lambda: config(self.base, "isolated-empty", **{"isolated-empty": {"port": 8765}}),
            "low port": lambda: config(self.base, "isolated-empty", **{"isolated-empty": {"port": 80}}),
            "unknown field": lambda: config(self.base, "isolated-empty", **{"isolated-empty": {"command": "rm"}}),
            "no title": lambda: config(self.base, "isolated-empty", **{"isolated-empty": {"title": " "}}),
            "unknown kind": lambda: config(self.base, "isolated-empty", **{"isolated-empty": {"kind": "shell"}}),
            "script outside": lambda: config(self.base, "wa4o-review", **{"wa4o-review": {"script": "../x.py"}}),
            "script absolute": lambda: config(self.base, "wa4o-review", **{"wa4o-review": {"script": "C:/x.py"}}),
            "script missing": lambda: config(self.base, "wa4o-review", **{"wa4o-review": {"script": "no_such_file.py"}}),
            "script not python": lambda: config(self.base, "wa4o-review", **{"wa4o-review": {"script": "Start_WebAlarm.bat"}}),
            "args not strings": lambda: config(self.base, "wa4o-review", **{"wa4o-review": {"args": [1]}}),
        }
        for label, make in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(launcher.LaunchConfigError):
                    launcher.load_launch(make())
        for label, text in (("broken json", "{"), ("duplicate key", '{"schema_version":1,"active":"standard","active":"x"}'),
                            ("other version", '{"schema_version":2,"active":"standard"}'), ("extra key", '{"schema_version":1,"x":1}')):
            with self.subTest(case=label):
                path = self.base / "raw.json"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(launcher.LaunchConfigError):
                    launcher.load_launch(path)

    def test_l4_machine_port_binding_moves_the_standard_port_and_stays_visible(self):
        with patch.dict(os.environ, {"WEB_ALARM_PORT": "9123"}):
            launch = launcher.load_launch(self.base / "absent.json")
            self.assertEqual((launch.standard, launch.port), (True, 9123))
            self.assertIn("WEB_ALARM_PORT", launcher.banner(launch, "u", "s", colors=False))
            with self.assertRaises(launcher.LaunchConfigError):
                launcher.load_launch(config(self.base, "isolated-empty", **{"isolated-empty": {"port": 9123}}))
        for bad in ("80", "x", "70000"):
            with self.subTest(value=bad), patch.dict(os.environ, {"WEB_ALARM_PORT": bad}):
                with self.assertRaises(launcher.LaunchConfigError):
                    launcher.load_launch(self.base / "absent.json")


class BannerAndPageTests(Base):
    def test_b1_standard_banner_is_green_and_test_banner_is_red_with_the_profile_name(self):
        standard = launcher.standard_launch()
        text = launcher.banner(standard, "http://127.0.0.1:8765/", "store", colors=True)
        self.assertIn(launcher.ESC + "[1;97;42m " + "СТАНДАРТНЫЙ ЗАПУСК — WEB ALARM ULTRA", text)
        self.assertNotIn("НЕСТАНДАРТНЫЙ", text)
        test = launcher.load_launch(config(self.base, "isolated-empty"))
        text = launcher.banner(test, "http://127.0.0.1:8766/", "tmp", colors=True)
        self.assertIn(launcher.ESC + "[1;97;41m " + "ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК", text)
        self.assertIn("isolated-empty", text)
        self.assertIn('"active": "standard"', text)
        self.assertNotIn("СТАНДАРТНЫЙ ЗАПУСК — WEB ALARM ULTRA", text)
        plain = launcher.banner(test, "u", "s", colors=False)
        self.assertNotIn(launcher.ESC, plain)
        self.assertIn("ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК", plain)
        script = launcher.load_launch(config(self.base, "wa4o-review"))
        self.assertIn("Браузер этот запуск не помечает", launcher.banner(script, "-", "-", colors=False))

    def test_b2_standard_page_is_unchanged_and_test_page_is_marked(self):
        page = wa_server.INDEX_HTML
        self.assertEqual(launcher.mark_page(page, launcher.standard_launch()), page)
        test = launcher.Launch(name="<b>x</b>", title="t", standard=False, storage="temp", port=9000)
        marked = launcher.mark_page(page, test)
        self.assertIn("<title>[ТЕСТ: &lt;b&gt;x&lt;/b&gt;] ", marked)
        self.assertIn("ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК · &lt;b&gt;x&lt;/b&gt;", marked)
        self.assertIn("position:fixed;inset:0;border:5px solid #d11a35;pointer-events:none", marked)
        self.assertNotIn("<b>x</b>", marked)
        self.assertEqual(marked.count('role="alert" style="position:fixed'), 1)


class RunTests(Base):
    def test_r1_standard_self_test_serves_the_unchanged_page_from_the_standard_storage(self):
        result = self.base / "r.json"
        code, text = self.run_launch(launcher.standard_launch(), self_test=result, port=0)
        data = json.loads(result.read_text(encoding="utf-8"))
        self.assertEqual(code, 0, text)
        self.assertEqual((data["standard"], data["storage_is_default"], data["page_unchanged_from_ui"],
                          data["page_marked_as_test"], data["ultra_chat_available"], data["stopped"]),
                         (True, True, True, False, True, True))
        self.assertIn("СТАНДАРТНЫЙ ЗАПУСК — WEB ALARM ULTRA", text)
        self.assertTrue(default_storage_root().is_dir())

    def test_r2_test_profile_uses_its_own_temp_storage_and_marks_the_page(self):
        result = self.base / "r.json"
        launch = launcher.load_launch(config(self.base, "isolated-empty"))
        before = set(Path(tempfile.gettempdir()).glob("wa-test-launch-isolated-empty-*"))
        code, text = self.run_launch(launch, self_test=result, port=0)
        data = json.loads(result.read_text(encoding="utf-8"))
        self.assertEqual(code, 0, text)
        self.assertEqual((data["standard"], data["storage_is_default"], data["page_marked_as_test"],
                          data["page_is_current"]), (False, False, True, True))
        left = set(Path(tempfile.gettempdir()).glob("wa-test-launch-isolated-empty-*")) - before
        self.assertEqual(left, set(), "the disposable test storage must be removed when the launch stops")
        self.assertIn("ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК", text)
        self.assertIn("isolated-empty", text)

    def test_r3_test_warning_stays_five_seconds_before_the_browser_and_standard_opens_at_once(self):
        for launch, expected_sleeps in ((launcher.standard_launch(), 0),
                                        (launcher.load_launch(config(self.base, "isolated-empty")), 5)):
            with self.subTest(standard=launch.standard):
                events = []

                def opener(url):
                    events.append(("open", url))
                    _thread.interrupt_main()  # the user closes the window while the server runs
                with patch.object(launcher, "_stop_on_break"):
                    code, text = self.run_launch(launch, port=0, sleep=lambda s: events.append(("sleep", s)),
                                                 opener=opener)
                    time.sleep(0.1)
                self.assertEqual(code, 0)
                self.assertEqual([e[0] for e in events], ["sleep"] * expected_sleeps + ["open"])
                self.assertTrue(text.rstrip().endswith("Сервер остановлен."))
                port = int(re.search(r"127\.0\.0\.1:(\d+)/", events[-1][1]).group(1))
                with socket.socket() as again:
                    again.bind(("127.0.0.1", port))  # the port was released

    @staticmethod
    def must_not_open(url):
        raise AssertionError("a refused launch must not open the browser (and must not start serving)")

    def test_r4_a_busy_port_is_reported_and_an_identical_running_launch_is_reused(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        self.addCleanup(listener.close)
        opened = []
        code, text = self.run_launch(launcher.standard_launch(), port=listener.getsockname()[1], opener=self.must_not_open)
        self.assertEqual(code, 3)
        self.assertIn("занят другой программой", text)
        other_storage = wa_server.create_server(wa_server.WebAlarmApi(self.base / "other"), port=0)
        threading.Thread(target=other_storage.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (other_storage.shutdown(), other_storage.server_close()))
        code, text = self.run_launch(launcher.standard_launch(), port=other_storage.server_port, opener=self.must_not_open)
        self.assertEqual(code, 3, "the same page with another storage is not the standard launch")
        running = wa_server.create_server(wa_server.WebAlarmApi(None), port=0)  # standard storage (TEMP here)
        thread = threading.Thread(target=running.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (running.shutdown(), running.server_close()))
        port = running.server_port
        code, text = self.run_launch(launcher.standard_launch(), port=port, opener=opened.append)
        self.assertEqual((code, opened), (0, [f"http://127.0.0.1:{port}/"]))
        self.assertIn("уже работает", text)
        test = launcher.load_launch(config(self.base, "isolated-empty"))
        code, text = self.run_launch(test, port=port, opener=self.must_not_open)
        self.assertEqual(code, 3, "a test launch must not reuse a standard server")
        code, text = self.run_launch(launcher.standard_launch(), port=port, opener=self.must_not_open, self_test=self.base / "x.json")
        self.assertEqual(code, 3, "a self-test never reuses a running server")

    def test_r9_a_second_launcher_on_the_same_port_is_refused_even_before_it_listens(self):
        # On Windows two HTTPServers with SO_REUSEADDR can share one port, so the port alone is no guard.
        port = free_port()
        holder = launcher._claim_port(port)
        self.assertIsNotNone(holder)
        try:
            code, text = self.run_launch(launcher.standard_launch(), port=port, opener=self.must_not_open)
            self.assertEqual(code, 3)
        finally:
            holder.release()
        result = self.base / "r.json"
        code, _ = self.run_launch(launcher.standard_launch(), port=port, self_test=result)
        self.assertEqual(code, 0, "the claim must be free again after its owner released it")
        again = launcher._claim_port(port)
        self.assertIsNotNone(again, "the self-test must release its claim")
        again.release()

    def test_r5_break_and_close_signals_end_the_server_through_the_same_stop_path(self):
        saved = {name: signal.getsignal(getattr(signal, name)) for name in ("SIGBREAK", "SIGTERM") if hasattr(signal, name)}
        try:
            launcher._stop_on_break()
            for name in saved:
                with self.subTest(signal=name):
                    with self.assertRaises(KeyboardInterrupt):
                        signal.getsignal(getattr(signal, name))(getattr(signal, name), None)
        finally:
            for name, handler in saved.items():
                signal.signal(getattr(signal, name), handler)

    def test_r6_ctrl_break_stops_a_real_launcher_process_cleanly(self):
        port = free_port()
        cfg = config(self.base, "isolated-empty", **{"isolated-empty": {"port": port}})
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        before = leftover_storages()
        child = subprocess.Popen([sys.executable, "-B", "-X", "utf8", "-m", "web_alarm.launcher", "--no-browser", "--config", str(cfg)],
                                 cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=flags,
                                 text=True, encoding="utf-8")
        lines = []
        deadline = time.time() + 30
        while time.time() < deadline:
            line = child.stdout.readline()
            lines.append(line)
            if "Сервер работает" in line or not line:
                break
        try:
            os.kill(child.pid, signal.CTRL_BREAK_EVENT)
        except (OSError, AttributeError) as exc:
            child.kill()
            child.communicate(timeout=10)
            self.skipTest(f"no console to deliver Ctrl+Break here ({type(exc).__name__}); stop path covered by r3/r5")
        rest, _ = child.communicate(timeout=30)
        output = "".join(lines) + rest
        self.assertEqual(child.returncode, 0, output[-500:])
        self.assertIn("ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК", output)
        self.assertIn("Сервер остановлен.", output)
        self.assertEqual(leftover_storages() - before, set(), "Ctrl+Break must also remove the test storage")

    def test_r7_script_profile_warns_then_runs_the_script_and_cannot_self_test(self):
        launch = launcher.load_launch(config(self.base, "wa4o-review"))
        sleeps, calls = [], []
        with patch.object(launcher.subprocess, "call", side_effect=lambda argv, cwd: calls.append((argv, cwd)) or 0), \
                patch.object(launcher, "_stop_on_break"):
            out = io.StringIO()
            self.assertEqual(launcher.run_script(launch, out=out, colors=False, sleep=sleeps.append), 0)
        self.assertEqual(sleeps, [1] * 5)
        self.assertEqual(calls, [([sys.executable, "-B", "-X", "utf8", "wa4o_ui_launcher.py"], launcher.REPO)])
        self.assertIn("ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК", out.getvalue())
        out = io.StringIO()
        self.assertEqual(launcher.main(["--config", str(config(self.base, "wa4o-review")), "--self-test", str(self.base / "s.json")], out=out), 2)

    def test_r8_a_refused_configuration_stops_with_a_red_message_and_nothing_starts(self):
        path = self.base / "bad.json"
        path.write_text("{", encoding="utf-8")
        out = io.StringIO()
        with patch.object(launcher, "run_web_alarm", side_effect=AssertionError("must not start")):
            self.assertEqual(launcher.main(["--config", str(path)], out=out), 2)
        self.assertIn("ЗАПУСК ОСТАНОВЛЕН", out.getvalue())
        self.assertIn('"active": "standard"', out.getvalue())


class BatTests(unittest.TestCase):
    def test_t1_the_bat_is_portable_ascii_and_only_delegates_to_the_launcher(self):
        raw = BAT.read_bytes()
        raw.decode("ascii")
        self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"), "batch files need CRLF line endings")
        text = raw.decode("ascii")
        self.assertIn('pushd "%~dp0"', text)
        self.assertIn('"%~dp0.venv\\Scripts\\python.exe"', text)
        self.assertIn("-m web_alarm.launcher %*", text)
        self.assertIn("pause", text)
        self.assertNotRegex(text, r"(?i)[a-z]:\\|\\users\\|8765|8766|8767|LOCALAPPDATA")
        self.assertEqual(sorted(p.name for p in REPO.glob("Start_WebAlarm*.bat")), ["Start_WebAlarm.bat"])


if __name__ == "__main__":
    unittest.main()
