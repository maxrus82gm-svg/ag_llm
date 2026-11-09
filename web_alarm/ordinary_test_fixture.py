"""Permanent TEST profile bootstrap: existing Ordinary Core bridge, web only.

All data is disposable. No provider, OAuth, Tk or live Workspace is configured.
Enter/EOF or Ctrl+C stops the server and removes only this process's TEMP root.
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true", help="automated offline checks only")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="ordinary_core_TEST_") as directory:
        root = Path(directory).resolve()
        # Install the already reviewed guard even if a caller supplied similarly
        # named environment variables. A missing guard fails before core imports.
        os.environ.update(ORDINARY_GUARD_LOG=str(root / "guard.jsonl"),
                          ORDINARY_GUARD_NETWORK="loopback", ORDINARY_GUARD_ROOT=str(ROOT))
        runpy.run_path(str(ROOT / "reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py"))
        from web_alarm.server import WebAlarmApi, create_server
        from web_alarm.ultra_chat import OrdinaryCoreChatService

        api = WebAlarmApi(root / "registry")
        chat = OrdinaryCoreChatService(api.registry, root)
        server = create_server(api, port=0, offline_chat=chat)
        server.daemon_threads = False
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        try:
            print("TEST OFFLINE · Ordinary Core Chat · только fake transport", flush=True)
            print("Нажмите Enter в окне запуска, чтобы остановить TEST и удалить временные чаты.", flush=True)
            opened = False
            if not args.no_browser:
                import webbrowser
                try:
                    opened = bool(webbrowser.open(url))
                except OSError:
                    pass
                if not opened:
                    print("Браузер не открылся автоматически. Откройте: " + url, flush=True)
            print("ORDINARY_TEST_READY " + json.dumps({"url": url, "root": str(root),
                  "core_bridge": True, "real_available": False,
                  "browser_requested": not args.no_browser, "browser_opened": opened}), flush=True)
            try:
                sys.stdin.readline()
            except KeyboardInterrupt:
                pass
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
    print("ORDINARY_TEST_CLEANED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
