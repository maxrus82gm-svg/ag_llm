"""Safe double-click launcher for the isolated WA4-O operator UI fixture.

Runs wa4o_ui_demo.py with a new disposable temp directory and random localhost
port. Never points the server at the user's regular Web Alarm storage.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen


def find_chrome() -> Path | None:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    path = shutil.which("chrome.exe")
    if path:
        candidates.append(Path(path))
    return next((p for p in candidates if p.is_file()), None)


def verify_response(url: str) -> None:
    with urlopen(url + "/status", timeout=8) as response:
        status = json.load(response)
    if status.get("service") != "web_alarm_server":
        raise RuntimeError("Unexpected server: Web Alarm signature missing")
    with urlopen(url + "/ui", timeout=8) as response:
        html = response.read().decode("utf-8")
    if "<title>Web Alarm Workspace</title>" not in html:
        raise RuntimeError("Operator panel HTML not served")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true",
                        help="Start server, check loopback endpoints and exit; do not open Chrome")
    args = parser.parse_args(argv)

    directory = Path(tempfile.mkdtemp(prefix="wa4o-review-")).resolve()
    process = None
    try:
        demo = Path(__file__).resolve().with_name("wa4o_ui_demo.py")
        process = subprocess.Popen(
            [sys.executable, "-B", "-u", str(demo), "--root", str(directory), "--port", "0"],
            cwd=demo.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        assert process.stdout is not None
        hello = process.stdout.readline().strip()
        try:
            info = json.loads(hello)
            url = info["url"]
            address = urlsplit(url)
            if (address.scheme != "http" or address.hostname != "127.0.0.1"
                    or not address.port or Path(info["root"]).resolve() != directory):
                raise ValueError("Unexpected fixture URL or storage root")
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError("Demo startup failed: " + hello[:1000]) from exc

        verify_response(url)
        if args.self_test:
            print("WA4-O launcher self-test PASS: local server, UI and disposable storage", flush=True)
            return 0

        print("Web Alarm — isolated review demo", flush=True)
        print("URL: " + url, flush=True)
        print("Disposable storage: " + str(directory), flush=True)
        chrome = find_chrome()
        if chrome is None:
            print("Chrome executable not found. Open the URL manually in Chrome.", flush=True)
        else:
            try:
                subprocess.Popen([str(chrome), "--new-window", url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError as exc:
                print("Could not open Chrome: " + str(exc), flush=True)
                print("Open the URL manually in Chrome.", flush=True)
        print("Leave this window open while reviewing. Press Ctrl+C to stop.", flush=True)
        return process.wait()
    except KeyboardInterrupt:
        print("\nStopping Web Alarm demo...", flush=True)
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print("Demo launcher error: " + str(exc), file=sys.stderr, flush=True)
        return 1
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=8)
            if process.stdout is not None:
                process.stdout.close()
        # directory was created by this launcher; clean only this disposable fixture.
        shutil.rmtree(directory, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
