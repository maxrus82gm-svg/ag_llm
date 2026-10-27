"""Web Alarm Ultra launcher behind the one permanent Start_WebAlarm.bat (CLAUDE-WUA-CHAT-LAUNCHER-001).

The standard launch is built in and cannot be redefined: the main application (web_alarm.server) with its usual
persistent storage (``default_storage_root()``), loopback 127.0.0.1, the folder picker and Ultra Chat on. It prints
a green "СТАНДАРТНЫЙ ЗАПУСК — WEB ALARM ULTRA". Anything else is a named test profile from ``launch_config.json``:
a red "ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК" with the profile name, a pause before the browser opens and, when the
profile runs the main application, a red frame and badge on every page. A test profile can never use the standard
storage or the standard port. Returning to normal: ``"active": "standard"`` in launch_config.json.

Machine binding (portability, programme No.37 section 2.4): the standard port may be changed per computer with the
environment variable WEB_ALARM_PORT; no user path is written anywhere in the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TextIO

from . import server as wa_server
from .server import WebAlarmApi, create_server
from .store_lock import InterProcessLock, StoreLockTimeout
from .workspace_registry import default_storage_root

REPO = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(__file__).with_name("launch_config.json")
STANDARD = "standard"
STANDARD_PORT = 8765
HOST = "127.0.0.1"
TEST_WARNING_SECONDS = 5
ESC = chr(27)
STANDARD_TEXT = "СТАНДАРТНЫЙ ЗАПУСК — WEB ALARM ULTRA"
TEST_TEXT = "ВНИМАНИЕ! НЕСТАНДАРТНЫЙ ТЕСТОВЫЙ ЗАПУСК"
RETURN_HINT = 'Вернуть стандартный запуск: в web_alarm\\launch_config.json указать "active": "standard".'
_CONFIG_KEYS = {"_comment", "schema_version", "active", "test_profiles"}
_WEB_KEYS = {"title", "kind", "storage", "port", "folder_picker", "ultra_chat", "note"}
_SCRIPT_KEYS = {"title", "kind", "script", "args", "note"}


class LaunchConfigError(Exception):
    """The launch configuration cannot be used; the message is shown to the user as is."""


@dataclass(frozen=True)
class Launch:
    name: str
    title: str
    standard: bool
    kind: str = "web_alarm"
    storage: str = "default"
    port: int = STANDARD_PORT
    folder_picker: bool = True
    ultra_chat: bool = True
    script: str | None = None
    args: tuple[str, ...] = field(default_factory=tuple)


def standard_port() -> int:
    """8765, or this computer's own binding from WEB_ALARM_PORT."""
    raw = os.environ.get("WEB_ALARM_PORT", "").strip()
    if not raw:
        return STANDARD_PORT
    if not raw.isdigit() or not 1024 <= int(raw) <= 65535:
        raise LaunchConfigError(f"WEB_ALARM_PORT={raw!r}: нужен номер порта 1024–65535.")
    return int(raw)


def standard_launch() -> Launch:
    return Launch(name=STANDARD, title="Web Alarm Ultra", standard=True, port=standard_port())


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LaunchConfigError(f"launch_config.json: ключ {key!r} повторяется.")
        result[key] = value
    return result


def _profile(name: str, raw: Any) -> Launch:
    if not isinstance(raw, dict):
        raise LaunchConfigError(f"Профиль {name!r}: ожидается объект.")
    kind = raw.get("kind")
    allowed = _WEB_KEYS if kind == "web_alarm" else _SCRIPT_KEYS if kind == "python_script" else None
    if allowed is None:
        raise LaunchConfigError(f"Профиль {name!r}: kind должен быть \"web_alarm\" или \"python_script\".")
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise LaunchConfigError(f"Профиль {name!r}: неизвестные поля {unknown}.")
    title = raw.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise LaunchConfigError(f"Профиль {name!r}: нужно понятное название title (до 120 символов).")
    if kind == "python_script":
        script = raw.get("script")
        args = raw.get("args", [])
        if not isinstance(script, str) or not script.endswith(".py") or "\\" in script or script.startswith("/"):
            raise LaunchConfigError(f"Профиль {name!r}: script — путь .py внутри проекта через \"/\".")
        target = (REPO / script).resolve()
        if REPO not in target.parents or not target.is_file():
            raise LaunchConfigError(f"Профиль {name!r}: скрипт {script!r} не найден внутри проекта.")
        if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
            raise LaunchConfigError(f"Профиль {name!r}: args — список строк.")
        return Launch(name=name, title=title.strip(), standard=False, kind=kind, storage="script",
                      port=0, script=script, args=tuple(args))
    if raw.get("storage") != "temp":
        raise LaunchConfigError(f"Профиль {name!r}: тестовый запуск основного приложения использует только "
                                "storage \"temp\" — штатное хранилище пользователя ему недоступно.")
    port = raw.get("port")
    if not isinstance(port, int) or isinstance(port, bool) or not 1024 <= port <= 65535:
        raise LaunchConfigError(f"Профиль {name!r}: port — число 1024–65535.")
    if port == standard_port():
        raise LaunchConfigError(f"Профиль {name!r}: порт {port} занят стандартным запуском; нужен другой.")
    flags = {key: raw.get(key, True) for key in ("folder_picker", "ultra_chat")}
    if not all(isinstance(value, bool) for value in flags.values()):
        raise LaunchConfigError(f"Профиль {name!r}: folder_picker и ultra_chat — true или false.")
    return Launch(name=name, title=title.strip(), standard=False, kind=kind, storage="temp", port=port, **flags)


