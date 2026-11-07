"""Local evidence capture for the two stable CMD entry points; no live standard server."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent.parent
EVIDENCE = PACKAGE / "evidence"
GUARD = ROOT / "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/guard"


def save(label, value):
    path = EVIDENCE / (label + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def environment(label):
    secret_keys = {"GIGACHAT_CREDENTIALS", "GIGACHAT_SCOPE", "GIGACHAT_ACCESS_TOKEN"}
    env = {key: os.environ[key] for key in os.environ if key.upper() not in secret_keys}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(GUARD) + os.pathsep + str(ROOT),
               ORDINARY_GUARD_LOG=str(EVIDENCE / (label + ".guard.jsonl")),
               ORDINARY_GUARD_NETWORK="loopback", ORDINARY_GUARD_ROOT=str(ROOT))
    return env


mode = sys.argv[1]
if mode in ("regression", "regression_web_final"):
    with tempfile.TemporaryDirectory(prefix="wa-launcher-regression-") as directory:
        env = environment(mode)
        env["LOCALAPPDATA"] = directory
        command = [sys.executable, "-B", "-X", "utf8", "-m", "unittest", "test_web_alarm_launcher", "-v"]
        started = time.monotonic()
        with (EVIDENCE / (mode + ".stdout.txt")).open("xb") as out, (EVIDENCE / (mode + ".stderr.txt")).open("xb") as err:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=out, stderr=err, timeout=90)
        save(mode, dict(command=command, exit_code=result.returncode, elapsed_seconds=time.monotonic()-started,
                        standard_storage_redirected_to_temp=True))
        print((EVIDENCE / (mode + ".stderr.txt")).read_text(encoding="utf-8")[-4300:])
elif mode == "launch":
    entry = ROOT / "Start_WebAlarm_Test.cmd"
    before = set(Path(tempfile.gettempdir()).glob("stage5_тест_*"))
    command = f'"{os.environ["COMSPEC"]}" /d /c call "{entry}"'
    with (EVIDENCE / "launch.stdout.txt").open("xb") as out, (EVIDENCE / "launch.stderr.txt").open("xb") as err:
        child = subprocess.Popen(command, cwd=tempfile.gettempdir(), env=environment(mode),
                                 stdin=subprocess.PIPE, stdout=out, stderr=err)
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            text = (EVIDENCE / "launch.stdout.txt").read_text(encoding="utf-8", errors="replace")
            match = re.search(r"TEST OFFLINE · http://127\.0\.0\.1:(\d+)/", text)
            if match:
                break
            if child.poll() is not None:
                raise RuntimeError("TEST launcher exited before readiness; see full stdout/stderr")
            time.sleep(0.2)
        else:
            raise RuntimeError(f"TEST readiness timeout; owned CMD pid={child.pid}")
        connection = http.client.HTTPConnection("127.0.0.1", int(match[1]), timeout=5)
        connection.request("GET", "/")
        reply = connection.getresponse()
        page = reply.read()
        connection.close()
        assert reply.status == 200 and b'data-stage5-offline="true"' in page
        created = set(Path(tempfile.gettempdir()).glob("stage5_тест_*")) - before
        assert len(created) == 1, sorted(map(str, created))
        save("launch_ready", dict(command=command, cwd=tempfile.gettempdir(), cmd_pid=child.pid,
                                  port=int(match[1]), page_status=reply.status, offline_page=True,
                                  disposable_storage=list(map(str, created))))
        print("TEST ready; HTTP 200, OFFLINE marker, disposable storage. Close the TEST Tk window.", flush=True)
        code = child.wait(timeout=180)
        child.stdin.close()
        assert code == 0, code
        assert not any(path.exists() for path in created)
        save("launch_finished", dict(exit_code=code, disposable_storage_removed=True,
                                     utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        print("TEST closed normally; CMD exit 0; temporary storage removed.", flush=True)
elif mode == "web_launch":
    command = f'"{os.environ["COMSPEC"]}" /d /c call "{ROOT / "Start_WebAlarm_Test.cmd"}"'
    before = set(Path(tempfile.gettempdir()).glob("stage5_тест_*"))
    stop = EVIDENCE / "web_stop.signal"
    assert not stop.exists()
    with (EVIDENCE / "web_launch.stdout.txt").open("xb") as out, (EVIDENCE / "web_launch.stderr.txt").open("xb") as err:
        child = subprocess.Popen(command, cwd=tempfile.gettempdir(), env=environment(mode),
                                 stdin=subprocess.PIPE, stdout=out, stderr=err)
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            text = (EVIDENCE / "web_launch.stdout.txt").read_text(encoding="utf-8", errors="replace")
            match = re.search(r"TEST OFFLINE · http://127\.0\.0\.1:(\d+)/", text)
            if match:
                break
            assert child.poll() is None, "TEST exited before readiness"
            time.sleep(0.2)
        else:
            raise RuntimeError("Web TEST readiness timeout")
        connection = http.client.HTTPConnection("127.0.0.1", int(match[1]), timeout=5)
        connection.request("GET", "/")
        reply = connection.getresponse()
        assert reply.status == 200 and b'data-stage5-offline="true"' in reply.read()
        connection.close()
        created = set(Path(tempfile.gettempdir()).glob("stage5_тест_*")) - before
        assert len(created) == 1
        save("web_launch_ready", dict(command=command, cwd=tempfile.gettempdir(), cmd_pid=child.pid,
                                      port=int(match[1]), page_status=reply.status, offline_page=True,
                                      disposable_storage=list(map(str, created))))
        print("Web-only TEST ready; inspect the browser, then create evidence/web_stop.signal.", flush=True)
        deadline = time.monotonic() + 180
        while not stop.exists() and time.monotonic() < deadline:
            assert child.poll() is None, "TEST must stay running until Enter"
            time.sleep(0.2)
        child.communicate(input=b"\r\n", timeout=15)
        assert child.returncode == 0, child.returncode
        assert not any(path.exists() for path in created)
        save("web_launch_finished", dict(exit_code=child.returncode, enter_stops_server=True,
                                         disposable_storage_removed=True))
        print("Web-only TEST: Enter stops server, CMD exit 0, temporary storage removed.", flush=True)
elif mode == "error":
    with tempfile.TemporaryDirectory(prefix="wa-entry-error-") as directory:
        base = Path(directory) / "Папка с пробелами & TEST"
        base.mkdir()
        entry = base / "Start_WebAlarm_Test.cmd"
        shutil.copyfile(ROOT / entry.name, entry)
        command = f'"{os.environ["COMSPEC"]}" /d /c call "{entry}"'
        with (EVIDENCE / "error.stdout.txt").open("xb") as out, (EVIDENCE / "error.stderr.txt").open("xb") as err:
            child = subprocess.Popen(command, cwd=tempfile.gettempdir(), stdin=subprocess.PIPE, stdout=out, stderr=err)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if b"This window will stay open" in (EVIDENCE / "error.stdout.txt").read_bytes():
                    break
                time.sleep(0.1)
            assert child.poll() is None, "error window must wait for input"
            child.communicate(input=b"\r\n", timeout=10)
            assert child.returncode == 1
            save("error", dict(exit_code=child.returncode, missing_python=True, paused_before_input=True,
                               cwd_independent=True, path_with_spaces_cyrillic_ampersand=True))
        print("Missing Python: clear error, waits for input, exit 1; non-repository cwd and special path passed.")
elif mode in ("conservation", "conservation_final"):
    before = json.loads((EVIDENCE / "baseline.json").read_text(encoding="utf-8"))
    current = {}
    folders = [ROOT / name for name in (".ultra", "Чат_pro", "Чат_Pro_01", ".obsidian")]
    folders.append(Path(os.environ["LOCALAPPDATA"]) / "WebAlarmWorkspace")
    for folder in folders:
        for directory, dirs, files in os.walk(folder, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink() and not (Path(directory) / d).is_junction()]
            for name in files:
                path = Path(directory) / name
                if not path.is_symlink():
                    data = path.read_bytes()
                    current[str(path)] = [len(data), hashlib.sha256(data).hexdigest()]
    changes = sorted(name for name in before["protected"].keys() | current.keys()
                     if before["protected"].get(name) != current.get(name))
    unchanged = []
    for name, expected in before["sources"].items():
        if name in ("web_alarm/launcher.py", "test_web_alarm_launcher.py",
                    "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/review_fixture.py"):
            continue
        data = (ROOT / name).read_bytes()
        assert [len(data), hashlib.sha256(data).hexdigest()] == expected, name
        unchanged.append(name)
    save(mode, dict(protected_file_count=len(before["protected"]), changed_existing_files=changes,
                              unchanged_sources=unchanged))
    print("Protected files:", len(before["protected"]), "changed:", len(changes))
    assert not changes, changes
else:
    raise SystemExit("Unknown check")
