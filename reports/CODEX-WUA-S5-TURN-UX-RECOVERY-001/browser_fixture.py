"""Temporary review driver, not a launcher/profile. Enter shuts down its own disposable fixture."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import threading
from unittest.mock import patch
from uuid import uuid4

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = PACKAGE / ("evidence/browser_final" if "--final" in sys.argv else "evidence/browser")
OUTPUT.mkdir(parents=True, exist_ok=True)
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT), ORDINARY_GUARD_NETWORK="loopback",
                  ORDINARY_GUARD_LOG=str(OUTPUT / "guard.jsonl"))
runpy.run_path(str(ROOT / "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/guard/sitecustomize.py"))
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ultra_chat import OfflineUltraChatService
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory(prefix="s5ux_browser_") as directory:
        root = Path(directory).resolve()
        api = WebAlarmApi(root / "registry")
        service = OfflineUltraChatService(api.registry, root)
        _, workspace = service.create_workspace({"title": "S5_UX_RECOVERY_SYNTHETIC"})
        ws = workspace["wa_workspace_id"]
        a, b = "chat_" + uuid4().hex, "chat_" + uuid4().hex
        service.create_chat(ws, {"chat_id": a, "title": "S5_UX_A", "initialize_workspace": True})
        service.create_chat(ws, {"chat_id": b, "title": "S5_UX_B_NEWEST"})
        server = create_server(api, port=0, offline_chat=service)
        server.daemon_threads = False
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        wires = []
        original = _FixtureTransport.send

        async def delayed(fake, payload, **kwargs):
            wires.append(payload)
            await asyncio.sleep(8 if payload["messages"][-1]["content"].startswith("S5_BROWSER_CANCEL") else 0.8)
            return await original(fake, payload, **kwargs)

        save("session.json", {"url": f"http://127.0.0.1:{server.server_port}/", "workspace_id": ws,
                              "chat_a": a, "chat_b": b, "synthetic_only": True,
                              "ui_sha256": hashlib.sha256((ROOT / "web_alarm/ui.py").read_bytes()).hexdigest()})
        print(f"S5_UX_BROWSER http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            with patch.object(_FixtureTransport, "send", delayed):
                sys.stdin.readline()
                server.shutdown()
                server.server_close()
                worker.join(5)
                for chat in (a, b):
                    save(chat + "_history.json", service.messages(ws, chat, None, 50))
                    save(chat + "_latest.json", service.latest_turn(ws, chat))
                    workspace_root = Path(api.registry.get(ws).workspace_root)
                    for raw in (workspace_root / ".ultra/chats" / chat / "messages").glob("*.json"):
                        (OUTPUT / raw.name).write_bytes(raw.read_bytes())
                save("fake_transport_requests.json", wires)
                print("S5_UX_BROWSER_STOPPED snapshots saved; disposable root cleanup only", flush=True)
        finally:
            if worker.is_alive():
                server.shutdown()
                server.server_close()
                worker.join(5)


if __name__ == "__main__":
    main()