def load_launch(config_path: Path = CONFIG_PATH) -> Launch:
    """The launch chosen by the configuration; a missing file means the standard launch."""
    if not config_path.exists():
        return standard_launch()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, LaunchConfigError):
            raise
        raise LaunchConfigError("launch_config.json не читается как JSON. " + RETURN_HINT) from None
    if not isinstance(data, dict) or data.get("schema_version") != 1 or set(data) - _CONFIG_KEYS:
        raise LaunchConfigError("launch_config.json: ожидается объект schema_version 1 с полями "
                                "active и test_profiles.")
    active = data.get("active", STANDARD)
    profiles = data.get("test_profiles", {})
    if not isinstance(profiles, dict):
        raise LaunchConfigError("launch_config.json: test_profiles — объект.")
    if STANDARD in profiles:
        raise LaunchConfigError("launch_config.json: стандартный запуск встроен и не переопределяется профилем.")
    if active == STANDARD:
        return standard_launch()
    if not isinstance(active, str) or active not in profiles:
        raise LaunchConfigError(f"launch_config.json: профиль {active!r} не найден. " + RETURN_HINT)
    return _profile(active, profiles[active])


# --- console -------------------------------------------------------------------------------------------------

def enable_colors(stream: TextIO) -> bool:
    """Turn on ANSI colours of the Windows console; False when the output is not a console."""
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError):
        return False


def paint(text: str, background: int, colors: bool) -> str:
    return f"{ESC}[1;97;{background}m {text} {ESC}[0m" if colors else text


def set_console_title(title: str) -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except (AttributeError, OSError):
            pass


def banner(launch: Launch, url: str, storage: str, colors: bool) -> str:
    if launch.standard:
        lines = ["", paint(STANDARD_TEXT, 42, colors), "",
                 f"Приложение: основное Web Alarm Ultra · адрес {url}",
                 f"Хранилище: штатное постоянное ({storage})"]
        if launch.port != STANDARD_PORT:
            lines.append(f"Порт {launch.port} задан машинной настройкой WEB_ALARM_PORT.")
    else:
        lines = ["", paint("=" * 64, 41, colors), paint(TEST_TEXT, 41, colors), paint("=" * 64, 41, colors), "",
                 f"Конфигурация: {launch.name} — {launch.title}"]
        if launch.kind == "web_alarm":
            lines += [f"Приложение: основное Web Alarm Ultra с тестовыми данными · адрес {url}",
                      f"Хранилище: временное тестовое ({storage}); удаляется при остановке, "
                      "штатные данные не затрагиваются.",
                      "В браузере тестовый режим отмечен красной рамкой и надписью."]
        else:
            lines += [f"Приложение: тестовый скрипт {launch.script}; адрес и данные определяет он сам.",
                      "Браузер этот запуск не помечает — ориентируйтесь на это окно."]
        lines.append(RETURN_HINT)
    lines.append("Остановить: закройте это окно или нажмите Ctrl+C.")
    return "\n".join(lines) + "\n"


# --- browser marking -------------------------------------------------------------------------------------------

