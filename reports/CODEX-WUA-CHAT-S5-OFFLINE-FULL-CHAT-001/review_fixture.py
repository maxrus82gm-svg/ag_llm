"""Disposable Stage 5 fixture launched by the existing TEST launcher."""
import argparse
import asyncio
import os
from pathlib import Path
import runpy
import sys
import tempfile
import threading
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--web-smoke", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="stage5_тест_") as directory:
        root = Path(directory).resolve()
        if "ORDINARY_GUARD_LOG" not in os.environ:
            os.environ.update(ORDINARY_GUARD_LOG=str(root / "guard.jsonl"), ORDINARY_GUARD_NETWORK="loopback",
                              ORDINARY_GUARD_ROOT=str(ROOT))
            runpy.run_path(str(PACKAGE / "guard/sitecustomize.py"))
        from web_alarm.server import WebAlarmApi, create_server
        from web_alarm.ultra_chat import OfflineUltraChatService
        from web_alarm.ordinary_chat_test_adapter import _FixtureTransport

        api = WebAlarmApi(root / "registry")
        chat = OfflineUltraChatService(api.registry, root)
        server = create_server(api, port=0, offline_chat=chat)
        server.daemon_threads = False
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        print(f"TEST OFFLINE · http://127.0.0.1:{server.server_address[1]}/", flush=True)
        original = _FixtureTransport.send

        async def visible_attempt(fake, payload, **kwargs):
            await asyncio.sleep(1.5)
            return await original(fake, payload, **kwargs)

        try:
            if args.web_smoke:
                # A test driver controls the fixture lifetime through stdin.
                with patch.object(_FixtureTransport, "send", visible_attempt):
                    sys.stdin.readline()
                return
            from ultra_ui import UltraApp
            with patch.object(_FixtureTransport, "send", visible_attempt):
                app = UltraApp(offline_chat=chat)
                if args.smoke:
                    import http.client
                    app.withdraw()
                    app.update()
                    assert "TEST OFFLINE" in app.title()
                    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                    try:
                        conn.request("GET", "/")
                        reply = conn.getresponse()
                        assert reply.status == 200 and b'data-stage5-offline="true"' in reply.read()
                    finally:
                        conn.close()
                        app.destroy()
                    print("TEST profile smoke: Web and Tk initialized on disposable storage")
                    return

                def close():
                    if app.offline_chat_panel.inflight:
                        app.offline_chat_panel.status.set("TEST · завершается активная операция")
                        app.after(100, close)
                    else:
                        app.destroy()

                app.protocol("WM_DELETE_WINDOW", close)
                app.mainloop()
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == "__main__":
    main()
