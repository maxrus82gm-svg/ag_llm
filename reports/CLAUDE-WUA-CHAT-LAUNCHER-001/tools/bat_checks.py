"""End-to-end checks of Start_WebAlarm.bat through cmd.exe (CLAUDE-WUA-CHAT-LAUNCHER-001).

The guarded test runner forbids non-Python children, so these run outside it with the same isolation: every child
gets LOCALAPPDATA / APPDATA inside a fresh TEMP folder, hence the "standard storage" of these runs is disposable. The
user's real standard storage is only compared by its folder times before and after (never read or written). Only
exit codes and yes/no facts are published: the console output contains local paths and is not stored.
Usage: bat_checks.py <out.json>
"""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BAT = REPO / "Start_WebAlarm.bat"
GREEN, RED = "СТАНДАРТНЫЙ ЗАПУСК — WEB ALARM ULTRA", "ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК"
base = Path(tempfile.mkdtemp(prefix="wa-bat-checks-")).resolve()
env = dict(os.environ, LOCALAPPDATA=str(base / "localappdata"), APPDATA=str(base / "appdata"))
for key in ("LOCALAPPDATA", "APPDATA"):
    Path(env[key]).mkdir()
real_root = Path(os.environ["LOCALAPPDATA"]) / "WebAlarmWorkspace"


def real_times():
    if not real_root.exists():
        return None
    return {p.name: p.stat().st_mtime_ns for p in [real_root, *sorted(real_root.iterdir())] if p.is_dir()}


def bat(path: Path, args: str, cwd: Path, timeout=120):
    done = subprocess.run(f'cmd /d /s /c ""{path}" {args}"', cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return done.returncode, done.stdout.decode("utf-8", "replace")


def config(name: str, active: str, **profile_changes) -> Path:
    data = json.loads((REPO / "web_alarm" / "launch_config.json").read_text(encoding="utf-8"))
    data["active"] = active
    for profile, changes in profile_changes.items():
        data["test_profiles"][profile].update(changes)
    path = base / name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def listening(port):
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def result(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


checks = {}
real_before = real_times()
elsewhere = base / "some other folder"
elsewhere.mkdir()

# B1 standard launch from a foreign current folder (as a desktop shortcut would start it)
code, out = bat(BAT, f'--self-test "{base / "b1.json"}"', elsewhere)
r = result(base / "b1.json")
checks["B1_standard_from_other_folder"] = {
    "exit": code, "green_banner": GREEN in out, "red_banner": RED in out,
    "self_test": r and {k: r[k] for k in ("standard", "storage_is_default", "page_unchanged_from_ui", "page_marked_as_test",
                                           "ultra_chat_available", "status", "stopped", "port")},
    "standard_storage_created_in_isolated_folder": (Path(env["LOCALAPPDATA"]) / "WebAlarmWorkspace").is_dir()}

# B2 a test profile chosen in the configuration, same BAT
port = free_port()
test_cfg = config("test.json", "isolated-empty", **{"isolated-empty": {"port": port}})
code, out = bat(BAT, f'--config "{test_cfg}" --self-test "{base / "b2.json"}"', elsewhere)
r = result(base / "b2.json")
checks["B2_test_profile"] = {"exit": code, "red_banner": RED in out, "profile_name_shown": "isolated-empty" in out,
                             "green_banner": GREEN in out, "return_hint_shown": '"active": "standard"' in out,
                             "self_test": r and {k: r[k] for k in ("standard", "storage_is_default", "page_marked_as_test",
                                                                    "page_is_current", "stopped")}}

# B3 back to standard: only "active" changes in the same configuration file
data = json.loads(test_cfg.read_text(encoding="utf-8"))
data["active"] = "standard"
test_cfg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
code, out = bat(BAT, f'--config "{test_cfg}" --self-test "{base / "b3.json"}"', elsewhere)
r = result(base / "b3.json")
checks["B3_switch_back_to_standard"] = {"exit": code, "green_banner": GREEN in out, "red_banner": RED in out,
                                         "standard": r and r["standard"], "page_marked_as_test": r and r["page_marked_as_test"]}

# B4 a real .lnk shortcut started by the shell in its own console window
lnk = base / "Web Alarm Ultra.lnk"
shell_env = dict(env, WA_LNK=str(lnk), WA_BAT=str(BAT), WA_ARGS=f'--self-test "{base / "b4.json"}"', WA_WD=str(elsewhere))
subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:WA_LNK);$s.TargetPath=$env:WA_BAT;"
                "$s.Arguments=$env:WA_ARGS;$s.WorkingDirectory=$env:WA_WD;$s.Save()"], env=shell_env, check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