def mark_page(page: str, launch: Launch) -> str:
    """The standard page is served unchanged; a test launch adds a red frame and badge to every page."""
    if launch.standard:
        return page
    name = html.escape(launch.name)
    badge = ('<div role="alert" style="position:fixed;right:12px;bottom:12px;z-index:2147483647;'
             'background:#b3122b;color:#fff;font:700 13px system-ui,Segoe UI,sans-serif;padding:8px 12px;'
             'border-radius:8px;box-shadow:0 2px 10px #0008;pointer-events:none">'
             f'{TEST_TEXT} · {name}</div>')
    # A frame above the page (not behind it: the header and panels have their own backgrounds), click-through.
    frame = ('<div aria-hidden="true" style="position:fixed;inset:0;border:5px solid #d11a35;pointer-events:none;'
             'z-index:2147483646"></div>')
    page = page.replace("<title>", "<title>[ТЕСТ: " + name + "] ", 1)
    return page.replace("<body>", "<body>" + frame + badge, 1)


class _MarkedHandler(wa_server._JsonHandler):
    def _send_html(self, page: str) -> None:
        super()._send_html(mark_page(page, self.server.web_alarm_launch))


def page_version(page: str) -> str:
    return hashlib.sha256(page.encode("utf-8")).hexdigest()[:12]


# --- running ---------------------------------------------------------------------------------------------------

def _get(url: str, timeout: float = 3) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"Cache-Control": "no-store"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def _already_running(url: str, expected_page: str, expected_storage: Path | None) -> str:
    """"same" only when a Web Alarm with the very same page AND the very same storage serves the port."""
    if expected_storage is None:
        return "other"  # a test launch never reuses another server
    try:
        status, body = _get(url + "status")
        page_status, page = _get(url)
        storage = json.loads(body).get("storage_root")
    except (OSError, ValueError, AttributeError):
        return "other"
    same_storage = isinstance(storage, str) and (
        os.path.normcase(str(Path(storage).resolve())) == os.path.normcase(str(expected_storage.resolve())))
    if status == 200 and page_status == 200 and same_storage and page.decode("utf-8", "replace") == expected_page:
        return "same"
    return "other"


def _port_in_use(port: int) -> bool:
    """Something already listens there. Needed because on Windows two HTTPServers (SO_REUSEADDR) share a port."""
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((HOST, port)) == 0


def _claim_port(port: int) -> InterProcessLock | None:
    """One launcher per port on this computer: the lock dies with the process; None when another launcher has it."""
    lock = InterProcessLock(Path(tempfile.gettempdir()) / f"web-alarm-ultra-launch-{port}.lock", timeout=0.2)
    try:
        lock.acquire()
    except StoreLockTimeout:
        return None
    return lock


def _remove_temp_storage(storage_root: Path | None) -> None:
    """A test profile's storage is disposable; the standard storage (None here) is never touched."""
    if storage_root is not None and Path(tempfile.gettempdir()).resolve() in storage_root.resolve().parents:
        shutil.rmtree(storage_root, ignore_errors=True)


def _stop_on_break() -> None:
    def raise_interrupt(*_args):
        raise KeyboardInterrupt
    for name in ("SIGBREAK", "SIGTERM"):
        if hasattr(signal, name):
            try:
                signal.signal(getattr(signal, name), raise_interrupt)
            except (ValueError, OSError):
                pass


def run_web_alarm(launch: Launch, *, out: TextIO, colors: bool, open_browser: bool = True,
                  self_test: Path | None = None, port: int | None = None,
                  sleep: Callable[[float], None] = time.sleep, opener: Callable[[str], Any] = webbrowser.open) -> int:
    storage_root = None if launch.standard else Path(tempfile.mkdtemp(prefix=f"wa-test-launch-{launch.name}-"))
    storage_text = str(default_storage_root() if launch.standard else storage_root)
    bind_port = launch.port if port is None else port
    expected_page = mark_page(wa_server.INDEX_HTML, launch)
    claim = _claim_port(bind_port) if bind_port else None
    try:
        if bind_port and (claim is None or _port_in_use(bind_port)):
            raise OSError("port busy")
        server = create_server(WebAlarmApi(storage_root), host=HOST, port=bind_port,
                               enable_folder_picker=launch.folder_picker, enable_ultra_chat=launch.ultra_chat)
    except OSError:
        if claim is not None:
            claim.release()
        _remove_temp_storage(storage_root)
        url = f"http://{HOST}:{bind_port}/"
        out.write(banner(launch, url, storage_text, colors))
        reuse_storage = default_storage_root() if launch.standard else None
        if self_test is None and _already_running(url, expected_page, reuse_storage) == "same":
            out.write("Этот запуск уже работает (та же версия интерфейса и то же хранилище). Открываю браузер.\n")
            if open_browser:
                opener(url)
            return 0
        out.write("\n" + paint(f"Порт {bind_port} занят другой программой, другой версией или другим режимом "
                               "Web Alarm. Закройте прежнее окно Web Alarm и запустите снова.", 41, colors) + "\n")
        return 3
    server.RequestHandlerClass = _MarkedHandler
    server.web_alarm_launch = launch
    url = f"http://{HOST}:{server.server_port}/"
    set_console_title(("Web Alarm Ultra — " + STANDARD_TEXT) if launch.standard else (f"[ТЕСТ] {launch.name} — " + TEST_TEXT))
    out.write(banner(launch, url, storage_text, colors))
    out.write(f"Версия интерфейса: {page_version(expected_page)}\n")
    out.flush()
    if self_test is not None:
        try:
            return _self_test(server, launch, url, expected_page, storage_text, self_test, out, colors)
        finally:
            if claim is not None:
                claim.release()
            _remove_temp_storage(storage_root)
    _stop_on_break()
    try:
        if not launch.standard:  # the warning stays on screen before any page opens
            for left in range(TEST_WARNING_SECONDS, 0, -1):
                out.write(f"Браузер откроется через {left} с — проверьте, что тестовый режим вам нужен.\n")
                out.flush()
                sleep(1)
        if open_browser:
            opener(url)
        out.write("Сервер работает.\n")
        out.flush()
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if claim is not None:
            claim.release()
        _remove_temp_storage(storage_root)
        out.write("Сервер остановлен.\n")
        out.flush()
    return 0


