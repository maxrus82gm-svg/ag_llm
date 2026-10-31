"""Open the stage-2 Ultra Chat (create / rename) on synthetic data only: a new TEMP folder holds the Web Alarm storage
and every Workspace; the real storage, real Workspaces, the network and GigaChat are never used.

Usage (from the repository root, with the project venv):
    python reports/CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001/tools/demo_s2.py [--port 8791] [--base <empty TEMP folder>]
Then open the printed address. With --base the same synthetic storage is reused (a restart check); otherwise a new
TEMP folder is made. Ctrl+C stops the server; the folder is removed unless --base was given.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import context_storage as cs  # noqa: E402
from web_alarm.server import WebAlarmApi, create_server  # noqa: E402


def build(base: Path) -> WebAlarmApi:
    api = WebAlarmApi(base / "web_alarm_storage")
    if api.registry.list():
        return api  # reused storage: nothing is added
    main = base / "demo_main"
    main.mkdir()
    cs.ensure_workspace_storage(main)
    chat = cs.create_chat(main, "Обсуждение проекта")["chat_id"]
    tb = cs.new_task_block_id()
    cs.append_raw_message(main, chat, "user", "Как устроено общее хранение?", task_block_id=tb)
    cs.append_raw_message(main, chat, "assistant", "Один writer ядра для Tk и веба.", task_block_id=tb)
    cs.create_chat(main, "План этапа 2")
    api.registry.register("Демо — общий Workspace", main)
    bare = base / "demo_bare"
    bare.mkdir()
    api.registry.register("Демо — папка без истории", bare)
    return api


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--base")
    args = parser.parse_args()
    keep = bool(args.base)
    base = Path(args.base).resolve() if args.base else Path(tempfile.mkdtemp(prefix="wa_s2_demo_")).resolve()
    base.mkdir(parents=True, exist_ok=True)
    server = create_server(build(base), port=args.port)
    print(f"Ultra Chat stage 2 demo: http://127.0.0.1:{server.server_port}/#chat", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if not keep:
            shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