started = time.time()
subprocess.run(f'cmd /d /c start "" /wait "{lnk}"', env=env, stdin=subprocess.DEVNULL, timeout=120)
while not (base / "b4.json").exists() and time.time() - started < 60:
    time.sleep(0.5)
r = result(base / "b4.json")
checks["B4_desktop_shortcut_own_console"] = {"shortcut_created": lnk.exists(),
                                             "self_test": r and {k: r[k] for k in ("standard", "storage_is_default", "page_unchanged_from_ui",
                                                                                    "console_colors", "status", "stopped")}}

# B5 a portable copy under a path with a space and Cyrillic, without the project .venv
mirror = base / "Web Alarm копия"
(mirror / "web_alarm").mkdir(parents=True)
shutil.copy2(BAT, mirror / BAT.name)
for path in (REPO / "web_alarm").iterdir():
    if path.suffix in {".py", ".json"}:
        shutil.copy2(path, mirror / "web_alarm" / path.name)
for name in ("context_storage.py", "model_registry.py"):
    shutil.copy2(REPO / name, mirror / name)
code, out = bat(mirror / BAT.name, f'--self-test "{base / "b5.json"}"', elsewhere)
r = result(base / "b5.json")
checks["B5_portable_copy_without_venv"] = {"exit": code, "fallback_python_announced": "Project .venv not found" in out,
                                           "green_banner": GREEN in out,
                                           "self_test": r and {k: r[k] for k in ("standard", "page_unchanged_from_ui", "status", "stopped")}}
shutil.rmtree(mirror)

# B6 a broken configuration stops with a red message and the BAT keeps the window open (pause)
bad = base / "bad.json"
bad.write_text("{", encoding="utf-8")
code, out = bat(BAT, f'--config "{bad}"', elsewhere)
checks["B6_refused_configuration"] = {"exit": code, "stopped_message": "ЗАПУСК ОСТАНОВЛЕН" in out,
                                      "bat_reports_code": "Web Alarm finished with code 2" in out, "server_started": "Сервер работает" in out}

# B7 the standard port is taken by another program
if not listening(8765):
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 8765))
    blocker.listen()
    try:
        code, out = bat(BAT, f'--self-test "{base / "b7.json"}"', elsewhere)
    finally:
        blocker.close()
    checks["B7_standard_port_busy"] = {"exit": code, "busy_message": "занят другой программой" in out,
                                       "self_test_written": (base / "b7.json").exists()}
else:
    checks["B7_standard_port_busy"] = "NOT RUN: port 8765 already in use on this computer"

# B8 double-click while running, then Ctrl+Break stops the first one cleanly
if not listening(8765):
    first = subprocess.Popen(f'cmd /d /s /c ""{BAT}" --no-browser"', cwd=elsewhere, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    seen, deadline = b"", time.time() + 60
    while time.time() < deadline and "Сервер работает".encode() not in seen:
        chunk = first.stdout.readline()
        if not chunk:
            break
        seen += chunk
    code2, out2 = bat(BAT, "--no-browser", elsewhere)
    os.kill(first.pid, signal.CTRL_BREAK_EVENT)
    try:
        rest, _ = first.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        first.kill()
        rest, _ = first.communicate()
    text = (seen + rest).decode("utf-8", "replace")
    time.sleep(1)
    checks["B8_second_click_and_ctrl_break"] = {
        "first_served": "Сервер работает" in text, "second_exit": code2, "second_reused_running": "уже работает" in out2,
        "second_started_another_server": "Сервер работает" in out2, "first_stopped_message": "Сервер остановлен." in text,
        "port_free_after_stop": not listening(8765)}
else:
    checks["B8_second_click_and_ctrl_break"] = "NOT RUN: port 8765 already in use on this computer"

checks["real_standard_storage_untouched"] = real_times() == real_before
shutil.rmtree(base, ignore_errors=True)
record = {"task": "CLAUDE-WUA-CHAT-LAUNCHER-001", "runner": "cmd.exe + Start_WebAlarm.bat, isolated LOCALAPPDATA/APPDATA in TEMP",
          "python": sys.version.split()[0], "checks": checks}
Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(checks, ensure_ascii=False, indent=1))