def _self_test(server, launch: Launch, url: str, expected_page: str, storage: str, target: Path, out: TextIO,
               colors: bool = False) -> int:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    result: dict[str, Any] = {"profile": launch.name, "standard": launch.standard, "kind": launch.kind,
                              "port": server.server_port, "storage_is_default": storage == str(default_storage_root()),
                              "console_colors": colors}
    try:
        status, body = _get(url + "status")
        result["status"] = status
        result["service"] = json.loads(body).get("service")
        page_status, page = _get(url)
        page_text = page.decode("utf-8")
        result["page_status"] = page_status
        result["page_is_current"] = page_text == expected_page
        result["page_marked_as_test"] = TEST_TEXT in page_text
        result["page_unchanged_from_ui"] = page_text == wa_server.INDEX_HTML
        result["page_version"] = page_version(page_text)
        cap_status, cap = _get(url + "ui/ultra-chat/capability")
        result["ultra_chat_available"] = json.loads(cap)["ultra_chat"]["available"]
    except (OSError, ValueError, KeyError) as exc:
        result["error"] = type(exc).__name__
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
    result["stopped"] = not thread.is_alive()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    out.write("Самопроверка завершена, сервер остановлен.\n")
    ok = (result.get("status") == 200 and result.get("page_is_current") and result["stopped"]
          and result.get("page_marked_as_test") == (not launch.standard))
    return 0 if ok else 4


def run_script(launch: Launch, *, out: TextIO, colors: bool, sleep: Callable[[float], None] = time.sleep) -> int:
    set_console_title(f"[ТЕСТ] {launch.name} — " + TEST_TEXT)
    out.write(banner(launch, "-", "-", colors))
    for left in range(TEST_WARNING_SECONDS, 0, -1):
        out.write(f"Тестовый скрипт запустится через {left} с.\n")
        out.flush()
        sleep(1)
    _stop_on_break()
    try:
        return subprocess.call([sys.executable, "-B", "-X", "utf8", launch.script, *launch.args], cwd=REPO)
    except KeyboardInterrupt:
        return 0


def main(argv: list[str] | None = None, out: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(prog="Start_WebAlarm.bat", description="Web Alarm Ultra launcher")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="other launch_config.json (tests)")
    parser.add_argument("--self-test", type=Path, help="start, check over HTTP, stop and write a JSON result")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    out = out or sys.stdout
    colors = enable_colors(out)
    try:
        launch = load_launch(args.config)
    except LaunchConfigError as exc:
        out.write("\n" + paint("ЗАПУСК ОСТАНОВЛЕН: конфигурация запуска не принята", 41, colors) + "\n" + str(exc) + "\n")
        return 2
    if launch.kind == "python_script":
        if args.self_test is not None:
            out.write("Самопроверка для тестового скрипта не поддерживается.\n")
            return 2
        return run_script(launch, out=out, colors=colors)
    return run_web_alarm(launch, out=out, colors=colors, open_browser=not args.no_browser, self_test=args.self_test)


if __name__ == "__main__":
    raise SystemExit(main())
